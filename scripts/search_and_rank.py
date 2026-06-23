from __future__ import annotations

import argparse
import json
import html
import os
import re
import math
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Any

def _is_driver_name(name: str) -> bool:
    """
    判断一个函数名是否是“程序入口 / 驱动函数”，例如 main / __main__ / <module> / test_xxx。

    这些函数通常只是做 IO 和调度，本身不携带核心算法逻辑，
    不应该作为“唯一高分匹配”就把整个程序对推到 1.0。
    """
    if not isinstance(name, str):
        return False
    n = name.strip().lower()
    if not n:
        return False
    if n in {"<module>", "__main__", "main"}:
        return True
    if n.startswith("test_") or n.startswith("benchmark_"):
        return True
    return False

def _read_source_lines(path: str) -> List[str]:
    """
    Best‑effort load of a source file. We try the path as given, then
    relative to the project root; on failure we return a single
    placeholder line.
    """
    candidates = [path]

    # If this is an absolute path under the project, also try relative.
    try:
        cwd = os.getcwd()
    except OSError:
        cwd = ""

    if cwd and path.startswith(cwd):
        rel = os.path.relpath(path, cwd)
        candidates.append(rel)

    # Try a few more relaxed variants.
    p = Path(path)
    if not p.is_absolute():
        candidates.append(str(Path(cwd) / p))

    for cand in candidates:
        try:
            with open(cand, "r", encoding="utf-8") as f:
                return f.readlines()
        except OSError:
            continue

    # Last resort: placeholder.
    return ["[source not available]\n"]


