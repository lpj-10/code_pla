# report/report_cluster.py
from __future__ import annotations
import os, json, html
from typing import Dict, Any, List

HTML_TMPL = """<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>M4 Clustering Report</title>
<style>
 body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin: 24px; }}
 h1 {{ margin-bottom: 8px; }}
 .meta {{ color:#666; margin-bottom:16px; }}
 .cluster {{ border:1px solid #ddd; border-radius:12px; padding:12px 16px; margin:12px 0; }}
 .badge {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:12px; background:#eef; margin-left:6px; }}
 .tmpl {{ background:#fee; }}
 .members {{ margin-top:8px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 13px; }}
 details {{ margin-top:8px; }}
</style>
</head>
<body>
<h1>M4 聚类报告</h1>
<div class="meta">总函数数：{N} ；簇数：{K}</div>
{CLUSTERS}
</body>
</html>
"""

def _row(c: Dict[str, Any]) -> str:
    tags = []
    if c.get("is_template_like"):
        tags.append('<span class="badge tmpl">template-like</span>')
    if c.get("stability") is not None:
        tags.append(f'<span class="badge">p={c["stability"]:.2f}</span>')
    tags.append(f'<span class="badge">size={c["size"]}</span>')
    tags.append(f'<span class="badge">mean_d={c["mean_intra_distance"]:.2f}</span>')

    members = "<br/>".join(html.escape(m) for m in c["members"])
    exemplar = html.escape(str(c.get("exemplar")))
    return f"""
    <div class="cluster">
      <div><b>Cluster #{c["cluster_id"]}</b> {' '.join(tags)}</div>
      <div>Exemplar: <code>{exemplar}</code></div>
      <details>
        <summary>成员列表</summary>
        <div class="members">{members}</div>
      </details>
    </div>
    """

def render_cluster_report(cluster_json: str, out_html: str):
    data = json.load(open(cluster_json, "r", encoding="utf-8"))
    rows = []
    # 排序：模板优先、大簇优先、均值距离小优先
    clusters = sorted(
        data["clusters"],
        key=lambda x: (not x.get("is_template_like", False), -x.get("size", 0), x.get("mean_intra_distance", 9e9))
    )
    for c in clusters:
        rows.append(_row(c))

    html_txt = HTML_TMPL.format(N=data.get("n_funcs", 0), K=len(clusters), CLUSTERS="".join(rows))
    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_txt)
    print(f"[cluster-report] saved -> {out_html}")
