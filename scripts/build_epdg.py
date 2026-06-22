# scripts/build_epdg.py
from __future__ import annotations

import os
import sys
from pathlib import Path
import argparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from epdg.effects_loader import EffectDB
from epdg.parser_frontend import build_for_file as build_py_file
from epdg.cxx_simple_frontend import build_for_cxx_file
from epdg.java_simple_frontend import build_for_java_file
from epdg.serializer import to_json


LANG_EXTS = {
    "python": {".py"},
    "c": {".c", ".h"},
    "cpp": {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"},
    "java": {".java"},
}


def _detect_lang(path: Path) -> str | None:
    ext = path.suffix.lower()
    for lang, exts in LANG_EXTS.items():
        if ext in exts:
            return lang
    return None


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Build E-PDG-style JSON from source files.")
    ap.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Root directory containing source files.",
    )
    ap.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Directory to write *.epdg.json files.",
    )
    ap.add_argument(
        "--effects",
        type=Path,
        default=ROOT_DIR / "effect_summaries.yaml",
        help="Effect summary YAML. Default: %(default)s",
    )
    ap.add_argument(
        "--lang",
        choices=["auto", "python", "c", "cpp", "java"],
        default="auto",
        help="If not 'auto', restrict to a single language.",
    )

    ap.add_argument(
        "--cxx-backend",
        choices=["auto", "llvm", "asm", "source"],
        default="auto",
        help="C/C++ frontend backend: auto (llvm->asm->source), llvm, asm, or source.",
    )

    ap.add_argument(
        "--cxx-opt",
        type=str,
        default="1",
        help="C/C++ compilation optimization level for clang (e.g., 0/1/2/3, s, z). Default: %(default)s",
    )
    ap.add_argument(
        "--cxx-target",
        type=str,
        default="",
        help="Optional clang -target triple (e.g., x86_64-linux-gnu, aarch64-linux-gnu). Default: empty (host default).",
    )
    ap.add_argument(
        "--cxx-extra-flags",
        type=str,
        default="",
        help="Extra flags appended to clang invocation for C/C++ (quoted string, e.g., \"-std=c++17 -DDEBUG\").",
    )
    args = ap.parse_args(argv)

    in_dir: Path = args.input
    out_dir: Path = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    edb = EffectDB.from_file(str(args.effects))

    def iter_files() -> list[tuple[Path, str]]:
        files: list[tuple[Path, str]] = []
        for p in in_dir.rglob("*"):
            if not p.is_file():
                continue
            lang = _detect_lang(p)
            if lang is None:
                continue
            if args.lang != "auto" and lang != args.lang:
                continue
            files.append((p, lang))
        return sorted(files, key=lambda x: str(x[0]))

    files = iter_files()
    if not files:
        print(f"[WARN] no source files found under {in_dir} for lang={args.lang}", file=sys.stderr)
        return

    for src_path, lang in files:
        try:
            if lang == "python":
                ver, funcs = build_py_file(src_path, edb, backend="ast")
            elif lang in {"c", "cpp"}:
                ver, funcs = build_for_cxx_file(src_path, edb, backend=args.cxx_backend, cxx_opt=args.cxx_opt, cxx_target=args.cxx_target, cxx_extra_flags=args.cxx_extra_flags)
            elif lang == "java":
                ver, funcs = build_for_java_file(src_path, edb)
            else:
                # Should not happen due to _detect_lang
                continue

            rel = src_path.relative_to(in_dir)
            out_path = out_dir / (str(rel) + ".epdg.json")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_json = to_json(str(src_path), ver, funcs)
            out_path.write_text(out_json, encoding="utf-8")
            print(f"[OK] {src_path} -> {out_path} [{lang}]")
        except Exception as e:
            print(f"[ERR] {src_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()