def _build_func_ranges(
    func_meta: Dict[str, Tuple[str, str, int]],
    src_cache: Dict[str, List[str]],
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Build function line ranges per program path.

    Returns:
        prog -> { fid -> {"name": str, "start": int, "end": int} }
    """
    prog_funcs: Dict[str, List[Tuple[str, str, int]]] = {}
    for fid, meta in func_meta.items():
        # meta is (path, name, first_lineno)
        if not isinstance(meta, (list, tuple)) or len(meta) < 3:
            continue
        path, name, first_lineno = meta[0], meta[1], meta[2]
        prog_funcs.setdefault(path, []).append((fid, name, int(first_lineno)))

    prog_ranges: Dict[str, Dict[str, Dict[str, int]]] = {}

    for path, flist in prog_funcs.items():
        flist.sort(key=lambda x: x[2])
        src_lines = src_cache.get(path) or _read_source_lines(path)
        src_cache[path] = src_lines
        n_lines = len(src_lines)

        ranges_for_prog: Dict[str, Dict[str, int]] = {}
        for i, (fid, name, start) in enumerate(flist):
            if i + 1 < len(flist):
                _, _, next_start = flist[i + 1]
                end = max(start, next_start - 1)
            else:
                end = n_lines
            ranges_for_prog[fid] = {
                "name": name,
                "start": int(start),
                "end": int(end),
            }

        prog_ranges[path] = ranges_for_prog

    return prog_ranges


def _escape(s: str) -> str:
    return html.escape(s, quote=False)


# Very simple, Python‑oriented syntax highlighting for demo purposes.
_PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
}


def _hl_strings(text: str) -> str:
    """
    Highlight string literals in an already‑escaped line of code.
    """
    # Match single or double quoted strings, non‑greedy.
    pattern = re.compile(r'(\".*?\"|\'.*?\')')

    def repl(m: re.Match) -> str:
        return f'<span class="tok-str">{m.group(0)}</span>'

    return pattern.sub(repl, text)


def _syntax_highlight(text: str) -> str:
    """
    Apply a very lightweight syntax highlight to an already‑escaped line:
    - Python keywords
    - string literals
    - trailing comment starting with '#'
    """
    # Handle trailing comment first.
    if "#" in text:
        code_part, comment_part = text.split("#", 1)
        code_part = code_part
        comment_html = f'<span class="tok-comment">#{comment_part}</span>'
    else:
        code_part = text
        comment_html = ""

    # Highlight strings in code part.
    code_part = _hl_strings(code_part)

    # Highlight keywords in code part.
    if _PY_KEYWORDS:
        kw_pattern = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in sorted(_PY_KEYWORDS)) + r")\b"
        )

        def kw_repl(m: re.Match) -> str:
            return f'<span class="tok-kw">{m.group(0)}</span>'

        code_part = kw_pattern.sub(kw_repl, code_part)

    return code_part + comment_html


def _render_code_block(lines: List[str]) -> str:
    """
    Render a code block where each line has a span with a data-line attribute,
    so that the front‑end JS can highlight ranges easily.
    """
    buf: List[str] = []
    buf.append('<pre class="code">')
    for i, line in enumerate(lines, start=1):
        # Strip trailing newline but preserve inner spacing.
        raw = line.rstrip("\n\r")
        escaped = _escape(raw)
        highlighted = _syntax_highlight(escaped)
        buf.append(
            f'<span class="ln" data-line="{i}">'
            f'<span class="no">{i:4d}</span> {highlighted}</span>'
        )
    buf.append("</pre>")
    return "\n".join(buf)


def render_report(
    out_path: str,
    func_meta: Dict[str, Tuple[str, str, int]],
    prog_pairs: Iterable[Tuple[str, str, float, List[Tuple[str, str, float]]]],
    func_rerank: Dict[str, List[Tuple[str, float, dict]]],
    threshold: float,
    json_root: str | None = None,
) -> None:
    """
    Render a pairwise similarity report.

    Args:
        out_path: where to write the HTML file.
        func_meta: mapping fid -> (path, name, first_lineno).
        prog_pairs: [(path_a, path_b, score, [(fid_a, fid_b, score), ...]), ...]
        func_rerank: full function‑level rerank map (unused here but kept
                     for compatibility / future extensions).
        threshold: similarity threshold (used for color coding only).
        json_root: root dir for *.epdg.json (unused here but kept for API compatibility).
    """
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    prog_pairs = list(prog_pairs)

    # Cache source and function ranges.
    src_cache: Dict[str, List[str]] = {}
    # Make sure we at least attempt to read source for each program in pairs.
    all_prog_paths = set()
    for pa, pb, _s, _matches in prog_pairs:
        all_prog_paths.add(pa)
        all_prog_paths.add(pb)
    for p in all_prog_paths:
        src_cache[p] = _read_source_lines(p)

    func_ranges = _build_func_ranges(func_meta, src_cache)

    # Build a reproducible ordering of programs in the summary table.
    prog_list = sorted(all_prog_paths)

    def prog_index(path: str) -> int:
        try:
            return prog_list.index(path)
        except ValueError:
            prog_list.append(path)
            return len(prog_list) - 1

    # Start HTML.
    buf: List[str] = []
    header_tpl = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Code Plagiarism – Pairwise Similarity Report</title>
<style>
body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 0;
  padding: 0;
  background: #f5f5f7;
}
header {
  padding: 16px 32px;
  background: #111827;
  color: #f9fafb;
}
header h1 {
  margin: 0;
  font-size: 20px;
}
header .meta {
  margin-top: 4px;
  font-size: 13px;
  color: #9ca3af;
}
main {
  padding: 16px 24px 32px 24px;
}
table.summary {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 24px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
  border-radius: 6px;
  overflow: hidden;
}
table.summary th,
table.summary td {
  padding: 8px 10px;
  font-size: 13px;
  border-bottom: 1px solid #e5e7eb;
}
table.summary th {
  text-align: left;
  background: #f3f4f6;
}
table.summary tr:last-child td {
  border-bottom: none;
}
.badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.3;
}
.badge-high {
  background: #fee2e2;
  color: #b91c1c;
}
.badge-med {
  background: #fef3c7;
  color: #92400e;
}
.badge-low {
  background: #e0f2fe;
  color: #075985;
}
section.pair {
  margin-bottom: 24px;
  padding: 16px;
  background: #ffffff;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}
section.pair h2 {
  margin: 0 0 8px 0;
  font-size: 15px;
}
.pair-meta {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}
.pair-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1.2fr) minmax(260px, 1.4fr) minmax(260px, 1.4fr);
  gap: 10px;
  align-items: flex-start;
}
.func-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
}
.func-table th,
.func-table td {
  padding: 4px 6px;
  border-bottom: 1px solid #e5e7eb;
}
.func-table th {
  background: #f9fafb;
  text-align: left;
}
.func-row {
  cursor: pointer;
}
.func-row:hover {
  background: #eff6ff;
}
.func-row.selected {
  background: #dbeafe;
}
.code-pane {
  background: #111827;
  color: #e5e7eb;
  padding: 8px 0;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
  overflow: auto;
  max-height: 480px;
}
.code-pane-header {
  padding: 0 10px 4px 10px;
  font-size: 11px;
  color: #9ca3af;
}
pre.code {
  margin: 0;
  padding: 0 10px 6px 10px;
}
.ln {
  display: block;
  white-space: pre;
}
.ln .no {
  display: inline-block;
  min-width: 36px;
  margin-right: 6px;
  color: #6b7280;
}
.ln.hl {
  background: #facc15;
  color: #111827;
}
.ln.hl .no {
  color: #4b5563;
}
.ln.hl-weak {
  background: #fde68a;
}

/* Simple token‑level syntax highlighting */
.tok-kw {
  color: #93c5fd;
  font-weight: 500;
}
.tok-str {
  color: #a7f3d0;
}
.tok-comment {
  color: #9ca3af;
  font-style: italic;
}
</style>
</head>
<body>
<header>
  <h1>Code Plagiarism – Pairwise Similarity Report</h1>
  <div class="meta">
    Program‑level pairs: __NUM_PAIRS__ &nbsp;&nbsp;|&nbsp;&nbsp;
    Greedy matching threshold: __THRESHOLD__
  </div>
</header>
<main>
"""
    header_html = (
        header_tpl
        .replace("__NUM_PAIRS__", str(len(prog_pairs)))
        .replace("__THRESHOLD__", f"{threshold:.2f}")
    )
    buf.append(header_html)

    # Summary table: list all program pairs.
    buf.append('<table class="summary">')
    buf.append(
        "<thead>"
        "<tr>"
        "<th>#</th>"
        "<th>Program A</th>"
        "<th>Program B</th>"
        "<th>Similarity</th>"
        "<th>Status</th>"
        "</tr>"
        "</thead>"
    )
    buf.append("<tbody>")
    for idx, (pa, pb, score, _matches) in enumerate(prog_pairs, start=1):
        if score >= 0.8:
            badge_class = "badge-high"
            badge_label = "high"
        elif score >= threshold:
            badge_class = "badge-med"
            badge_label = "medium"
        else:
            badge_class = "badge-low"
            badge_label = "low"
        buf.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{_escape(pa)}</td>"
            f"<td>{_escape(pb)}</td>"
            f"<td>{score:.3f}</td>"
            f'<td><span class="badge {badge_class}">{badge_label}</span></td>'
            "</tr>"
        )
    buf.append("</tbody></table>")

    # Per‑pair sections.
    for idx, (pa, pb, score, matches) in enumerate(prog_pairs, start=1):
        prog_index(pa)  # ensure indices are stable
        prog_index(pb)

        # Resolve source and ranges.
        src_a = src_cache.get(pa) or _read_source_lines(pa)
        src_b = src_cache.get(pb) or _read_source_lines(pb)
        ranges_a = func_ranges.get(pa, {})
        ranges_b = func_ranges.get(pb, {})

        buf.append(f'<section class="pair" id="pair-{idx}" data-pair-id="{idx}">')
        buf.append(
            f"<h2>Pair {idx}: {_escape(pa)} &nbsp;&nbsp;vs&nbsp;&nbsp; {_escape(pb)}</h2>"
        )
        buf.append(
            '<div class="pair-meta">'
            f"Aggregated similarity: <strong>{score:.4f}</strong> &nbsp;&nbsp;"
            f"(threshold = {threshold:.2f})"
            "</div>"
        )

        # Grid: left = match table, middle = code A, right = code B.
        buf.append('<div class="pair-grid">')

        # 1) Function matches table.
        buf.append('<div class="pair-cell matches">')
        buf.append('<table class="func-table">')
        buf.append(
            "<thead>"
            "<tr>"
            "<th>#</th>"
            "<th>Function A</th>"
            "<th>Lines A</th>"
            "<th>Function B</th>"
            "<th>Lines B</th>"
            "<th>Score</th>"
            "</tr>"
            "</thead>"
        )
        buf.append("<tbody>")
        for j, (fid_a, fid_b, fs) in enumerate(matches, start=1):
            ra = ranges_a.get(fid_a)
            rb = ranges_b.get(fid_b)

            if ra is not None:
                a_name = ra["name"]
                a_start = ra["start"]
                a_end = ra["end"]
            else:
                # Fallback: try to parse from fid or leave empty.
                a_name = fid_a.split("::")[-1]
                a_start = 1
                a_end = len(src_a)

            if rb is not None:
                b_name = rb["name"]
                b_start = rb["start"]
                b_end = rb["end"]
            else:
                b_name = fid_b.split("::")[-1]
                b_start = 1
                b_end = len(src_b)

            buf.append(
                f'<tr class="func-row" '
                f'data-pair-id="{idx}" '
                f'data-match-idx="{j}" '
                f'data-a-start="{a_start}" '
                f'data-a-end="{a_end}" '
                f'data-b-start="{b_start}" '
                f'data-b-end="{b_end}">'
                f"<td>{j}</td>"
                f"<td>{_escape(a_name)}</td>"
                f"<td>{a_start}–{a_end}</td>"
                f"<td>{_escape(b_name)}</td>"
                f"<td>{b_start}–{b_end}</td>"
                f"<td>{fs:.3f}</td>"
                "</tr>"
            )
        if not matches:
            buf.append(
                '<tr><td colspan="6" style="font-size:12px;color:#6b7280;">'
                "No function‑level matches recorded for this pair."
                "</td></tr>"
            )
        buf.append("</tbody></table>")
        buf.append("</div>")  # matches cell

        # 2) Code pane A.
        buf.append('<div class="pair-cell code-a">')
        buf.append(
            f'<div class="code-pane" data-prog-role="a" data-pair-id="{idx}">'
        )
        buf.append(
            f'<div class="code-pane-header">A: {_escape(pa)}</div>'
        )
        buf.append(_render_code_block(src_a))
        buf.append("</div>")
        buf.append("</div>")

        # 3) Code pane B.
        buf.append('<div class="pair-cell code-b">')
        buf.append(
            f'<div class="code-pane" data-prog-role="b" data-pair-id="{idx}">'
        )
        buf.append(
            f'<div class="code-pane-header">B: {_escape(pb)}</div>'
        )
        buf.append(_render_code_block(src_b))
        buf.append("</div>")
        buf.append("</div>")

        buf.append("</div>")  # pair-grid
        buf.append("</section>")

    # JS for highlighting.
    buf.append(
        """
</main>
<script>
function clearHighlights(root) {
  root.querySelectorAll('.ln.hl, .ln.hl-weak').forEach(function (el) {
    el.classList.remove('hl');
    el.classList.remove('hl-weak');
  });
}

function markRange(pane, startLine, endLine, strong) {
  if (!pane) return;
  var lnList = pane.querySelectorAll('.ln');
  var n = lnList.length;
  var s = Math.max(1, startLine);
  var e = Math.min(n, endLine);
  for (var i = s; i <= e; i++) {
    var el = pane.querySelector('.ln[data-line=\"' + i + '\"]');
    if (!el) continue;
    if (strong) {
      el.classList.add('hl');
      el.classList.remove('hl-weak');
    } else {
      if (!el.classList.contains('hl')) {
        el.classList.add('hl-weak');
      }
    }
  }
}

function onFuncRowClick(ev) {
  var row = ev.currentTarget;
  var pairId = row.getAttribute('data-pair-id');
  var aStart = parseInt(row.getAttribute('data-a-start'), 10) || 1;
  var aEnd   = parseInt(row.getAttribute('data-a-end'), 10)   || aStart;
  var bStart = parseInt(row.getAttribute('data-b-start'), 10) || 1;
  var bEnd   = parseInt(row.getAttribute('data-b-end'), 10)   || bStart;

  var pairSection = document.getElementById('pair-' + pairId);
  if (!pairSection) return;

  pairSection.querySelectorAll('.func-row.selected').forEach(function (tr) {
    tr.classList.remove('selected');
  });
  row.classList.add('selected');

  var paneA = pairSection.querySelector('.code-pane[data-prog-role=\"a\"]');
  var paneB = pairSection.querySelector('.code-pane[data-prog-role=\"b\"]');
  clearHighlights(paneA);
  clearHighlights(paneB);

  markRange(paneA, aStart, aEnd, true);
  markRange(paneB, bStart, bEnd, true);

  if (paneA) paneA.scrollTop = Math.max(0, (aStart - 5) * 14);
  if (paneB) paneB.scrollTop = Math.max(0, (bStart - 5) * 14);
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.func-row').forEach(function (row) {
    row.addEventListener('click', onFuncRowClick);
  });
});
</script>
</body>
</html>
"""
    )

    out_file.write_text("\n".join(buf), encoding="utf-8")



