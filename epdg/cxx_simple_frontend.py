
# epdg/cxx_simple_frontend.py
from __future__ import annotations

"""C / C++ frontend that produces lightweight E‑PDG style ``FuncIR`` objects.

相对于最早期的占位版本，这一实现真正把 C / C++ 的 ``effect_signature``
接到了 :mod:`epdg.effects_loader.EffectDB` 上：

* **优先** 使用 ``clang -S -emit-llvm`` 生成 LLVM IR，把每条指令当作一个
  ``NodeIR``，指令序列作为 `tokens_norm`；
* 在 IR 层用正则抽取调用目标（例如 ``@printf``），并通过 ``EffectDB.match``
  映射到抽象资源（FILE / NET / RNG / TIME 等）和副作用 flag；
* 如果本机没有 clang 或编译失败，则退回到简单的**源码级近似**：每一行
  变成一个 ``NodeIR``，用正则找出看起来像函数调用的名字（例如 ``printf``、
  ``send``、``recv``、``rand`` 等）再接到同一套 effect summaries；
* 最后对每个 ``FuncIR`` 聚合为统一的 ``effect_signature``，字段布局与
  Python 前端保持一致，便于下游检索与排序代码直接复用。
"""

import re
import shutil
import subprocess
import shlex
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

from .ast_pdg_builder import FuncIR, NodeIR
from .effects_loader import EffectDB
from .effect_nodes import materialize_effect_nodes
_C_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_C_NUMBER = re.compile(r"^[0-9]+(u|U|l|L|ul|UL)?$")
_C_LINE_COMMENT = re.compile(r"//.*$")
_C_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)

# LLVM IR: 可选的 opcode / call 解析
_LLVM_INSTR_RE = re.compile(
    r"^\s*(?:[%@][^\s=]+\s*=\s*)?(?P<op>[a-z][a-z0-9_.]*)\b"
)
_LLVM_CALL_RE = re.compile(
    r"@(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)


def _strip_comments(src: str) -> str:
    src = _C_BLOCK_COMMENT.sub(" ", src)
    src = _C_LINE_COMMENT.sub("", src)
    return src


def _tokenize_source(src: str) -> List[str]:
    """非常轻量级的 C/C++ 词法归一化，用于 tokens_norm。

    这里只做三件事：

    * 去掉注释；
    * 把整数字面量折叠成 ``<NUM>``；
    * 其它 token 原样保留（包括运算符和括号），便于做简单的 n‑gram/Jaccard。
    """
    src = _strip_comments(src)
    tokens: List[str] = []
    pattern = r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|==|!=|<=|>=|->|::|&&|\|\||[{}();,<>+\-*/%=]"
    for tok in re.findall(pattern, src):
        if _C_NUMBER.match(tok):
            tokens.append("<NUM>")
        elif _C_IDENT.match(tok):
            tokens.append(tok)
        else:
            tokens.append(tok)
    return tokens


def _extract_calls_from_source_line(line: str) -> List[str]:
    """从源码行中抽取「看起来像函数调用」的标识符。

    规则很保守，只抓形如 ``foo(...)`` 的模式，同时过滤掉常见关键字。
    对于 ``std::rand(x)`` 等形式，我们依赖 ``rand(`` 这一部分同样能被识别。
    """
    # 去掉行内注释，避免在注释里误报
    line = _C_LINE_COMMENT.sub("", line)
    # 简单抹掉字符串/字符字面量，减少噪音
    line = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '"STR"', line)
    line = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "'CHR'", line)

    calls: List[str] = []
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", line):
        name = m.group(1)
        if name in {"if", "for", "while", "switch", "return", "sizeof"}:
            continue
        calls.append(name)
    return calls


