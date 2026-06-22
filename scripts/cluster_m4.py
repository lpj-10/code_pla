# scripts/cluster_m4.py
from __future__ import annotations

import os
import sys
import json, argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from tqdm import tqdm

# Ensure repository root is on sys.path for sibling imports
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ranking.rerank import load_func_map, _fallback_embed
from ranking.enc_vcome import load_model as vcome_load, func_embedding as vcome_func_embed
from ranking.align_dep import dep_consistent_align
from clustering.dacd import dacd_distance
from clustering.hdbscan_cluster import group_cluster
from report.report_cluster import render_cluster_report

def _norm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x) + 1e-9
    return x / n

def pack_func(f: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(f, dict) and "_pack" in f and isinstance(f["_pack"], dict):
        return f["_pack"]
    return {
        "nodes":    f.get("nodes", []),
        "cfg":      f.get("cfg", []),
        "pdg_data": f.get("pdg_data", []),
        "pdg_ctrl": f.get("pdg_ctrl", []),
        "effects_summary": f.get("effects_summary", {}),
        "source_meta":     f.get("source_meta", {}),
    }

def _coerce_func_map(res) -> Dict[str, Dict[str, Any]]:
    if isinstance(res, dict):
        return res
    if isinstance(res, (tuple, list)):
        cands = [x for x in res if isinstance(x, dict)]
        for d in cands:
            if len(d) == 0:  # 也可能是函数表
                fm = d
                continue
            if all(isinstance(k, (str, int)) for k in d.keys()) and all(isinstance(v, dict) for v in d.values()):
                return d
        if cands:
            return cands[0]
    raise SystemExit("load_func_map() 返回格式不符合预期。")

def main():
    ap = argparse.ArgumentParser("M4: HDBSCAN + DACD 聚类与去模板（Top-K 对齐 & 并行）")
    ap.add_argument("-j", "--json_root", required=True, help="*.epdg.json 根目录")
    ap.add_argument("-o", "--out_json", default="data/artifacts/clusters/m4_clusters.json")
    ap.add_argument("-r", "--out_report", default="data/artifacts/reports/m4_clusters.html")
    ap.add_argument("--use_vcome", action="store_true")
    ap.add_argument("--vcome_ckpt", type=str, default=None)
    ap.add_argument("--min_cluster_size", type=int, default=4)
    ap.add_argument("--min_samples", type=int, default=1)
    ap.add_argument("--max_funcs", type=int, default=2000, help="最多聚类的函数数（防 O(N^2)）")
    ap.add_argument("--weights", type=str, default=None, help='DACD 权重 JSON，如 {"vcome":0.5,"align":0.3,"eff":0.1,"graph":0.1}')
    ap.add_argument("--align_topk", type=int, default=20, help="每个函数仅对 Top-K 嵌入近邻做依赖对齐")
    ap.add_argument("--align_workers", type=int, default=0, help="对齐并行 worker 数（0=串行）")
    args = ap.parse_args()

    weights = json.loads(args.weights) if args.weights else None

    # —— 1) 载入函数 —— #
    print("[load] functions ...")
    res = load_func_map(args.json_root)
    fmap: Dict[str, Dict[str, Any]] = _coerce_func_map(res)

    funcs: List[Dict[str, Any]] = []
    for fid, f in fmap.items():
        pf = pack_func(f)
        f["_pack"] = pf
        f["id"] = str(fid)
        funcs.append(f)

    if len(funcs) > args.max_funcs:
        print(f"[warn] 函数数 {len(funcs)} 超出 max_funcs={args.max_funcs}，仅取前 {args.max_funcs}")
        funcs = funcs[:args.max_funcs]

    # —— 2) 编码（VCoME 或回退） —— #
    vcome = None
    if args.use_vcome:
        if not args.vcome_ckpt:
            raise SystemExit("--use_vcome 需要 --vcome_ckpt")
        ckpt_path = Path(args.vcome_ckpt)
        if not ckpt_path.exists():
            # 常见路径修正：若用户给了 data/artifacts/vcome_multi.pt，则尝试 data/artifacts/vcome/vcome_multi.pt
            alt = ROOT_DIR / "data" / "artifacts" / "vcome" / ckpt_path.name
            if alt.exists():
                print(f"[warn] ckpt not found at {ckpt_path}; using {alt} instead")
                ckpt_path = alt
        vcome = vcome_load(ckpt_path)

    if not funcs:
        print("[embed] no functions found; skipping clustering.")
        empty_out = {"n_funcs": 0, "n_clusters": 0, "clusters": []}
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(empty_out, f, ensure_ascii=False, indent=2)
        render_cluster_report(args.out_json, args.out_report)
        print(f"[done] no functions to cluster → {args.out_report}")
        return

    print("[embed] encoding functions ...")
    Z = []
    for f in tqdm(funcs):
        if vcome is not None:
            try:
                z = vcome_func_embed(f, vcome)
            except Exception:
                z = _fallback_embed(f)
        else:
            z = _fallback_embed(f)
        Z.append(_norm(np.asarray(z, dtype="float32")))
    Z = np.vstack(Z)  # [N, D]

    # —— 3) 仅对 Top-K 近邻做依赖对齐（其余用余弦作近似） —— #
    N = len(funcs)
    print(f"[align-plan] build Top-{args.align_topk} neighbor plan, N={N} ...")
    # 余弦相似（Z 已归一化）：快速得到 S=Z Z^T
    S = np.clip(np.matmul(Z, Z.T), -1.0, 1.0)  # [N,N]
    np.fill_diagonal(S, 1.0)

    # 默认用 cos≥0 作为“温和近似”，在依赖对齐后写回
    alignS = np.maximum(S, 0.0).astype("float32")
    np.fill_diagonal(alignS, 1.0)

    do_align = not (vcome is not None and vcome.get("mock"))
    if do_align:
        # 每个 i 取 Top-K 邻居（排除自己）
        K = max(1, min(args.align_topk, N-1))
        neighbor_sets: List[set] = []
        for i in range(N):
            # argpartition 取 Top-K 索引，再按相似度排序
            idx = np.argpartition(-S[i], K+1)[:K+1]
            idx = [j for j in idx if j != i]
            idx = sorted(idx, key=lambda j: -S[i, j])[:K]
            neighbor_sets.append(set(idx))

        # 生成唯一配对清单
        pair_list: List[Tuple[int,int]] = []
        seen = set()
        for i in range(N):
            for j in neighbor_sets[i]:
                a, b = (i, j) if i < j else (j, i)
                key = (a, b)
                if a != b and key not in seen:
                    seen.add(key)
                    pair_list.append(key)

        print(f"[align] plan pairs: {len(pair_list)} (由 Top-K 生成，原始全对为 {N*(N-1)//2})")

        def _do_align(pair: Tuple[int,int]) -> Tuple[int,int,float]:
            i, j = pair
            try:
                s, pairs, _ = dep_consistent_align(funcs[i], funcs[j])
                return (i, j, float(s))
            except Exception:
                return (i, j, 0.0)

        if args.align_workers and args.align_workers > 0:
            # 多进程跑对齐
            from multiprocessing import Pool
            print(f"[align] running in parallel with {args.align_workers} workers ...")
            with Pool(processes=args.align_workers) as pool:
                for i, j, s in tqdm(pool.imap_unordered(_do_align, pair_list, chunksize=16), total=len(pair_list)):
                    alignS[i, j] = alignS[j, i] = s
        else:
            # 串行跑对齐
            for i, j in tqdm(pair_list, total=len(pair_list)):
                _, _, s = (i, j, _do_align((i, j))[2])
                alignS[i, j] = alignS[j, i] = s
    else:
        print("[align] skipped dependency alignment (mock VCoME checkpoint); using cosine only.")

    # —— 4) 构造 DACD 距离矩阵 —— #
    print("[dist] build DACD distance matrix ...")
    D = np.zeros((N, N), dtype="float64")
    for i in tqdm(range(N)):
        D[i, i] = 0.0
        for j in range(i+1, N):
            d = dacd_distance(
                funcs[i], funcs[j],
                vec_a=Z[i], vec_b=Z[j],
                align_s=float(alignS[i, j]),
                weights=weights
            )
            D[i, j] = D[j, i] = float(d)

    # —— 5) HDBSCAN 聚类 & 报告 —— #
    print("[cluster] HDBSCAN / fallback Agglomerative ...")
    out = group_cluster(
        funcs,
        dist_matrix=D,
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        output_json=args.out_json
    )
    render_cluster_report(args.out_json, args.out_report)
    print(f"[done] clusters: {out.get('n_clusters')} → {args.out_report}")

if __name__ == "__main__":
    main()
