
# scripts/pipeline_full_multilang.py
"""End-to-end multi-language plagiarism pipeline (no eval).

从源代码目录开始，一次性跑完：
  1) 源码 → E-PDG JSON（多语言，含副作用）
  2) E-PDG JSON → 多视图 JSON（补 AST / DFG 视图）
  3) 多视图 JSON → MinHash / WL / k-path 索引
  4) 索引 + 副作用向量 → LSH 候选函数对
  5) 多视图 JSON → opcode vocab
  6) 多视图 JSON + vocab → 训练多视图 VCoME
  7) LSH 候选 + VCoME → rerank + 程序级聚合 + 程序聚类 JSON
  8) rerank JSON → 程序聚类 HTML 报告（含函数级 diff）

使用方式示例（在项目根目录下）::

    python scripts/pipeline_full_multilang.py \
      --src_root data/submissions \
      --json_root data/artifacts/json \
      --json_mv_root data/artifacts/json_mv \
      --effects effect_summaries.yaml \
      --index_path data/artifacts/index/epdg_lsh.pkl \
      --candidates_json data/artifacts/retrieval/lsh_pairs.json \
      --vocab_path data/opcode_vocab.json \
      --vcome_ckpt data/artifacts/vcome/vcome_multi.pt \
      --rerank_json data/artifacts/retrieval/reranked_pairs.json \
      --clusters_html data/artifacts/reports/program_clusters.html \
      --device cpu

如已有训练好的 VCoME 多视图模型，可加上 --skip_train，跳过训练直接复用 ckpt::

    python scripts/pipeline_full_multilang.py \
      --src_root data/submissions \
      --skip_train \
      --device cuda
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
    print(f"\n[step] {desc}")
    print(" ", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"[ERROR] step failed ({desc}), return code={result.returncode}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="End-to-end multi-language plagiarism pipeline (no eval)."
    )
    ap.add_argument(
        "--src_root",
        type=Path,
        required=True,
        help="Root directory containing student source submissions (multi-language).",
    )
    ap.add_argument(
        "--json_root",
        type=Path,
        default=Path("data/artifacts/json"),
        help="Directory to write base *.epdg.json files.",
    )
    ap.add_argument(
        "--json_mv_root",
        type=Path,
        default=Path("data/artifacts/json_mv"),
        help="Directory to write multi-view *.epdg.json files (AST/DFG enriched).",
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
        "--vocab_path",
        type=Path,
        default=Path("data/opcode_vocab.json"),
        help="Output path for opcode vocab JSON.",
    )
    ap.add_argument(
        "--vcome_ckpt",
        type=Path,
        default=Path("data/artifacts/vcome/vcome_multi.pt"),
        help="Path to save or load multi-view VCoME checkpoint (.pt).",
    )
    ap.add_argument(
        "--rerank_json",
        type=Path,
        default=Path("data/artifacts/retrieval/reranked_pairs.json"),
        help="Output path for reranked pairs + per-program JSON.",
    )
    ap.add_argument(
        "--clusters_html",
        type=Path,
        default=Path("data/artifacts/reports/program_clusters.html"),
        help="Output path for HTML clusters report.",
    )

    # training / embedding hyper-parameters (VCoME)
    ap.add_argument("--epochs", type=int, default=20, help="Training epochs for VCoME.")
    ap.add_argument(
        "--train_batch_size",
        type=int,
        default=32,
        help="Batch size for VCoME training.",
    )
    ap.add_argument("--train_lr", type=float, default=1e-3, help="Learning rate for VCoME.")
    ap.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for training and embedding, e.g. 'cpu' or 'cuda'.",
    )
    ap.add_argument("--max_tokens", type=int, default=512)
    ap.add_argument("--node_feat_dim", type=int, default=16)
    ap.add_argument("--token_dim", type=int, default=128)
    ap.add_argument("--graph_dim", type=int, default=128)
    ap.add_argument("--eff_dim", type=int, default=64)
    ap.add_argument("--final_dim", type=int, default=256)
    ap.add_argument("--drop_edge_p", type=float, default=0.1)
    ap.add_argument("--jitter_feat_p", type=float, default=0.0)
    ap.add_argument("--jitter_std", type=float, default=0.01)
    ap.add_argument("--tau", type=float, default=0.1)

    # rerank / clustering hyper-parameters
    ap.add_argument(
        "--rerank_batch_size",
        type=int,
        default=32,
        help="Batch size for VCoME embedding during rerank.",
    )
    ap.add_argument(
        "--vcome_weight",
        type=float,
        default=1.0,
        help="Weight of VCoME similarity in final combined score.",
    )
    ap.add_argument(
        "--lsh_weight",
        type=float,
        default=0.0,
        help="Weight of LSH/WL similarity in final combined score.",
    )
    ap.add_argument(
        "--cluster_method",
        type=str,
        choices=["auto", "hdbscan", "graph"],
        default="auto",
        help="Program-level clustering method.",
    )
    ap.add_argument(
        "--cluster_min_size",
        type=int,
        default=2,
        help="Minimum cluster size for program-level clustering.",
    )
    ap.add_argument(
        "--cluster_edge_threshold",
        type=float,
        default=0.75,
        help="Similarity threshold used when building program graph for clustering.",
    )
    ap.add_argument(
        "--max_funcs_per_edge",
        type=int,
        default=20,
        help="Max number of function-level pairs to show per program edge in HTML.",
    )

    ap.add_argument(
        "--skip_train",
        action="store_true",
        help="If set, skip VCoME training and assume vcome_ckpt already exists.",
    )

    args = ap.parse_args(argv)

    # Ensure directories exist
    args.json_root.mkdir(parents=True, exist_ok=True)
    args.json_mv_root.mkdir(parents=True, exist_ok=True)
    args.index_path.parent.mkdir(parents=True, exist_ok=True)
    args.candidates_json.parent.mkdir(parents=True, exist_ok=True)
    args.vocab_path.parent.mkdir(parents=True, exist_ok=True)
    args.rerank_json.parent.mkdir(parents=True, exist_ok=True)
    args.clusters_html.parent.mkdir(parents=True, exist_ok=True)

    # 1) build_epdg: 源代码 → E-PDG JSON
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
        desc="1/8 build_epdg: source -> E-PDG JSON",
    )

    # 2) enrich_graph_views: 单视图 → 多视图 (AST/DFG)
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "enrich_graph_views.py"),
            "-j",
            str(args.json_root),
            "-o",
            str(args.json_mv_root),
        ],
        desc="2/8 enrich_graph_views: base -> multi-view JSON",
    )

    # 3) build_index: 多视图 JSON → LSH 索引
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_index.py"),
            "-j",
            str(args.json_mv_root),
            "-o",
            str(args.index_path),
        ],
        desc="3/8 build_index: multi-view JSON -> LSH index",
    )

    # 4) build_lsh_candidates: LSH 索引 + 副作用 → 候选函数对
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_lsh_candidates.py"),
            "-i",
            str(args.index_path),
            "-j",
            str(args.json_mv_root),
            "-o",
            str(args.candidates_json),
        ],
        desc="4/8 build_lsh_candidates: index -> candidate function pairs",
    )

    # 5) build_opcode_vocab: 多视图 JSON → opcode vocab
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_opcode_vocab.py"),
            "-j",
            str(args.json_mv_root),
            "-o",
            str(args.vocab_path),
        ],
        desc="5/8 build_opcode_vocab: multi-view JSON -> opcode vocab",
    )

    # 6) 训练多视图 VCoME (可选)
    if not args.skip_train:
        run_step(
            [
                sys.executable,
                "-m",
                "vcome.train_vcome_multi",
                "-j",
                str(args.json_mv_root),
                "-v",
                str(args.vocab_path),
                "-o",
                str(args.vcome_ckpt),
                "--epochs",
                str(args.epochs),
                "--bs",
                str(args.train_batch_size),
                "--lr",
                str(args.train_lr),
                "--device",
                args.device,
                "--max_tokens",
                str(args.max_tokens),
                "--node_feat_dim",
                str(args.node_feat_dim),
                "--token_dim",
                str(args.token_dim),
                "--graph_dim",
                str(args.graph_dim),
                "--eff_dim",
                str(args.eff_dim),
                "--final_dim",
                str(args.final_dim),
                "--drop_edge_p",
                str(args.drop_edge_p),
                "--jitter_feat_p",
                str(args.jitter_feat_p),
                "--jitter_std",
                str(args.jitter_std),
                "--tau",
                str(args.tau),
            ],
            desc="6/8 train_vcome_multi: train multi-view VCoME model",
        )
    else:
        print("[skip] 6/8 train_vcome_multi: --skip_train specified, reusing existing ckpt")

    # 7) rerank_candidates_multi: LSH 候选 + VCoME → 程序级 JSON
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "rerank_candidates_multi.py"),
            "-j",
            str(args.json_mv_root),
            "-v",
            str(args.vocab_path),
            "-C",
            str(args.candidates_json),
            "-o",
            str(args.rerank_json),
            "--ckpt",
            str(args.vcome_ckpt),
            "--device",
            args.device,
            "--max_tokens",
            str(args.max_tokens),
            "--node_feat_dim",
            str(args.node_feat_dim),
            "--batch_size",
            str(args.rerank_batch_size),
            "--vcome_weight",
            str(args.vcome_weight),
            "--lsh_weight",
            str(args.lsh_weight),
            "--cluster_method",
            args.cluster_method,
            "--cluster_min_size",
            str(args.cluster_min_size),
            "--cluster_edge_threshold",
            str(args.cluster_edge_threshold),
        ],
        desc="7/8 rerank_candidates_multi: rerank + program-level aggregation + clustering",
    )

    # 8) render_clusters_report: 程序聚类 JSON → HTML 报告
    run_step(
        [
            sys.executable,
            str(SCRIPTS_DIR / "render_clusters_report.py"),
            "-i",
            str(args.rerank_json),
            "-o",
            str(args.clusters_html),
            "--edge_threshold",
            str(args.cluster_edge_threshold),
            "--max_funcs_per_edge",
            str(args.max_funcs_per_edge),
        ],
        desc="8/8 render_clusters_report: JSON -> HTML clusters report",
    )

    print("\n[OK] pipeline_full_multilang completed end-to-end.")
    print("     HTML report at:", args.clusters_html)


if __name__ == "__main__":
    main()
