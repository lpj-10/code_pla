#!/usr/bin/env python
# scripts/render_clusters_report.py
from __future__ import annotations

"""
从 rerank_candidates_multi.py 生成的 JSON 结果中，读取 program_clusters / per_program / pairs，
生成一个 HTML 聚类报告，并为每一条高风险程序边生成一个简单的“函数级 diff 视图”页面。

整体结构：
  rerank_candidates_multi.json
    -> program_clusters  (M4 聚类结果)
    -> per_program       (程序级聚合统计)
    -> pairs             (逐函数候选对，已带 VCoME / LSH / combined 分数)

  本脚本会输出：
    - 一个总的聚类报告：program_clusters.html
    - 一个 pairs/cluster{cid}_edge{k}.html 目录，里面是每条高风险边的函数级详情页面
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import defaultdict

import sys

# 允许从项目根目录导入 report.py_highlight
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from report.py_highlight import highlight_python
except Exception:  # 容错：如果导入失败，就退化成纯文本输出
    def highlight_python(code: str, mark_lines=None) -> str:  # type: ignore
        import html as _html
        lines = code.splitlines()
        out = ["<pre class='code hl'>"]
        for i, line in enumerate(lines, 1):
            safe = _html.escape(line)
            out.append(f"<div class='ln'><span class='no'>{i:>4}</span> {safe}</div>")
        out.append("</pre>")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _escape_html(s: Any) -> str:
    import html
    return html.escape(str(s), quote=True)


def _short_prog(path: str) -> str:
    return Path(path).name


def _edge_detail_rel_path(cluster_id: int, edge_idx: int) -> str:
    """cluster {cluster_id} 中第 edge_idx 条边对应的详情页面相对路径。"""
    return f"pairs/cluster{cluster_id}_edge{edge_idx}.html"


def _read_source(path: str) -> str:
    try:
        p = Path(path)
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    return ""


def _func_label(meta: Dict[str, Any]) -> str:
    name = meta.get("name") or meta.get("func_name") or "<anon>"
    lineno = meta.get("first_lineno") or meta.get("lineno") or -1
    try:
        lineno = int(lineno)
    except Exception:
        lineno = -1
    if lineno and lineno > 0:
        return f"{name} @L{lineno}"
    return str(name)


def _edge_key(pi: str, pj: str) -> Tuple[str, str]:
    return (pi, pj) if pi <= pj else (pj, pi)


def _build_prog_pair_index(pairs: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """
    把 rerank 之后的逐函数 pairs 按 (program_i, program_j) 分桶，方便后面按程序对取出所有函数对。

    约定：key = (min(pi, pj), max(pi, pj))，列表内部按 combined_score 降序。
    """
    idx: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for p in pairs:
        mi = p.get("meta_i") or {}
        mj = p.get("meta_j") or {}
        pi = mi.get("json_path") or mi.get("prog") or mi.get("program")  # 兼容不同字段名
        pj = mj.get("json_path") or mj.get("prog") or mj.get("program")
        if not pi or not pj:
            continue
        key = _edge_key(str(pi), str(pj))
        idx[key].append(p)

    for key, lst in idx.items():
        lst.sort(key=lambda x: float(x.get("combined_score", 0.0)), reverse=True)
    return idx


# ---------------------------------------------------------------------------
# 详情页面：程序对 -> 函数级“diff 视图”
# ---------------------------------------------------------------------------

def _guess_source_path(func_meta: Dict[str, Any], fallback_prog: str) -> str:
    """尝试从 func id 里解析源码路径，失败则退化到 json_path / prog / fallback。"""
    fid = str(func_meta.get("id", ""))
    if "::" in fid:
        cand = fid.split("::", 1)[0]
        if cand:
            return cand
    jp = func_meta.get("json_path") or func_meta.get("prog") or func_meta.get("program")
    if jp:
        return str(jp)
    return fallback_prog


def _render_edge_detail_page(
    out_path: Path,
    cluster_id: int,
    edge_idx: int,
    prog_i: str,
    prog_j: str,
    func_pairs: List[Dict[str, Any]],
    back_href: str,
    max_funcs: int = 20,
) -> None:
    """为某个程序对渲染一个简单的函数级详情页面。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 小缓存，避免重复读同一源码文件
    source_cache: Dict[str, str] = {}

    def get_source(meta: Dict[str, Any], fallback_prog: str) -> Tuple[str, str]:
        src_path = _guess_source_path(meta, fallback_prog)
        if src_path not in source_cache:
            source_cache[src_path] = _read_source(src_path)
        return src_path, source_cache[src_path]

    rows_html: List[str] = []

    top_pairs = func_pairs[:max_funcs]
    for rank, p in enumerate(top_pairs, start=1):
        mi = p.get("meta_i", {})
        mj = p.get("meta_j", {})
        vcome = float(p.get("vcome_sim", 0.0))
        lsh = float(p.get("lsh_sim", 0.0))
        comb = float(p.get("combined_score", 0.0))

        label_i = _func_label(mi)
        label_j = _func_label(mj)

        path_i, src_i = get_source(mi, prog_i)
        path_j, src_j = get_source(mj, prog_j)

        if src_i:
            code_i = highlight_python(src_i)
        else:
            code_i = "<pre class='code hl'><div class='ln'><span class='no'>    </span> <em>source not found</em></div></pre>"

        if src_j:
            code_j = highlight_python(src_j)
        else:
            code_j = "<pre class='code hl'><div class='ln'><span class='no'>    </span> <em>source not found</em></div></pre>"

        rows_html.append(
            f"""
            <section class="func-pair">
              <h2>Pair #{rank}: <code>{_escape_html(label_i)}</code> ↔ <code>{_escape_html(label_j)}</code></h2>
              <p class="scores">
                combined = <strong>{comb:.4f}</strong> &nbsp;|&nbsp;
                vcome_sim = {vcome:.4f} &nbsp;|&nbsp;
                lsh_sim = {lsh:.4f}
              </p>
              <div class="prog-labels">
                <div class="col-info">
                  <h3>Program i</h3>
                  <p><code>{_escape_html(path_i)}</code></p>
                </div>
                <div class="col-info">
                  <h3>Program j</h3>
                  <p><code>{_escape_html(path_j)}</code></p>
                </div>
              </div>
              <div class="code-row">
                <div class="col">{code_i}</div>
                <div class="col">{code_j}</div>
              </div>
            </section>
            """
        )

    if not rows_html:
        rows_html.append("<p>No function-level pairs found for this program edge.</p>")

    html_txt = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>Cluster {cluster_id} - Edge {edge_idx} details</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin: 20px; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color:#6b7280; margin-bottom: 16px; }}
    a.back {{ font-size:13px; }}
    .func-pair {{ border:1px solid #e5e7eb; border-radius:12px; padding:12px 16px; margin:16px 0; }}
    .func-pair h2 {{ margin-top:0; font-size:16px; }}
    .scores {{ font-size:13px; color:#374151; margin:4px 0 8px 0; }}
    .prog-labels {{ display:flex; gap:16px; font-size:12px; color:#4b5563; margin-bottom:4px; }}
    .prog-labels .col-info {{ flex:1; min-width:0; }}
    .prog-labels code {{ background:#f3f4f6; padding:2px 4px; border-radius:4px; }}
    .code-row {{ display:flex; gap:16px; align-items:flex-start; }}
    .code-row .col {{ flex:1; min-width:0; overflow:auto; max-height:520px; }}
    pre.code.hl {{ background:#111827; color:#e5e7eb; padding:8px 8px 8px 0; border-radius:8px; font-size:12px; font-family:Menlo,Consolas,monospace; overflow:auto; }}
    pre.code.hl .ln {{ white-space:pre; }}
    pre.code.hl .no {{ display:inline-block; width:40px; padding-right:8px; color:#6b7280; }}
    pre.code.hl .k {{ color:#93c5fd; font-weight:600; }}
    pre.code.hl .n {{ color:#fbbf24; }}
    pre.code.hl .s {{ color:#34d399; }}
    pre.code.hl .c {{ color:#9ca3af; font-style:italic; }}
    pre.code.hl .mark {{ background:#374151; }}
  </style>
</head>
<body>
  <a class='back' href='{_escape_html(back_href)}'>&larr; Back to clusters</a>
  <h1>Cluster {cluster_id} – Edge {edge_idx}</h1>
  <p class='meta'>
    Program i: <code>{_escape_html(prog_i)}</code><br/>
    Program j: <code>{_escape_html(prog_j)}</code><br/>
  </p>
  {"".join(rows_html)}
</body>
</html>
"""

    out_path.write_text(html_txt, encoding="utf-8")


def build_pair_detail_pages(
    results: Dict[str, Any],
    out_dir: Path,
    cluster_html_name: str,
    max_funcs_per_edge: int = 20,
) -> None:
    """根据 program_clusters + pairs，为每条高风险边产出一个详情 HTML 页面。"""
    prog_clusters = results.get("program_clusters") or {}
    clusters: List[Dict[str, Any]] = prog_clusters.get("clusters", []) or []
    pairs = results.get("pairs") or []

    if not clusters or not pairs:
        return

    prog_pair_index = _build_prog_pair_index(pairs)
    if not prog_pair_index:
        return

    for c in clusters:
        cid = int(c.get("id", c.get("cluster_id", -1)))
        edges: List[Dict[str, Any]] = c.get("high_risk_edges", []) or []
        if not edges:
            continue
        for edge_idx, e in enumerate(edges, start=1):
            pi = str(e.get("prog_i", ""))
            pj = str(e.get("prog_j", ""))
            if not pi or not pj:
                continue
            key = _edge_key(pi, pj)
            func_pairs = prog_pair_index.get(key, [])
            detail_rel = _edge_detail_rel_path(cid, edge_idx)
            detail_path = out_dir / detail_rel
            back_href = os.path.relpath(out_dir / cluster_html_name, detail_path.parent)
            _render_edge_detail_page(
                out_path=detail_path,
                cluster_id=cid,
                edge_idx=edge_idx,
                prog_i=pi,
                prog_j=pj,
                func_pairs=func_pairs,
                back_href=back_href,
                max_funcs=max_funcs_per_edge,
            )


# ---------------------------------------------------------------------------
# 聚类报告主页面
# ---------------------------------------------------------------------------

def _build_cluster_section(
    clusters: List[Dict[str, Any]],
    per_program: Dict[str, Dict[str, Any]],
    edge_threshold: float,
) -> str:
    parts: List[str] = []
    if not clusters:
        parts.append("<p>No clusters found.</p>")
        return "\n".join(parts)

    for c in clusters:
        cid = int(c.get("id", c.get("cluster_id", -1)))
        members: List[str] = c.get("members", []) or []
        size = c.get("size", len(members))
        edges: List[Dict[str, Any]] = c.get("high_risk_edges", []) or []

        parts.append('<details class="cluster-block" open>')
        parts.append(
            f'<summary><strong>Cluster {cid}</strong> '
            f'(size = {size}, high-risk edges = {len(edges)})</summary>'
        )

        # 成员列表
        parts.append('<div class="cluster-members">')
        parts.append("<h3>Members</h3>")
        parts.append("<ul>")
        for prog in sorted(members):
            short = _escape_html(_short_prog(prog))
            full = _escape_html(prog)
            stats = per_program.get(prog, {})
            avg_combined = stats.get("avg_combined")
            pair_count = stats.get("pair_count")
            meta_items = []
            if pair_count is not None:
                meta_items.append(f"pair_count = {pair_count}")
            if avg_combined is not None:
                meta_items.append(f"avg_combined = {avg_combined:.4f}")
            meta_str = " | ".join(meta_items) if meta_items else ""
            parts.append(
                f'<li><code title="{full}">{short}</code>'
                + (f' <span class="meta">{_escape_html(meta_str)}</span>' if meta_str else "")
                + "</li>"
            )
        parts.append("</ul>")
        parts.append("</div>")  # cluster-members

        # 高风险边
        parts.append('<div class="cluster-edges">')
        parts.append(
            f"<h3>High-risk edges (avg_combined ≥ {edge_threshold:.2f})</h3>"
        )
        if not edges:
            parts.append("<p>No high-risk edges in this cluster.</p>")
        else:
            parts.append('<table class="edge-table">')
            parts.append(
                "<thead><tr>"
                "<th>#</th>"
                "<th>Program i</th>"
                "<th>Program j</th>"
                "<th>avg_combined</th>"
                "<th>pair_count</th>"
                "<th>Details</th>"
                "</tr></thead>"
            )
            parts.append("<tbody>")
            for edge_idx, e in enumerate(edges, start=1):
                pi = str(e.get("prog_i", ""))
                pj = str(e.get("prog_j", ""))
                ac = float(e.get("avg_combined", 0.0))
                pc = int(e.get("pair_count", 0))
                href = _edge_detail_rel_path(cid, edge_idx)
                parts.append(
                    "<tr>"
                    f"<td>{edge_idx}</td>"
                    f'<td><code title="{_escape_html(pi)}">{_escape_html(_short_prog(pi))}</code></td>'
                    f'<td><code title="{_escape_html(pj)}">{_escape_html(_short_prog(pj))}</code></td>'
                    f"<td>{ac:.4f}</td>"
                    f"<td>{pc}</td>"
                    f'<td><a href="{_escape_html(href)}" target="_blank">view functions</a></td>'
                    "</tr>"
                )
            parts.append("</tbody></table>")
        parts.append("</div>")  # cluster-edges

        parts.append("</details>")

    return "\n".join(parts)


def build_html_report(
    results: Dict[str, Any],
    title: str = "Program Clusters Report",
    edge_threshold: float = 0.75,
    source_json_name: str = "",
) -> str:
    prog_clusters = results.get("program_clusters") or {}
    per_program = results.get("per_program") or {}
    pairs = results.get("pairs") or []

    method = prog_clusters.get("method", "none")
    clusters: List[Dict[str, Any]] = prog_clusters.get("clusters", []) or []
    assignments: Dict[str, int] = prog_clusters.get("assignments", {}) or {}
    noise: List[str] = prog_clusters.get("noise", []) or []

    num_programs = len(per_program)
    num_pairs = len(pairs)
    num_clusters = len(clusters)
    num_noise = len(noise)

    # summary 区
    summary_html = f"""
    <section class="summary">
      <h2>Summary</h2>
      <ul>
        <li>Total programs: <strong>{num_programs}</strong></li>
        <li>Total function pairs (after rerank): <strong>{num_pairs}</strong></li>
        <li>Clustering method: <strong>{_escape_html(method)}</strong></li>
        <li>Number of clusters: <strong>{num_clusters}</strong></li>
        <li>Noise programs (unclustered): <strong>{num_noise}</strong></li>
      </ul>
    </section>
    """

    # 集群区
    clusters_html = _build_cluster_section(clusters, per_program, edge_threshold=edge_threshold)

    # noise 列表
    if noise:
        noise_items = "".join(
            f'<li><code title="{_escape_html(p)}">{_escape_html(_short_prog(p))}</code></li>'
            for p in sorted(noise)
        )
        noise_html = f"""
        <section class="noise">
          <h2>Noise programs (not clustered)</h2>
          <ul>{noise_items}</ul>
        </section>
        """
    else:
        noise_html = ""

    src_note = f" from <code>{_escape_html(source_json_name)}</code>" if source_json_name else ""

    html_txt = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>{_escape_html(title)}</title>
  <style>
    body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial; margin:24px; }}
    h1 {{ margin-bottom:4px; }}
    .meta {{ color:#6b7280; margin-bottom:16px; }}
    .summary ul {{ list-style:disc; padding-left:20px; }}
    .cluster-block {{ border:1px solid #e5e7eb; border-radius:12px; padding:12px 16px; margin:12px 0; }}
    .cluster-block > summary {{ cursor:pointer; font-size:15px; }}
    .cluster-members h3 {{ margin:8px 0 4px 0; }}
    .cluster-members ul {{ margin:0; padding-left:18px; }}
    .cluster-members li {{ margin-bottom:3px; font-size:13px; }}
    .cluster-members code {{ background:#f3f4f6; padding:1px 4px; border-radius:4px; }}
    .cluster-members .meta {{ font-size:12px; color:#6b7280; margin-left:6px; }}
    .cluster-edges h3 {{ margin:16px 0 4px 0; }}
    .edge-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    .edge-table th, .edge-table td {{ border:1px solid #e5e7eb; padding:4px 6px; text-align:left; }}
    .edge-table th {{ background-color:#e5e7eb; }}
    .edge-table tr:nth-child(even) {{ background-color:#f9fafb; }}
    .edge-table tr:hover {{ background-color:#e0f2fe; }}
    .edge-table a {{ font-size:12px; }}
    .noise code {{ background-color:#fef3c7; padding:1px 4px; border-radius:4px; }}
  </style>
</head>
<body>
  <h1>{_escape_html(title)}</h1>
  <p class='meta'>Program-level clustering report{src_note}</p>
  {summary_html}
  <section class="clusters">
    <h2>Clusters</h2>
    {clusters_html}
  </section>
  {noise_html}
</body>
</html>
"""
    return html_txt


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render HTML program-cluster report and per-edge function details from rerank JSON."
    )
    ap.add_argument(
        "-i", "--input", required=True, help="Path to rerank_candidates_multi JSON result."
    )
    ap.add_argument(
        "-o", "--out_html", required=True, help="Path to output HTML for clusters (e.g., reports/program_clusters.html)."
    )
    ap.add_argument(
        "--title", type=str, default="Program Clusters Report", help="HTML title for report."
    )
    ap.add_argument(
        "--edge_threshold",
        type=float,
        default=0.75,
        help="Only conceptually used for legend text; actual high-risk edges已在 JSON 中筛好。",
    )
    ap.add_argument(
        "--max_funcs_per_edge",
        type=int,
        default=20,
        help="Max number of function-level pairs to show per program edge.",
    )
    args = ap.parse_args()

    in_path = Path(args.input)
    with in_path.open("r", encoding="utf-8") as f:
        results = json.load(f)

    out_path = Path(args.out_html)
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 先生成聚类报告 HTML 文本
    html_txt = build_html_report(
        results,
        title=args.title,
        edge_threshold=args.edge_threshold,
        source_json_name=in_path.name,
    )

    # 2) 写聚类报告
    out_path.write_text(html_txt, encoding="utf-8")
    print(f"[OK] wrote cluster HTML report -> {out_path}")

    # 3) 生成每条高风险程序边的函数级详情页面
    build_pair_detail_pages(
        results,
        out_dir=out_dir,
        cluster_html_name=out_path.name,
        max_funcs_per_edge=args.max_funcs_per_edge,
    )
    print(f"[OK] wrote per-edge function detail pages under {out_dir / 'pairs'}")


if __name__ == "__main__":
    main()
