# epdg/dataflow_ssa.py
"""
Forward dataflow with abstract stack to build def-use edges at bytecode level.
- Models locals/globals by name
- Models value stack with virtual temporaries v0,v1,... and propagates across blocks via CFG
- Produces:
    * var_defs: name -> set(block_id) that may define it
    * var_uses: name -> set(block_id) that may read it
    * defuse_edges: (def_bid -> use_bid, name or vN)
Limitations: simplified join (union), ignores types, approximates call stack effects.
"""
import dis
from typing import Dict, List, Tuple, Set, Optional
from .bytecode_cfg import CFG, BasicBlock

READ_OPS = {"LOAD_FAST","LOAD_GLOBAL","LOAD_DEREF","LOAD_NAME"}
WRITE_OPS = {"STORE_FAST","STORE_GLOBAL","STORE_DEREF","STORE_NAME"}
PUSH_OPS = {"LOAD_CONST","BUILD_LIST","BUILD_TUPLE","BUILD_SET","BUILD_MAP"}

class FrameState:
    def __init__(self, stack: Optional[List[str]]=None, defs: Optional[Dict[str, Set[int]]]=None):
        self.stack = list(stack) if stack is not None else []
        self.defs = {k:set(v) for k,v in (defs.items() if defs else [])}

    def copy(self):
        return FrameState(self.stack, self.defs)

def simulate_block(b: BasicBlock, in_state: FrameState, next_vid: int) -> Tuple[FrameState, List[Tuple[int,str,str]], int]:
    """
    Returns (out_state, local_defuse_edges, next_vid)
    defuse_edges contain tuples (src_def_bid, dst_use_bid, key) where key is name or vN.
    """
    state = in_state.copy()
    edges: List[Tuple[int,str,str]] = []
    for ins in b.instrs:
        op = ins.opname
        # approximate stack effect
        try:
            popc = dis.stack_effect(dis.opmap.get(op, 0), ins.arg or 0, jump=False)
        except Exception:
            popc = 0
        if popc < 0:
            # pop values
            for _ in range(abs(popc)):
                if state.stack:
                    state.stack.pop()
        # handle loads/stores
        if op in READ_OPS and isinstance(ins.argval, str):
            name = ins.argval
            # record use edges from reaching defs
            for src in state.defs.get(name, set()):
                edges.append((src, b.bid, name))
            # push a virtual representing this value
            state.stack.append(f"v{next_vid}"); next_vid += 1
        elif op in WRITE_OPS and isinstance(ins.argval, str):
            name = ins.argval
            # a store consumes stack top; we mark this block as def
            state.defs.setdefault(name, set()).add(b.bid)
        elif op in PUSH_OPS:
            state.stack.append(f"v{next_vid}"); next_vid += 1
        elif op in {"CALL","PRECALL"}:
            # calls consume args (unknown); to be conservative, clear some stack
            if state.stack:
                state.stack.pop()
            # push a result
            state.stack.append(f"v{next_vid}"); next_vid += 1
        # handle pushes from positive stack effect (already pushed by loads/builds etc.)
        # ignore attr ops here
    return state, edges, next_vid

def join_states(a: FrameState, b: FrameState) -> FrameState:
    # union of defs; drop stack (unsound across joins), keep empty stack
    defs: Dict[str, Set[int]] = {}
    for m in (a.defs, b.defs):
        for k,v in m.items():
            defs.setdefault(k, set()).update(v)
    return FrameState(stack=[], defs=defs)

def forward_dataflow(cfg: CFG) -> Tuple[Dict[str, Set[int]], Dict[str, Set[int]], List[Tuple[int,int,str]]]:
    """
    Returns var_defs, var_uses, defuse_edges (def_bid -> use_bid, key)
    """
    in_states: Dict[int, FrameState] = {}
    out_states: Dict[int, FrameState] = {}
    local_edges: List[Tuple[int,int,str]] = []  # collect per block

    # init all in-states empty
    for b in cfg.blocks:
        in_states[b.bid] = FrameState()
        out_states[b.bid] = FrameState()

    # worklist with iteration bound to guarantee termination.
    # The original code could diverge because simulate_block creates fresh
    # virtual variable names (v0, v1, ...) on every invocation, making the
    # stack comparison always fail on loops.  We now:
    #   1) compare only *defs* (not stack) for convergence, and
    #   2) enforce a hard iteration limit as a safety net.
    work = [b.bid for b in cfg.blocks]
    next_vid = 0
    max_iters = len(cfg.blocks) ** 2 + len(cfg.blocks) + 1
    iters = 0
    while work and iters < max_iters:
        iters += 1
        bid = work.pop(0)
        b = cfg.blocks[bid]
        # in-state = join of predecessors
        preds = cfg.pred.get(bid, [])
        inst = FrameState()
        for p in preds:
            inst = join_states(inst, out_states[p])
        out, edges, next_vid = simulate_block(b, inst, next_vid)
        local_edges.extend([(src, b.bid, key) for (src, _, key) in edges])
        # Convergence check: only compare defs (stack contains ephemeral
        # virtual names that grow monotonically and would never stabilise).
        if out.defs != out_states[bid].defs:
            out_states[bid] = out
            for s in cfg.succ.get(bid, []):
                if s not in work:
                    work.append(s)

    # collect var_defs/uses
    var_defs: Dict[str, Set[int]] = {}
    var_uses: Dict[str, Set[int]] = {}
    for b in cfg.blocks:
        defs = out_states[b.bid].defs
        for name, srcs in defs.items():
            var_defs.setdefault(name, set()).update(srcs)
    for _, ubid, key in local_edges:
        if not key.startswith("v"):
            var_uses.setdefault(key, set()).add(ubid)
    # def-use: de-dup
    defuse = list({(src, dst, key) for (src, dst, key) in local_edges})
    return var_defs, var_uses, defuse
