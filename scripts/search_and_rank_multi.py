# scripts/search_and_rank_multi.py
from __future__ import annotations

"""All-vs-all similarity + HTML report on top of *.epdg.json.

Compared to the original research pipeline (LSH + VCoME), this script is a
lightweight, dependency-free implementation that still respects the same
high-level design:

* read E-PDG style JSON for each source file
* derive per-function semantic features
* aggregate to per-program scores
* emit a JSON result file and an interactive HTML report

The similarity is currently based on

* Jaccard of normalised opcode / token sets, and
* cosine similarity of effect-signature vectors.

You can later plug a learned embedding model in here without touching the
reporting layer.
"""

import json
import math
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Set

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from report.report_html import render_pair_report  # type: ignore[import]


@dataclass
class FuncInfo:
    prog_id: int
    file: str
    func_id: str
    name: str
    start_line: int
    end_line: int
    tokens: Set[str]
    effect_counts: Dict[str, float]
    language: str
    effect_flags: Set[str]


@dataclass
class ProgramInfo:
    prog_id: int
    file: str
    language: str
    code: str


def _infer_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".py":
        return "python"
    if ext in {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}:
        return "c/cpp"
    if ext == ".java":
        return "java"
    return "unknown"


def _load_epdg_tree(json_root: Path) -> Tuple[List[ProgramInfo], List[FuncInfo], List[str]]:
    """Scan all *.epdg.json under json_root and collect programs / functions.

    Returns (programs, functions, effect_keys).
    """
    json_files = sorted(json_root.rglob("*.epdg.json"))
    if not json_files:
        raise SystemExit(f"No .epdg.json files found under {json_root}")

    programs: List[ProgramInfo] = []
    functions: List[FuncInfo] = []
    effect_key_set: Set[str] = set()

    prog_id_by_file: Dict[str, int] = {}

    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        src_file = data.get("file") or data.get("source") or ""
        if not src_file:
            # Fall back: strip .epdg.json suffix
            src_file = str(jf.with_suffix("").with_suffix(""))
        lang = _infer_language(src_file)

        if src_file not in prog_id_by_file:
            # Load source code, relative to ROOT_DIR if needed
            src_path = Path(src_file)
            if not src_path.is_absolute():
                candidate = ROOT_DIR / src_file
                if candidate.exists():
                    src_path = candidate
            try:
                code = Path(src_path).read_text(encoding="utf-8")
            except Exception:
                code = ""
            pid = len(programs)
            prog_id_by_file[src_file] = pid
            programs.append(ProgramInfo(prog_id=pid, file=src_file, language=lang, code=code))
        else:
            pid = prog_id_by_file[src_file]

        for f in data.get("functions", []):
            fid = f.get("id") or f.get("func_id") or f.get("name") or "<unknown>"
            name = f.get("name") or "<unknown>"
            # Approximate line span from nodes
            nodes = f.get("nodes", [])
            linenos = [n.get("lineno", 0) for n in nodes if n.get("lineno")]
            if linenos:
                start_line = min(linenos)
                end_line = max(linenos)
            else:
                start_line = int(f.get("first_lineno", 1))
                end_line = start_line

            tokens_list = f.get("tokens_norm") or []
            tokens = set(str(t) for t in tokens_list)

            eff_sig = f.get("effect_signature") or {}
            counts = {str(k): float(v) for k, v in (eff_sig.get("counts") or {}).items()}
            effect_key_set.update(counts.keys())
            flags_raw = eff_sig.get("flags") or []
            flags: Set[str] = set(str(x) for x in flags_raw)

            functions.append(
                FuncInfo(
                    prog_id=pid,
                    file=src_file,
                    func_id=str(fid),
                    name=str(name),
                    start_line=start_line,
                    end_line=end_line,
                    tokens=tokens,
                    effect_counts=counts,
                    language=lang,
                    effect_flags=flags,
                )
            )

    effect_keys = sorted(effect_key_set)
    return programs, functions, effect_keys


def _cosine_from_counts(a: Dict[str, float], b: Dict[str, float], keys: List[str]) -> float:
    if not keys:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for k in keys:
        va = a.get(k, 0.0)
        vb = b.get(k, 0.0)
        dot += va * vb
        na += va * va
        nb += vb * vb
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot / (math.sqrt(na) * math.sqrt(nb)))


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    if union == 0:
        return 0.0
    return float(inter) / float(union)


def _func_similarity(fa: FuncInfo, fb: FuncInfo, eff_keys: List[str], alpha: float) -> float:
    """Combined token + effect similarity for a pair of functions.

    The score is primarily a convex combination of token Jaccard and effect
    signature cosine similarity.  When either side is dominated by unknown
    calls (as signalled by the ``FLAG:unknown`` bit derived from
    ``effect_summaries.yaml``), we subtract a small penalty so that such
    pairs are ranked slightly lower than equally-scored pairs whose effects
    are backed by precise summaries.
    """
    jac = _jaccard(fa.tokens, fb.tokens)
    eff = _cosine_from_counts(fa.effect_counts, fb.effect_counts, eff_keys)
    score = alpha * jac + (1.0 - alpha) * eff

    # Down-weight pairs that involve unknown / conservatively summarised calls.
    penalty = 0.0
    if "unknown" in fa.effect_flags or "unknown" in fb.effect_flags:
        penalty += 0.05

    score -= penalty
    if score < 0.0:
        return 0.0
    return score


