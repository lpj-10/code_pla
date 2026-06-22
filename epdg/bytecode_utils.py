import dis
import types
from typing import Dict, List, Tuple

# Opcodes that we completely ignore when building normalised opcode sequences.
IGNORE = {"NOP", "RESUME", "CACHE", "EXTENDED_ARG"}


def _is_interesting_name(name: str) -> bool:
    """Return True if a LOAD_* of this name should be kept as a distinct token.

    We only treat a small set of *library* / API names as interesting so that we
    stay robust to student variable renaming while still capturing task-level
    behaviour differences, for example::

        Counter / dict / list / set       -> collection operations
        split / lower / strip / format    -> string processing
        print / input / sys.stdin.read   -> IO pattern

    Everything else falls back to a coarse opcode token.
    """
    if not isinstance(name, str):
        return False
    lname = name.lower()
    # IO-ish
    if lname in {"print", "input"}:
        return True
    if lname.startswith("sys.") or lname == "sys":
        return True
    # Collections
    if lname in {"counter", "dict", "list", "set"}:
        return True
    # Common string helpers
    if lname in {"split", "join", "lower", "upper", "strip", "format"}:
        return True
    return False


def normalize_instr(op: dis.Instruction) -> str:
    """Map a CPython instruction to a stable, moderately-detailed opcode token.

    Compared to the original version, this keeps a bit more information for
    library / API calls while still bucketing literals and generic variable
    loads / stores.  The intent is to make ``tokens_norm`` more task-sensitive
    (fact vs word_freq vs fib) without overfitting on student-specific names.
    """
    opname = op.opname
    if opname in IGNORE:
        return ""

    # Bucket literal constants.
    if opname == "LOAD_CONST":
        v = op.argval
        if isinstance(v, bool):
            return "LOAD_CONST_BOOL"
        if isinstance(v, int):
            if v < -10 ** 6:
                return "LOAD_CONST_INT_BIG_NEG"
            if v > 10 ** 6:
                return "LOAD_CONST_INT_BIG_POS"
            return "LOAD_CONST_INT_SMALL"
        if isinstance(v, float):
            return "LOAD_CONST_FLOAT"
        if isinstance(v, str):
            L = len(v)
            if L <= 8:
                return "LOAD_CONST_STR_S"
            if L <= 64:
                return "LOAD_CONST_STR_M"
            return "LOAD_CONST_STR_L"
        return "LOAD_CONST_OTHER"

    # Loads / stores of variables and attributes.  For most names we only keep
    # the coarse opcode, but for a small whitelist of library helpers we keep
    # the name as a suffix, e.g. "LOAD_METHOD@split".
    if opname in {
        "LOAD_FAST", "STORE_FAST",
        "LOAD_DEREF", "STORE_DEREF",
        "LOAD_GLOBAL", "STORE_GLOBAL",
        "LOAD_NAME", "STORE_NAME",
        "LOAD_ATTR", "STORE_ATTR",
        "LOAD_METHOD",
    }:
        # Only specialise loads that carry a useful library / API name.
        if opname.startswith("LOAD") and _is_interesting_name(getattr(op, "argval", None)):
            return f"{opname}@{op.argval}"
        return opname

    # Collapse PRECALL / CALL_* into a small set of call markers.  We keep a
    # light distinction between "CALL_METHOD" and generic calls, since bound
    # method calls often encode string / collection helpers.
    if opname in {"PRECALL"}:
        # This is mostly an implementation detail in modern CPython; we can
        # safely ignore it in the normalised view.
        return ""
    if opname in {"CALL_METHOD"}:
        return "CALL_METHOD"
    if opname in {"CALL", "CALL_FUNCTION"}:
        return "CALL_FUNC"

    # Fallback: keep the raw opcode name.  This still preserves e.g. branches,
    # arithmetic ops, comparisons, etc.
    return opname


def walk_code_objects(root_code: types.CodeType):
    """Depth‑first walk of a code object and all nested functions / lambdas.

    Yields ``(code_object, qualified_name)`` pairs.
    """
    stack: List[Tuple[types.CodeType, str]] = [(root_code, "<module>")]
    while stack:
        co, qn = stack.pop()
        yield co, qn
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                child_qn = f"{qn}.{c.co_name}"
                stack.append((c, child_qn))


def function_opcode_tokens(root_code: types.CodeType) -> Dict[Tuple[str, int], List[str]]:
    """Return a mapping from (qualified_name, first_lineno) to opcode tokens.

    This is used as the "IR‑level view" for Python functions.  Downstream
    components treat it as a bag‑of‑tokens or sequence input; control / data
    dependencies are handled separately by the AST / E‑PDG builder.
    """
    out: Dict[Tuple[str, int], List[str]] = {}
    for co, qn in walk_code_objects(root_code):
        toks: List[str] = []
        for ins in dis.Bytecode(co):
            t = normalize_instr(ins)
            if t:
                toks.append(t)
        out[(qn, co.co_firstlineno)] = toks
    return out