def _apply_effects_for_calls(call_names: List[str], effects_db: EffectDB) -> Dict[str, Any]:
    """根据 effect_summaries.yaml，为一批调用聚合副作用信息。

    返回形如 ``{"reads": [...], "writes": [...], "flags": {...}}`` 的字典，
    便于直接挂到 ``NodeIR.effects``。
    """
    reads: List[str] = []
    writes: List[str] = []
    flags: Dict[str, bool] = {}

    default_getter = getattr(effects_db, "default_item", None)

    for fq in call_names:
        item = effects_db.match(fq)
        if item is None and callable(default_getter):
            item = default_getter()
        if item is None:
            continue
        reads.extend(item.reads)
        writes.extend(item.writes)
        for k, v in item.flags.items():
            if v:
                flags[k] = True

    if not (reads or writes or flags):
        return {}
    return {"reads": reads, "writes": writes, "flags": flags}


def _finalise_effect_signature(ir: FuncIR) -> None:
    """把 ``NodeIR.effects`` 聚合成统一的 ``effect_signature``。"""
    ir.pdg_eff.clear()
    for n in ir.nodes:
        eff = n.effects or {}
        for loc in eff.get("reads", []):
            ir.pdg_eff.append((n.nid, loc, "READ"))
        for loc in eff.get("writes", []):
            ir.pdg_eff.append((n.nid, loc, "WRITE"))
        for k, v in eff.get("flags", {}).items():
            if v:
                ir.pdg_eff.append((n.nid, f"FLAG:{k}", "FLAG"))

    sig = {
        "R_STACK": 0,
        "W_STACK": 0,
        "R_GLOBAL": 0,
        "W_GLOBAL": 0,
        "R_HEAP": 0,
        "W_HEAP": 0,
        "FILE_IO": 0,
        "NET_IO": 0,
        "DB_IO": 0,
        "ENV": 0,
        "RNG": 0,
        "TIME": 0,
        "EXC": 0,
    }
    flags = set()

    for _, res, tag in ir.pdg_eff:
        if res.startswith("FILE"):
            sig["FILE_IO"] += 1
        if res.startswith("NET"):
            sig["NET_IO"] += 1
        if res.startswith("DB"):
            sig["DB_IO"] += 1
        if res.startswith("ENV"):
            sig["ENV"] += 1
        if res.startswith("RNG"):
            sig["RNG"] += 1
        if res.startswith("TIME"):
            sig["TIME"] += 1
        if res.startswith("EXC") or res.startswith("FLAG:exception"):
            sig["EXC"] += 1

        if res.startswith("STACK"):
            key = "R_STACK" if tag == "READ" else "W_STACK"
            sig[key] += 1
        if res.startswith("GLOBAL"):
            key = "R_GLOBAL" if tag == "READ" else "W_GLOBAL"
            sig[key] += 1
        if res.startswith("HEAP"):
            key = "R_HEAP" if tag == "READ" else "W_HEAP"
            sig[key] += 1

        if res.startswith("FLAG:"):
            flags.add(res[5:])

    ir.effect_signature = {"counts": sig, "flags": sorted(flags)}


