
# scripts/build_lsh_candidates.py
from __future__ import annotations

"""
基于现有 MinHash + LSH 索引，生成给 VCoME 多视图精排使用的候选对 JSON。

输入：
  - 由 retrieval/index_build.py 生成的 index.pkl
  - 一个包含 *.epdg.json 的根目录（与训练 / 数据集相同）

输出 JSON 格式（与 rerank_candidates_multi.py 约定保持一致）：
--------------------------------------------------------------------
{
  "pairs": [
    {
      "lsh_sim": 0.93,
      "meta_i": {
        "id": "progA::foo",
        "json_path": "data/artifacts/json_mv/fileA.epdg.json",
        "func_idx": 0,
        "name": "foo",
        "first_lineno": 10
      },
      "meta_j": {
        "id": "progB::bar",
        "json_path": "data/artifacts/json_mv/fileB.epdg.json",
        "func_idx": 2,
        "name": "bar",
        "first_lineno": 5
      }
    },
    ...
  ],
  "meta": {
    "built_by": "scripts/build_lsh_candidates.py",
    "index_path": ".../index.pkl",
    "json_root": "data/artifacts/json_mv",
    "topk_recall": 128,
    "min_candidates": 10,
    "num_funcs": 1234,
    "num_pairs": 5678
  }
}
--------------------------------------------------------------------
"""

import os
import sys
import json
import math
import pickle
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from retrieval.minhash_lsh import shingles  # type: ignore
from ranking.rerank import load_func_map    # 复用已有的扫描逻辑


def _cosine(a, b) -> float:
    if a is None or b is None:
        return 0.0
    if len(a) == 0 or len(b) == 0:
        return 0.0
    if len(a) != len(b):
        L = min(len(a), len(b))
        a = a[:L]
        b = b[:L]
    num = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        num += float(x) * float(y)
        na += float(x) * float(x)
        nb += float(y) * float(y)
    if na <= 0 or nb <= 0:
        return 0.0
    return float(num / math.sqrt(na * nb))


def _program_path(func_id: str) -> str:
    # 与 ranking.rerank 里的约定保持一致：func_id = "json_path::func_name"（若无显式 id）
    return func_id.split("::")[0]


def _basename(func_id: str) -> str:
    # 只看 json 文件名，避免把同一作业文件内部小函数彼此当成候选
    return Path(_program_path(func_id)).name