# === Phase 4: program-level aggregation override (penalty_task etc.) ===


def _compute_program_stats(
    prog_a: str,
    prog_b: str,
    base_score: float,
    matches: List[Tuple[str, str, float]],
    func_meta: Dict[str, Tuple[str, str, int]],
    func_len: Dict[str, int],
    total_sem: Dict[str, int],
    prog_funcs: Dict[str, List[str]],
    hi_thresh: float = 0.55,
) -> Dict[str, float]:
    """Collect a set of features for a program pair from function-level matches.

    Features include:
      - base_score: length-weighted aggregation from build_prog_pairs_from_lsh
      - max_pair: max function-level score
      - mean_pair: mean function-level score
      - top3_mean: mean of top-3 function-level scores
      - hi_count: number of function-level matches with score >= hi_thresh
      - cov_a, cov_b: semantic coverage on each side (by function length)
      - cov_min: min(cov_a, cov_b)
      - func_cov_a, func_cov_b: fraction of functions with at least one match
      - avg_high_score: mean score over strong matches (>= hi_thresh), 0 if none
      - high_cov: alias of cov_min, kept for clarity in the scoring layer
    """
    scores = [s for (_fa, _fb, s) in matches]
    if scores:
        max_pair = max(scores)
        mean_pair = sum(scores) / float(len(scores))
        topk = sorted(scores, reverse=True)[:3]
        top3_mean = sum(topk) / float(len(topk))
        hi_count = sum(1 for s in scores if s >= hi_thresh)
    else:
        max_pair = 0.0
        mean_pair = 0.0
        top3_mean = 0.0
        hi_count = 0

    # Count all matches for diagnostics, but only use "strong" matches (>= hi_thresh)
    # when computing coverage-related features.
    num_matches = float(len(matches))
    strong_pairs = [(fa, fb, s) for (fa, fb, s) in matches if s >= hi_thresh]

    if strong_pairs:
        # Unique function ids per side for strong matches only.
        fids_a = {fa for (fa, _fb, _s) in strong_pairs}
        fids_b = {fb for (_fa, fb, _s) in strong_pairs}

        # Semantic coverage on each side (length-weighted).
        covered_a = 0
        covered_b = 0
        for fid in fids_a:
            meta = func_meta.get(fid)
            if not meta:
                continue
            path, _name, _first_lineno = meta
            if path != prog_a:
                continue
            covered_a += max(1, func_len.get(fid, 1))
        for fid in fids_b:
            meta = func_meta.get(fid)
            if not meta:
                continue
            path, _name, _first_lineno = meta
            if path != prog_b:
                continue
            covered_b += max(1, func_len.get(fid, 1))

        total_a = max(1, total_sem.get(prog_a, 0))
        total_b = max(1, total_sem.get(prog_b, 0))
        cov_a = float(covered_a) / float(total_a)
        cov_b = float(covered_b) / float(total_b)
        cov_min = min(cov_a, cov_b)

        # Function-level coverage by count (strong matches only).
        funcs_a = prog_funcs.get(prog_a, [])
        funcs_b = prog_funcs.get(prog_b, [])
        func_cov_a = float(len(fids_a & set(funcs_a))) / float(len(funcs_a)) if funcs_a else 0.0
        func_cov_b = float(len(fids_b & set(funcs_b))) / float(len(funcs_b)) if funcs_b else 0.0

        # Average score over strong matches.
        avg_high_score = sum(s for (_fa, _fb, s) in strong_pairs) / float(len(strong_pairs))
    else:
        cov_a = 0.0
        cov_b = 0.0
        cov_min = 0.0
        func_cov_a = 0.0
        func_cov_b = 0.0
        avg_high_score = 0.0

    return {
        "base_score": float(base_score),
        "max_pair": float(max_pair),
        "mean_pair": float(mean_pair),
        "top3_mean": float(top3_mean),
        "hi_count": float(hi_count),
        "num_matches": float(num_matches),
        "cov_a": float(cov_a),
        "cov_b": float(cov_b),
        "cov_min": float(cov_min),
        "func_cov_a": float(func_cov_a),
        "func_cov_b": float(func_cov_b),
        "avg_high_score": float(avg_high_score),
        "high_cov": float(cov_min),
    }


