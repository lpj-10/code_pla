
# retrieval/index_build.py
"""Build recall indexes over E‑PDG JSONs.

This module constructs:
- a MinHash + LSH index over token k‑gram shingles, and
- an additional MinHash + LSH index over graph‑based shingles
  (WL‑hash + short k‑paths on the PDG/E‑PDG),
- plus a dense effect‑signature vector table and basic function meta.

The returned index object is a plain dictionary that is safe to
pickle, with at least the following keys (for backward compatibility):

    {
      "meta": {...},
      "minhash": <MinHasher for tokens>,
      "lsh": <LSH for tokens>,
      "graph_minhash": <MinHasher for graphs>,
      "graph_lsh": <LSH for graphs>,
      "effect_vecs": { fid -> [floats] },
      "func_meta": { fid -> (file, name, first_lineno) },
      "params": {...}
    }
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

from .minhash_lsh import MinHasher, LSH, shingles
from .graph_fingerprints import graph_shingles_for_func


def _effect_vector(esig: dict) -> List[float]:
    """Normalised effect‑signature vector.

    The layout is kept in sync with scripts/search_and_rank.py.
    """
    counts = esig.get("counts", {}) if isinstance(esig, dict) else {}
    order = [
        "FILE_IO",
        "NET_IO",
        "DB_IO",
        "ENV",
        "RNG",
        "TIME",
        "EXC",
        "R_STACK",
        "W_STACK",
        "R_GLOBAL",
        "W_GLOBAL",
        "R_HEAP",
        "W_HEAP",
    ]
    vec = [float(counts.get(k, 0.0)) for k in order]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def build_index(
    json_root: str,
    num_perm: int = 128,
    bands: int = 32,
    k: int = 5,
    graph_num_perm: int = 128,
    graph_bands: int = 32,
    wl_iters: int = 2,
    kpath_k: int = 3,
    kpath_per_node: int = 32,
):
    """Build combined token + graph LSH indexes from a tree of *.epdg.json files."""
    root = Path(json_root)

    token_hasher = MinHasher(num_perm=num_perm, seed=2025)
    token_lsh = LSH(bands=bands)

    graph_hasher = MinHasher(num_perm=graph_num_perm, seed=2025 + 10_000)
    graph_lsh = LSH(bands=graph_bands)

    effect_vecs: Dict[str, List[float]] = {}
    func_meta: Dict[str, Tuple[str, str, int]] = {}

    num_files = 0
    num_funcs = 0

    for p in root.rglob("*.epdg.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            # Skip malformed JSON but do not abort the whole build.
            continue

        num_files += 1
        file_path = data.get("file", str(p))

        for f in data.get("functions", []) or []:
            fid = f.get("id")
            if not fid:
                # Fallback to a stable composite id.
                fid = f"{file_path}::{f.get('name', '<anon>')}::{f.get('first_lineno', -1)}"

            # 1) Token‑level shingle LSH
            toks = f.get("tokens_norm") or []
            if toks:
                sh = shingles(toks, k=k)
                if sh:
                    sig = token_hasher.signature(sh)
                    token_lsh.insert(fid, sig)

            # 2) Graph‑level WL/k‑path shingles
            g_sh = graph_shingles_for_func(
                f,
                wl_iters=wl_iters,
                use_kpaths=True,
                kpath_k=kpath_k,
                kpath_per_node=kpath_per_node,
            )
            if g_sh:
                g_sig = graph_hasher.signature(g_sh)
                graph_lsh.insert(fid, g_sig)

            # 3) Effect signature vector
            esig = _effect_vector(f.get("effect_signature") or {})
            effect_vecs[fid] = esig

            # 4) Basic meta for reporting
            func_meta[fid] = (
                file_path,
                f.get("name", ""),
                int(f.get("first_lineno", -1)),
            )

            num_funcs += 1

    meta = {
        "json_root": str(root.resolve()),
        "num_files": num_files,
        "num_funcs": num_funcs,
    }
    params = {
        "num_perm": num_perm,
        "bands": bands,
        "k": k,
        "graph_num_perm": graph_num_perm,
        "graph_bands": graph_bands,
        "wl_iters": wl_iters,
        "kpath_k": kpath_k,
        "kpath_per_node": kpath_per_node,
    }

    return {
        "meta": meta,
        "minhash": token_hasher,
        "lsh": token_lsh,
        "graph_minhash": graph_hasher,
        "graph_lsh": graph_lsh,
        "effect_vecs": effect_vecs,
        "func_meta": func_meta,
        "params": params,
    }


def save(path: str, index_obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    import pickle

    with open(path, "wb") as f:
        pickle.dump(index_obj, f)


def load(path: str):
    import pickle

    with open(path, "rb") as f:
        return pickle.load(f)
