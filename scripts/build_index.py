
# scripts/build_index.py
from __future__ import annotations

"""CLI to build combined token + graph LSH index over *.epdg.json.

Usage example:

    python scripts/build_index.py \\
      -j data/artifacts/json \\
      -o data/artifacts/index/epdg_lsh.pkl \\
      --num_perm 128 --bands 32 --k 5

The resulting index .pkl is compatible with scripts/search_and_rank.py.
"""

import os
import sys
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from retrieval.index_build import build_index, save


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-j",
        "--json_root",
        required=True,
        help="Directory containing *.epdg.json files",
    )
    ap.add_argument(
        "-o",
        "--out_index",
        required=True,
        help="Path to save the built index .pkl",
    )
    ap.add_argument(
        "--num_perm",
        type=int,
        default=128,
        help="Number of permutations for token MinHash",
    )
    ap.add_argument(
        "--bands",
        type=int,
        default=32,
        help="Number of LSH bands for token signatures",
    )
    ap.add_argument(
        "-k",
        "--shingle_k",
        type=int,
        default=5,
        help="k for token k-gram shingles",
    )
    ap.add_argument(
        "--graph_num_perm",
        type=int,
        default=128,
        help="Number of permutations for graph MinHash",
    )
    ap.add_argument(
        "--graph_bands",
        type=int,
        default=32,
        help="Number of LSH bands for graph signatures",
    )
    ap.add_argument(
        "--wl_iters",
        type=int,
        default=2,
        help="WL iterations for graph fingerprints",
    )
    ap.add_argument(
        "--kpath_k",
        type=int,
        default=3,
        help="Path length k for k-path fingerprints",
    )
    ap.add_argument(
        "--kpath_per_node",
        type=int,
        default=32,
        help="Max paths per node when enumerating k-paths",
    )
    args = ap.parse_args()

    index_obj = build_index(
        json_root=args.json_root,
        num_perm=args.num_perm,
        bands=args.bands,
        k=args.shingle_k,
        graph_num_perm=args.graph_num_perm,
        graph_bands=args.graph_bands,
        wl_iters=args.wl_iters,
        kpath_k=args.kpath_k,
        kpath_per_node=args.kpath_per_node,
    )

    save(args.out_index, index_obj)

    meta = index_obj.get("meta", {})
    params = index_obj.get("params", {})
    print("[OK] index saved to:", args.out_index)
    print(
        f"[meta] files={meta.get('num_files', '?')}, "
        f"functions={meta.get('num_funcs', '?')}"
    )
    print(
        "[params]",
        f"tokens(num_perm={params.get('num_perm')}, bands={params.get('bands')}, k={params.get('k')}); ",
        f"graph(num_perm={params.get('graph_num_perm')}, bands={params.get('graph_bands')}, ",
        f"wl_iters={params.get('wl_iters')}, kpath_k={params.get('kpath_k')})",
    )
