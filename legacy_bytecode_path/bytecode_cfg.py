# epdg/bytecode_cfg.py (enhanced)
"""
Bytecode-level basic blocks and CFG builder (Python 3.11+).
Adds an optional exception sink block for RAISE_VARARGS and RERAISE edges.
"""
import dis
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

JUMP_OPS = {
    "JUMP_FORWARD", "JUMP_BACKWARD", "JUMP_BACKWARD_NO_INTERRUPT",
    "JUMP_IF_FALSE_OR_POP", "JUMP_IF_TRUE_OR_POP",
    "POP_JUMP_IF_FALSE", "POP_JUMP_IF_TRUE",
    "POP_JUMP_FORWARD_IF_FALSE", "POP_JUMP_FORWARD_IF_TRUE",
    "POP_JUMP_BACKWARD_IF_FALSE", "POP_JUMP_BACKWARD_IF_TRUE",
    "FOR_ITER",
}
RET_OPS = {"RETURN_VALUE", "RAISE_VARARGS", "RERAISE"}
EXC_OPS = {"RAISE_VARARGS", "RERAISE"}

@dataclass
class Instr:
    idx: int
    offset: int
    opname: str
    arg: int
    argval: object
    starts_line: int

@dataclass
class BasicBlock:
    bid: int
    start_idx: int
    end_idx: int
    lineno: int
    instrs: List[Instr] = field(default_factory=list)

@dataclass
class CFG:
    blocks: List[BasicBlock]
    succ: Dict[int, List[int]]  # bid -> [bid]
    pred: Dict[int, List[int]]
    exc_sink: int = -1          # optional exception sink block id

def build_cfg(code, add_exception_sink: bool=True) -> CFG:
    bytecode = list(dis.Bytecode(code))
    instrs: List[Instr] = [
        Instr(i, ins.offset, ins.opname, ins.arg or 0, ins.argval, ins.starts_line or -1)
        for i, ins in enumerate(bytecode)
    ]
    n = len(instrs)
    leaders = set([0])
    for i, ins in enumerate(instrs):
        if ins.opname in JUMP_OPS:
            if isinstance(ins.argval, int):
                for j, jins in enumerate(instrs):
                    if jins.offset == ins.argval:
                        leaders.add(j); break
            if i+1 < n and ins.opname not in {"JUMP_FORWARD","JUMP_BACKWARD","JUMP_BACKWARD_NO_INTERRUPT"}:
                leaders.add(i+1)
        if getattr(bytecode[i], "is_jump_target", False):
            leaders.add(i)
        if ins.opname in RET_OPS and i+1 < n:
            leaders.add(i+1)
    order = sorted(leaders)
    if order[-1] != n: order.append(n)
    blocks: List[BasicBlock] = []
    bid_of_idx = {}
    for k in range(len(order)-1):
        s, e = order[k], order[k+1]
        b = BasicBlock(bid=len(blocks), start_idx=s, end_idx=e-1,
                       lineno=instrs[s].starts_line if instrs[s].starts_line!=-1 else (instrs[s].starts_line))
        b.instrs = instrs[s:e]
        blocks.append(b)
        for i in range(s, e):
            bid_of_idx[i] = b.bid
    succ = {b.bid: [] for b in blocks}
    pred = {b.bid: [] for b in blocks}

    # Optional exception sink
    exc_sink = -1
    if add_exception_sink:
        exc_sink = len(blocks)
        blocks.append(BasicBlock(bid=exc_sink, start_idx=n, end_idx=n, lineno=-1, instrs=[]))
        succ[exc_sink] = []
        pred[exc_sink] = []

    for b in blocks:
        if b.bid == exc_sink: 
            continue
        last = b.instrs[-1] if b.instrs else None
        def target_bid(ins: Instr):
            if isinstance(ins.argval, int):
                for j, jins in enumerate(instrs):
                    if jins.offset == ins.argval:
                        return bid_of_idx.get(j, None)
            return None
        if last:
            if last.opname in {"JUMP_FORWARD","JUMP_BACKWARD","JUMP_BACKWARD_NO_INTERRUPT"}:
                tb = target_bid(last)
                if tb is not None: succ[b.bid].append(tb); pred[tb].append(b.bid)
            elif last.opname in {"POP_JUMP_IF_FALSE","POP_JUMP_IF_TRUE",
                                 "POP_JUMP_FORWARD_IF_FALSE","POP_JUMP_FORWARD_IF_TRUE",
                                 "POP_JUMP_BACKWARD_IF_FALSE","POP_JUMP_BACKWARD_IF_TRUE",
                                 "JUMP_IF_FALSE_OR_POP","JUMP_IF_TRUE_OR_POP","FOR_ITER"}:
                tb = target_bid(last)
                if tb is not None: succ[b.bid].append(tb); pred[tb].append(b.bid)
                nb = b.bid+1
                if nb < len(blocks)-(1 if exc_sink!=-1 else 0): succ[b.bid].append(nb); pred[nb].append(b.bid)
            elif last.opname in EXC_OPS and exc_sink!=-1:
                succ[b.bid].append(exc_sink); pred[exc_sink].append(b.bid)
            elif last.opname == "RETURN_VALUE":
                pass
            else:
                nb = b.bid+1
                if nb < len(blocks)-(1 if exc_sink!=-1 else 0): succ[b.bid].append(nb); pred[nb].append(b.bid)
    return CFG(blocks=blocks, succ=succ, pred=pred, exc_sink=exc_sink)
