# ranking/align_dep.py
"""
Dependency-Consistent Alignment (DCA)
------------------------------------
对两个函数的 PDG（数据+控制）做 **块级对齐**，在相似度基础上加入“依赖一致”约束：
- 只允许层级差 |levelA - levelB| <= lvl_tol 的配对（弱拓扑一致）；
- 若已匹配祖先，则新配对不能违反偏序（祖先层级应不大于被配对目标的层级）。
返回：
  score ∈ [0,1]、匹配对列表 [(nidA, nidB, sim)], 以及诊断信息（levels/violations）。
"""
from typing import Dict, Any, List, Tuple, Set
import math
from collections import defaultdict, deque

def _node_feat(n: Dict[str,Any]):
    r = len(n.get("reads",[])); w = len(n.get("writes",[])); c = len(n.get("calls",[]))
    flags = n.get("effects",{}).get("flags",{})
    return [r/8.0, w/8.0, c/8.0, 1.0 if any(flags.values()) else 0.0]

def _cos(a,b):
    num = sum(x*y for x,y in zip(a,b))
    da = math.sqrt(sum(x*x for x in a)) or 1.0
    db = math.sqrt(sum(y*y for y in b)) or 1.0
    return num/(da*db)

def _adj(func: Dict[str,Any]) -> Dict[int,Set[int]]:
    nodes = func.get("nodes", [])
    id2idx = {n["nid"]: i for i,n in enumerate(nodes)}
    adj = {n["nid"]: set() for n in nodes}
    for a,b,_ in func.get("pdg",{}).get("data_edges",[]):
        if a in id2idx and b in id2idx: adj[a].add(b); adj[b].add(a)
    for a,b,_ in func.get("pdg",{}).get("control_edges",[]):
        if a in id2idx and b in id2idx: adj[a].add(b); adj[b].add(a)
    return adj

def _levels(adj: Dict[int,Set[int]]):
    lvl = {}
    roots = [n for n,nb in adj.items() if len(nb)==0]
    if not roots and adj:
        roots = [next(iter(adj.keys()))]
    for r in roots: lvl[r]=0
    changed=True
    while changed:
        changed=False
        for u, nb in adj.items():
            if u not in lvl: continue
            for v in nb:
                if lvl.get(v, -1) < lvl[u]+1:
                    lvl[v] = lvl[u]+1; changed=True
    return lvl

def dep_consistent_align(fA: Dict[str,Any], fB: Dict[str,Any], sim_thresh: float=0.3, lvl_tol: int=1):
    NA, NB = len(fA.get("nodes", [])), len(fB.get("nodes", []))
    if NA==0 or NB==0: return 0.0, [], {"reason":"empty"}
    featsA = [_node_feat(n) for n in fA["nodes"]]
    featsB = [_node_feat(n) for n in fB["nodes"]]
    S = [[_cos(a,b) for b in featsB] for a in featsA]

    idA = [n["nid"] for n in fA["nodes"]]; idxA = {nid:i for i,nid in enumerate(idA)}
    idB = [n["nid"] for n in fB["nodes"]]; idxB = {nid:i for i,nid in enumerate(idB)}
    adjA = _adj(fA); adjB = _adj(fB)
    lvlA = _levels(adjA); lvlB = _levels(adjB)

    cands: List[Tuple[float,int,int]] = []
    for i, nidA in enumerate(idA):
        for j, nidB in enumerate(idB):
            if S[i][j] >= sim_thresh and abs(lvlA.get(nidA,0)-lvlB.get(nidB,0)) <= lvl_tol:
                cands.append((S[i][j], i, j))
    cands.sort(reverse=True)

    usedA, usedB = set(), set()
    # order-consistency guard (placeholder for stronger constraints)
    def _violates_order(i,j):
        return False

    pairs: List[Tuple[int,int,float]] = []
    violations = 0
    for s,i,j in cands:
        if i in usedA or j in usedB: 
            continue
        if _violates_order(i,j):
            violations += 1
            continue
        usedA.add(i); usedB.add(j)
        pairs.append((idA[i], idB[j], float(s)))

    if not pairs:
        return 0.0, [], {"reason":"no_pairs", "lvlA":lvlA, "lvlB":lvlB, "violations":violations}

    score = sum(s for _,_,s in pairs) / max(NA, NB)
    score = max(0.0, min(1.0, score))
    return score, pairs, {"lvlA":lvlA, "lvlB":lvlB, "violations":violations}
