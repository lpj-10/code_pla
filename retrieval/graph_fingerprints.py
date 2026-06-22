
# retrieval/graph_fingerprints.py
"""
Graph‑based fingerprints for E‑PDG functions.

This module provides WL‑hash style multiset labels and short k‑path
fingerprints over the PDG/E‑PDG of each function. The resulting
shingles are string tokens that can be fed into MinHash + LSH, in the
same way as token k‑grams.

Design goals:
- Dependency‑free and deterministic.
- Conservative handling of edge formats, since JSON may store edges as
  2‑tuples, 3‑tuples or dictionaries with various key names.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Iterable, List, Set, Tuple, Any
from collections import defaultdict

# ----------------------------------------------------------------------
# Helpers: robust edge extraction and PDG adjacency
# ----------------------------------------------------------------------

def _edge_pairs(edges: Any):
    """Yield (src, dst) integer node ids from many possible encodings.

    Supports:
    - [(s, t), ...]
    - [(s, t, kind), ...]
    - [{"s":..., "t":...}, ...]
    - [{"src"/"dst"} or {"source"/"target"}, ...]
    - Other iterables with length >= 2 where the first two elements
      are interpreted as (s, t).
    """
    if not edges:
        return
    for e in edges:
        s = t = None
        if isinstance(e, dict):
            s = e.get("s") or e.get("src") or e.get("source")
            t = e.get("t") or e.get("dst") or e.get("target")
        elif isinstance(e, (list, tuple)):
            if len(e) >= 2:
                s, t = e[0], e[1]
        if s is None or t is None:
            continue
        try:
            s_i = int(s)
            t_i = int(t)
        except Exception:
            continue
        yield s_i, t_i


def build_pdg_undirected(func_obj: Dict[str, Any]) -> Tuple[Dict[int, str], Dict[int, Set[int]]]:
    """Build an undirected PDG adjacency + node labels from a Func JSON dict.

    - Node labels default to `kind`.
    - Edges come from data_edges, control_edges, and effect_edges.
    """
    nodes = func_obj.get("nodes", []) or []
    labels: Dict[int, str] = {}
    adj: Dict[int, Set[int]] = defaultdict(set)

    for n in nodes:
        try:
            nid = int(n.get("nid"))
        except Exception:
            continue
        kind = str(n.get("kind", "UNK"))
        labels[nid] = kind
        # ensure the node exists in adjacency even if isolated
        _ = adj[nid]

    pdg = func_obj.get("pdg") or {}
    for key in ("data_edges", "control_edges", "effect_edges"):
        for s, t in _edge_pairs(pdg.get(key) or []):
            if s in labels and t in labels:
                adj[s].add(t)
                adj[t].add(s)

    return labels, adj


# ----------------------------------------------------------------------
# WL‑hash style multiset labels
# ----------------------------------------------------------------------

def wl_shingles_for_func(
    func_obj: Dict[str, Any],
    iters: int = 2,
) -> Set[str]:
    """Return a set of WL‑hash label strings for a function's PDG.

    We start from `kind` labels and iteratively hash the multiset of
    neighbour labels. All intermediate iterations' labels are added
    as shingles.
    """
    if iters <= 0:
        return set()

    labels, adj = build_pdg_undirected(func_obj)
    if not labels:
        return set()

    # iteration 0: original kinds
    current = {nid: str(lbl) for nid, lbl in labels.items()}
    shingles: Set[str] = set(f"WL0:{lbl}" for lbl in current.values())

    for it in range(1, iters + 1):
        new_labels: Dict[int, str] = {}
        for nid, lbl in current.items():
            neigh_labs = [current.get(nbr, "") for nbr in adj.get(nid, ())]
            neigh_labs.sort()
            concat = lbl + "|" + "|".join(neigh_labs)
            digest = hashlib.blake2b(concat.encode("utf-8"), digest_size=8).hexdigest()
            new_lbl = f"WL{it}:{digest}"
            new_labels[nid] = new_lbl
        current = new_labels
        shingles.update(current.values())

    return shingles


# ----------------------------------------------------------------------
# Short k‑path fingerprints
# ----------------------------------------------------------------------

def kpath_shingles_for_func(
    func_obj: Dict[str, Any],
    k: int = 3,
    max_paths_per_node: int = 32,
) -> Set[str]:
    """Generate short labelled paths on the undirected PDG.

    We restrict to simple paths with limited branching per start node
    for robustness. For the M0–M1 scale of student assignments this
    is typically sufficient.
    """
    if k <= 1:
        return set()

    labels, adj = build_pdg_undirected(func_obj)
    if not labels:
        return set()

    shingles: Set[str] = set()

    def dfs(path: List[int], depth: int, budget_left: List[int]) -> None:
        nid = path[-1]
        if depth == k:
            labs = [labels.get(x, "UNK") for x in path]
            shingles.add("PATH:" + "->".join(labs))
            return
        # simple path: avoid immediate backtracking
        for nbr in sorted(adj.get(nid, ())):
            if len(path) >= 2 and nbr == path[-2]:
                continue
            if budget_left[0] <= 0:
                return
            budget_left[0] -= 1
            dfs(path + [nbr], depth + 1, budget_left)

    for nid in sorted(labels.keys()):
        budget_left = [max_paths_per_node]
        dfs([nid], 1, budget_left)

    return shingles


# ----------------------------------------------------------------------
# Combined graph shingles
# ----------------------------------------------------------------------

def graph_shingles_for_func(
    func_obj: Dict[str, Any],
    wl_iters: int = 2,
    use_kpaths: bool = True,
    kpath_k: int = 3,
    kpath_per_node: int = 32,
) -> Set[str]:
    """Union of WL labels and k‑path fingerprints for a function.

    The resulting strings are suitable to be passed directly to
    :class:`MinHasher.signature`.
    """
    result: Set[str] = set()
    if wl_iters > 0:
        result |= wl_shingles_for_func(func_obj, iters=wl_iters)
    if use_kpaths and kpath_k > 1:
        result |= kpath_shingles_for_func(
            func_obj, k=kpath_k, max_paths_per_node=kpath_per_node
        )
    return result
