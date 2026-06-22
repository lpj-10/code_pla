#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def enrich_file(in_path: Path, out_path: Path) -> None:
    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False

    for func in data.get("functions", []):
        pdg: Dict[str, Any] = func.get("pdg", {})

        # ---- DFG 视图：如果不存在或者是空列表，就用 data_edges 填充 ----
        dfg_edges = func.get("dfg_edges")
        if (not dfg_edges) and pdg.get("data_edges") is not None:
            # 直接复制一份，避免共享引用
            func["dfg_edges"] = list(pdg["data_edges"])
            changed = True

        # ---- AST 视图：如果不存在或者是空列表，就用 control_edges 的 (src,dst) 填充 ----
        ast_edges = func.get("ast_edges")
        if (not ast_edges) and pdg.get("control_edges") is not None:
            func["ast_edges"] = [
                [src, dst] for (src, dst, _label) in pdg["control_edges"]
            ]
            changed = True

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        # 即使 changed == False，也把文件写出去，这样可以保持输出目录结构一致
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Post-process *.epdg.json to add explicit DFG/AST edge views "
                    "from PDG data/control edges."
    )
    ap.add_argument(
        "-j", "--json-root", required=True,
        help="Root directory containing *.epdg.json files."
    )
    ap.add_argument(
        "-o", "--out-root",
        help="Output root for enriched JSONs. "
             "If omitted and --inplace is not set, use <json_root>_mv."
    )
    ap.add_argument(
        "--inplace", action="store_true",
        help="Modify JSON files in-place under json_root."
    )
    args = ap.parse_args()

    json_root = Path(args.json_root)
    if not json_root.is_dir():
        raise SystemExit(f"json_root is not a directory: {json_root}")

    if args.inplace:
        out_root = json_root
    else:
        out_root = Path(args.out_root) if args.out_root else Path(str(json_root) + "_mv")
        out_root.mkdir(parents=True, exist_ok=True)

    for p in json_root.rglob("*.epdg.json"):
        rel = p.relative_to(json_root)
        out_path = out_root / rel if not args.inplace else p
        enrich_file(p, out_path)


if __name__ == "__main__":
    main()