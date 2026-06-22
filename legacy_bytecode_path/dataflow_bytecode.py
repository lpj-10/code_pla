# epdg/dataflow_bytecode.py
from typing import List, Dict, Tuple
from .bytecode_cfg import CFG, BasicBlock

READ_OPS = {"LOAD_FAST","LOAD_GLOBAL","LOAD_DEREF","LOAD_NAME"}
WRITE_OPS = {"STORE_FAST","STORE_GLOBAL","STORE_DEREF","STORE_NAME"}
ATTR_OP = "LOAD_ATTR"
CALL_OPS = {"PRECALL","CALL"}

def block_rw_calls(block: BasicBlock):
    reads, writes, calls = set(), set(), []
    name_stack = None
    for ins in block.instrs:
        op = ins.opname
        if op in READ_OPS and isinstance(ins.argval, str):
            reads.add(ins.argval)
            name_stack = ins.argval
        elif op == ATTR_OP and isinstance(ins.argval, str):
            if name_stack:
                name_stack = f"{name_stack}.{ins.argval}"
        elif op in WRITE_OPS and isinstance(ins.argval, str):
            writes.add(ins.argval)
        elif op in CALL_OPS:
            if name_stack:
                calls.append(name_stack)
            name_stack = None
        else:
            pass
    return sorted(reads), sorted(writes), calls

def pdg_data_edges(blocks: List[BasicBlock], rw_map: Dict[int, Tuple[List[str],List[str],List[str]]]):
    edges = []
    last_def: Dict[str,int] = {}
    for b in blocks:
        reads, writes, _ = rw_map[b.bid]
        for r in reads:
            if r in last_def:
                edges.append((last_def[r], b.bid, r))
        for w in writes:
            last_def[w] = b.bid
    return edges
