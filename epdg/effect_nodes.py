# epdg/effect_nodes.py
from __future__ import annotations

"""Materialize side-effect resources into explicit graph nodes.

Why:
- The pipeline's graph fingerprints (retrieval/graph_fingerprints.py) expects
  PDG edges to be integer node pairs.
- Existing frontends often store side effects as (nid, "FILE[stdout]", "WRITE")
  which is not graph-usable.
- By turning resources into real NodeIR nodes (with stable kind labels),
  effect edges participate in graph similarity.

This module converts:
  FuncIR.pdg_eff: List[(src_nid, resource_str, tag_str)]
into:
  FuncIR.pdg_effect_edges: List[(src_nid, res_node_nid)]
and appends resource nodes into FuncIR.nodes.
It also keeps the original pdg_eff as raw/debug info.

Design choice:
- By default we create *one node per (group, tag)*, e.g., RES_FILE_READ.
  This keeps the graph compact and stable across programs.
- You may switch to per-resource nodes (group, tag, exact resource) for richer
  reports, but similarity may become noisier.
"""

from typing import Dict, List, Tuple, Optional, Any

from .ast_pdg_builder import FuncIR, NodeIR


def _resource_group(res: str) -> str:
    r = (res or "").upper()
    if r.startswith("FILE") or r.startswith("FILE_IO"):
        return "FILE"
    if r.startswith("NET") or r.startswith("NET_IO"):
        return "NET"
    if r.startswith("DB") or r.startswith("DB_IO"):
        return "DB"
    if r.startswith("ENV"):
        return "ENV"
    if r.startswith("RNG"):
        return "RNG"
    if r.startswith("TIME"):
        return "TIME"
    if r.startswith("STACK"):
        return "STACK"
    if r.startswith("GLOBAL"):
        return "GLOBAL"
    if r.startswith("HEAP"):
        return "HEAP"
    if r.startswith("FLAG:"):
        # e.g., FLAG:exception
        return "FLAG_" + r.split(":", 1)[1].upper()
    return "RES"


def _res_kind(group: str, tag: str) -> str:
    t = (tag or "").upper()
    if t in {"READ", "WRITE"}:
        return f"RES_{group}_{t}"
    if t == "FLAG":
        return f"RES_{group}"
    return f"RES_{group}"


def materialize_effect_nodes(func: FuncIR) -> None:
    """Append resource nodes and create integer PDG effect edges.

    After this, ``func.pdg_effect_edges`` will be populated and suitable for
    graph fingerprints / graph similarity.
    """
    # Ensure attribute exists even if no effects
    if not hasattr(func, "pdg_effect_edges") or getattr(func, "pdg_effect_edges") is None:
        setattr(func, "pdg_effect_edges", [])

    # If there are no raw effects, nothing to do
    raw = getattr(func, "pdg_eff", None) or []
    if not raw:
        return

    # Build an allocation cursor (local to this function)
    max_nid = 0
    for n in func.nodes:
        try:
            max_nid = max(max_nid, int(getattr(n, "nid", 0)))
        except Exception:
            continue
    next_nid = max_nid + 1

    # One node per (group, tag)
    key_to_nid: Dict[Tuple[str, str], int] = {}
    new_nodes: List[NodeIR] = []
    new_edges: List[Tuple[int, int]] = []

    for src_nid, res, tag in raw:
        group = _resource_group(str(res))
        kind = _res_kind(group, str(tag))
        key = (kind, str(tag).upper())
        if key not in key_to_nid:
            rnid = next_nid
            next_nid += 1
            key_to_nid[key] = rnid
            new_nodes.append(
                NodeIR(
                    nid=rnid,
                    kind=kind,
                    lineno=0,
                    reads=[],
                    writes=[],
                    calls=[],
                    effects={"resource": str(res), "tag": str(tag)},
                )
            )
        new_edges.append((int(src_nid), key_to_nid[key]))

    # Attach
    func.nodes.extend(new_nodes)
    # Dedup edges
    dedup = []
    seen = set()
    for s, t in new_edges:
        if (s, t) not in seen:
            seen.add((s, t))
            dedup.append((s, t))
    func.pdg_effect_edges = dedup
