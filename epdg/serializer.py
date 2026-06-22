import json
from dataclasses import asdict
from typing import List, Dict
from .ast_pdg_builder import FuncIR, NodeIR


def _aggregate_debug_info(f: FuncIR) -> Dict[str, object]:
    """Compute lightweight summaries for a function.

    These fields are optional and safe to ignore by downstream components.
    """
    called: List[str] = []
    for n in f.nodes:
        try:
            called.extend(list(getattr(n, "calls", []) or []))
        except Exception:
            pass

    modules: List[str] = []
    for c in called:
        # heuristic: strip module prefix if present (e.g., os.path.join -> os.path)
        if "." in c:
            modules.append(c.split(".", 1)[0])

    op_counts: Dict[str, int] = {}
    for n in f.nodes:
        k = str(getattr(n, "kind", "UNK"))
        op_counts[k] = op_counts.get(k, 0) + 1

    called = sorted(set(called))
    modules = sorted(set(modules))

    return {
        "dbg_called_funcs": called,
        "dbg_modules": modules,
        "dbg_op_category_counts": op_counts,
        "called_funcs": called,
        "modules": modules,
        "op_category_counts": op_counts,
    }


def func_to_dict(f: FuncIR) -> dict:
    # Graph-usable effect edges (int,int) are stored on f.pdg_effect_edges by effect_nodes.materialize_effect_nodes().
    base = {
        "id": f.fid,
        "name": f.name,
        "first_lineno": f.first_lineno,
        "nodes": [asdict(n) for n in f.nodes],
        "cfg": {"edges": getattr(f, "cfg_edges", [])},
        "pdg": {
            "data_edges": getattr(f, "pdg_data", []),
            "control_edges": getattr(f, "pdg_ctrl", []),
            "effect_edges": getattr(f, "pdg_effect_edges", []),
            # Keep the original string form for debug/report display
            "effect_raw": getattr(f, "pdg_eff", []),
        },
        "dfg_edges": getattr(f, "dfg_edges", []),
        "ast_edges": getattr(f, "ast_edges", []),
        "effect_signature": getattr(f, "effect_signature", {}),
        "tokens_norm": getattr(f, "tokens_norm", []),
    }

    try:
        base.update(_aggregate_debug_info(f))
    except Exception:
        pass
    return base


def to_json(file_path: str, py_version: str, funcs: List[FuncIR]) -> str:
    obj = {"file": file_path, "py_version": py_version, "functions": [func_to_dict(f) for f in funcs]}
    return json.dumps(obj, ensure_ascii=False, indent=2)