def _score_program_pair(stats: Dict[str, float], min_coverage: float) -> float:
    """Combine program-pair features into a single similarity score in [0, 1].

    Phase 4: program-level aggregation focuses on two key quantities:

      - high_cov: semantic coverage contributed by *strong* function matches
                  (length-weighted, already computed as cov_min over strong pairs)
      - avg_high_score: average function-level similarity over strong matches

    The final score is a simple, interpretable combination:

        S_prog = alpha * high_cov + beta * avg_high_score - gamma * penalty_unmatched

    where penalty_unmatched is derived from the fraction of functions on each side
    that have no strong match. If there are no strong matches or coverage is
    negligible, the score collapses to 0 regardless of base_score.

    The min_coverage parameter acts as a soft gate: when high_cov is below
    min_coverage, the score is further downweighted.
    """
    base = float(stats.get("base_score", 0.0))
    cov_min = float(stats.get("cov_min", 0.0))
    high_cov = float(stats.get("high_cov", cov_min))
    avg_high = float(stats.get("avg_high_score", stats.get("top3_mean", 0.0)))
    func_cov_a = float(stats.get("func_cov_a", 0.0))
    func_cov_b = float(stats.get("func_cov_b", 0.0))
    hi_count = float(stats.get("hi_count", 0.0))

    # Clamp into [0, 1]
    high_cov = max(0.0, min(1.0, high_cov))
    avg_high = max(0.0, min(1.0, avg_high))
    func_cov_a = max(0.0, min(1.0, func_cov_a))
    func_cov_b = max(0.0, min(1.0, func_cov_b))

    # If there are no strong matches or effectively zero high-coverage, this pair
    # should not be considered similar, regardless of base_score.
    if hi_count <= 0.0 or high_cov <= 1e-3:
        return 0.0

    # --- Unmatched function ratio penalty (Phase 4.2 / 4.3 light version) ---
    # We keep the same intuition as before: if many functions on either side
    # have no strong match, the program-level similarity should be reduced.
    unmatched_a = max(0.0, 1.0 - func_cov_a)
    unmatched_b = max(0.0, 1.0 - func_cov_b)
    unmatched_avg = 0.5 * (unmatched_a + unmatched_b)
    penalty_unmatched = unmatched_avg  # in [0, 1]

    # Soft coverage gate w.r.t. the user-specified min_coverage.
    if min_coverage > 0.0 and high_cov < min_coverage:
        cov_factor = high_cov / max(min_coverage, 1e-6)
    else:
        cov_factor = 1.0

    # We bias towards coverage first, then average high score. The weights can be
    # tuned later on real data if needed.
    alpha = 0.6  # coverage weight
    beta = 0.4   # average high-score weight
    gamma = 0.4  # unmatched penalty weight

    raw = alpha * high_cov + beta * avg_high - gamma * penalty_unmatched

    # Ensure non-negative score before coverage gating.
    raw = max(0.0, raw)

    score = raw * cov_factor

    # As a very mild tie-breaker, allow a tiny contribution from the base score
    # so that, among equally covered pairs, those with more overall structure
    # similarity are ranked slightly higher. This term is intentionally capped.
    score += 0.1 * max(0.0, min(1.0, base)) * high_cov

    # Finally, clamp to [0, 1].
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return score

# === CLI entrypoint and helpers ===
import sys


def _load_epdg_source_path(json_root: str, json_path: str, cache: Dict[str, str]) -> str:
    """
    Given a root and a json_path (relative or absolute), return the original source file path.

    Strategy:
    - Try a few possible filesystem locations for the EPDG JSON.
    - If the JSON can be opened, look for keys like "source_path", "source_file", "file", "path"
      that might hold the original source path.
    - Cache by the json_path key.
    """
    if json_path in cache:
        return cache[json_path]

    candidates = []
    p = Path(json_path)

    # If json_path is absolute, try it directly.
    if p.is_absolute():
        candidates.append(p)
    else:
        # Try json_root / json_path if json_root is given.
        if json_root:
            candidates.append(Path(json_root) / p)
        # Also try json_path as-is, relative to CWD.
        candidates.append(p)

    data = None
    epdg_path_used = None
    for cand in candidates:
        try:
            with open(cand, "r", encoding="utf-8") as f:
                data = json.load(f)
            epdg_path_used = cand
            break
        except OSError:
            continue

    if data is not None:
        # Common keys that may store the original source path.
        for key in ["source_path", "source_file", "file", "path"]:
            val = data.get(key)
            if isinstance(val, str) and val:
                cache[json_path] = val
                return val

    # Fallback: if we found a JSON file but no explicit source key, use its path;
    # otherwise, fall back to the json_path string as given.
    if epdg_path_used is not None:
        cache[json_path] = str(epdg_path_used)
    else:
        cache[json_path] = json_path
    return cache[json_path]


