# scripts/pipeline_bytecode.py
"""End-to-end plagiarism pipeline using the BYTECODE-based PDG builder.

This is the bytecode-path counterpart of ``pipeline_pure_lsh_dacd.py``.
The only difference is Stage 1: it uses ``build_epdg_bytecode.py``
(bytecode CFG + SSA dataflow + post-dominator control dependence)
instead of ``build_epdg.py`` (AST-based builder).

Stages 2-5 are identical — they operate on the same JSON format.

Usage::

    # Pure LSH (bytecode path)
    python scripts/pipeline_bytecode.py --src_root data/submissions_simple

    # With DACD template clustering
    python scripts/pipeline_bytecode.py --src_root data/submissions_simple --with_dacd
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def run_step(cmd: list[str], desc: str) -> None:
    print(f"\n[step] {desc}")
    print("  ", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(
            f"[ERROR] step failed ({desc}), return code={result.returncode}"
        )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="End-to-end plagiarism pipeline (BYTECODE path).",
    )
    ap.add_argument("--src_root", type=Path, default=Path("data/submissions"),
                    help="Root directory containing Python submissions.")
    ap.add_argument("--json_root", type=Path,
                    default=Path("data/artifacts/json_bytecode"),
                    help="Directory to write base E-PDG *.epdg.json files.")
    ap.add_argument("--json_mv_root", type=Path,
                    default=Path("data/artifacts/json_mv_bytecode"),
                    help="Directory for multi-view JSON files.")
    ap.add_argument("--effects", type=Path,
                    default=Path("effect_summaries.yaml"),
                    help="Effect summaries YAML.")
    ap.add_argument("--index_path", type=Path,
                    default=Path("data/artifacts/index/epdg_lsh_bytecode.pkl"),
                    help="Output path for LSH index pickle.")
    ap.add_argument("--candidates_json", type=Path,
                    default=Path("data/artifacts/retrieval/lsh_pairs_bytecode.json"),
                    help="Output path for LSH candidate pairs.")
    ap.add_argument("--out_json", type=Path,
                    default=Path("data/artifacts/retrieval/baseline_pairs_bytecode.json"),
                    help="Output path for final similarity JSON.")
    ap.add_argument("--report_html", type=Path,
                    default=Path("data/artifacts/reports/baseline_pairs_bytecode.html"),
                    help="Output path for HTML report.")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--min_coverage", type=float, default=0.3)
    ap.add_argument("--with_dacd", action="store_true",
                    help="Enable DACD template clustering.")
    ap.add_argument("--dacd_clusters", type=Path, default=None)
    ap.add_argument("--dacd_min_cluster_size", type=int, default=8)
    ap.add_argument("--dacd_epsilon", type=float, default=0.35)
    args = ap.parse_args(argv)

    # ── Stage 1: build_epdg_bytecode (BYTECODE path) ──────────────────
    run_step(
        [sys.executable, str(SCRIPTS_DIR / "build_epdg_bytecode.py"),
         "-i", str(args.src_root),
         "-o", str(args.json_root),
         "--effects", str(args.effects)],
        desc="1/5 build_epdg_bytecode: source -> E-PDG JSON (bytecode path)",
    )

    # ── Stage 2: enrich_graph_views (identical) ───────────────────────
    run_step(
        [sys.executable, str(SCRIPTS_DIR / "enrich_graph_views.py"),
         "-j", str(args.json_root),
         "-o", str(args.json_mv_root)],
        desc="2/5 enrich_graph_views: base -> multi-view JSON",
    )

    json_for_index = args.json_mv_root

    # ── Stage 3: build_index (identical) ──────────────────────────────
    run_step(
        [sys.executable, str(SCRIPTS_DIR / "build_index.py"),
         "-j", str(json_for_index),
         "-o", str(args.index_path)],
        desc="3/5 build_index: multi-view JSON -> LSH index",
    )

    # ── Stage 4: build_lsh_candidates (identical) ─────────────────────
    run_step(
        [sys.executable, str(SCRIPTS_DIR / "build_lsh_candidates.py"),
         "-i", str(args.index_path),
         "-j", str(json_for_index),
         "-o", str(args.candidates_json)],
        desc="4/5 build_lsh_candidates: LSH index -> candidate function pairs",
    )

    # ── Stage 5 (optional): DACD clustering ───────────────────────────
    dacd_path: Path | None = args.dacd_clusters
    if args.with_dacd:
        if dacd_path is None:
            dacd_path = args.json_mv_root / "dacd_clusters.json"
        run_step(
            [sys.executable, "-m", "clustering.hdbscan_cluster",
             "--json-root", str(args.json_mv_root),
             "--output", str(dacd_path),
             "--min-cluster-size", str(args.dacd_min_cluster_size),
             "--epsilon", str(args.dacd_epsilon)],
            desc="5/6 DACD clustering: multi-view JSON -> dacd_clusters.json",
        )
    else:
        dacd_path = None

    # ── Final stage: search_and_rank (identical) ──────────────────────
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "search_and_rank.py"),
        "-i", str(args.index_path),
        "-j", str(args.json_mv_root),
        "-o", str(args.out_json),
        "-r", str(args.report_html),
        "--threshold", str(args.threshold),
        "--min_coverage", str(args.min_coverage),
        "--candidates", str(args.candidates_json),
    ]
    if dacd_path is not None:
        cmd.extend(["--dacd_clusters", str(dacd_path)])

    desc_last = ("6/6 search_and_rank: candidates (+ DACD) -> JSON + HTML"
                 if args.with_dacd
                 else "5/5 search_and_rank: candidates -> JSON + HTML")
    run_step(cmd, desc=desc_last)

    print("\n[OK] pipeline_bytecode completed end-to-end.")
    print("     JSON  report:", args.out_json)
    print("     HTML  report:", args.report_html)
    if args.with_dacd:
        print("     DACD clusters:", dacd_path)


if __name__ == "__main__":
    main()
