# clustering/dacd.py
from __future__ import annotations

from typing import Dict, Any, List, Set, Tuple
import numpy as np

from retrieval.graph_fingerprints import graph_shingles_for_func
from ranking.rerank import _fallback_embed  # type: ignore[attr-defined]

__all__ = [
    "dacd_distance",
]

# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------


def _vec_norm(x: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(x)) + 1e-9
    if n == 0.0:
        return x.astype("float32")
    return (x / n).astype("float32")


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    da = float(np.linalg.norm(a))
    db = float(np.linalg.norm(b))
    if da == 0.0 or db == 0.0:
        return 0.0
    return float(np.dot(a, b) / (da * db + 1e-9))


def jaccard_set(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    if not u:
        return 1.0
    return len(a & b) / (len(u) + 1e-9)


# 统一的 effect key 空间，与 bytecode E-PDG 的 effect_signature 对齐
EFF_KEYS: List[str] = [
    "FILE_IO",
    "NET_IO",
    "DB_IO",
    "ENV",
    "RNG",
    "TIME",
    "EXC",
    "R_GLOBAL",
    "W_GLOBAL",
    "R_HEAP",
    "W_HEAP",
    "R_STACK",
    "W_STACK",
]


def _as_func_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    DACD 在不同阶段可能拿到两种结构：
      - 直接是函数 JSON 对象；
      - 或者是 { "_pack": func_json, ... }。
    这里统一成函数 JSON。
    """
    pack = obj.get("_pack")
    if isinstance(pack, dict):
        return pack
    return obj


def effect_bag(obj: Dict[str, Any]) -> Set[str]:
    """
    把一个函数的副作用摘要统一成一个 set，用于 Jaccard。
    优先使用 effect_signature.counts；如果没有，则从节点 effects.flags 聚合。
    """
    f = _as_func_dict(obj)
    bag: Set[str] = set()

    sig = f.get("effect_signature") or {}
    counts = sig.get("counts") or {}
    if isinstance(counts, dict):
        for k in EFF_KEYS:
            try:
                v = float(counts.get(k, 0.0))
            except Exception:
                v = 0.0
            if v > 0.0:
                bag.add(k)

    if bag:
        return bag

    # 回退：从 nodes[].effects.flags 统计
    counts2 = {k: 0 for k in EFF_KEYS}
    for n in f.get("nodes", []) or []:
        eff = n.get("effects") or {}
        flags = eff.get("flags") if isinstance(eff, dict) else {}
        if isinstance(flags, dict):
            for k in EFF_KEYS:
                if flags.get(k):
                    counts2[k] += 1

    for k, v in counts2.items():
        if v > 0:
            bag.add(k)
    return bag


def graph_path_bag(obj: Dict[str, Any]) -> Set[str]:
    """
    使用 retrieval.graph_fingerprints.graph_shingles_for_func 生成
    WL + k-path 的路径指纹集合。
    """
    f = _as_func_dict(obj)
    try:
        return graph_shingles_for_func(f)
    except Exception:
        return set()


def semantic_vec(obj: Dict[str, Any]) -> np.ndarray:
    """
    统一的语义向量来源：
      1. 如果有 vcome_vec 字段，则优先使用（兼容未来你真的训练完 VCoME）。
      2. 否则使用 ranking.rerank._fallback_embed 给出的结构+副作用特征。
    """
    f = _as_func_dict(obj)
    vec = None

    v_raw = f.get("vcome_vec")
    if isinstance(v_raw, (list, tuple)):
        try:
            arr = np.asarray(v_raw, dtype="float32")
            if arr.size > 0:
                vec = arr.reshape(-1)
        except Exception:
            vec = None

    if vec is None:
        try:
            arr = _fallback_embed(f)
            vec = np.asarray(arr, dtype="float32").reshape(-1)
        except Exception:
            vec = np.zeros(1, dtype="float32")

    return _vec_norm(vec)


DEFAULT_WEIGHTS: Dict[str, float] = {
    # "vcome" 不再代表“必须有 VCoME 向量”，而是“统一语义向量”的权重。
    "vcome": 0.5,
    # 对齐特征目前在 DACD 中默认不开启（避免在 O(N^2) 上跑 dep_consistent_align）。
    "align": 0.0,
    # 副作用 / 结构视图用于补充语义向量。
    "eff": 0.25,
    "graph": 0.25,
}


def dacd_distance(
    qa: Dict[str, Any],
    qb: Dict[str, Any],
    align_s: float | None = None,
    weights: Dict[str, float] | None = None,
) -> float:
    """DACD 主距离函数（模板簇识别用）。

    设计目标：
      - 不再硬依赖 VCoME：没有 vcome_vec 也可以工作；
      - 特征输入在「只有 LSH + effect_signature」的场景下仍然可用；
      - 将来你接入轻量 GNN / VCoME-lite 时，只要在 JSON 里加上 vcome_vec，
        这里即可自动利用。

    参数：
      qa, qb: 函数级 JSON 对象或 { "_pack": func_json, ... }。
      align_s: 可选的结构对齐相似度（0~1），如果没有就传 None。
      weights: 自定义各部分权重；如果为 None，则使用 DEFAULT_WEIGHTS。
    """
    W = dict(DEFAULT_WEIGHTS)
    if weights:
        W.update(weights)

    # 1) 语义向量距离
    d_vc = None
    if W.get("vcome", 0.0) > 0.0:
        va = semantic_vec(qa)
        vb = semantic_vec(qb)
        s_vc = cosine(va, vb)
        # clamp 到 [-1, 1]
        s_vc = max(min(s_vc, 1.0), -1.0)
        d_vc = 1.0 - s_vc

    # 2) 对齐距离（目前默认权重为 0，仅当你显式传入 align_s 且调大 W["align"] 时生效）
    d_align = None
    if align_s is not None and W.get("align", 0.0) > 0.0:
        s_align = max(min(float(align_s), 1.0), 0.0)
        d_align = 1.0 - s_align

    # 3) 副作用 Jaccard 距离
    d_eff = None
    if W.get("eff", 0.0) > 0.0:
        e1 = effect_bag(qa)
        e2 = effect_bag(qb)
        s_eff = jaccard_set(e1, e2)
        d_eff = 1.0 - s_eff

    # 4) 结构路径 Jaccard 距离
    d_graph = None
    if W.get("graph", 0.0) > 0.0:
        g1 = graph_path_bag(qa)
        g2 = graph_path_bag(qb)
        s_graph = jaccard_set(g1, g2)
        d_graph = 1.0 - s_graph

    # 按有效分量做加权平均，避免“某个分量缺失但权重>0”导致偏移
    num = 0.0
    den = 0.0

    if d_vc is not None:
        num += W["vcome"] * float(d_vc)
        den += W["vcome"]
    if d_align is not None:
        num += W["align"] * float(d_align)
        den += W["align"]
    if d_eff is not None:
        num += W["eff"] * float(d_eff)
        den += W["eff"]
    if d_graph is not None:
        num += W["graph"] * float(d_graph)
        den += W["graph"]

    if den <= 0.0:
        # 信息不足时保守返回 1.0（“完全不相似”）
        return 1.0

    d = num / den
    # clamp 到 [0, 1]
    return float(max(0.0, min(1.0, d)))