# --- New helpers for function length and program score aggregation ---
def _infer_func_length(meta: dict) -> int:
    """
    Best-effort inference of a function's "size" from LSH metadata.
    Falls back to 1 if no length-like field is present.
    """
    # Try a few common keys that may encode token or node counts.
    for key in ["num_tokens", "token_len", "n_tokens", "n_tokens_norm", "node_count", "num_nodes"]:
        v = meta.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
    return 1


def _aggregate_program_score(
    matches: List[Tuple[str, str, float]],
    func_len: Dict[str, int],
    min_func_score: float = 0.0,
) -> float:
    """
    Aggregate function-level scores into a program-level score using
    length-weighted averaging. Only function pairs with score >=
    min_func_score are used.
    """
    num = 0.0
    denom = 0.0
    for fid_a, fid_b, s in matches:
        if s < min_func_score:
            continue
        la = func_len.get(fid_a, 1)
        lb = func_len.get(fid_b, 1)
        w = max(la, lb)
        num += s * w
        denom += w
    if denom <= 0.0:
        return 0.0
    return num / denom



# --- Conservative template/obfuscation function name filter ---

def _is_template_name(name: str) -> bool:
    """
    Very conservative template function detector:
    - File-level <module>
    - Obvious obfuscation helpers like __obf_* or _obf_*
    """
    if not isinstance(name, str):
        return False
    if name == "<module>":
        return True
    lower = name.lower()
    if lower.startswith("__obf_") or lower.startswith("_obf_"):
        return True
    return False


# --- Template/obfuscation helper detection via function length and effect tags ---

def _extract_effect_tags(meta: dict) -> List[str]:
    """
    Extract lower-cased effect tags from typical metadata keys.
    This is best-effort and will gracefully handle missing keys.
    """
    keys = ["effect_signature", "effect_summary", "effects", "effect_sig", "eff_tags"]
    tags: List[str] = []
    for k in keys:
        v = meta.get(k)
        if isinstance(v, str):
            parts = re.split(r"[;,/]", v)
            for p in parts:
                p = p.strip().lower()
                if p:
                    tags.append(p)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    t = item.strip().lower()
                    if t:
                        tags.append(t)
    return tags


# --- Degree and call-count extraction helpers ---
def _get_neighbor_degree(meta: dict) -> int:
    """Best-effort extraction of a function's neighbor degree from LSH metadata."""
    for key in ["neighbor_degree", "degree", "deg", "out_degree", "inout_degree"]:
        v = meta.get(key)
        if isinstance(v, (int, float)):
            return int(v)
    return 0


def _get_call_count(meta: dict) -> int:
    """Best-effort extraction of a function's call-count from LSH metadata."""
    for key in ["call_count", "num_calls", "total_calls"]:
        v = meta.get(key)
        if isinstance(v, (int, float)):
            return int(v)
    return 0



def _is_template_func(meta: dict) -> bool:
    """
    Decide whether a function should be treated as a template / obfuscation helper.

    Heuristics:
    - Name-based rules (obvious obfuscation helpers, <module>, etc.).
    - Very small wrappers (length <= 3 by token/node count).
    - Effect-signature tags that look like logging / instrumentation / obfuscation.
    - Degree / call-count based hints: small, high-degree wrappers are likely templates.
    """
    name = meta.get("name", "")
    length = _infer_func_length(meta)

    # Strong name-based rules first.
    if _is_template_name(name):
        return True

    lower = name.lower()
    if lower.startswith("safe_bind"):
        return True
    if lower.startswith("_hidden_") or lower.startswith("__obf_") or lower.startswith("obf_"):
        return True

    # Effect-signature based hints.
    eff_tags = _extract_effect_tags(meta)
    for t in eff_tags:
        if any(key in t for key in ["obfus", "template", "logging", "metric", "profil", "debug", "instrument"]):
            return True

    # Extremely small helpers are very likely wrappers / templates.
    if length <= 3:
        return True

    # Degree / call-count based hints: small, high-degree wrappers are likely templates.
    deg = _get_neighbor_degree(meta)
    calls = _get_call_count(meta)
    if length <= 8 and (deg >= 64 or calls >= 32):
        return True

    return False


def _normalize_name_for_match(name: str) -> str:
    """Normalize a function name for rough similarity comparison.

    We keep only lowercase letters and digits and strip separators so that
    `fib`, `fib_recursive`, `Fib` all map to something comparable.
    """
    if not isinstance(name, str):
        return ""
    name = name.strip()
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _score_func_pair(meta_i: dict, meta_j: dict, lsh_sim: float, base_threshold: float) -> float:
    """Compute a refined function-level similarity S_func.

    Starting from the raw LSH similarity, we incorporate several signals:
      - approximate function length (tokens / nodes);
      - name similarity (exact / substring / common prefix);
      - neighbor degree and template-like hints from the LSH metadata.

    The result is in [0, 1]. Very template-like, tiny, or clearly mismatched
    functions are heavily downweighted or mapped to 0.
    """
    try:
        s = float(lsh_sim)
    except Exception:
        return 0.0
    if s <= 0.0:
        return 0.0
    if s > 1.0:
        s = 1.0

    # --- Length ratio penalty: large mismatches in size are suspicious ---
    len_i = _infer_func_length(meta_i)
    len_j = _infer_func_length(meta_j)
    if len_i > 0 and len_j > 0:
        ratio = float(max(len_i, len_j)) / float(min(len_i, len_j))
        if ratio > 8.0:
            s *= 0.2
        elif ratio > 4.0:
            s *= 0.4
        elif ratio > 2.0:
            s *= 0.7

    # --- Name similarity: identical / very close names boost trust ---
    name_i_norm = _normalize_name_for_match(meta_i.get("name", ""))
    name_j_norm = _normalize_name_for_match(meta_j.get("name", ""))
    if name_i_norm and name_j_norm:
        if name_i_norm == name_j_norm:
            name_factor = 1.0
        elif name_i_norm in name_j_norm or name_j_norm in name_i_norm:
            # fib vs fibonacci 这一类
            name_factor = 0.9
        else:
            common = 0
            for a, b in zip(name_i_norm, name_j_norm):
                if a != b:
                    break
                common += 1
            if common >= 3:
                name_factor = 0.7
            else:
                # Very different names, treat more conservatively.
                name_factor = 0.4
        # Interpolate between “no name signal” (0.5) and the name_factor.
        s *= 0.5 + 0.5 * name_factor

    # --- Neighbor-degree based penalty: high-degree helpers look like templates ---
    deg_i = _get_neighbor_degree(meta_i)
    deg_j = _get_neighbor_degree(meta_j)
    for deg in (deg_i, deg_j):
        if deg >= 128:
            s *= 0.3
        elif deg >= 64:
            s *= 0.5
        elif deg >= 32:
            s *= 0.8

    # --- Explicit template-like flag from LSH candidate metadata ---
    if bool(meta_i.get("is_template_like")) or bool(meta_j.get("is_template_like")):
        s *= 0.3

    # --- Driver / main 限制：main-main 永远不能当成“满分匹配” ---
    orig_name_i = meta_i.get("name", "")
    orig_name_j = meta_j.get("name", "")
    if _is_driver_name(orig_name_i) and _is_driver_name(orig_name_j):
        # 不论 LSH 有多高，driver ↔ driver 的函数级匹配最多给到 0.8，
        # 这样在 hi_thresh=0.9 的设定下，它不会成为 hi-match，也无法单独把程序对推到 1.0。
        if s > 0.8:
            s = 0.8

    # If after all penalties the score is effectively zero, drop it.
    if s < 1e-4:
        return 0.0

    # Clamp to [0, 1].
    if s < 0.0:
        s = 0.0
    if s > 1.0:
        s = 1.0

    # Use the CLI threshold as a rough lower bound; pairs that fall far below
    # it after penalties are not strong enough to be treated as real matches.
    if base_threshold > 0.0 and s < 0.5 * base_threshold:
        return 0.0

    return s