def build_id_location_map(json_root: str) -> Dict[str, Dict[str, Any]]:
    """
    扫描 json_root 下的 *.epdg.json，构造：
      { func_id: {json_path, func_idx, name, first_lineno, id} }

    func_id 生成规则与 load_func_map / index_build 一致：
      fid = f["id"] 若存在，否则： "<json_path>::<函数名>"
    """
    id_loc: Dict[str, Dict[str, Any]] = {}
    root = Path(json_root)

    for p in root.rglob("*.epdg.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        prog = str(p)
        for idx, f in enumerate(data.get("functions", [])):
            fid = f.get("id") or f"{prog}::{f.get('name', '<anon>')}"
            loc = {
                "json_path": prog,
                "func_idx": idx,
                "name": f.get("name", "<anon>"),
                "id": f.get("id"),
                "first_lineno": f.get("first_lineno", f.get("lineno", -1)),
            }
            # Propagate effect-related fields if present
            for eff_key in ["effect_signature", "effect_summary", "effects", "effect_sig", "eff_tags"]:
                if eff_key in f:
                    loc[eff_key] = f[eff_key]
            # 后写入的同名 fid 会覆盖前者，保持与索引构建阶段一致
            id_loc[fid] = loc

    return id_loc


def build_lsh_candidates(
    index_path: str,
    json_root: str,
    out_json: str,
    topk_recall: int = 128,
    min_candidates: int = 10,
    min_tokens: int = 3,
    template_degree_soft: int = 64,
    template_degree_hard: int = 128,
) -> None:
    """构建给 VCoME 精排使用的 LSH 候选对。

    相比最初版本，这里增加了两类鲁棒性策略：
      1. 短函数过滤：tokens_norm 长度小于 min_tokens 的函数完全跳过召回；
      2. 模板惩罚：若某个函数在很多不同查询里频繁作为邻居出现，则视为模板样式：
         - degree >= template_degree_soft: 在 meta 里打 is_template_like 标记；
         - degree >= template_degree_hard: 与其它同样高 degree 的函数之间的 pair 直接丢弃。
    """
    # 1) 载入索引
    with open(index_path, "rb") as f:
        idx = pickle.load(f)

    hasher = idx["minhash"]
    lsh = idx["lsh"]
    effect_vecs: Dict[str, List[float]] = idx.get("effect_vecs", {})
    params = idx.get("params", {})
    k = int(params.get("k", 5))

    # 2) 载入函数 map（用于 tokens_norm）
    func_map, _ = load_func_map(json_root)
    if not isinstance(func_map, dict):
        raise TypeError(f"load_func_map should return a dict, got {type(func_map)}")

    # 2.1) 预先统计每个函数的 token 长度
    func_token_len: Dict[str, int] = {}
    for fid, f in func_map.items():
        toks = f.get("tokens_norm", []) or []
        func_token_len[fid] = len(toks)

    # 3) 预构建 func_id -> 位置 / 元信息 的映射
    id_loc = build_id_location_map(json_root)

    # 预估 effect_vec 维度，用于缺失时的零向量
    zero_vec: List[float] = []
    if effect_vecs:
        first_vec = next(iter(effect_vecs.values()))
        zero_vec = [0.0] * len(first_vec)

    candidate_ids: Dict[str, List[Tuple[str, float]]] = {}
    # 记录“被多少个不同查询函数视为候选”的 degree，用于模板检测
    neighbor_degree: Dict[str, int] = {}

    short_skipped = 0

    # 3.1) 遍历所有函数，做 LSH 查询 + effect_vec 补充
    for fid, f in func_map.items():
        toks = f.get("tokens_norm", []) or []
        tok_len = len(toks)

        # 过短函数直接跳过，避免公共 small helper 污染候选集
        if tok_len < min_tokens:
            short_skipped += 1
            continue
        if not toks:
            continue

        sh = shingles(toks, k=k)
        sig = hasher.signature(sh)
        cset = set(lsh.query(sig))
        if fid in cset:
            cset.remove(fid)

        # 若 LSH 候选太少，用 effect_vec 做一次全局粗排补足
        if len(cset) < min_candidates and effect_vecs:
            base = effect_vecs.get(fid, zero_vec)
            sims = []
            for cid, vec in effect_vecs.items():
                if cid == fid:
                    continue
                sims.append((cid, _cosine(base, vec)))
            sims.sort(key=lambda x: x[1], reverse=True)
            extra = [cid for cid, _ in sims[: max(min_candidates * 5, 50)]]
            cset.update(extra)

        # 不和自己同一个 json 文件比
        qbn = _basename(fid)
        filtered: List[Tuple[str, float]] = []
        base_vec = effect_vecs.get(fid, zero_vec)
        for cid in cset:
            # 候选函数也做一次长度过滤，极短函数直接丢弃
            if func_token_len.get(cid, 0) < min_tokens:
                continue
            if _basename(cid) == qbn:
                continue
            vec = effect_vecs.get(cid, zero_vec)
            score = _cosine(base_vec, vec)
            filtered.append((cid, score))

        # 按 lsh_sim 降序，截断在 topk_recall
        filtered.sort(key=lambda x: x[1], reverse=True)
        filtered = filtered[:topk_recall]

        # 更新 neighbor_degree：记录每个 cid 被多少个查询 fid 视为邻居
        for cid, _ in filtered:
            neighbor_degree[cid] = neighbor_degree.get(cid, 0) + 1

        candidate_ids[fid] = filtered

    if short_skipped:
        print(f"[info] skipped {short_skipped} short functions (tokens_norm < {min_tokens}) at recall stage")

    # 4) 展开为全局 pair 列表，去重 (fid_i, fid_j)
    pairs: List[Dict[str, Any]] = []
    seen_pairs = set()

    for fid_i, cand_list in candidate_ids.items():
        loc_i = id_loc.get(fid_i)
        if not loc_i:
            continue

        len_i = func_token_len.get(fid_i, 0)
        deg_i = neighbor_degree.get(fid_i, 0)
        is_tmpl_i = deg_i >= template_degree_soft

        for fid_j, lsh_sim in cand_list:
            if fid_i == fid_j:
                continue
            loc_j = id_loc.get(fid_j)
            if not loc_j:
                continue

            len_j = func_token_len.get(fid_j, 0)
            deg_j = neighbor_degree.get(fid_j, 0)
            is_tmpl_j = deg_j >= template_degree_soft

            # 候选函数过短直接跳过
            if len_j < min_tokens:
                continue

            # 若两边都是高 degree 的模板函数，认为不具备区分力，硬过滤
            if deg_i >= template_degree_hard and deg_j >= template_degree_hard:
                continue

            key = tuple(sorted((fid_i, fid_j)))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            meta_i = {
                "id": fid_i,
                "json_path": loc_i["json_path"],
                "func_idx": int(loc_i["func_idx"]),
                "name": loc_i.get("name"),
                "first_lineno": int(loc_i.get("first_lineno", -1)),
                "token_len": int(len_i),
                "neighbor_degree": int(deg_i),
                "is_template_like": bool(is_tmpl_i),
            }
            meta_j = {
                "id": fid_j,
                "json_path": loc_j["json_path"],
                "func_idx": int(loc_j["func_idx"]),
                "name": loc_j.get("name"),
                "first_lineno": int(loc_j.get("first_lineno", -1)),
                "token_len": int(len_j),
                "neighbor_degree": int(deg_j),
                "is_template_like": bool(is_tmpl_j),
            }
            # Propagate effect-related fields from loc_i and loc_j
            for eff_key in ["effect_signature", "effect_summary", "effects", "effect_sig", "eff_tags"]:
                if eff_key in loc_i:
                    meta_i[eff_key] = loc_i[eff_key]
                if eff_key in loc_j:
                    meta_j[eff_key] = loc_j[eff_key]

            pairs.append(
                {
                    "lsh_sim": float(lsh_sim),
                    "meta_i": meta_i,
                    "meta_j": meta_j,
                }
            )

    out = {
        "pairs": pairs,
        "meta": {
            "built_by": "scripts/build_lsh_candidates.py",
            "index_path": os.path.abspath(index_path),
            "json_root": os.path.abspath(json_root),
            "topk_recall": int(topk_recall),
            "min_candidates": int(min_candidates),
            "min_tokens": int(min_tokens),
            "template_degree_soft": int(template_degree_soft),
            "template_degree_hard": int(template_degree_hard),
            "num_funcs": len(func_map),
            "num_pairs": len(pairs),
        },
    }

    out_path = Path(out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[OK] wrote LSH candidates JSON with {len(pairs)} pairs to {out_path}")



def main():
    ap = argparse.ArgumentParser(
        description="Build LSH candidate pairs JSON for VCoME multi-view reranker."
    )
    ap.add_argument(
        "-i",
        "--index",
        required=True,
        help="Path to index pickle, e.g. data/artifacts/retrieval/index.pkl",
    )
    ap.add_argument(
        "-j",
        "--json_root",
        required=True,
        help="Root directory that contains *.epdg.json files.",
    )
    ap.add_argument(
        "-o",
        "--out_json",
        required=True,
        help="Output JSON path for candidate pairs.",
    )
    ap.add_argument(
        "--topk_recall",
        type=int,
        default=128,
        help="Top-K candidate functions per query kept after rough ranking.",
    )
    ap.add_argument(
        "--min_candidates",
        type=int,
        default=10,
        help="If LSH returns fewer than this, use effect_vec cosine to supplement.",
    )
    ap.add_argument(
        "--min_tokens",
        type=int,
        default=3,
        help="Minimum tokens_norm length for a function to participate in recall.",
    )
    ap.add_argument(
        "--template_degree_soft",
        type=int,
        default=64,
        help="Neighbor degree above which a function is treated as template-like (soft penalty).",
    )
    ap.add_argument(
        "--template_degree_hard",
        type=int,
        default=128,
        help="Neighbor degree above which template-template pairs are dropped at recall.",
    )

    args = ap.parse_args()

    build_lsh_candidates(
        index_path=args.index,
        json_root=args.json_root,
        out_json=args.out_json,
        topk_recall=args.topk_recall,
        min_candidates=args.min_candidates,
        min_tokens=args.min_tokens,
        template_degree_soft=args.template_degree_soft,
        template_degree_hard=args.template_degree_hard,
    )


if __name__ == "__main__":
    main()
