
# epdg/java_simple_frontend.py
from __future__ import annotations

"""Java 前端：基于 bytecode 的 IR‑first + 源码回退，并接入 effect_summaries.yaml。

核心目标有两点：

1. 在 JVM 字节码层识别诸如 ``java.io.PrintStream.println``、
   ``java.net.Socket.getInputStream``、``java.util.Random.nextInt`` 等调用，
   并通过 :class:`EffectDB` 映射到统一的抽象资源与副作用；
2. 即使环境中没有 ``javac`` / ``javap``，也能退回到简单的源码级近似，
   至少保证诸如 ``System.out.println`` 这类典型调用能被识别出来。

最终每个 Java 源文件会被视作一个 pseudo‑function，其 ``effect_signature``
字段与 Python / C 前端保持完全一致，便于下游检索与评分直接复用。
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict, Any

from .ast_pdg_builder import FuncIR, NodeIR
from .effects_loader import EffectDB


_JAVA_LINE_COMMENT = re.compile(r"//.*$")
_JAVA_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)

# javap -c 反汇编行：
#    0: invokevirtual #4                  // Method java/io/PrintStream.println:(Ljava/lang/String;)V
_JVM_INSTR_RE = re.compile(r"^\s*[0-9]+:\s+(?P<op>[a-z_][a-z0-9_]*)\b")
_JVM_INVOKE_RE = re.compile(
    r"//\s*Method\s+([A-Za-z0-9_/$]+)/([A-Za-z0-9_$<>]+):"
)


def _strip_comments(src: str) -> str:
    src = _JAVA_BLOCK_COMMENT.sub(" ", src)
    src = _JAVA_LINE_COMMENT.sub("", src)
    return src


def _tokenize_source(src: str) -> List[str]:
    """非常轻量的 Java 词法归一化，用于 tokens_norm。"""
    src = _strip_comments(src)
    tokens: List[str] = []
    pattern = r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|==|!=|<=|>=|&&|\|\||[{}();,<>+\-*/%=]"
    for tok in re.findall(pattern, src):
        if tok.isdigit():
            tokens.append("<NUM>")
        else:
            tokens.append(tok)
    return tokens



def _extract_calls_from_source_line(line: str) -> List[str]:
    """从 Java 源码行里抽取可能的调用名称。

    为了跟 effect_summaries.yaml 对齐，这里加入了几条启发式规则：

    * 如果行中出现 ``System.out.println(``，直接输出 ``System.out.println``；
    * 如果出现 ``new Random(`` 或 `` Random ``，则视为使用 java.util.Random，
      直接映射到 ``java.util.Random.nextInt`` 这一代表性调用；
    * 如果出现 ``Math.random(``，则映射到 ``java.lang.Math.random``；
    * 其余调用只做简单的 ``foo(...)`` 检测，主要用于兜底。
    """
    line = _JAVA_LINE_COMMENT.sub("", line)
    # 抹掉字符串字面量，减少噪音
    line = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '"STR"', line)

    calls: List[str] = []

    if "System.out.println" in line:
        calls.append("System.out.println")

    # 识别 Random / RNG 使用
    if "new Random" in line or " Random " in line:
        calls.append("java.util.Random.nextInt")

    # 识别 Math.random
    if "Math.random" in line:
        calls.append("java.lang.Math.random")

    # 通用 foo(...) 检测（主要用于其它库调用的兜底）
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_\.]*)\s*\(", line):
        name = m.group(1)
        if name in {"if", "for", "while", "switch", "return", "catch", "new"}:
            continue
        calls.append(name)

    # 去重并保持顺序
    seen = set()
    uniq: List[str] = []
    for c in calls:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _apply_effects_for_calls(call_names: List[str], effects_db: EffectDB) -> Dict[str, Any]:
    """与 C 前端共享的副作用聚合逻辑。"""
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
    """不依赖 javac 的 Java 源码级兜底前端。"""
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


    # AST view for Java source: approximate brace-based block tree.
    # We connect each statement inside the innermost open '{...}' block
    # as a child of the line where that block started.
    lineno_to_node = {n.lineno: n for n in ir.nodes}
    ast_edges: List[Tuple[int, int]] = []
    block_stack: List[int] = []  # stack of lineno that opened current blocks

    for lineno, line in enumerate(lines, start=1):
        node = lineno_to_node.get(lineno)
        if node is not None and block_stack:
            parent_lineno = block_stack[-1]
            parent = lineno_to_node.get(parent_lineno)
            if parent is not None and parent.nid != node.nid:
                ast_edges.append((parent.nid, node.nid))

        open_braces = line.count("{")
        close_braces = line.count("}")

        for _ in range(open_braces):
            block_stack.append(lineno)
        for _ in range(close_braces):
            if block_stack:
                block_stack.pop()

    ir.ast_edges = ast_edges

    for a, b in zip(ir.nodes, ir.nodes[1:]):
        ir.cfg_edges.append((a.nid, b.nid))

    _finalise_effect_signature(ir)
    ir.tokens_norm = tokens
    return "java/source", [ir]


def _have_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _build_from_bytecode(path: Path, effects_db: EffectDB) -> Tuple[str, List[FuncIR]]:
    """基于 javac + javap 的 IR‑first Java 前端。"""
    if not (_have_tool("javac") and _have_tool("javap")):
        raise RuntimeError("javac / javap not found on PATH")

    with tempfile.TemporaryDirectory(prefix="epdg_java_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        # 编译到临时目录
        cmd = ["javac", "-g", "-d", str(tmpdir), str(path)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"javac failed for {path}: {proc.stderr.strip()}")  # pragma: no cover

        # 对所有 *.class 文件做 javap -c
        class_files = list(tmpdir.rglob("*.class"))
        if not class_files:
            raise RuntimeError(f"no .class files produced for {path}")  # pragma: no cover

        # 我们仍然把整个翻译单元视作一个 pseudo‑function，只是 tokens 和调用来自所有方法
        fid = f"{path}::<bytecode>@1"
        ir = FuncIR(fid=fid, name="<bytecode>", first_lineno=1)

        lineno = 1
        for cf in class_files:
            rel = cf.relative_to(tmpdir)
            class_name = ".".join(rel.with_suffix("").parts)
            cmd_jp = ["javap", "-classpath", str(tmpdir), "-c", class_name]
            proc_jp = subprocess.run(
                cmd_jp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if proc_jp.returncode != 0:
                # 尽量继续处理其他类
                print(f"[WARN] javap failed for {class_name}: {proc_jp.stderr.strip()}", file=sys.stderr)
                continue

            for line in proc_jp.stdout.splitlines():
                m = _JVM_INSTR_RE.match(line)
                if not m:
                    continue
                op = m.group("op")
                nid = len(ir.nodes) + 1
                node = NodeIR(nid=nid, kind=f"jvm::{op}", lineno=lineno)
                lineno += 1

                calls: List[str] = []
                m_call = _JVM_INVOKE_RE.search(line)
                if m_call:
                    owner_slash, method = m_call.group(1), m_call.group(2)
                    owner = owner_slash.replace("/", ".")
                    fqname = f"{owner}.{method}"
                    calls.append(fqname)

                node.calls = calls
                eff = _apply_effects_for_calls(calls, effects_db)
                if eff:
                    node.effects = eff
                ir.nodes.append(node)

        for a, b in zip(ir.nodes, ir.nodes[1:]):
            ir.cfg_edges.append((a.nid, b.nid))

        # For Java bytecode view, reuse linear CFG as a simple AST backbone.
        ir.ast_edges = list(ir.cfg_edges)

        _finalise_effect_signature(ir)
        ir.tokens_norm = [n.kind for n in ir.nodes]
        return "java/bytecode", [ir]


def build_for_java_file(path: Path, effects_db: EffectDB, prefer_bytecode: bool = True) -> Tuple[str, List[FuncIR]]:
    """公开入口，供 :mod:`scripts.build_epdg` 调用。

    * 默认使用 javac + javap 的字节码路径；
    * 失败时自动回退到源码级前端；
    * 两种路径都会把调用名称接到 ``effect_summaries.yaml``，例如：
      ``System.out.println``、``java.io.PrintStream.println``,
      ``java.net.Socket.getInputStream``, ``java.util.Random.nextInt`` 等。
    """
    if prefer_bytecode:
        try:
            return _build_from_bytecode(path, effects_db)
        except Exception as exc:  # pragma: no cover - best effort fallback
            print(f"[WARN] Java bytecode frontend failed for {path}: {exc}", file=sys.stderr)
    return _build_from_source(path, effects_db)
