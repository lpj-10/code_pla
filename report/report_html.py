# report/report_html.py
from __future__ import annotations

"""Interactive HTML report for pairwise similarity.

This module consumes the JSON structure produced by
:smod:`scripts.search_and_rank_multi` and renders a **self‑contained**
HTML file with:

* a summary table of suspicious program pairs
* for each pair:
  - a function‑level similarity table
  - side‑by‑side source code panes
  - an IR / E‑PDG panel per matched function

Compared to the previous version，本版在前端上做了两件事：

1. 点击函数匹配行（语义块）时，不仅高亮两侧源码行，还会：
   * 在下方的 IR / E‑PDG 面板中高亮对应的函数级子图容器；
2. IR 面板里的每条 IR 节点都是可点击的：
   * 点击某个 IR 节点，会高亮对应行号的源码（左右两边一起高亮），
     并突出该 IR 节点本身。

这样就实现了你提的「点击语义块高亮两边源码和 IR」以及
「函数级 E‑PDG 子图高亮」的需求。
"""

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, List

import json
import html
import math


def _escape(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _load_template_info(json_root: Path) -> Dict[str, Dict[str, Any]]:
    """Load DACD template-cluster information if available.

    We look for a file named ``dacd_clusters.json`` under ``json_root``.
    For each cluster marked ``is_template_like == true``, we assign a
    per-function record:

    .. code-block:: json

        {
          "weight": <float in (0, 1]>,
          "cluster_id": <int>
        }

    The exact weight formula mirrors the heuristic used in the scoring
    script: larger clusters and clusters spread across many files obtain
    smaller weights (stronger downweighting).
    """
    path = json_root / "dacd_clusters.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    clusters = data.get("clusters") or []
    info: Dict[str, Dict[str, Any]] = {}

    for cid, c in enumerate(clusters):
        try:
            if not c.get("is_template_like"):
                continue
            members = c.get("members") or []
            if not members:
                continue
            size = int(c.get("size") or len(members) or 1)
            distinct_files = int(c.get("distinct_files") or 1)
        except Exception:
            continue

        # Heuristic: same shape as in search_and_rank.py
        size_term = 1.0 / float(max(2.0, math.log(2.0 + float(size))))
        spread_term = 1.0 / float(max(2.0, math.log(2.0 + float(distinct_files))))
        w = size_term * spread_term * 2.0
        if w < 0.1:
            w = 0.1
        if w > 0.8:
            w = 0.8

        for fid in members:
            fid_str = str(fid)
            prev = info.get(fid_str)
            # If a function appears in multiple template clusters, keep the
            # strongest downweight (smallest weight).
            if prev is None or w < float(prev.get("weight", 1.0)):
                info[fid_str] = {"cluster_id": int(cid), "weight": float(w)}

    return info



# ---------------------------------------------------------------------------
# E-PDG / IR 索引：从 json_root 重新读取 *.epdg.json
# ---------------------------------------------------------------------------

def _build_epdg_index(json_root: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Scan all *.epdg.json and build an index:

    index[file_key][func_id] -> raw function dict from E-PDG JSON.

    file_key 统一使用文件名（不含路径），这样可以和 ProgramInfo.file
    里常见的「相对路径/文件名」对齐。
    """
    index: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not json_root.exists():
        return index

    for jf in sorted(json_root.rglob("*.epdg.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        file_field = data.get("file") or jf.stem
        file_key = Path(file_field).name
        func_map: Dict[str, Dict[str, Any]] = index.setdefault(file_key, {})
        for f in data.get("functions", []):
            fid = f.get("id") or f.get("func_id") or f.get("name") or "<unknown>"
            func_map[str(fid)] = f
    return index


def _lookup_func_epdg(
    epdg_index: Mapping[str, Mapping[str, Mapping[str, Any]]],
    file_path: str,
    func_id: str,
) -> Mapping[str, Any] | None:
    file_key = Path(file_path).name
    by_file = epdg_index.get(file_key)
    if not by_file:
        return None
    return by_file.get(str(func_id))


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_code_pane(prog: Mapping[str, Any], role: str) -> str:
    """Render a single code pane.

    ``role`` is "a" or "b" used by JS query selectors.
    """
    code = prog.get("code", "") or ""
    lines = code.splitlines()
    buf: List[str] = []
    buf.append(
        f'<div class="code-pane" data-prog-id="{_escape(prog.get("prog_id"))}" '
        f'data-prog-role="{_escape(role)}">'
    )
    header = (
        f'{_escape(prog.get("file", ""))}'
        f' &nbsp; <span class="lang">{_escape(prog.get("language", ""))}</span>'
    )
    buf.append(f'<div class="code-header">{header}</div>')
    buf.append('<pre class="code"><code>')
    if not lines:
        buf.append(
            '<span class="ln"><span class="no"> </span>'
            '<em>[source not available]</em></span>'
        )
    else:
        for i, line in enumerate(lines, start=1):
            safe = _escape(line.rstrip("\n"))
            buf.append(
                f'<span class="ln" data-line="{i}">'
                f'<span class="no">{i:4d}</span> {safe}'
                '</span>'
            )
    buf.append('</code></pre>')
    buf.append('</div>')
    return "\n".join(buf)



def _render_func_table(
    pair_idx: int,
    pair: Mapping[str, Any],
    template_info: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    rows: List[str] = []
    for idx, m in enumerate(pair.get("func_matches", [])):
        fa = m.get("func_a", {})
        fb = m.get("func_b", {})
        fid_a = str(fa.get("func_id", ""))
        fid_b = str(fb.get("func_id", ""))

        # Decide template label for this match.
        has_tmpl_a = bool(template_info and fid_a and fid_a in template_info)
        has_tmpl_b = bool(template_info and fid_b and fid_b in template_info)
        if has_tmpl_a and has_tmpl_b:
            tmpl_label = "A+B template"
        elif has_tmpl_a:
            tmpl_label = "A template"
        elif has_tmpl_b:
            tmpl_label = "B template"
        else:
            tmpl_label = ""

        rows.append(
            f'<tr class="func-row" '
            f'data-pair-id="{pair_idx}" '
            f'data-idx="{idx}" '
            f'data-a-start="{fa.get("start_line", 1)}" '
            f'data-a-end="{fa.get("end_line", 1)}" '
            f'data-b-start="{fb.get("start_line", 1)}" '
            f'data-b-end="{fb.get("end_line", 1)}">'
            f'<td>{idx + 1}</td>'
            f'<td>{_escape(fa.get("name", ""))}</td>'
            f'<td>{_escape(fb.get("name", ""))}</td>'
            f'<td>{m.get("score", 0.0):.3f}</td>'
            f'<td>'
            f'<span class="tmpl-pill">{_escape(tmpl_label)}</span>' if tmpl_label else ''
            f'</td>'
            '</tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="5"><em>No high-confidence function matches.</em></td></tr>')
    header = (
        '<thead><tr>'
        '<th>#</th><th>Function A</th><th>Function B</th><th>Similarity</th><th>Template</th>'
        '</tr></thead>'
    )
    body = '<tbody>\n' + '\n'.join(rows) + '\n</tbody>'
    return f'<table class="func-table">{header}{body}</table>'




def _compute_blocks(epdg_func: Mapping[str, Any]) -> Tuple[Dict[int, int], List[Dict[str, Any]]]:
    """Derive a coarse block partition of an E-PDG function graph for UI highlighting.

    We treat blocks as connected components over the union of CFG data/control edges.
    Effect edges通常是 node→资源，不直接连结两个 IR 节点，因此在这里不计入连通性。

    Returns
    -------
    nid_to_block:
        映射每个 nid -> block index（0..B-1）。
    blocks:
        一个按源码行号排序的 block 元信息列表，每个元素包含:
        {"id": int, "nids": List[int], "line_min": int, "line_max": int}
    """
    nodes = epdg_func.get("nodes") or []
    if not nodes:
        return {}, []

    from collections import defaultdict

    adj: Dict[int, set] = defaultdict(set)

    def _add_edge(u: Any, v: Any) -> None:
        try:
            ui = int(u)
            vi = int(v)
        except Exception:
            return
        if ui == vi:
            return
        adj[ui].add(vi)
        adj[vi].add(ui)

    # 初始化所有 nid，避免孤立节点丢失
    for n in nodes:
        nid = n.get("nid")
        try:
            ni = int(nid)
        except Exception:
            continue
        adj.setdefault(ni, set())

    cfg = epdg_func.get("cfg") or {{}}
    for e in cfg.get("edges", []) or []:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            _add_edge(e[0], e[1])

    pdg = epdg_func.get("pdg") or {{}}
    for e in pdg.get("data_edges", []) or []:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            _add_edge(e[0], e[1])
    for e in pdg.get("control_edges", []) or []:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            _add_edge(e[0], e[1])

    # 如果没有任何边，就把所有节点视为单一 block
    if not any(adj.values()):
        nids = []
        line_nums: List[int] = []
        for n in nodes:
            nid = n.get("nid")
            try:
                ni = int(nid)
            except Exception:
                continue
            nids.append(ni)
            ln = n.get("lineno") or 0
            if ln:
                line_nums.append(int(ln))
        meta = {
            "id": 0,
            "nids": nids,
            "line_min": min(line_nums) if line_nums else 0,
            "line_max": max(line_nums) if line_nums else 0,
        }
        nid_to_block = {ni: 0 for ni in nids}
        return nid_to_block, [meta]

    # DFS 找连通分量
    nid_to_block: Dict[int, int] = {}
    blocks_meta: List[Dict[str, Any]] = []
    current_block = 0

    for nid in sorted(adj.keys()):
        if nid in nid_to_block:
            continue
        stack = [nid]
        comp: List[int] = []
        while stack:
            u = stack.pop()
            if u in nid_to_block:
                continue
            nid_to_block[u] = current_block
            comp.append(u)
            for v in adj.get(u, ()):
                if v not in nid_to_block:
                    stack.append(v)

        comp_nodes = [n for n in nodes if n.get("nid") in comp]
        line_nums: List[int] = []
        for n in comp_nodes:
            ln = n.get("lineno") or 0
            if ln:
                line_nums.append(int(ln))
        meta = {
            "id": current_block,
            "nids": comp,
            "line_min": min(line_nums) if line_nums else 0,
            "line_max": max(line_nums) if line_nums else 0,
        }
        blocks_meta.append(meta)
        current_block += 1

    # 按行号排序，并把 block id 压缩成 0..B-1
    blocks_meta.sort(key=lambda m: ((m.get("line_min") or 0), m.get("id") or 0))
    remap = {meta["id"]: idx for idx, meta in enumerate(blocks_meta)}
    for meta in blocks_meta:
        meta["nids"] = list(meta.get("nids") or [])
        old_id = meta["id"]
        meta["id"] = remap.get(old_id, 0)

    nid_to_block = {nid: remap.get(bid, 0) for nid, bid in nid_to_block.items()}
    return nid_to_block, blocks_meta

def _render_ir_pane(
    epdg_func: Mapping[str, Any] | None,
    side: str,
    pair_idx: int,
    match_idx: int,
) -> str:
    """Render IR + a lightweight E-PDG textual view for one side of a function match.

    本版本在函数粒度之上，进一步对 E-PDG 做了一个**粗粒度的 block 切分**，
    主要用于「块级子图高亮」的前端交互：
      * 使用 CFG + PDG(data/control) 的连通分量作为 block；
      * 为每个 block 计算一个近似的源码行号区间 [line_min, line_max]；
      * 为 IR 节点 / PDG 节点 / effect edges 打上 data-block-id，供前端按块高亮。
    """
    label_side = "A" if side == "a" else "B"
    if not epdg_func:
        return (
            f'<div class="ir-pane" data-side="{_escape(side)}">'
            f'<div class="ir-header">Side {label_side} – IR / E-PDG</div>'
            '<div class="ir-body"><em>[no E-PDG available]</em></div>'
            '</div>'
        )

    nodes = list(epdg_func.get("nodes") or [])
    pdg = epdg_func.get("pdg") or {}
    effect_edges = list(pdg.get("effect_edges") or [])
    data_edges = list(pdg.get("data_edges") or [])
    control_edges = list(pdg.get("control_edges") or [])

    # 计算块级划分
    nid_to_block, blocks = _compute_blocks(epdg_func)
    # 兜底：如果构不出 block，但有节点，就统一视为一个 block
    if not blocks and nodes:
        nids: List[int] = []
        line_nums: List[int] = []
        for n in nodes:
            nid = n.get("nid")
            try:
                ni = int(nid)
            except Exception:
                continue
            nids.append(ni)
            ln = n.get("lineno") or 0
            if ln:
                line_nums.append(int(ln))
        blocks = [{
            "id": 0,
            "nids": nids,
            "line_min": min(line_nums) if line_nums else 0,
            "line_max": max(line_nums) if line_nums else 0,
        }]
        nid_to_block = {ni: 0 for ni in nids}

    buf: List[str] = []
    buf.append(
        f'<div class="ir-pane" data-side="{_escape(side)}">'
        f'<div class="ir-header">Side {label_side} – IR / E-PDG</div>'
        '<div class="ir-body">'
    )

    # Block chip bar
    buf.append('<div class="block-bar">')
    if not blocks:
        buf.append('<span class="block-chip"><em>[no IR blocks]</em></span>')
    else:
        for meta in blocks:
            bid = meta.get("id", 0)
            line_min = int(meta.get("line_min") or 0)
            line_max = int(meta.get("line_max") or 0)
            nids = meta.get("nids") or []
            label = f"Block {bid + 1}"
            if line_min or line_max:
                if line_max and line_max != line_min:
                    label += f" (lines {line_min}-{line_max}"
                else:
                    label += f" (line {line_min}"
                if nids:
                    label += f", {len(nids)} nodes)"
                else:
                    label += ")"
            elif nids:
                label += f" ({len(nids)} nodes)"
            buf.append(
                f'<span class="block-chip" '
                f'data-pair-id="{pair_idx}" '
                f'data-match-idx="{match_idx}" '
                f'data-side="{_escape(side)}" '
                f'data-block-id="{bid}" '
                f'data-line-start="{line_min}" '
                f'data-line-end="{line_max}">{_escape(label)}</span>'
            )
    buf.append('</div>')  # .block-bar

    # IR 节点列表（可点击）
    buf.append('<div class="ir-node-list">')
    if not nodes:
        buf.append('<div class="ir-node"><em>[no IR nodes]</em></div>')
    else:
        # 按行号 / nid 排序，方便用户浏览
        def _sort_key(n: Mapping[str, Any]) -> Tuple[int, int]:
            ln = n.get("lineno") or 0
            try:
                nid = int(n.get("nid"))
            except Exception:
                nid = 0
            return int(ln), nid

        for n in sorted(nodes, key=_sort_key):
            nid_val = n.get("nid", "?")
            lineno = n.get("lineno") or 0
            kind = n.get("kind", "?")
            try:
                bid = nid_to_block.get(int(nid_val), 0)
            except Exception:
                bid = 0
            desc = f"n{nid_val} @ line {lineno} – {kind}"
            buf.append(
                f'<div class="ir-node" '
                f'data-pair-id="{pair_idx}" '
                f'data-match-idx="{match_idx}" '
                f'data-side="{_escape(side)}" '
                f'data-line="{lineno}" '
                f'data-nid="{nid_val}" '
                f'data-block-id="{bid}">{_escape(desc)}</div>'
            )
    buf.append('</div>')  # .ir-node-list

    # E-PDG 文本视图（节点 + 资源边）
    buf.append('<div class="pdg-view">')
    # 简单的节点行
    buf.append('<div class="pdg-nodes">')
    for n in nodes:
        nid_val = n.get("nid", "?")
        lineno = n.get("lineno") or 0
        try:
            bid = nid_to_block.get(int(nid_val), 0)
        except Exception:
            bid = 0
        buf.append(
            f'<span class="pdg-node" '
            f'data-nid="{nid_val}" '
            f'data-line="{lineno}" '
            f'data-block-id="{bid}">n{nid_val}</span>'
        )
    buf.append('</div>')  # .pdg-nodes

    # 只展示 effect_edges，控制/数据边用计数提示
    if effect_edges:
        buf.append('<div class="pdg-edges">')
        for src, tgt, kind in effect_edges[:80]:
            try:
                bid = nid_to_block.get(int(src), 0)
            except Exception:
                bid = 0
            buf.append(
                '<div class="pdg-edge" '
                f'data-src="{src}" '
                f'data-kind="{_escape(kind)}" '
                f'data-block-id="{bid}">'
                f'n{src} --[{_escape(kind)}]→ {_escape(tgt)}</div>'
            )
        if len(effect_edges) > 80:
            buf.append(
                f'<div class="pdg-edge-more">… {len(effect_edges) - 80} more edges</div>'
            )
        buf.append('</div>')  # .pdg-edges
    else:
        buf.append('<div class="pdg-edges"><em>[no effect edges]</em></div>')

    if data_edges or control_edges:
        buf.append(
            f'<div class="pdg-summary">'
            f'data edges: {len(data_edges)}, control edges: {len(control_edges)}</div>'
        )
    buf.append('</div>')  # .pdg-view

    buf.append('</div></div>')  # .ir-body, .ir-pane
    return "\n".join(buf)
def _render_ir_match_block(
    pair_idx: int,
    match_idx: int,
    match: Mapping[str, Any],
    epdg_index: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> str:
    fa = match.get("func_a", {})
    fb = match.get("func_b", {})
    fa_epdg = _lookup_func_epdg(epdg_index, fa.get("file", ""), fa.get("func_id", ""))
    fb_epdg = _lookup_func_epdg(epdg_index, fb.get("file", ""), fb.get("func_id", ""))

    header = (
        f'Match {match_idx + 1}: '
        f'{_escape(fa.get("name", ""))} ↔ {_escape(fb.get("name", ""))} '
        f'(score={match.get("score", 0.0):.3f})'
    )

    left = _render_ir_pane(fa_epdg, side="a", pair_idx=pair_idx, match_idx=match_idx)
    right = _render_ir_pane(fb_epdg, side="b", pair_idx=pair_idx, match_idx=match_idx)

    return (
        f'<div class="ir-match" data-pair-id="{pair_idx}" data-match-idx="{match_idx}">'
        f'<div class="ir-match-header">{header}</div>'
        f'<div class="ir-graph-columns">{left}{right}</div>'
        '</div>'
    )


def _render_pair_section(
    idx: int,
    pair: Mapping[str, Any],
    prog_map: Mapping[int, Mapping[str, Any]],
    epdg_index: Mapping[str, Mapping[str, Mapping[str, Any]]],
    template_info: Mapping[str, Mapping[str, Any]] | None,
) -> str:
    pid_a = pair.get("prog_a")
    pid_b = pair.get("prog_b")
    prog_a = dict(prog_map[pid_a])
    prog_b = dict(prog_map[pid_b])
    prog_a["prog_id"] = pid_a
    prog_b["prog_id"] = pid_b

    header = (
        f'<h2 id="pair-{idx}">Pair {idx + 1}: '
        f'{_escape(prog_a.get("file", ""))} ↔ {_escape(prog_b.get("file", ""))} '
        f'(score = {pair.get("score", 0.0):.3f})</h2>'
    )

    func_table = _render_func_table(idx, pair, template_info=template_info)
    code_a = _render_code_pane(prog_a, role="a")
    code_b = _render_code_pane(prog_b, role="b")

    # IR / E-PDG 面板：为该 pair 的每个函数匹配生成一块
    ir_blocks: List[str] = []
    for midx, m in enumerate(pair.get("func_matches", [])):
        ir_blocks.append(_render_ir_match_block(idx, midx, m, epdg_index))
    if not ir_blocks:
        ir_panel = '<div class="ir-panel"><em>No function-level matches for this pair.</em></div>'
    else:
        ir_panel = '<div class="ir-panel">' + "".join(ir_blocks) + '</div>'

    return (
        f'<section class="pair" id="pair-{idx}">'
        f'{header}'
        '<div class="pair-content">'
        f'<div class="func-table-wrapper">{func_table}</div>'
        f'<div class="code-columns">{code_a}{code_b}</div>'
        '</div>'
        f'{ir_panel}'
        '</section>'
    )


def _render_summary_table(
    pairs: Sequence[Mapping[str, Any]],
    prog_map: Mapping[int, Mapping[str, Any]],
    template_info: Mapping[str, Mapping[str, Any]] | None,
) -> str:
    rows: List[str] = []
    for idx, pair in enumerate(pairs):
        pid_a = pair.get("prog_a")
        pid_b = pair.get("prog_b")
        pa = prog_map.get(pid_a, {})
        pb = prog_map.get(pid_b, {})
        rows.append(
            '<tr>'
            f'<td>{idx + 1}</td>'
            f'<td><a href="#pair-{idx}">{_escape(pa.get("file", ""))}</a></td>'
            f'<td><a href="#pair-{idx}">{_escape(pb.get("file", ""))}</a></td>'
            f'<td>{pair.get("score", 0.0):.3f}</td>'
            '</tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="4"><em>No suspicious pairs above threshold.</em></td></tr>')

    header = (
        '<thead><tr>'
        '<th>#</th><th>Program A</th><th>Program B</th><th>Similarity</th>'
        '</tr></thead>'
    )
    body = '<tbody>\n' + '\n'.join(rows) + '\n</tbody>'
    return f'<table class="summary-table">{header}{body}</table>'


# ---------------------------------------------------------------------------
# HTML skeleton + JS
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      padding: 0 1.5rem 3rem;
      background: #f7f7f9;
    }}
    h1 {{
      margin-top: 1.5rem;
      font-size: 1.8rem;
    }}
    h2 {{
      margin-top: 2rem;
      font-size: 1.4rem;
    }}
    .meta {{
      margin: 0.5rem 0 1.5rem;
      color: #555;
      font-size: 0.9rem;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
    }}
    th, td {{
      border: 1px solid #e0e0e0;
      padding: 0.4rem 0.6rem;
      font-size: 0.9rem;
    }}
    th {{
      background: #f0f0f5;
      text-align: left;
    }}
    .summary-table {{
      margin-bottom: 1.5rem;
    }}
    .pair {{
      margin: 1.5rem 0;
      padding: 1rem 1rem 1.2rem;
      border-radius: 12px;
      background: #ffffff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }}
    .pair-content {{
      display: grid;
      grid-template-columns: minmax(280px, 320px) 1fr;
      gap: 1rem;
      align-items: flex-start;
    }}
    .func-table-wrapper {{
      max-height: 360px;
      overflow: auto;
      border-radius: 8px;
      border: 1px solid #e0e0e0;
      background: #fafbff;
    }}
    .func-table thead th {{
      position: sticky;
      top: 0;
      background: #f0f0f8;
      z-index: 1;
    }
    .tmpl-pill {
      display: inline-block;
      padding: 0.1rem 0.35rem;
      border-radius: 999px;
      font-size: 0.7rem;
      background: #fef3c7;
      color: #92400e;
      border: 1px solid #fde68a;
      white-space: nowrap;
    }
}
    .func-row {{
      cursor: pointer;
    }}
    .func-row:hover {{
      background: #eef2ff;
    }}
    .code-columns {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }}
    .code-pane {{
      border-radius: 8px;
      background: #0b1020;
      color: #f5f5f5;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      max-height: 420px;
    }}
    .code-header {{
      background: #151a30;
      padding: 0.35rem 0.6rem;
      font-size: 0.75rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .code-header .lang {{
      opacity: 0.7;
      font-weight: 500;
    }}
    .code {{
      margin: 0;
      padding: 0.4rem 0.8rem 0.6rem;
      overflow: auto;
    }}
    .code .ln {{
      display: block;
      white-space: pre;
    }}
    .code .no {{
      display: inline-block;
      width: 3.5em;
      color: #5f6475;
      margin-right: 0.25rem;
    }}
    .code .ln.mark {{
      background: #2d3a5f;
    }}

    /* IR / E-PDG panel */
    /* Block-level E-PDG chips */
    .block-bar {{
      margin: 0.25rem 0 0.4rem;
      font-size: 0.75rem;
    }}
    .block-chip {{
      display: inline-block;
      padding: 0.12rem 0.35rem;
      margin: 0 0.25rem 0.18rem 0;
      border-radius: 999px;
      background: #f1f2fb;
      border: 1px solid #d4d7f5;
      cursor: pointer;
      white-space: nowrap;
    }}
    .block-chip:hover {{
      background: #e3e6ff;
    }}
    .block-chip.active-block {{
      background: #4f46e5;
      border-color: #3730a3;
      color: #ffffff;
    }}

    .ir-panel {{
      margin-top: 1rem;
      padding-top: 0.5rem;
      border-top: 1px dashed #ddd;
    }}
    .ir-match {{
      border-radius: 8px;
      border: 1px solid #e0e0e0;
      padding: 0.5rem 0.7rem 0.6rem;
      margin: 0.5rem 0;
      background: #fafafe;
    }}
    .ir-match-header {{
      font-size: 0.86rem;
      margin-bottom: 0.35rem;
      color: #333;
    }}
    .ir-match.active {{
      border-color: #5163ff;
      box-shadow: 0 0 0 1px rgba(81,99,255,0.18);
      background: #f3f4ff;
    }}
    .ir-graph-columns {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }}
    .ir-pane {{
      border-radius: 6px;
      border: 1px solid #e0e0e0;
      background: #ffffff;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      max-height: 220px;
      overflow: hidden;
    }}
    .ir-header {{
      background: #f5f5fb;
      padding: 0.25rem 0.4rem;
      font-weight: 500;
      font-size: 0.78rem;
    }}
    .ir-body {{
      padding: 0.25rem 0.4rem 0.35rem;
      overflow: auto;
      display: grid;
      grid-template-columns: minmax(160px, 1.2fr) minmax(180px, 1.3fr);
      gap: 0.4rem;
    }}
    .ir-node-list {{
      border-right: 1px dashed #e0e0e0;
      padding-right: 0.3rem;
    }}
    .ir-node {{
      padding: 0.12rem 0.2rem;
      border-radius: 4px;
      cursor: pointer;
      margin-bottom: 0.08rem;
    }}
    .ir-node:hover {{
      background: #eef2ff;
    }}
    .ir-node.mark-ir {{
      background: #d6e0ff;
      border: 1px solid #5163ff;
    }}
    .pdg-view {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }}
    .pdg-nodes {{
      margin-bottom: 0.25rem;
    }}
    .pdg-node {{
      display: inline-block;
      padding: 0.05rem 0.18rem;
      margin: 0 0.08rem 0.08rem 0;
      border-radius: 3px;
      background: #f0f2ff;
      font-size: 0.7rem;
    }}
    .pdg-node.mark-ir {{
      background: #d6e0ff;
      font-weight: 600;
    }}
    .pdg-edge.mark-ir {{
      background: #eef2ff;
      font-weight: 600;
    }}

    .pdg-edge {{
      font-size: 0.72rem;
      margin-bottom: 0.08rem;
    }}
    .pdg-summary {{
      margin-top: 0.2rem;
      font-size: 0.72rem;
      color: #666;
    }}
    .pdg-more {{
      font-size: 0.72rem;
      color: #999;
    }}

    @media (max-width: 1100px) {{
      .pair-content {{
        grid-template-columns: 1fr;
      }}
      .code-columns {{
        grid-template-columns: 1fr;
      }}
      .ir-graph-columns {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">
    Total programs: {num_programs} &nbsp;|&nbsp;
    Suspicious pairs: {num_pairs} &nbsp;|&nbsp;
    Token weight α = {alpha:.2f}, prog_threshold = {prog_th:.2f}, func_threshold = {func_th:.2f}
  </div>

  <h2>Summary of program pairs</h2>
  {summary_table}

  {pair_sections}

  

<script>
  (function() {{

    function clearHighlightsInSection(section) {{
      section.querySelectorAll('.code-pane .ln.mark').forEach(function(el) {{
        el.classList.remove('mark');
      }});
      section.querySelectorAll('.ir-node.mark-ir').forEach(function(el) {{
        el.classList.remove('mark-ir');
      }});
      section.querySelectorAll('.block-chip.active-block').forEach(function(el) {{
        el.classList.remove('active-block');
      }});
      // 保留 .ir-match.active，由函数级点击控制
    }}

    function markRange(section, selectorBase, start, end) {{
      if (!section) return;
      if (!start && !end) return;
      var s = start || end || 0;
      var e = end || start || s;
      if (s > e) {{
        var tmp = s; s = e; e = tmp;
      }}
      var panes = section.querySelectorAll(selectorBase);
      panes.forEach(function(pane) {{
        var lines = pane.querySelectorAll('.ln');
        lines.forEach(function(lnEl) {{
          var ln = parseInt(lnEl.getAttribute('data-line') || '0', 10);
          if (ln >= s && ln <= e) {{
            lnEl.classList.add('mark');
          }}
        }});
      }});
    }}

    function onFuncRowClick(ev) {{
      var row = ev.currentTarget;
      var pairId = row.getAttribute('data-pair-id');
      var matchIdx = row.getAttribute('data-idx');
      var aStart = parseInt(row.getAttribute('data-a-start') || '1', 10);
      var aEnd   = parseInt(row.getAttribute('data-a-end')   || String(aStart), 10);
      var bStart = parseInt(row.getAttribute('data-b-start') || '1', 10);
      var bEnd   = parseInt(row.getAttribute('data-b-end')   || String(bStart), 10);

      var section = document.getElementById('pair-' + pairId);
      if (!section) return;

      clearHighlightsInSection(section);

      // 高亮左右源码
      markRange(section, '.code-pane[data-prog-role="a"]', aStart, aEnd);
      markRange(section, '.code-pane[data-prog-role="b"]', bStart, bEnd);

      // 高亮对应 ir-match 卡片
      section.querySelectorAll('.ir-match').forEach(function(card) {{
        if (card.getAttribute('data-pair-id') === String(pairId) &&
            card.getAttribute('data-match-idx') === String(matchIdx)) {{
          card.classList.add('active');
          card.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
        }} else {{
          card.classList.remove('active');
        }}
      }});
    }}

    function onIrNodeClick(ev) {{
      var node = ev.currentTarget;
      var pairId = node.getAttribute('data-pair-id');
      var matchIdx = node.getAttribute('data-match-idx');
      var side = node.getAttribute('data-side');
      var line = parseInt(node.getAttribute('data-line') || '0', 10);
      var blockId = node.getAttribute('data-block-id');

      var section = document.getElementById('pair-' + pairId);
      if (!section) return;

      // 只清除 IR 节点和源码的高亮，保留 pair 级 active 状态
      section.querySelectorAll('.ir-node.mark-ir').forEach(function(el) {{
        el.classList.remove('mark-ir');
      }});
      section.querySelectorAll('.code-pane .ln.mark').forEach(function(el) {{
        el.classList.remove('mark');
      }});
      section.querySelectorAll('.block-chip.active-block').forEach(function(el) {{
        el.classList.remove('active-block');
      }});

      node.classList.add('mark-ir');

      // 对应 block chip 高亮
      if (blockId !== null && blockId !== undefined) {{
        section.querySelectorAll('.block-chip').forEach(function(chip) {{
          if (chip.getAttribute('data-pair-id') === String(pairId) &&
              chip.getAttribute('data-match-idx') === String(matchIdx) &&
              chip.getAttribute('data-side') === side &&
              chip.getAttribute('data-block-id') === String(blockId)) {{
            chip.classList.add('active-block');
          }}
        }});
      }}

      if (line > 0) {{
        // 双侧按同一行号高亮（对跨语言是近似 anchor）
        ['a', 'b'].forEach(function(role) {{
          var pane = section.querySelector('.code-pane[data-prog-role="' + role + '"]');
          if (!pane) return;
          var lnEl = pane.querySelector('.ln[data-line="' + line + '"]');
          if (lnEl) {{
            lnEl.classList.add('mark');
            lnEl.scrollIntoView({{ block: 'center', behavior: 'smooth' }});
          }}
        }});
      }}
    }}

    function onBlockChipClick(ev) {{
      var chip = ev.currentTarget;
      var pairId = chip.getAttribute('data-pair-id');
      var matchIdx = chip.getAttribute('data-match-idx');
      var side = chip.getAttribute('data-side');
      var blockId = chip.getAttribute('data-block-id');
      var lineStart = parseInt(chip.getAttribute('data-line-start') || '0', 10);
      var lineEnd   = parseInt(chip.getAttribute('data-line-end')   || '0', 10);

      var section = document.getElementById('pair-' + pairId);
      if (!section) return;

      // 重置本 pair 内的高亮
      section.querySelectorAll('.code-pane .ln.mark').forEach(function(el) {{
        el.classList.remove('mark');
      }});
      section.querySelectorAll('.ir-node.mark-ir').forEach(function(el) {{
        el.classList.remove('mark-ir');
      }});
      section.querySelectorAll('.block-chip.active-block').forEach(function(el) {{
        el.classList.remove('active-block');
      }});

      chip.classList.add('active-block');

      // 高亮所有属于该 block 的 IR 节点 / PDG 节点 / effect edges
      section.querySelectorAll('.ir-node').forEach(function(node) {{
        if (node.getAttribute('data-match-idx') === String(matchIdx) &&
            node.getAttribute('data-side') === side &&
            node.getAttribute('data-block-id') === String(blockId)) {{
          node.classList.add('mark-ir');
        }}
      }});
      section.querySelectorAll('.pdg-node').forEach(function(node) {{
        if (node.getAttribute('data-block-id') === String(blockId)) {{
          node.classList.add('mark-ir');
        }}
      }});
      section.querySelectorAll('.pdg-edge').forEach(function(edge) {{
        if (edge.getAttribute('data-block-id') === String(blockId)) {{
          edge.classList.add('mark-ir');
        }}
      }});

      if (lineStart || lineEnd) {{
        markRange(section, '.code-pane[data-prog-role="a"]', lineStart, lineEnd);
        markRange(section, '.code-pane[data-prog-role="b"]', lineStart, lineEnd);
      }}
    }}

    document.addEventListener('DOMContentLoaded', function() {{
      document.querySelectorAll('table.func-table tr.func-row').forEach(function(row) {{
        row.addEventListener('click', onFuncRowClick);
      }});

      document.querySelectorAll('.ir-node').forEach(function(node) {{
        node.addEventListener('click', onIrNodeClick);
      }});

      document.querySelectorAll('.block-chip').forEach(function(chip) {{
        chip.addEventListener('click', onBlockChipClick);
      }});
    }});

  }})();
  </script>


</body>
</html>
"""


def render_pair_report(result: Mapping[str, Any], out_path: str | Path) -> None:
    """Render the interactive HTML report for the given similarity result dict."""
    meta = result.get("meta", {})
    programs = result.get("programs", [])
    pairs = result.get("pairs", [])

    alpha = float(meta.get("alpha", 0.7))
    prog_th = float(meta.get("prog_threshold", 0.6))
    func_th = float(meta.get("func_threshold", 0.6))
    json_root = Path(meta.get("json_root", "."))

    # Optional: load DACD template-cluster information for annotation.
    template_info = _load_template_info(json_root)

    prog_map = {int(p["prog_id"]): p for p in programs if "prog_id" in p}
    summary_table = _render_summary_table(pairs, prog_map, template_info)

    epdg_index = _build_epdg_index(json_root)

    pair_sections: List[str] = []
    for idx, pair in enumerate(pairs):
        pair_sections.append(
            _render_pair_section(idx, pair, prog_map, epdg_index, template_info)
        )

    title = "Code Plagiarism – Pairwise Similarity Report"

    html_text = _HTML_TEMPLATE.format(
        title=title,
        num_programs=len(programs),
        num_pairs=len(pairs),
        alpha=alpha,
        prog_th=prog_th,
        func_th=func_th,
        summary_table=summary_table,
        pair_sections="\n".join(pair_sections),
    )

    out_path = Path(out_path)
    out_path.write_text(html_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Compatibility wrapper for legacy pipeline (search_and_rank.py)
# ---------------------------------------------------------------------------

def render_report(
    out_path: str | Path,
    func_meta: Mapping[str, tuple],
    prog_pairs: Sequence[tuple],
    func_scores: Mapping[str, Sequence[tuple]],
    threshold: float,
    json_root: str | Path = ".",
) -> None:
    """Backward-compatible renderer used by scripts/search_and_rank.py.

    It adapts the older data structures (prog_pairs/func_scores/func_meta)
    into the unified format expected by ``render_pair_report``.
    """

    def _infer_lang(path: str) -> str:
        ext = Path(path).suffix.lower()
        if ext == ".py":
            return "python"
        if ext in {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}:
            return "c/cpp"
        if ext == ".java":
            return "java"
        return "unknown"

    # 1) Collect program list (ids are stable across this rendering).
    prog_paths = sorted({meta[0] for meta in func_meta.values()})
    prog_id: Dict[str, int] = {p: i for i, p in enumerate(prog_paths)}
    programs = [
        {"prog_id": pid, "file": p, "language": _infer_lang(p), "code": ""}
        for p, pid in prog_id.items()
    ]

    # 2) Build pairs with function matches.
    pairs: List[Dict[str, Any]] = []
    for pa, pb, agg, chosen in prog_pairs:
        pair: Dict[str, Any] = {
            "prog_a": prog_id.get(pa, 0),
            "prog_b": prog_id.get(pb, 0),
            "score": float(agg),
            "func_matches": [],
        }
        for qid, cid, score in chosen:
            qa = func_meta.get(qid, (pa, "<unknown>", 0))
            qb = func_meta.get(cid, (pb, "<unknown>", 0))

            # Look up align_pairs meta if present in func_scores.
            align_pairs: List[Any] = []
            for cand_id, _, meta in func_scores.get(qid, []):
                if cand_id == cid:
                    align_pairs = list(meta.get("align_pairs", []))
                    break

            pair["func_matches"].append(
                {
                    "func_a": {
                        "func_id": qid,
                        "name": qa[1],
                        "start_line": qa[2] or 0,
                        "end_line": qa[2] or 0,
                        "file": qa[0],
                    },
                    "func_b": {
                        "func_id": cid,
                        "name": qb[1],
                        "start_line": qb[2] or 0,
                        "end_line": qb[2] or 0,
                        "file": qb[0],
                    },
                    "score": float(score),
                    "align_pairs": align_pairs,
                }
            )
        pairs.append(pair)

    result = {
        "meta": {
            "alpha": 0.0,  # not used in this path
            "prog_threshold": float(threshold),
            "func_threshold": float(threshold),
            "json_root": str(json_root),
        },
        "programs": programs,
        "pairs": pairs,
    }

    render_pair_report(result, out_path)
