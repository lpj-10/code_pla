# scripts/pipeline_pure_lsh_dacd.py
"""End-to-end pure-LSH plagiarism pipeline (optional DACD templates).

从源代码目录开始，一次性跑完当前文档
`docs/code_plagiarism_pipelines_latest_no_eval.md` 里的 4.1–4.6 步骤：

  1) 源码 → E-PDG JSON（含副作用）
  2) E-PDG JSON → 多视图 JSON（AST / DFG / PDG 视图）
  3) 多视图 JSON → MinHash / LSH 索引
  4) 索引 + 多视图 JSON → LSH 候选函数对
  5) （可选）E-PDG 多视图 JSON → DACD 模板簇 + 模板降权 JSON
  6) LSH 候选 + DACD 模板信息 → 程序级查重分数 + HTML 报告

默认参数与 `code_plagiarism_pipelines_latest_no_eval.md` 文档保持一致，
同时提供 `--with_dacd` 开关控制是否运行 DACD 模板簇步骤。

用法示例（在项目根目录下）::

    # 只用纯 LSH 流程（不跑 DACD）
    python scripts/pipeline_pure_lsh_dacd.py \
      --src_root data/submissions

    # 启用 DACD 模板簇 + 群体降权
    python scripts/pipeline_pure_lsh_dacd.py \
      --src_root data/submissions \
      --with_dacd

你也可以通过 `-h` 查看所有参数及默认值。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
# Ensure repo root on sys.path for config_ablation and sibling modules.
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def run_step(cmd: list[str], desc: str) -> None:
    """Run a single pipeline step with pretty logging.

    如果子进程返回非零退出码，会直接退出整个脚本。
    """
    print(f"\n[step] {desc}")
    print("  ", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"[ERROR] step failed ({desc}), return code={result.returncode}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="End-to-end pure-LSH plagiarism pipeline (optional DACD templates)."
    )
    ap.add_argument(
        "--src_root",
        type=Path,
        default=Path("data/submissions"),
        help="Root directory containing source submissions to check.",
    )
    ap.add_argument(
        "--json_root",
        type=Path,
        default=Path("data/artifacts/json"),
        help="Directory to write base E-PDG *.epdg.json files.",
    )
    ap.add_argument(
        "--json_mv_root",
        type=Path,
        default=Path("data/artifacts/json_mv"),
        help="Directory to write multi-view *.epdg.json files (AST/DFG/PDG enriched)." ,
    )
    ap.add_argument(
        "--effects",
        type=Path,
        default=Path("effect_summaries.yaml"),
        help="Effect summaries YAML for building E-PDG.",
    )
    ap.add_argument(
        "--index_path",
        type=Path,
        default=Path("data/artifacts/index/epdg_lsh.pkl"),
        help="Output path for LSH index pickle.",
    )
    ap.add_argument(
        "--candidates_json",
        type=Path,
        default=Path("data/artifacts/retrieval/lsh_pairs.json"),
        help="Output path for LSH candidate pairs JSON.",
    )
    ap.add_argument(
        "--out_json",
        type=Path,
        default=Path("data/artifacts/retrieval/baseline_pairs.json"),
        help="Output path for final program-level similarity JSON.",
    )
    ap.add_argument(
        "--report_html",
        type=Path,
        default=Path("data/artifacts/reports/baseline_pairs.html"),
        help="Output path for final HTML report.",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Similarity threshold for program pairs (see search_and_rank.py)." ,
    )
    ap.add_argument(
        "--min_coverage",
        type=float,
        default=0.3,
        help="Minimum coverage fraction when aggregating function matches.",
    )
    # DACD / template-related options
    ap.add_argument(
        "--with_dacd",
        action="store_true",
        help="Enable DACD template clustering and downweighting (4.6)." ,
    )
    ap.add_argument(
        "--dacd_clusters",
        type=Path,
        default=None,
        help="Path to write/read dacd_clusters.json. Defaults to <json_mv_root>/dacd_clusters.json.",
    )
    ap.add_argument(
        "--dacd_min_cluster_size",
        type=int,
        default=8,
        help="Minimum cluster size for DACD template clustering.",
    )
    ap.add_argument(
        "--dacd_epsilon",
        type=float,
        default=0.35,
        help="Scale parameter (distance threshold) for DACD clustering.",
    )

    args = ap.parse_args(argv)

    # 1) build_epdg: 源码 -> base E-PDG JSON
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_epdg.py"),
            "-i",
            str(args.src_root),
            "-o",
            str(args.json_root),
            "--effects",
            str(args.effects),
        ],
        desc="1/5 build_epdg: source -> E-PDG JSON",
    )

    # 2) enrich_graph_views: base -> multi-view JSON
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "enrich_graph_views.py"),
            "-j",
            str(args.json_root),
            "-o",
            str(args.json_mv_root),
        ],
        desc="2/5 enrich_graph_views: base -> multi-view JSON",
    )

    # 后续步骤统一在 multi-view JSON 上工作
    json_for_index = args.json_mv_root

    # 3) build_index: 多视图 JSON -> LSH 索引
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_index.py"),
            "-j",
            str(json_for_index),
            "-o",
            str(args.index_path),
        ],
        desc="3/5 build_index: multi-view JSON -> LSH index",
    )

    # 4) build_lsh_candidates: 索引 + 多视图 JSON -> LSH 候选函数对
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_lsh_candidates.py"),
            "-i",
            str(args.index_path),
            "-j",
            str(json_for_index),
            "-o",
            str(args.candidates_json),
        ],
        desc="4/5 build_lsh_candidates: LSH index -> candidate function pairs",
    )

    # 5) （可选）DACD 模板簇 + 群体降权
    dacd_path: Path | None = args.dacd_clusters
    if args.with_dacd:
        if dacd_path is None:
            dacd_path = args.json_mv_root / "dacd_clusters.json"

        run_step(
            [
                sys.executable,
                "-m",
                "clustering.hdbscan_cluster",
                "--json-root",
                str(args.json_mv_root),
                "--output",
                str(dacd_path),
                "--min-cluster-size",
                str(args.dacd_min_cluster_size),
                "--epsilon",
                str(args.dacd_epsilon),
            ],
            desc="5/6 DACD clustering: multi-view JSON -> dacd_clusters.json",
        )
    else:
        # 不跑 DACD 时，保持 dacd_path=None，让 search_and_rank 走纯 LSH 分支。
        dacd_path = None

    # 最后一阶段：search_and_rank 程序级聚合 + HTML 报告
    # 注意：search_and_rank.py 目前期望 json_root 指向 E-PDG JSON 根目录。
    # 在最新管线中我们推荐使用包含多视图字段的 json_mv_root。
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "search_and_rank.py"),
        "-i",
        str(args.index_path),
        "-j",
        str(args.json_mv_root),
        "-o",
        str(args.out_json),
        "-r",
        str(args.report_html),
        "--threshold",
        str(args.threshold),
        "--min_coverage",
        str(args.min_coverage),
        "--candidates",
        str(args.candidates_json),
    ]
    if dacd_path is not None:
        cmd.extend(["--dacd_clusters", str(dacd_path)])

    desc_last = "6/6 search_and_rank: candidates (+ DACD) -> JSON + HTML" if args.with_dacd         else "5/5 search_and_rank: candidates -> JSON + HTML"
    run_step(cmd, desc=desc_last)

    print("\n[OK] pipeline_pure_lsh_dacd completed end-to-end.")
    print("     JSON  report:", args.out_json)
    print("     HTML  report:", args.report_html)
    if args.with_dacd:
        print("     DACD clusters:", dacd_path)


if __name__ == "__main__":  # pragma: no cover
    main()
