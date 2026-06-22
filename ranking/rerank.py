# ranking/rerank.py — robust VCoME-aware reranker + loader for E-PDG json
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections.abc import Iterable

import numpy as np

__all__ = [
    "load_func_map",
    "rerank",
]

# ======================================================================
# 1) 读取 .epdg.json → {func_id -> 函数对象}, {func_id -> (program_path, func_name, lineno)}
# ======================================================================

def load_func_map(json_root: str) -> Tuple[Dict[str, dict], Dict[str, tuple]]:
    """
    扫描 json_root 下所有 *.epdg.json，返回：
      func_map: { func_id: function_json_object }
      func_meta: { func_id: (program_path, func_name, lineno) }

    说明：
      - 优先使用 JSON 函数对象里的 f["id"] 作为 func_id；
      - 若缺失，用 "json文件绝对路径::函数名" 生成稳定 id。
    """
    func_map: Dict[str, dict] = {}
    func_meta: Dict[str, tuple] = {}
    root = Path(json_root)

    for p in root.rglob("*.epdg.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        prog = str(p)
        for f in data.get("functions", []):
            fid = f.get("id") or f"{prog}::{f.get('name','<anon>')}"
            func_map[fid] = f
            func_meta[fid] = (
                prog,                      # 程序（json 文件路径）
                f.get("name", "<anon>"),   # 函数名
                f.get("lineno", -1),       # 起始行号（若有）
            )
    return func_map, func_meta


# ======================================================================
# 2) 工具：鲁棒提取边 (s, t)，兼容 2元组/3元组/字典/可迭代
# ======================================================================

def _edge_pairs(edges):
    """
    把各种形态的边转换成 (s, t) 迭代器。
    支持：
      - [(s, t), ...]
      - [(s, t, kind), ...]
      - [{"s":..., "t":...}, ...] 或 {"src"/"dst"} / {"source"/"target"}
      - 其他可迭代且长度>=2的条目
    """
    if edges is None:
        return
    for e in edges:
        if isinstance(e, dict):
            s = e.get("s") or e.get("src") or e.get("source") or e.get(0)
            t = e.get("t") or e.get("dst") or e.get("target") or e.get(1)
            if s is not None and t is not None:
                yield (s, t)
        elif isinstance(e, (list, tuple)):
            if len(e) >= 2:
                yield (e[0], e[1])
        else:
            if isinstance(e, Iterable) and not isinstance(e, (str, bytes)):
                try:
                    it = iter(e)
                    s = next(it)
                    t = next(it)
                    yield (s, t)
                except Exception:
                    continue


# ======================================================================
# 3) VCoME 兼容封装 & 回退嵌入
# ======================================================================

# 相似度融合权重（可按需要调整）
W_COS = 0.7   # 余弦相似度权重
W_BASE = 0.3  # 粗排分数（来自 LSH/ANN）的权重

def _coerce_vcome(vcome: Any):
    """
    统一 vcome 对象为 (model, device, encode_fn or None)
    允许：
      - (model, device)
      - (model, device, encode_fn)
      - {'model':..., 'device':..., 'encode':...}
      - 自定义对象：有 .encode(...) / .device
    """
    model = None
    device = "cpu"
    encode = None

    if isinstance(vcome, (tuple, list)):
        if len(vcome) >= 3:
            model, device, encode = vcome[0], vcome[1], vcome[2]
        elif len(vcome) == 2:
            model, device = vcome[0], vcome[1]
            encode = getattr(model, "encode", None) or getattr(model, "encode_func", None)
        elif len(vcome) == 1:
            model = vcome[0]
            device = getattr(model, "device", "cpu")
            encode = getattr(model, "encode", None) or getattr(model, "encode_func", None)
    elif isinstance(vcome, dict):
        model = vcome.get("model") or vcome.get("m")
        device = vcome.get("device", "cpu")
        encode = vcome.get("encode") or vcome.get("encoder")
    else:
        model = vcome
        device = getattr(vcome, "device", "cpu")
        encode = getattr(vcome, "encode", None) or getattr(vcome, "encode_func", None)

    return model, device, encode

def _vec_norm(x: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(x))
    return x if n == 0.0 else (x / (n + 1e-8))

def _fallback_embed(f: dict) -> np.ndarray:
    """
    VCoME 不可用时的稳健特征（结构+副作用摘要），维度固定、可归一化。
    """
    nodes = f.get("nodes", [])

    # CFG/PDG 取边（可能是 list 或 dict）
    cfg = f.get("cfg", {}) or {}
    cfg_edges = cfg.get("edges", []) if isinstance(cfg, dict) else (cfg or [])

    pdg = f.get("pdg", {}) or {}
    data_edges = pdg.get("data_edges", [])
    ctrl_edges = pdg.get("control_edges", [])

    feats: List[float] = []

    # 基础规模特征
    feats += [len(nodes), len(cfg_edges), len(data_edges), len(ctrl_edges)]

    # 副作用计数（与 E-PDG 的 flags 对齐）
    eff_keys = [
        "FILE_IO", "NET_IO", "DB_IO", "ENV", "RNG", "TIME", "EXC",
        "R_GLOBAL", "W_GLOBAL", "R_HEAP", "W_HEAP", "R_STACK", "W_STACK"
    ]
    counts = {k: 0 for k in eff_keys}
    for n in nodes:
        eff = n.get("effects") or {}
        flags = eff.get("flags") if isinstance(eff, dict) else {}
        if isinstance(flags, dict):
            for k in eff_keys:
                if flags.get(k):
                    counts[k] += 1
    feats += [counts[k] for k in eff_keys]

    # 度统计（鲁棒解析不同边结构）
    deg = {}
    for (s, t) in _edge_pairs(cfg_edges):
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1
    for (s, t) in _edge_pairs(data_edges):
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1
    for (s, t) in _edge_pairs(ctrl_edges):
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1

    deg_vals = list(deg.values()) or [0]
    feats += [float(np.mean(deg_vals)), float(np.std(deg_vals)), float(np.max(deg_vals))]

    v = np.array(feats, dtype="float32")
    return _vec_norm(v)

def _default_vcome_encode(f: dict, model: Any, device: str) -> np.ndarray:
    """
    vcome 给出 (model, device) 但没有 encode_fn 的情况，尝试 model.encode(...)
    失败则回退。
    """
    enc = getattr(model, "encode", None) or getattr(model, "encode_func", None)
    if callable(enc):
        try:
            try:
                vec = enc(f, device)  # 签名 (f, device)
            except TypeError:
                vec = enc(f)          # 签名 (f)
        except Exception:
            return _fallback_embed(f)

        vec = np.asarray(vec, dtype="float32")
        return _vec_norm(vec)

    return _fallback_embed(f)

def _embed(f: dict, use_vcome: bool = False, vcome: Any = None) -> np.ndarray:
    """
    根据是否启用 VCoME 选择编码方式；任何异常都回退到稳健嵌入。
    """
    if use_vcome and vcome is not None:
        m, dev, enc = _coerce_vcome(vcome)

        # 显式的 encode_fn 优先
        if callable(enc):
            try:
                try:
                    vec = enc(f, m, dev)  # 最通用签名 (f, model, device)
                except TypeError:
                    try:
                        vec = enc(f)      # (f)
                    except TypeError:
                        try:
                            vec = enc(f, dev)  # (f, device)
                        except TypeError:
                            vec = enc(f, m)    # (f, model)
                vec = np.asarray(vec, dtype="float32")
                return _vec_norm(vec)
            except Exception:
                return _fallback_embed(f)

        # 否则尝试 model 自带 encode(...)
        return _default_vcome_encode(f, m, dev)

    # 未启用/加载失败 → 回退
    return _fallback_embed(f)


# ======================================================================
# 4) rerank：把候选（LSH/ANN 粗排）按向量余弦重排并融合
# ======================================================================

def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    da = float(np.linalg.norm(a))
    db = float(np.linalg.norm(b))
    if da == 0.0 or db == 0.0:
        return 0.0
    return float(np.dot(a, b) / (da * db + 1e-8))

def rerank(
    func_map: Dict[str, dict],
    query_ids: List[str],
    candidate_ids: Dict[str, List[Any]],
    topk: int = 50,
    use_vcome: bool = False,
    vcome_ckpt: str | None = None,
) -> Dict[str, List[Tuple[str, float, dict]]]:
    """
    输入：
      - func_map: { func_id -> 函数 JSON 对象 }
      - query_ids: [qid, ...]
      - candidate_ids:
          { qid -> [cid, ...] }
        或 { qid -> [(cid, base_score), ...] }
      - topk: 每个 qid 取前 k 个
      - use_vcome / vcome_ckpt: 是否启用 VCoME（失败会自动回退）

    输出：
      { qid: [ (cid, score, meta), ... ] }
    其中 meta 至少包含 "align_pairs": []（供报告联动高亮；若后续加入对齐器，可把映射写入这里）。
    """
    # 尝试加载 VCoME
    vcome_obj = None
    if use_vcome:
        try:
            from ranking.enc_vcome import load_model as _load_vcome_model
            if vcome_ckpt:
                vcome_obj = _load_vcome_model(vcome_ckpt)
        except Exception:
            vcome_obj = None  # 失败自动回退

    # 需要编码的函数 id 集合
    all_ids = set(query_ids)
    for qid in query_ids:
        for item in candidate_ids.get(qid, []):
            cid = item[0] if isinstance(item, (tuple, list)) else item
            all_ids.add(cid)

    # 计算向量
    Z: Dict[str, np.ndarray] = {}
    for fid in all_ids:
        f = func_map.get(fid)
        if f is None:
            continue
        Z[fid] = _embed(f, use_vcome=use_vcome, vcome=vcome_obj)

    # 对每个 qid 重排候选
    out: Dict[str, List[Tuple[str, float, dict]]] = {}
    for qid in query_ids:
        qv = Z.get(qid)
        if qv is None:
            continue

        sims: List[Tuple[str, float, dict]] = []
        for item in candidate_ids.get(qid, []):
            if isinstance(item, (tuple, list)):
                cid = item[0]
                base = float(item[1]) if len(item) > 1 else 0.0
            else:
                cid = item
                base = 0.0

            if cid == qid:
                continue

            cv = Z.get(cid)
            if cv is None:
                continue
            # 对齐分：依赖一致对齐（若 JSON 含 nodes/pdg）
            s_align = 0.0; apairs = []
            try:
                from ranking.align_dep import dep_consistent_align
                s_align, pairs, _ainfo = dep_consistent_align(qf, cf)
                apairs = [(int(a), int(b)) for a,b,_ in pairs]
            except Exception:
                pass

            cos = _cos_sim(qv, cv)
            # 融合权重（经验值）：余弦 0.6 + 基础分 0.1 + 对齐 0.3
            W_COS, W_BASE, W_ALIGN = 0.6, 0.1, 0.3
            score = W_COS * cos + W_BASE * base + W_ALIGN * s_align
            sims.append((cid, float(score), {"align_pairs": apairs}))

        sims.sort(key=lambda x: x[1], reverse=True)
        out[qid] = sims[:topk]

    return out


# ======================================================================
# 可选：简单自检
# ======================================================================
if __name__ == "__main__":
    # 仅做最基础的导入/类型签名检查
    print("ranking.rerank loaded. Exposed:", __all__)
