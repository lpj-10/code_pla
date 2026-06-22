# epdg/control_dependence.py
from typing import Dict, List, Set, Tuple
from .bytecode_cfg import CFG

def compute_postdominators(cfg: CFG) -> Dict[int, Set[int]]:
    nodes = {b.bid for b in cfg.blocks}
    exits = {b for b in nodes if not cfg.succ[b]}
    postdom = {b: set(nodes) for b in nodes}
    for e in exits:
        postdom[e] = {e}
    changed = True
    while changed:
        changed = False
        for b in nodes - exits:
            succs = cfg.succ[b]
            if not succs:
                new = {b}
            else:
                inter = None
                for s in succs:
                    inter = postdom[s] if inter is None else (inter & postdom[s])
                new = {b} | (inter or set())
            if new != postdom[b]:
                postdom[b] = new; changed = True
    return postdom

def control_dependence_edges(cfg: CFG) -> List[Tuple[int,int,str]]:
    postdom = compute_postdominators(cfg)
    edges: List[Tuple[int,int,str]] = []
    for a, succs in cfg.succ.items():
        for b in succs:
            diff = postdom[b] - postdom[a]
            for n in diff:
                if n != a:
                    edges.append((a, n, "CTRL_DEP"))
    edges = list({(s,t,k) for (s,t,k) in edges})
    return edges