def _group_by_program(functions: List[FuncInfo]) -> Dict[int, List[FuncInfo]]:
    by_prog: Dict[int, List[FuncInfo]] = {}
    for f in functions:
        by_prog.setdefault(f.prog_id, []).append(f)
    return by_prog


def _program_pairs(
    programs: List[ProgramInfo],
    functions: List[FuncInfo],
    eff_keys: List[str],
    alpha: float,
    prog_threshold: float,
    func_threshold: float,
    topk_pairs: int,
) -> List[Dict]:
    by_prog = _group_by_program(functions)
    pairs: List[Dict] = []

    n = len(programs)
    for i in range(n):
        for j in range(i + 1, n):
            fa_list = by_prog.get(i, [])
            fb_list = by_prog.get(j, [])
            if not fa_list or not fb_list:
                continue

            # Build all candidate function pairs
            candidates: List[Tuple[float, int, int]] = []
            for ia, fa in enumerate(fa_list):
                for ib, fb in enumerate(fb_list):
                    s = _func_similarity(fa, fb, eff_keys, alpha)
                    if s >= func_threshold:
                        candidates.append((s, ia, ib))

            if not candidates:
                continue

            candidates.sort(reverse=True, key=lambda t: t[0])
            used_a: Set[int] = set()
            used_b: Set[int] = set()
            func_matches: List[Dict] = []

            for score, ia, ib in candidates:
                if ia in used_a or ib in used_b:
                    continue
                used_a.add(ia)
                used_b.add(ib)
                fa = fa_list[ia]
                fb = fb_list[ib]
                func_matches.append(
                    {
                        "score": score,
                        "func_a": {
                            "file": fa.file,
                            "func_id": fa.func_id,
                            "name": fa.name,
                            "start_line": fa.start_line,
                            "end_line": fa.end_line,
                            "language": fa.language,
                        },
                        "func_b": {
                            "file": fb.file,
                            "func_id": fb.func_id,
                            "name": fb.name,
                            "start_line": fb.start_line,
                            "end_line": fb.end_line,
                            "language": fb.language,
                        },
                    }
                )

            if not func_matches:
                continue

            prog_score = sum(m["score"] for m in func_matches) / len(func_matches)
            if prog_score < prog_threshold:
                continue

            pairs.append(
                {
                    "prog_a": programs[i].prog_id,
                    "prog_b": programs[j].prog_id,
                    "score": prog_score,
                    "func_matches": func_matches,
                }
            )

    pairs.sort(key=lambda p: p["score"], reverse=True)
    if topk_pairs > 0:
        pairs = pairs[:topk_pairs]
    return pairs


def main(argv: List[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="All-vs-all similarity + HTML report from *.epdg.json.")
    ap.add_argument("-j", "--json_root", type=Path, required=True, help="Root directory containing *.epdg.json.")
    ap.add_argument("-o", "--out_json", type=Path, required=True, help="Path to write result JSON.")
    ap.add_argument(
        "-r",
        "--report_html",
        type=Path,
        required=False,
        help="If set, also render an interactive HTML report to this path.",
    )
    ap.add_argument(
        "--alpha",
        type=float,
        default=0.7,
        help="Weight for token Jaccard vs effect-signature cosine (default: 0.7).",
    )
    ap.add_argument(
        "--prog_threshold",
        type=float,
        default=0.6,
        help="Minimum program-level similarity to keep (default: 0.6).",
    )
    ap.add_argument(
        "--func_threshold",
        type=float,
        default=0.6,
        help="Minimum function-level similarity to consider (default: 0.6).",
    )
    ap.add_argument(
        "--topk_pairs",
        type=int,
        default=200,
        help="Maximum number of program pairs to keep in the result (default: 200).",
    )

    args = ap.parse_args(argv)

    programs, functions, eff_keys = _load_epdg_tree(args.json_root)
    print(f"[info] loaded {len(programs)} programs, {len(functions)} functions, {len(eff_keys)} effect keys")

    pairs = _program_pairs(
        programs=programs,
        functions=functions,
        eff_keys=eff_keys,
        alpha=args.alpha,
        prog_threshold=args.prog_threshold,
        func_threshold=args.func_threshold,
        topk_pairs=args.topk_pairs,
    )

    out = {
        "meta": {
            "json_root": str(args.json_root),
            "alpha": args.alpha,
            "prog_threshold": args.prog_threshold,
            "func_threshold": args.func_threshold,
        },
        "programs": [asdict(p) for p in programs],
        "effect_keys": eff_keys,
        "pairs": pairs,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote results JSON to {args.out_json}")

    if args.report_html is not None:
        args.report_html.parent.mkdir(parents=True, exist_ok=True)
        render_pair_report(out, args.report_html)
        print(f"[OK] wrote HTML report to {args.report_html}")


if __name__ == "__main__":
    main()
