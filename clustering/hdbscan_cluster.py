# clustering/hdbscan_cluster.py
from __future__ import annotations

"""
DACD-based function clustering and template detection.

This module provides a small, self-contained helper that takes a set of
function-level E-PDG JSONs (the same schema as produced by build_epdg.py +
serializer.func_to_dict) and clusters them using a DACD-style distance.

It is intentionally decoupled from any VCoME / GNN requirements:
- The distance function dacd_distance() will automatically fall back to
  a hand-crafted embedding when no vcome_vec is present.
- Clustering is performed with HDBSCAN if available; otherwise we fall
  back to AgglomerativeClustering with a distance threshold.

Typical usage (from code):

    from clustering.hdbscan_cluster import run_dacd_template_clustering
    out = run_dacd_template_clustering(
        json_root="data/artifacts/json_mv",
        output_json="data/artifacts/clusters/dacd_clusters.json",
    )

You can also run this module as a script:

    python -m clustering.hdbscan_cluster \
        --json-root data/artifacts/json_mv \
        --output data/artifacts/clusters/dacd_clusters.json
"""

from typing import Dict, Any, List, Tuple
import os
import json
import math

import numpy as np

try:  # pragma: no cover - optional dependency
    import hdbscan  # type: ignore
    HAS_HDBSCAN = True
except Exception:  # pragma: no cover
    try:
        from sklearn.cluster import AgglomerativeClustering  # type: ignore
        HAS_HDBSCAN = False
    except Exception:
        AgglomerativeClustering = None  # type: ignore
        HAS_HDBSCAN = False

from clustering.dacd import dacd_distance
from ranking.align_dep import dep_consistent_align  # imported for future use


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_funcs(json_root: str, lang: str = "auto", max_funcs: int = 0) -> List[Dict[str, Any]]:
    """Scan a directory of *.epdg.json / *_epdg.json and collect function dicts.

    Each entry in the returned list has the form:

        {
            "_pack": <function_json>,
            "file": "<path/to/file.epdg.json>",
            "func_index": <int>,
            "lang": "<language>",
        }

    If the function JSON does not have an "id" field, we generate a
    stable synthetic id based on file path and index.
    """
    root = os.path.abspath(json_root)
    out: List[Dict[str, Any]] = []
    counter = 0

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".epdg.json"):
                continue
            fpath = os.path.join(dirpath, fn)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            file_lang = data.get("language") or data.get("lang") or "unknown"
            if lang != "auto" and file_lang != lang:
                continue

            funcs = data.get("functions") or []
            for idx, fobj in enumerate(funcs):
                if not isinstance(fobj, dict):
                    continue
                fid = fobj.get("id")
                if not isinstance(fid, str):
                    # Synthetic id: path::idx
                    fid = f"{os.path.relpath(fpath, root)}::func{idx}"
                    fobj["id"] = fid

                out.append(
                    {
                        "_pack": fobj,
                        "file": fpath,
                        "func_index": idx,
                        "lang": file_lang,
                    }
                )
                counter += 1
                if max_funcs and counter >= max_funcs:
                    return out

    return out


def _pairwise_distance_matrix(funcs: List[Dict[str, Any]], use_align: bool = False) -> np.ndarray:
    """Compute a full pairwise distance matrix using dacd_distance.

    Parameters
    ----------
    funcs:
        List of function wrappers as produced by _collect_funcs().
    use_align:
        If True, we will call dep_consistent_align() to get an optional
        alignment score for each pair and feed it into dacd_distance().
        For now the default is False to avoid O(N^2) alignment cost,
        since the DACD defaults already set align weight to 0.
    """
    n = len(funcs)
    # hdbscan expects double precision for the precomputed metric; keep the matrix float64.
    D = np.zeros((n, n), dtype="float64")
    for i in range(n):
        D[i, i] = 0.0
    for i in range(n):
        fi = funcs[i]
        for j in range(i + 1, n):
            fj = funcs[j]
            align_s = None
            if use_align:
                try:
                    align_s = dep_consistent_align(fi["_pack"], fj["_pack"])
                except Exception:
                    align_s = None
            d = dacd_distance(fi, fj, align_s=align_s)
            D[i, j] = D[j, i] = float(d)
    return D