def _build_from_source(path: Path, effects_db: EffectDB) -> Tuple[str, List[FuncIR]]:
    """简单的 C/C++ 源码级前端。

    * 整个文件视作一个 pseudo‑function；
    * 每一行是一个 ``NodeIR``；
    * ``tokens_norm`` 是全文件 token 序列；
    * 调用名通过正则抽取后接到 ``effect_summaries.yaml``。
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin1")

    lines = text.splitlines() or [""]
    tokens = _tokenize_source(text)

    fid = f"{path}::<file>@1"
    ir = FuncIR(fid=fid, name="<file>", first_lineno=1)

    for i, line in enumerate(lines):
        nid = len(ir.nodes) + 1
        node = NodeIR(nid=nid, kind="Line", lineno=i + 1)
        calls = _extract_calls_from_source_line(line)
        node.calls = calls
        eff = _apply_effects_for_calls(calls, effects_db)
        if eff:
            node.effects = eff
        ir.nodes.append(node)


    # AST view for C/C++ source: approximate brace-based block tree.
    # We connect each statement inside the innermost open '{...}' block
    # as a child of the line where that block started.
    lineno_to_node = {n.lineno: n for n in ir.nodes}
    ast_edges: List[Tuple[int, int]] = []
    block_stack: List[int] = []  # stack of lineno that opened current blocks

    for lineno, line in enumerate(lines, start=1):
        node = lineno_to_node.get(lineno)
        # If we are inside any block, connect current node as child of innermost parent.
        if node is not None and block_stack:
            parent_lineno = block_stack[-1]
            parent = lineno_to_node.get(parent_lineno)
            if parent is not None and parent.nid != node.nid:
                ast_edges.append((parent.nid, node.nid))

        # Count braces on this line to maintain block stack.
        open_braces = line.count("{")
        close_braces = line.count("}")

        # For each opening brace, push current line as a new block root.
        for _ in range(open_braces):
            block_stack.append(lineno)

        # For each closing brace, pop one block if any.
        for _ in range(close_braces):
            if block_stack:
                block_stack.pop()

    ir.ast_edges = ast_edges


    # 线性 CFG
    for a, b in zip(ir.nodes, ir.nodes[1:]):
        ir.cfg_edges.append((a.nid, b.nid))

    _finalise_effect_signature(ir)
    ir.tokens_norm = tokens
    return "c/source", [ir]


def _choose_clang(path: Path) -> str | None:
    """根据扩展名选择 clang 或 clang++，若都不存在则返回 None。"""
    exts_cpp = {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
    compiler = "clang++" if path.suffix.lower() in exts_cpp else "clang"
    if shutil.which(compiler):
        return compiler
    other = "clang++" if compiler == "clang" else "clang"
    if shutil.which(other):
        return other
    return None


def _build_from_llvm_ir(
    path: Path,
    effects_db: EffectDB,
    *,
    cxx_opt: str = "1",
    cxx_target: str = "",
    cxx_extra_flags: str = "",
) -> Tuple[str, List[FuncIR]]:
    """LLVM IR‑first 的 C/C++ 前端（可控 clang flags）。

    这一轮补齐参数贯通：
    - cxx_opt: clang -O{level}，用于控制 IR/asm 的稳定性与语义信息量
    - cxx_target: clang -target <triple>，用于跨架构对齐
    - cxx_extra_flags: 追加额外编译参数（shlex split）
    """
    compiler = _choose_clang(path)
    if not compiler:
        raise RuntimeError("clang / clang++ not found on PATH")

    cmd: List[str] = [compiler, "-S", "-emit-llvm", "-g", "-o", "-"]

    # opt level
    if cxx_opt:
        opt = str(cxx_opt).strip()
        if not opt.startswith("-O"):
            opt = f"-O{opt}"
        cmd.append(opt)

    # target triple
    if cxx_target:
        cmd += ["-target", str(cxx_target).strip()]

    # extra flags (append last so user can override)
    if cxx_extra_flags:
        cmd += shlex.split(cxx_extra_flags)

    cmd.append(str(path))

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{compiler} failed for {path}: {proc.stderr.strip()}")  # pragma: no cover

    ir_text = proc.stdout.splitlines()

    fid = f"{path}::<tu>"
    ir = FuncIR(
        fid=fid,
        name=path.name,
        first_lineno=1,
        nodes=[],
        cfg_edges=[],
        pdg_data=[],
        pdg_ctrl=[],
        pdg_eff=[],
        tokens_norm=[],
        dfg_edges=[],
        ast_edges=[],
    )

    nid = 1
    for ln, raw in enumerate(ir_text, start=1):
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        m = _LLVM_INSTR_RE.match(s)
        if not m:
            continue
        op = m.group("op")
        calls: List[str] = []
        eff: Dict[str, Any] = {}

        if op == "call":
            cm = _LLVM_CALL_RE.search(s)
            if cm:
                name = cm.group("name")
                calls = [name]
                hit = effects_db.match(name)
                if hit is not None:
                    eff = {"reads": list(hit.reads), "writes": list(hit.writes), "flags": dict(hit.flags)}

        node = NodeIR(
            nid=nid,
            kind=f"llvm::{op}",
            lineno=ln,
            reads=[],
            writes=[],
            calls=calls,
            effects=eff,
        )
        ir.nodes.append(node)
        nid += 1

    # tokens_norm
    ir.tokens_norm = [n.kind for n in ir.nodes]

    # effect aggregation + resource nodes
    materialize_effect_nodes(ir)

    return "c/llvm_ir", [ir]


def _build_from_asm(
    path: Path,
    effects_db: EffectDB,
    *,
    cxx_opt: str = "1",
    cxx_target: str = "",
    cxx_extra_flags: str = "",
) -> Tuple[str, List[FuncIR]]:
    """Assembly-first C/C++ frontend.

    This compiles the translation unit to assembly and then parses it with
    :mod:`epdg.asm_frontend`.

    参数贯通：
    - cxx_opt -> clang -O{level}
    - cxx_target -> clang -target <triple>
    - cxx_extra_flags -> append to clang

    NOTE: For x86 targets, we request Intel syntax (-masm=intel). For ARM targets,
    we do not set -masm and let clang emit the native syntax.
    """
    compiler = _choose_clang(path)
    if compiler is None:
        raise RuntimeError("clang/clang++ not found in PATH")

    tmp_s = path.with_suffix(path.suffix + ".tmp.s")

    cmd: List[str] = [compiler, "-S"]

    # opt level
    if cxx_opt:
        opt = str(cxx_opt).strip()
        if not opt.startswith("-O"):
            opt = f"-O{opt}"
        cmd.append(opt)

    # target triple
    tgt = (cxx_target or "").strip()
    if tgt:
        cmd += ["-target", tgt]

    # Intel syntax only for x86-like targets
    is_arm = False
    t_lower = tgt.lower()
    if "aarch64" in t_lower or t_lower.startswith("arm"):
        is_arm = True
    # if target not specified, assume host; still safe to keep intel on most hosts
    if not is_arm:
        cmd.append("-masm=intel")

    # reduce noise
    cmd += [
        "-fno-asynchronous-unwind-tables",
        "-fno-unwind-tables",
    ]

    # extra flags (append last so user can override)
    if cxx_extra_flags:
        cmd += shlex.split(cxx_extra_flags)

    cmd += [str(path), "-o", str(tmp_s)]

    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    asm_text = tmp_s.read_text(encoding="utf-8", errors="ignore")
    try:
        tmp_s.unlink(missing_ok=True)
    except Exception:
        pass

    from .asm_frontend import build_from_asm_text  # lazy: only needed for asm backend
    return build_from_asm_text(str(path), asm_text, effects_db)


def build_for_cxx_file(
    path: Path,
    effects_db: EffectDB,
    *,
    backend: str = "auto",
    prefer_ir: bool = True,
    cxx_opt: str = "1",
    cxx_target: str = "",
    cxx_extra_flags: str = "",
) -> Tuple[str, List[FuncIR]]:
    """公开入口，供 :mod:`scripts.build_epdg` 使用。

    backend:
      - auto: prefer llvm ir first (if prefer_ir), else asm, else source fallback
      - llvm: force LLVM IR
      - asm: force Assembly
      - source: simple source fallback

    参数贯通：cxx_opt / cxx_target / cxx_extra_flags 会传入 clang 调用。
    """
    b = (backend or "auto").lower()

    if b == "llvm":
        return _build_from_llvm_ir(
            path, effects_db, cxx_opt=cxx_opt, cxx_target=cxx_target, cxx_extra_flags=cxx_extra_flags
        )
    if b == "asm":
        return _build_from_asm(
            path, effects_db, cxx_opt=cxx_opt, cxx_target=cxx_target, cxx_extra_flags=cxx_extra_flags
        )
    if b == "source":
        return _build_from_source(path, effects_db)

    # auto
    if prefer_ir:
        try:
            return _build_from_llvm_ir(
                path, effects_db, cxx_opt=cxx_opt, cxx_target=cxx_target, cxx_extra_flags=cxx_extra_flags
            )
        except Exception:
            pass
    try:
        return _build_from_asm(
            path, effects_db, cxx_opt=cxx_opt, cxx_target=cxx_target, cxx_extra_flags=cxx_extra_flags
        )
    except Exception:
        return _build_from_source(path, effects_db)