# --- Name and effect-based task similarity for function-level scores ---

_GENERIC_NAME_TOKENS = {
    "main", "solution", "sol", "helper", "util", "utils", "function",
    "func", "student", "answer", "result", "res", "tmp",
}

def _normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.strip()

def _split_name_tokens(name: str) -> List[str]:
    name = _normalize_name(name).lower()
    if not name:
        return []
    parts = re.split(r"[^a-z0-9]+", name)
    toks: List[str] = []
    for p in parts:
        p = p.strip()
        if not p or len(p) <= 1:
            continue
        if p in _GENERIC_NAME_TOKENS:
            continue
        toks.append(p)
    return toks

def _name_similarity(name_a: str, name_b: str) -> float:
    na = _normalize_name(name_a)
    nb = _normalize_name(name_b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    if len(na) >= 3 and len(nb) >= 3:
        short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
        if long_.startswith(short):
            return 0.8

    toks_a = set(_split_name_tokens(na))
    toks_b = set(_split_name_tokens(nb))
    if not toks_a or not toks_b:
        return 0.0
    inter = len(toks_a & toks_b)
    union = len(toks_a | toks_b)
    if union <= 0:
        return 0.0
    return float(inter) / float(union)

def _effect_similarity(tags_a: List[str], tags_b: List[str]) -> float:
    """Jaccard similarity over effect tags.

    当一侧或两侧都没有 tags 的时候，把它当作「没有语义证据」而不是「完全一致」，
    返回 0.0，这样名字就成为主要的 task 信号。
    """
    sa = set(tags_a or [])
    sb = set(tags_b or [])
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    if union <= 0:
        return 0.0
    return float(inter) / float(union)

def _compute_s_func(meta_i: dict, meta_j: dict, lsh_sim: float) -> float:
    """
    Combine LSH-style structural similarity with name and effect-based
    task similarity to obtain a task-aware function-level score S_func.

    Intuition:
      - S_token: structural similarity (lsh_sim, already in [0, 1]).
      - S_name: similarity of function names after removing generic tokens.
      - S_effect: Jaccard similarity of effect tags.

    When both S_name and S_effect are very low, we treat the pair as
    likely cross-task and downweight aggressively to 0.
    """
    try:
        s_token = float(lsh_sim)
    except Exception:
        s_token = 0.0
    if s_token <= 0.0:
        return 0.0
    s_token = max(0.0, min(1.0, s_token))

    name_i = meta_i.get("name", "") or ""
    name_j = meta_j.get("name", "") or ""
    s_name = _name_similarity(name_i, name_j)

    tags_i = _extract_effect_tags(meta_i)
    tags_j = _extract_effect_tags(meta_j)
    s_eff = _effect_similarity(tags_i, tags_j)

    # 学生作业场景：函数名一般都比较可靠，effect tags 用来微调
    semantic_factor = 0.7 * s_name + 0.3 * s_eff

    # 名字和 effect 都几乎完全不对齐，视为 cross-task，直接杀掉
    if semantic_factor <= 0.05:
        return 0.0

    # 用 semantic_factor 作为 gate 去调节结构相似度，留一个小底座
    # 避免轻微语义不一致就完全清零
    gate = 0.2 + 0.8 * semantic_factor  # in [0.2, 1.0]
    score = s_token * gate

    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return score


def build_prog_pairs_from_lsh(
    json_root: str,
    lsh_path: str,
    threshold: float,
) -> Tuple[
    Dict[str, Tuple[str, str, int]],
    Dict[str, int],
    List[Tuple[str, str, float, List[Tuple[str, str, float]]]],
]:
    """
    Load LSH candidate pairs JSON, aggregate program-level pairs with
    function-level scores.

    Returns:
        func_meta: fid -> (path, name, first_lineno)
        func_len: fid -> function length (semantic size)
        prog_pairs: [(prog_a, prog_b, agg_score, [(fid_a, fid_b, func_score), ...]), ...]
    """
    with open(lsh_path, "r", encoding="utf-8") as f:
        lsh_data = json.load(f)

    pairs = lsh_data.get("pairs", [])

    epdg_src_cache: Dict[str, str] = {}
    func_meta: Dict[str, Tuple[str, str, int]] = {}
    # Function length cache: fid -> approximate length in tokens/nodes.
    func_len: Dict[str, int] = {}
    # Program-level map: (prog_a, prog_b) -> list of (fid_a, fid_b, func_score)
    prog_pairs_map: Dict[Tuple[str, str], List[Tuple[str, str, float]]] = {}

    for pair in pairs:
        meta_i = pair.get("meta_i", {})
        meta_j = pair.get("meta_j", {})
        lsh_sim = pair.get("lsh_sim", None)
        if lsh_sim is None:
            continue

        try:
            raw_sim = float(lsh_sim)
        except Exception:
            continue
        if raw_sim <= 0.0:
            continue

        # Template / obfuscation filter: if either side looks like a template helper,
        # do not let this match contribute to program-level similarity at all.
        if _is_template_func(meta_i) or _is_template_func(meta_j):
            continue

        # Compute refined function-level similarity S_func using metadata.
        func_score = _score_func_pair(meta_i, meta_j, raw_sim, threshold)
        # Drop pairs whose refined score is essentially zero or clearly below the CLI threshold.
        if func_score <= 0.0:
            continue
        if threshold > 0.0 and func_score < threshold:
            continue

        # Extract meta fields after we know this pair is worth keeping.
        json_path_i = meta_i.get("json_path")
        func_idx_i = meta_i.get("func_idx")
        name_i = meta_i.get("name", "")
        first_lineno_i = meta_i.get("first_lineno", 1)

        json_path_j = meta_j.get("json_path")
        func_idx_j = meta_j.get("func_idx")
        name_j = meta_j.get("name", "")
        first_lineno_j = meta_j.get("first_lineno", 1)

        if json_path_i is None or func_idx_i is None or json_path_j is None or func_idx_j is None:
            continue

        prog_path_i = _load_epdg_source_path(json_root, json_path_i, epdg_src_cache)
        prog_path_j = _load_epdg_source_path(json_root, json_path_j, epdg_src_cache)

        fid_i = f"{json_path_i}::f{func_idx_i}"
        fid_j = f"{json_path_j}::f{func_idx_j}"

        # Record function meta (path, name, first_lineno).
        func_meta[fid_i] = (prog_path_i, name_i, first_lineno_i)
        func_meta[fid_j] = (prog_path_j, name_j, first_lineno_j)

        # Record approximate function lengths for later coverage-weighted aggregation.
        if fid_i not in func_len:
            func_len[fid_i] = _infer_func_length(meta_i)
        if fid_j not in func_len:
            func_len[fid_j] = _infer_func_length(meta_j)

        key = (prog_path_i, prog_path_j)
        prog_pairs_map.setdefault(key, []).append((fid_i, fid_j, float(func_score)))

    prog_pairs: List[Tuple[str, str, float, List[Tuple[str, str, float]]]] = []

    for (prog_a, prog_b), matches in prog_pairs_map.items():
        if not matches:
            continue

        # For each function on each side, keep only its best match score.
        best_a: Dict[str, float] = {}
        best_b: Dict[str, float] = {}

        for (fa, fb, score) in matches:
            prev_a = best_a.get(fa)
            if prev_a is None or score > prev_a:
                best_a[fa] = score
            prev_b = best_b.get(fb)
            if prev_b is None or score > prev_b:
                best_b[fb] = score

        # Length-weighted aggregation: larger functions contribute more.
        num = 0.0
        denom = 0.0
        for fa, s in best_a.items():
            w = max(1, func_len.get(fa, 1))
            num += s * w
            denom += w
        for fb, s in best_b.items():
            w = max(1, func_len.get(fb, 1))
            num += s * w
            denom += w
        if denom <= 0.0:
            continue
        agg_score = num / denom

        # Sort matches by function-level score, descending, for display.
        matches_sorted = sorted(matches, key=lambda x: x[2], reverse=True)
        prog_pairs.append((prog_a, prog_b, float(agg_score), matches_sorted))

    return func_meta, func_len, prog_pairs




# --- DACD template downweighting helpers ---

def _load_template_weights(dacd_path: str) -> Dict[str, float]:
    """Load DACD cluster JSON and build a func_id -> weight map.

    The intent is to downweight functions that belong to large,
    highly repetitive template clusters. We only consider clusters
    where "is_template_like" is true. The weight is in (0, 1],
    with smaller values meaning stronger downweighting.
    """
    if not dacd_path:
        return {}
    if not os.path.exists(dacd_path):
        return {}
    try:
        with open(dacd_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    clusters = data.get("clusters") or []
    weights: Dict[str, float] = {}

    for c in clusters:
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

        # Heuristic: larger / more widespread clusters get stronger downweight.
        # Base term from cluster size.
        size_term = 1.0 / float(max(2.0, math.log(2.0 + float(size))))
        # Additional factor from how many different files this pattern appears in.
        spread_term = 1.0 / float(max(2.0, math.log(2.0 + float(distinct_files))))
        w = size_term * spread_term * 2.0
        # Clamp to a reasonable range so we never fully erase contributions.
        if w < 0.1:
            w = 0.1
        if w > 0.8:
            w = 0.8

        for fid in members:
            if not isinstance(fid, str):
                continue
            prev = weights.get(fid)
            if prev is None:
                weights[fid] = float(w)
            else:
                # If a function happens to appear in multiple template clusters,
                # use the strongest downweight (smallest weight).
                weights[fid] = float(min(prev, w))

    return weights


def _apply_template_weights(
    func_len: Dict[str, int], template_weights: Dict[str, float]
) -> Dict[str, float]:
    """Return a new func_len dict with template functions downweighted.

    We simply multiply the semantic length of each function by its
    template weight in (0, 1]. Non-template functions keep weight 1.0.
    The rest of the pipeline (coverage computation and aggregation)
    then automatically treats heavily templated functions as smaller
    contributions to program-level similarity.
    """
    if not template_weights:
        # Nothing to do; return a shallow copy.
        return {k: float(v) for k, v in func_len.items()}

    adjusted: Dict[str, float] = {}
    for fid, length in func_len.items():
        w = template_weights.get(fid, 1.0)
        try:
            base_len = float(length)
        except Exception:
            base_len = 1.0
        if base_len <= 0.0:
            base_len = 1.0
        adjusted[fid] = base_len * float(w)
    return adjusted


# --- Semantic-coverage based downweighting ---
def _apply_coverage_downweight(
    func_meta: Dict[str, Tuple[str, str, int]],
    func_len: Dict[str, int],
    prog_pairs: List[Tuple[str, str, float, List[Tuple[str, str, float]]]],
    min_coverage: float = 0.3,
) -> List[Tuple[str, str, float, List[Tuple[str, str, float]]]]:
    """\
    For each program pair, compute a rich set of statistics describing
    how similar the two programs are (by function-level matches, semantic
    coverage, and function coverage), and then combine those statistics
    into a single program-level similarity score.

    The output list has the same structure as the input prog_pairs, but
    the third element of each tuple is the newly computed program-level
    score.
    """
    # Total semantic length and function sets per program.
    total_sem: Dict[str, int] = {}
    prog_funcs: Dict[str, List[str]] = {}
    for fid, (path, _name, _first_lineno) in func_meta.items():
        length = max(1, func_len.get(fid, 1))
        total_sem[path] = total_sem.get(path, 0) + length
        prog_funcs.setdefault(path, []).append(fid)

    adjusted: List[Tuple[str, str, float, List[Tuple[str, str, float]]]] = []

    for prog_a, prog_b, base_score, matches in prog_pairs:
        if not matches:
            adjusted.append((prog_a, prog_b, 0.0, matches))
            continue

        stats = _compute_program_stats(
            prog_a=prog_a,
            prog_b=prog_b,
            base_score=base_score,
            matches=matches,
            func_meta=func_meta,
            func_len=func_len,
            total_sem=total_sem,
            prog_funcs=prog_funcs,
        )
        new_score = _score_program_pair(stats, min_coverage=min_coverage)

        # Debug print to understand behaviour during tuning.
        print(
            "[program_sim] "
            f"{prog_a} vs {prog_b}: "
            f"base={stats['base_score']:.3f}, "
            f"max_pair={stats['max_pair']:.3f}, "
            f"top3_mean={stats['top3_mean']:.3f}, "
            f"cov_a={stats['cov_a']:.2%}, "
            f"cov_b={stats['cov_b']:.2%}, "
            f"func_cov_a={stats['func_cov_a']:.2%}, "
            f"func_cov_b={stats['func_cov_b']:.2%}, "
            f"hi_count={int(stats['hi_count'])} "
            f"-> final={new_score:.3f}"
        )

        adjusted.append((prog_a, prog_b, new_score, matches))

    return adjusted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--index", type=str, required=True, help="(unused) index path")
    parser.add_argument("-j", "--json_root", type=str, required=True, help="Root dir for EPDG JSON")
    parser.add_argument("-o", "--out_json", type=str, required=True, help="Output JSON file (program pairs)")
    parser.add_argument("-r", "--report_html", type=str, required=True, help="Output HTML report")
    parser.add_argument("--topk_recall", type=int, default=128, help="(unused) kept for compatibility")
    parser.add_argument("--threshold", type=float, default=0.6, help="Similarity threshold (function-level)")
    parser.add_argument(
        "--min_coverage",
        type=float,
        default=0.3,
        help="Minimum fraction of source lines that must be covered by matched functions; "
             "pairs below this are automatically downweighted.",
    )
    parser.add_argument("--candidates", type=str, default=None, help="Path to LSH candidate JSON")
    parser.add_argument(
        "--dacd_clusters",
        type=str,
        default=None,
        help="Optional path to DACD cluster JSON for template downweighting; "
             "if omitted, will try <json_root>/dacd_clusters.json if it exists.",
    )
    args = parser.parse_args()

    # Find candidate JSON path
    candidates_path = args.candidates
    if not candidates_path:
        # Try default: data/artifacts/retrieval/lsh_pairs.json
        default_path = os.path.join("data", "artifacts", "retrieval", "lsh_pairs.json")
        if os.path.exists(default_path):
            candidates_path = default_path
        else:
            # Try relative to index path
            index_path = Path(args.index)
            p1 = index_path.parent.parent / "retrieval" / "lsh_pairs.json"
            p2 = index_path.parent / "lsh_pairs.json"
            if p1.exists():
                candidates_path = str(p1)
            elif p2.exists():
                candidates_path = str(p2)
            else:
                print(
                    "[ERROR] Could not find LSH candidate file. Specify with --candidates.",
                    file=sys.stderr,
                )
                sys.exit(1)
    # Load and aggregate
    func_meta, func_len, prog_pairs = build_prog_pairs_from_lsh(
        args.json_root,
        candidates_path,
        args.threshold,
    )
    # Apply DACD template downweighting (if clusters are available) by
    # shrinking the effective semantic length of heavily templated functions
    # before computing coverage and aggregation. This way, common templates
    # contribute less to program-level similarity, but are not completely ignored.
    template_weights_path = args.dacd_clusters
    if not template_weights_path:
        # Default: look for a DACD clustering result under the JSON root.
        default_dacd = os.path.join(args.json_root, "dacd_clusters.json")
        if os.path.exists(default_dacd):
            template_weights_path = default_dacd

    if template_weights_path:
        tmpl_weights = _load_template_weights(template_weights_path)
        if tmpl_weights:
            print(f"[dacd] Loaded {len(tmpl_weights)} template function weights from {template_weights_path}")
            # Remap cluster-member keys to func_meta fids.
            # Cluster members: "/path/to/source.py::funcname@lineno"
            # func_meta fids:   "path/to/json.epdg.json::fN" with values (source_path, func_name, first_lineno)
            _remapped: Dict[str, float] = {}
            _remap_count = 0
            for fid, (src_path, func_name, first_lineno) in func_meta.items():
                # Build the cluster-member-style key: source_path::func_name@first_lineno
                cluster_key = f"{src_path}::{func_name}@{first_lineno}"
                w = tmpl_weights.get(cluster_key)
                if w is not None:
                    _remapped[fid] = w
                    _remap_count += 1
            if _remap_count > 0:
                print(f"[dacd] Remapped {_remap_count} template weights to func_meta fids")
                eff_func_len = _apply_template_weights(func_len, _remapped)
            else:
                print("[dacd] WARNING: could not remap any template weights — key formats may differ")
                eff_func_len = {k: float(v) for k, v in func_len.items()}
        else:
            eff_func_len = {k: float(v) for k, v in func_len.items()}
    else:
        eff_func_len = {k: float(v) for k, v in func_len.items()}

    # Apply semantic-coverage based downweighting so that high similarity on
    # tiny portions of the programs does not dominate the final score.
    prog_pairs = _apply_coverage_downweight(
        func_meta,
        eff_func_len,
        prog_pairs,
        min_coverage=args.min_coverage,
    )
    # Sort program pairs by final score (descending) so that the report
    # and JSON present the most suspicious pairs first.
    prog_pairs = sorted(prog_pairs, key=lambda x: x[2], reverse=True)

    # Ensure output dirs exist
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_html).parent.mkdir(parents=True, exist_ok=True)
    # Write JSON
    out_json_obj = {
        "pairs": [
            {
                "prog_a": pa,
                "prog_b": pb,
                "score": float(score),
                "matches": [
                    {"fid_a": fa, "fid_b": fb, "score": float(fs)} for (fa, fb, fs) in matches
                ],
            }
            for (pa, pb, score, matches) in prog_pairs
        ]
    }
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out_json_obj, f, indent=2)
    print(f"[OK] results -> {args.out_json}")
    # Write HTML
    render_report(
        args.report_html,
        func_meta,
        prog_pairs,
        func_rerank={},
        threshold=args.threshold,
        json_root=args.json_root,
    )
    print(f"[OK] report  -> {args.report_html}")


if __name__ == "__main__":
    main()
