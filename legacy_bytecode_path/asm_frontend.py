# epdg/asm_frontend.py
from __future__ import annotations

"""
Assembly frontend that produces ``FuncIR`` objects (E-PDG-like).

This frontend is intentionally lightweight:
- It consumes compiler-produced assembly (Intel syntax recommended for x86).
- It tokenizes + normalizes each instruction into tokens_norm (stable).
- It builds:
  * CFG from basic blocks and jumps
  * DFG/PDG data edges from last-def (def-use) on canonical vars
  * PDG control edges from postdominators (block-level), then mapped to instruction nodes
- It attaches side effects via EffectDB on call targets, then materializes effect resource nodes.

This module depends on:
- epdg.asm_normalize: normalization + read/write extraction
- epdg.control_dependence: control dependence
- epdg.effect_nodes: resource node materialization

这一轮改动：
- 根据 detect_arch 选择 x86 / arm64 的 comment/branch/normalize 分支
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from epdg.ast_pdg_builder import FuncIR, NodeIR
from epdg.effects_loader import EffectDB
from epdg.effect_nodes import materialize_effect_nodes
from .control_dependence import control_dependence_edges
from .asm_normalize import (
    detect_arch,
    strip_comment,
    is_directive,
    parse_label,
    split_operands,
    normalize_instruction,
    extract_reads_writes,
    RegState,
)


@dataclass
class _Block:
    bid: int
    start_i: int   # instruction index inclusive
    end_i: int     # instruction index exclusive


@dataclass
class _MiniCFG:
    blocks: List[Any]
    succ: Dict[int, List[int]]


# x86 jump mnemonics: jxx / jmp
_X86_JMP_RE = re.compile(r"^(j[a-z]+)\b", re.I)

def _is_branch(op: str, arch: str) -> bool:
    ol = op.lower()
    if arch.startswith("arm"):
        # treat these as branches for CFG block splitting
        if ol in {"b", "br"}:
            return True
        if ol.startswith("b.") and ol != "bl" and ol != "blr":
            return True
        if ol in {"cbz","cbnz","tbz","tbnz"}:
            return True
        return False
    return bool(_X86_JMP_RE.match(ol))

def _is_uncond_jmp(op: str, arch: str) -> bool:
    ol = op.lower()
    if arch.startswith("arm"):
        return ol in {"b","br"}
    return ol == "jmp"

def _is_ret(op: str, arch: str) -> bool:
    ol = op.lower()
    if arch.startswith("arm"):
        return ol == "ret"
    return ol in {"ret","retq"}

def _extract_branch_target(operands: List[str], op: str, arch: str) -> Optional[str]:
    if not operands:
        return None
    if arch.startswith("arm"):
        ol = op.lower()
        # b label / b.eq label / br xN (indirect)
        if ol in {"b"} or ol.startswith("b."):
            t = operands[0].strip()
            t = t.split()[0]
            return t if t and not t.startswith(("x","w")) else None
        if ol in {"cbz","cbnz","tbz","tbnz"}:
            # target is last operand
            t = operands[-1].strip()
            t = t.split()[0]
            return t
        return None
    # x86
    t = operands[0].strip()
    t = re.sub(r"\b(qword|dword|word|byte)\b\s*ptr\s*", "", t, flags=re.I).strip()
    t = t.lstrip("*").strip()
    t = t.split()[0]
    return t if t else None


def _match_call_effects(effects_db: EffectDB, call_name: str) -> Dict[str, Any]:
    """Return a dict with reads/writes/flags using EffectDB best-effort matching."""
    name = call_name.strip()
    name = re.sub(r"@PLT.*$", "", name)
    name = name.split("(")[0].strip()
    if not name:
        return {}
    m = effects_db.match(name)
    if m is None:
        default_getter = getattr(effects_db, "default_item", None)
        if callable(default_getter):
            m = default_getter()
    if not m:
        return {}
    return {"reads": list(m.reads), "writes": list(m.writes), "flags": dict(m.flags)}


def _summarize_effects(func: FuncIR) -> None:
    """Populate pdg_eff and effect_signature from NodeIR.effects."""
    func.pdg_eff.clear()
    for n in func.nodes:
        eff = n.effects or {}
        for loc in eff.get("reads", []):
            func.pdg_eff.append((n.nid, loc, "READ"))
        for loc in eff.get("writes", []):
            func.pdg_eff.append((n.nid, loc, "WRITE"))
        for k, v in (eff.get("flags", {}) or {}).items():
            if v:
                func.pdg_eff.append((n.nid, f"FLAG:{k}", "FLAG"))

    sig = {
        "R_STACK": 0, "W_STACK": 0,
        "R_GLOBAL": 0, "W_GLOBAL": 0,
        "R_HEAP": 0, "W_HEAP": 0,
        "FILE_IO": 0, "NET_IO": 0, "DB_IO": 0,
        "ENV": 0, "RNG": 0, "TIME": 0,
    }
    for _, res, tag in func.pdg_eff:
        r = (res or "").upper()
        t = (tag or "").upper()
        if r.startswith("STACK"):
            sig["R_STACK" if t == "READ" else "W_STACK"] += 1
        elif r.startswith("GLOBAL") or r.startswith("MEM_GLOBAL"):
            sig["R_GLOBAL" if t == "READ" else "W_GLOBAL"] += 1
        elif r.startswith("HEAP"):
            sig["R_HEAP" if t == "READ" else "W_HEAP"] += 1
        elif r.startswith("FILE") or r.startswith("FILE_IO"):
            sig["FILE_IO"] += 1
        elif r.startswith("NET"):
            sig["NET_IO"] += 1
        elif r.startswith("DB"):
            sig["DB_IO"] += 1
        elif r.startswith("ENV"):
            sig["ENV"] += 1
        elif r.startswith("RNG"):
            sig["RNG"] += 1
        elif r.startswith("TIME"):
            sig["TIME"] += 1
    func.effect_signature = sig


def build_from_asm_text(file_path: str, asm_text: str, effects_db: EffectDB) -> Tuple[str, List[FuncIR]]:
    """Parse an assembly text into one or more FuncIR objects.

    NOTE: function boundary detection is best-effort; if no function is detected,
    the whole file is treated as a single pseudo-function.
    """
    lines = asm_text.splitlines()
    arch = detect_arch(lines)

    # Pass 1: find function label candidates
    func_labels: Set[str] = set()
    for ln in lines:
        s = strip_comment(ln, arch)
        if not s.strip():
            continue
        if is_directive(s):
            continue
        lab = parse_label(s)
        if lab:
            # ignore local labels like .Ltmp0
            if lab.startswith(".L") or lab.startswith("L") and lab[1:2].isdigit():
                continue
            func_labels.add(lab)

    # pick a function name (first non-local label)
    func_name = None
    for l in func_labels:
        if not l.startswith(".L") and not l.startswith("L"):
            func_name = l
            break
    if func_name is None:
        func_name = "<asm>"

    # Parse instructions (single function skeleton)
    rs = RegState(arch=arch)
    nodes: List[NodeIR] = []
    tokens: List[str] = []

    # label -> instruction index
    label_to_i: Dict[str, int] = {}
    pending_labels: List[str] = []

    nid = 1
    inst_ops: List[Tuple[str, List[str], int]] = []  # (op, operands, nid)

    for i, ln in enumerate(lines, start=1):
        s = strip_comment(ln, arch).strip()
        if not s:
            continue
        if is_directive(s):
            continue
        lab = parse_label(s)
        if lab:
            pending_labels.append(lab)
            continue
        # instruction
        parts = s.split(None, 1)
        op = parts[0]
        ops = parts[1] if len(parts) > 1 else ""
        operands = split_operands(ops) if ops else []

        for lb in pending_labels:
            label_to_i[lb] = len(inst_ops)
        pending_labels = []

        reads, writes, calls = extract_reads_writes(op, operands, rs, arch)
        eff = {}
        if calls:
            eff = _match_call_effects(effects_db, calls[0])

        node = NodeIR(
            nid=nid,
            kind=f"asm::{op.lower()}",
            lineno=i,
            reads=sorted([v for v in reads if v]),
            writes=sorted([v for v in writes if v]),
            calls=calls,
            effects=eff,
        )
        nodes.append(node)
        tokens.append(normalize_instruction(op, operands, rs, arch))
        inst_ops.append((op, operands, nid))
        nid += 1

    ir = FuncIR(
        fid=f"{file_path}::{func_name}",
        name=func_name,
        first_lineno=1,
        nodes=nodes,
        cfg_edges=[],
        pdg_data=[],
        pdg_ctrl=[],
        pdg_eff=[],
        tokens_norm=tokens,
        dfg_edges=[],
        ast_edges=[],
    )

    # Build basic blocks + CFG
    n_inst = len(inst_ops)
    if n_inst == 0:
        _summarize_effects(ir)
        materialize_effect_nodes(ir)
        return "c/asm", [ir]

    # Leaders: 0, any branch target, any instruction after conditional branch, and instruction that has a label
    leaders: Set[int] = {0}
    for lb, idx in label_to_i.items():
        leaders.add(idx)
    branch_targets: Set[int] = set()
    for idx, (op, operands, _nid) in enumerate(inst_ops):
        if _is_branch(op, arch):
            tgt = _extract_branch_target(operands, op, arch)
            if tgt and tgt in label_to_i:
                branch_targets.add(label_to_i[tgt])
            if idx + 1 < n_inst and (not _is_uncond_jmp(op, arch)) and (not _is_ret(op, arch)):
                leaders.add(idx + 1)
    leaders |= branch_targets
    leaders_list = sorted(leaders)

    blocks: List[_Block] = []
    for bi, start in enumerate(leaders_list):
        end = leaders_list[bi + 1] if bi + 1 < len(leaders_list) else n_inst
        blocks.append(_Block(bid=bi, start_i=start, end_i=end))

    # map instruction index -> block id
    inst_to_bid: Dict[int, int] = {}
    for b in blocks:
        for ii in range(b.start_i, b.end_i):
            inst_to_bid[ii] = b.bid

    # build succ at block level
    succ: Dict[int, List[int]] = {b.bid: [] for b in blocks}
    for b in blocks:
        last_i = b.end_i - 1
        op, operands, _nid = inst_ops[last_i]
        if _is_ret(op, arch):
            succ[b.bid] = []
            continue
        if _is_branch(op, arch):
            tgt = _extract_branch_target(operands, op, arch)
            if tgt and tgt in label_to_i:
                succ[b.bid].append(inst_to_bid[label_to_i[tgt]])
            # fallthrough for conditional branches
            if not _is_uncond_jmp(op, arch):
                nb = b.bid + 1
                if nb < len(blocks):
                    succ[b.bid].append(nb)
        else:
            nb = b.bid + 1
            if nb < len(blocks):
                succ[b.bid].append(nb)
        # de-dup
        succ[b.bid] = list(dict.fromkeys(succ[b.bid]))

    # instruction-level CFG edges: within-block sequential + block-to-block edges
    for b in blocks:
        for ii in range(b.start_i, b.end_i - 1):
            ir.cfg_edges.append((inst_ops[ii][2], inst_ops[ii + 1][2]))
    for b in blocks:
        last_nid = inst_ops[b.end_i - 1][2]
        for sb in succ[b.bid]:
            first_nid = inst_ops[blocks[sb].start_i][2]
            ir.cfg_edges.append((last_nid, first_nid))

    # DFG / PDG data edges via last-def
    last_def: Dict[str, int] = {}
    for node in ir.nodes:
        for v in node.reads:
            if v in last_def:
                ir.pdg_data.append((last_def[v], node.nid, v))
                ir.dfg_edges.append((last_def[v], node.nid))
        for v in node.writes:
            last_def[v] = node.nid

    # PDG control edges via postdominators (block level) then map to instruction nodes
    try:
        dummy_blocks = [type("B", (), {"bid": b.bid}) for b in blocks]
        cfg_obj = _MiniCFG(blocks=dummy_blocks, succ=succ)
        cd_edges = control_dependence_edges(cfg_obj)  # (bid, bid, "CTRL_DEP")
        for sbid, tbid, k in cd_edges:
            s_last_i = blocks[sbid].end_i - 1
            s_nid = inst_ops[s_last_i][2]
            t_first_i = blocks[tbid].start_i
            t_nid = inst_ops[t_first_i][2]
            ir.pdg_ctrl.append((s_nid, t_nid, k))
    except Exception:
        pass

    _summarize_effects(ir)
    materialize_effect_nodes(ir)
    return "c/asm", [ir]
