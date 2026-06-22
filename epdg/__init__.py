# epdg/__init__.py
"""
E-PDG (Effect-augmented Program Dependence Graph) minimal package.

This package exposes a tiny, stable API so that scripts can do:
    from epdg import load_effects, build_for_file, to_json

Main Exports:
- EffectDB, EffectItem: effect summaries (YAML/JSON) loader & entry type
- Builder, FuncIR, NodeIR: AST → PDG/E-PDG builder and IR dataclasses
- build_for_file: one-shot frontend (AST + bytecode tokens attachment)
- function_opcode_tokens, normalize_instr: bytecode utilities
- to_json: JSON serializer for FuncIR list

Version: bump this if you change the public schema.
"""

from .effects_loader import EffectDB, EffectItem  # noqa: F401
from .ast_pdg_builder import Builder, FuncIR, NodeIR  # noqa: F401
from .parser_frontend import build_for_file  # noqa: F401
from .bytecode_utils import function_opcode_tokens, normalize_instr  # noqa: F401
from .serializer import to_json  # noqa: F401

__all__ = [
    "EffectDB",
    "EffectItem",
    "Builder",
    "FuncIR",
    "NodeIR",
    "build_for_file",
    "function_opcode_tokens",
    "normalize_instr",
    "to_json",
    "load_effects",
    "__version__",
]

__version__ = "0.1.0"

def load_effects(path: str) -> EffectDB:
    """
    Convenience loader for effect summaries (YAML or JSON).

    Example:
        from epdg import load_effects, build_for_file, to_json
        edb = load_effects("effect_summaries.yaml")
        pyver, funcs = build_for_file(Path("foo.py"), edb)
        print(to_json("foo.py", pyver, funcs))
    """
    return EffectDB.from_file(path)

