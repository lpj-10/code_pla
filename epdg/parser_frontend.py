# epdg/parser_frontend.py
import platform
from pathlib import Path
from typing import List, Tuple

from .effects_loader import EffectDB
from .ast_pdg_builder import Builder as ASTBuilder, FuncIR
from .bytecode_utils import function_opcode_tokens


def build_for_file(py_path: Path, effects_db: EffectDB, backend: str = "ast") -> Tuple[str, List[FuncIR]]:
    """Build E‑PDG style IR for a single Python source file.

    To keep the implementation robust and avoid depending on the more fragile
    bytecode builder, we *always* use the AST‑based builder here and treat the
    ``backend`` argument as a no‑op kept only for backward compatibility.

    The returned functions already contain:
      - nodes / CFG / PDG / effect_signature from :class:`ASTBuilder`
      - an additional ``tokens_norm`` field filled from CPython bytecode
        opcodes via :func:`function_opcode_tokens`.
    """
    src = py_path.read_text(encoding="utf-8")
    pyver = platform.python_version()

    builder = ASTBuilder(effects_db)
    funcs = builder.build_from_ast(str(py_path), src)

    # Attach opcode‑level token sequence for downstream models.
    try:
        code_obj = compile(src, str(py_path), "exec")
        tokmap = function_opcode_tokens(code_obj)  # (qualname, first_lineno) -> List[str]
    except Exception:
        tokmap = {}

    for f in funcs:
        best_tokens = None
        best_dist = 1e9
        for (qn, ln), toks in tokmap.items():
            # Match by qualified name and proximity of first line number.
            if (f.name == "<module>" and qn == "<module>") or qn.endswith(f".{f.name}"):
                d = abs(ln - f.first_lineno)
                if d < best_dist:
                    best_dist = d
                    best_tokens = toks
        f.tokens_norm = best_tokens or []

    return pyver, funcs
