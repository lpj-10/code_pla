# scripts/build_epdg_bytecode.py
"""Build E-PDG JSON using the bytecode-based PDG builder.

This is the bytecode-path counterpart of ``build_epdg.py`` (AST path).
It compiles Python source to code objects, then uses
``legacy_bytecode_path.bytecode_pdg_builder.BytecodeBuilder``
to construct PDG with:
  - Real basic-block CFG from CPython bytecode
  - SSA-style worklist dataflow analysis
  - Post-dominator-based control dependence edges

NOTE: Only supports Python source files (.py). C/C++/Java are not
      supported on this path.

Usage::

    python scripts/build_epdg_bytecode.py \\
      -i data/submissions_simple \\
      -o data/artifacts/json \\
      --effects effect_summaries.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from epdg.effects_loader import EffectDB
from epdg.bytecode_utils import function_opcode_tokens
from epdg.serializer import to_json
from legacy_bytecode_path.bytecode_pdg_builder import BytecodeBuilder


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Build E-PDG JSON from Python sources (bytecode path).",
    )
    ap.add_argument("-i", "--input", type=Path, required=True,
                    help="Root directory containing .py files.")
    ap.add_argument("-o", "--output", type=Path, required=True,
                    help="Directory to write *.epdg.json files.")
    ap.add_argument("--effects", type=Path,
                    default=ROOT_DIR / "effect_summaries.yaml",
                    help="Effect summary YAML.")
    args = ap.parse_args(argv)

    in_dir: Path = args.input
    out_dir: Path = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    edb = EffectDB.from_file(str(args.effects))
    builder = BytecodeBuilder(edb)

    import platform
    pyver = platform.python_version()

    files = sorted(p for p in in_dir.rglob("*.py") if p.is_file())
    if not files:
        print(f"[WARN] no .py files found under {in_dir}", file=sys.stderr)
        return

    for src_path in files:
        try:
            src = src_path.read_text(encoding="utf-8")
            code_obj = compile(src, str(src_path), "exec")

            funcs = builder.build_from_code(str(src_path), code_obj)

            # Attach opcode token sequences (same as AST path)
            try:
                tokmap = function_opcode_tokens(code_obj)
            except Exception:
                tokmap = {}
            for f in funcs:
                best_tokens = None
                best_dist = 1e9
                for (qn, ln), toks in tokmap.items():
                    if (f.name == "<module>" and qn == "<module>") or \
                       qn.endswith(f".{f.name}"):
                        d = abs(ln - f.first_lineno)
                        if d < best_dist:
                            best_dist = d
                            best_tokens = toks
                f.tokens_norm = best_tokens or []

            # Materialize effect nodes for graph similarity
            try:
                from epdg.effect_nodes import materialize_effect_nodes
                for f in funcs:
                    materialize_effect_nodes(f)
            except Exception:
                pass

            rel = src_path.relative_to(in_dir)
            out_path = out_dir / (str(rel) + ".epdg.json")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_json = to_json(str(src_path), pyver, funcs)
            out_path.write_text(out_json, encoding="utf-8")
            print(f"[OK] {src_path} -> {out_path} [python/bytecode]")
        except Exception as e:
            print(f"[ERR] {src_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