def _medoid(dist_matrix: np.ndarray, idxs: List[int]) -> int:
    """Return the index of the medoid (min avg distance) within idxs."""
    if not idxs:
        return -1
    if len(idxs) == 1:
        return idxs[0]
    sub = dist_matrix[np.ix_(idxs, idxs)]
    # average distance to others for each member
    mean_d = sub.mean(axis=1)
    k = int(mean_d.argmin())
    return idxs[k]


# ---------------------------------------------------------------------------
# Public API: clustering + template-heuristic
# ---------------------------------------------------------------------------


def run_dacd_template_clustering(
    json_root: str,
    output_json: str | None = None,
    lang: str = "auto",
    max_funcs: int = 0,
    min_cluster_size: int = 8,
    epsilon: float = 0.35,
    use_align: bool = False,
) -> Dict[str, Any]:
    """Cluster functions with DACD distance and flag template-like clusters.

    Parameters
    ----------
    json_root:
        Root directory containing *.epdg.json files (output of build_epdg.py).
    output_json:
        Where to save the result summary. If None, nothing is written.
    lang:
        Language filter. "auto" means use all languages. Otherwise only
        functions whose top-level JSON "language" field equals this string
        will be used.
    max_funcs:
        Optional limit on total number of functions (0 = no limit). This is
        important because the distance matrix is O(N^2) in memory/time.
    min_cluster_size:
        Minimum cluster size passed to HDBSCAN (if available). Also used
        in the template heuristic.
    epsilon:
        Rough scale for "tight clusters". For HDBSCAN this is used as
        cluster_selection_epsilon; for AgglomerativeClustering we use it
        as distance_threshold.
    use_align:
        Whether to compute structural-alignment scores for each pair and
        pass them into dacd_distance(). The default is False to keep the
        cost manageable.

    Returns
    -------
    A dict of the form:

        {
          "params": {...},
          "num_functions": N,
          "num_clusters": K,
          "distance_matrix_shape": [N, N],
          "clusters": [
            {
              "cluster_id": 0,
              "size": 12,
              "members": ["file1.py::func0", ...],
              "exemplar": "file1.py::func0",
              "mean_node_size": 9.3,
              "mean_intra_distance": 0.21,
              "stability": 0.87 | null,
              "is_template_like": true/false,
            },
            ...
          ],
        }
    """
    funcs = _collect_funcs(json_root, lang=lang, max_funcs=max_funcs)
    n = len(funcs)
    if n == 0:
        raise RuntimeError(f"No functions found under json_root={json_root!r}")

    # Pairwise distance
    D = _pairwise_distance_matrix(funcs, use_align=use_align)

    # Clustering
    labels: np.ndarray
    stability: np.ndarray | None = None

    if HAS_HDBSCAN:
        clusterer = hdbscan.HDBSCAN(  # type: ignore[attr-defined]
            metric="precomputed",
            min_cluster_size=min_cluster_size,
            cluster_selection_epsilon=epsilon,
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(D)
        # cluster_persistence_ is a (n_clusters,) array; probabilities_ is per-point
        try:
            stability = getattr(clusterer, "cluster_persistence_", None)
        except Exception:
            stability = None
    else:
        if "AgglomerativeClustering" not in globals() or AgglomerativeClustering is None:  # type: ignore[name-defined]
            raise RuntimeError(
                "Neither hdbscan nor sklearn.cluster.AgglomerativeClustering is available. "
                "Please install 'hdbscan' or 'scikit-learn' to use DACD clustering."
            )
        # Build a hierarchy and cut at distance_threshold=epsilon
        clusterer = AgglomerativeClustering(  # type: ignore[name-defined]
            affinity="precomputed",
            linkage="average",
            distance_threshold=epsilon,
            n_clusters=None,
        )
        labels = clusterer.fit_predict(D)
        stability = None

    # Group indices by cluster id, ignoring noise label (-1 in HDBSCAN)
    clusters: Dict[int, List[int]] = {}
    for idx, lab in enumerate(labels):
        if lab < 0:
            continue
        lab_int = int(lab)
        clusters.setdefault(lab_int, []).append(idx)

    out: Dict[str, Any] = {
        "params": {
            "json_root": json_root,
            "lang": lang,
            "max_funcs": max_funcs,
            "min_cluster_size": min_cluster_size,
            "epsilon": epsilon,
            "use_align": use_align,
            "has_hdbscan": bool(HAS_HDBSCAN),
        },
        "num_functions": int(n),
        "num_clusters": int(len(clusters)),
        "distance_matrix_shape": [int(n), int(n)],
        "clusters": [],
    }

    # Compute per-cluster statistics and template heuristic
    for cid, idxs in sorted(clusters.items(), key=lambda kv: kv[0]):
        med = _medoid(D, idxs)
        sizes = []
        files = set()
        for i in idxs:
            f = funcs[i]["_pack"]
            sizes.append(len(f.get("nodes", []) or []))
            files.add(funcs[i]["file"])
        mean_size = float(np.mean(sizes)) if sizes else 0.0
        # mean intra-cluster distance
        if len(idxs) > 1:
            dm = D[np.ix_(idxs, idxs)]
            tri = dm[np.triu_indices(len(idxs), k=1)]
            mean_d = float(tri.mean()) if tri.size > 0 else 0.0
        else:
            mean_d = 0.0

        # 简单模板启发式：簇够大 + 均值距离够小 + 函数规模偏小 + 出现在多个文件
        distinct_files = len(files)
        is_template = (
            (len(idxs) >= max(8, min_cluster_size * 2))
            and (mean_size < 12)
            and (mean_d < 0.35)
            and (distinct_files >= 3)
        )

        cluster_item = {
            "cluster_id": int(cid),
            "size": len(idxs),
            "members": [funcs[i]["_pack"].get("id") for i in idxs],
            "exemplar": funcs[med]["_pack"].get("id") if med >= 0 else None,
            "mean_node_size": mean_size,
            "mean_intra_distance": mean_d,
            "distinct_files": int(distinct_files),
            "stability": float(stability[cid]) if (stability is not None and cid < len(stability)) else None,
            "is_template_like": bool(is_template),
        }
        out["clusters"].append(cluster_item)

    if output_json:
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    return out


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _main(argv: List[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Cluster functions with DACD distance and flag template-like clusters.",
    )
    ap.add_argument(
        "--json-root",
        required=True,
        help="Root directory containing *.epdg.json files (after E-PDG build).",
    )
    ap.add_argument(
        "--output",
        help="Path to output JSON summary. Default: <json-root>/dacd_clusters.json",
    )
    ap.add_argument(
        "--lang",
        default="auto",
        help='Language filter, e.g., "python". Default: auto (all languages).',
    )
    ap.add_argument(
        "--max-funcs",
        type=int,
        default=0,
        help="Optional limit on number of functions (0 = no limit).",
    )
    ap.add_argument(
        "--min-cluster-size",
        type=int,
        default=8,
        help="Minimum cluster size for HDBSCAN / heuristic.",
    )
    ap.add_argument(
        "--epsilon",
        type=float,
        default=0.35,
        help="Scale parameter for cluster tightness (distance threshold).",
    )
    ap.add_argument(
        "--use-align",
        action="store_true",
        help="Enable structural alignment in dacd_distance (slower, O(N^2)).",
    )

    args = ap.parse_args(argv)

    json_root = args.json_root
    output = args.output or os.path.join(json_root, "dacd_clusters.json")

    run_dacd_template_clustering(
        json_root=json_root,
        output_json=output,
        lang=args.lang,
        max_funcs=args.max_funcs,
        min_cluster_size=args.min_cluster_size,
        epsilon=args.epsilon,
        use_align=bool(args.use_align),
    )


if __name__ == "__main__":  # pragma: no cover
    _main()
