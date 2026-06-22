import ast
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set, FrozenSet

from .effects_loader import EffectDB


@dataclass
class NodeIR:
    nid: int
    kind: str
    lineno: int
    reads: List[str] = field(default_factory=list)
    writes: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    effects: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FuncIR:
    fid: str
    name: str
    first_lineno: int
    nodes: List[NodeIR] = field(default_factory=list)
    cfg_edges: List[Tuple[int, int]] = field(default_factory=list)
    pdg_data: List[Tuple[int, int, str]] = field(default_factory=list)
    pdg_ctrl: List[Tuple[int, int, str]] = field(default_factory=list)
    pdg_eff: List[Tuple[int, str, str]] = field(default_factory=list)
    # materialized effect edges: (src_nid, res_node_nid) for graph similarity
    pdg_effect_edges: List[Tuple[int, int]] = field(default_factory=list)
    effect_signature: Dict[str, Any] = field(default_factory=dict)
    tokens_norm: List[str] = field(default_factory=list)
    # multi-view edges: optional data-flow and AST views
    dfg_edges: List[Tuple[int, int]] = field(default_factory=list)
    ast_edges: List[Tuple[int, int]] = field(default_factory=list)


def get_call_fqname(call: ast.Call) -> str:
    def attr_to_str(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return attr_to_str(node.value) + "." + node.attr
        return "<expr>"
    return attr_to_str(call.func)


class RWVisitor(ast.NodeVisitor):
    def __init__(self):
        self.reads = set()
        self.writes = set()
        self.calls = []

    def visit_Name(self, n: ast.Name):
        if isinstance(n.ctx, ast.Load):
            self.reads.add(n.id)
        elif isinstance(n.ctx, (ast.Store, ast.Del)):
            self.writes.add(n.id)

    def visit_Attribute(self, n: ast.Attribute):
        self.visit(n.value)

    def visit_Call(self, n: ast.Call):
        self.calls.append(get_call_fqname(n))
        self.generic_visit(n)


class Builder:
    def __init__(self, effects: EffectDB):
        self.effects = effects
        self._next_nid = 1

    def build_from_ast(self, file_path: str, src: str) -> List[FuncIR]:
        tree = ast.parse(src, filename=file_path)
        funcs: List[FuncIR] = []

        class FVisitor(ast.NodeVisitor):
            def __init__(self, outer: "Builder"):
                self.outer = outer

            def visit_FunctionDef(self, node: ast.FunctionDef):
                funcs.append(self.outer._build_func(node, file_path))

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                funcs.append(self.outer._build_func(node, file_path))

        FVisitor(self).visit(tree)
        funcs.insert(0, self._build_module(tree, file_path))
        return funcs

    # ------------------------------------------------------------------ #
    #  Node creation                                                      #
    # ------------------------------------------------------------------ #

    def _new_node(self, kind: str, lineno: int, n: Optional[ast.AST]) -> NodeIR:
        v = RWVisitor()
        if n is not None:
            v.visit(n)
        node = NodeIR(
            nid=self._next_nid, kind=kind, lineno=lineno,
            reads=sorted(v.reads), writes=sorted(v.writes), calls=v.calls,
        )
        self._next_nid += 1
        eff_reads, eff_writes, flags = [], [], {}
        for fq in node.calls:
            m = self.effects.match(fq)
            if m is None:
                default_getter = getattr(self.effects, "default_item", None)
                if callable(default_getter):
                    m = default_getter()
            if m:
                eff_reads += m.reads
                eff_writes += m.writes
                flags.update(m.flags)
        if eff_reads or eff_writes or flags:
            node.effects = {"reads": eff_reads, "writes": eff_writes, "flags": flags}
        return node

    # ------------------------------------------------------------------ #
    #  Phase 1: recursive CFG + control-edge construction                 #
    #                                                                     #
    #  Unlike the old flat builder that connected nodes linearly, this    #
    #  version recursively decomposes compound statements (If / For /     #
    #  While / Try) and builds a proper CFG with branch, merge and        #
    #  back-edges.  Control-dependence edges are emitted directly during  #
    #  construction: each node is marked as ctrl-dependent on its nearest #
    #  enclosing predicate.                                               #
    # ------------------------------------------------------------------ #

    def _build_stmts(
        self,
        stmts: list,
        ir: FuncIR,
        ctrl_parent: Optional[int],
        ctrl_tag: Optional[str],
    ) -> Tuple[Optional[int], Set[int]]:
        """Process a sequence of statements.

        Returns ``(entry_nid | None, exit_nids)`` where *exit_nids* is the
        set of node-ids whose CFG successors have not yet been wired up
        (i.e. the "dangling" exits that the caller must connect to the
        next statement or to the function exit).
        """
        if not stmts:
            return None, set()

        first_entry: Optional[int] = None
        prev_exits: Set[int] = set()

        for s in stmts:
            entry, exits = self._build_stmt(s, ir, ctrl_parent, ctrl_tag)
            if entry is not None:
                # Wire previous dangling exits → current entry
                for ex in prev_exits:
                    ir.cfg_edges.append((ex, entry))
                if first_entry is None:
                    first_entry = entry
            prev_exits = exits

        return first_entry, prev_exits

    def _build_stmt(
        self,
        s: ast.stmt,
        ir: FuncIR,
        ctrl_parent: Optional[int],
        ctrl_tag: Optional[str],
    ) -> Tuple[int, Set[int]]:
        """Build node(s) for a single statement.

        Returns ``(entry_nid, exit_nids)``.
        """

        # --- ast.If --------------------------------------------------- #
        if isinstance(s, ast.If):
            pred = self._new_node("If", s.lineno, s.test)
            ir.nodes.append(pred)
            if ctrl_parent is not None:
                ir.pdg_ctrl.append((ctrl_parent, pred.nid, ctrl_tag))

            # Then branch
            then_entry, then_exits = self._build_stmts(
                s.body, ir, pred.nid, "IF_TRUE")
            if then_entry is not None:
                ir.cfg_edges.append((pred.nid, then_entry))

            # Else branch
            if s.orelse:
                else_entry, else_exits = self._build_stmts(
                    s.orelse, ir, pred.nid, "IF_FALSE")
                if else_entry is not None:
                    ir.cfg_edges.append((pred.nid, else_entry))
                return pred.nid, then_exits | else_exits
            else:
                # No else: predicate itself is also an exit (false branch)
                return pred.nid, then_exits | {pred.nid}

        # --- ast.For / ast.While -------------------------------------- #
        if isinstance(s, (ast.For, ast.While)):
            if isinstance(s, ast.While):
                ctrl = self._new_node("While", s.lineno, s.test)
            else:
                # Capture iterable reads (e.g. range(n)) and target writes
                ctrl = self._new_node("For", s.lineno, s.iter)
                tw = RWVisitor()
                tw.visit(s.target)
                ctrl.writes = sorted(set(ctrl.writes) | tw.writes)

            ir.nodes.append(ctrl)
            if ctrl_parent is not None:
                ir.pdg_ctrl.append((ctrl_parent, ctrl.nid, ctrl_tag))

            body_entry, body_exits = self._build_stmts(
                s.body, ir, ctrl.nid, "LOOP_BODY")
            if body_entry is not None:
                ir.cfg_edges.append((ctrl.nid, body_entry))
            # Back-edges from body exits → loop header
            for ex in body_exits:
                ir.cfg_edges.append((ex, ctrl.nid))

            # Loop exits when condition is false (or iterator exhausted)
            return ctrl.nid, {ctrl.nid}

        # --- ast.Try -------------------------------------------------- #
        if isinstance(s, ast.Try):
            ctrl = self._new_node("Try", s.lineno, None)
            ir.nodes.append(ctrl)
            if ctrl_parent is not None:
                ir.pdg_ctrl.append((ctrl_parent, ctrl.nid, ctrl_tag))

            body_entry, body_exits = self._build_stmts(
                s.body, ir, ctrl.nid, "TRY_BODY")
            if body_entry is not None:
                ir.cfg_edges.append((ctrl.nid, body_entry))

            exits: Set[int] = set(body_exits)

            for h in s.handlers:
                h_entry, h_exits = self._build_stmts(
                    h.body, ir, ctrl.nid, "EXCEPT_BODY")
                if h_entry is not None:
                    ir.cfg_edges.append((ctrl.nid, h_entry))
                exits |= h_exits

            if s.finalbody:
                fin_entry, fin_exits = self._build_stmts(
                    s.finalbody, ir, ctrl.nid, "FINALLY")
                if fin_entry is not None:
                    for ex in exits:
                        ir.cfg_edges.append((ex, fin_entry))
                    exits = fin_exits

            return ctrl.nid, exits

        # --- default: simple statement -------------------------------- #
        node = self._new_node(
            type(s).__name__, getattr(s, "lineno", -1), s)
        ir.nodes.append(node)
        if ctrl_parent is not None:
            ir.pdg_ctrl.append((ctrl_parent, node.nid, ctrl_tag))
        return node.nid, {node.nid}

    # ------------------------------------------------------------------ #
    #  Phase 2: reaching-definition data-flow analysis                    #
    #                                                                     #
    #  Standard iterative worklist algorithm on the CFG built in Phase 1: #
    #                                                                     #
    #    in[n]  = ⋃ out[p]   for p ∈ pred(n)                             #
    #    out[n] = gen[n] ∪ (in[n] − kill[n])                             #
    #                                                                     #
    #  This correctly handles branches (if/else), loops (back-edges) and  #
    #  merge points — a significant improvement over the old linear       #
    #  last_def scan.                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_reaching_defs(ir: FuncIR) -> None:
        if not ir.nodes:
            return

        nid_set = {n.nid for n in ir.nodes}

        # Build adjacency from cfg_edges
        succ: Dict[int, Set[int]] = defaultdict(set)
        pred: Dict[int, Set[int]] = defaultdict(set)
        for src, dst in ir.cfg_edges:
            if src in nid_set and dst in nid_set:
                succ[src].add(dst)
                pred[dst].add(src)

        # Fallback: if the CFG has no edges (single-node or empty body),
        # use a linear chain so that sequential defs still reach later uses.
        if not ir.cfg_edges:
            for a, b in zip(ir.nodes, ir.nodes[1:]):
                succ[a.nid].add(b.nid)
                pred[b.nid].add(a.nid)
                ir.cfg_edges.append((a.nid, b.nid))

        # gen / kill per node
        gen: Dict[int, Dict[str, int]] = {
            n.nid: {v: n.nid for v in n.writes} for n in ir.nodes
        }
        kill_vars: Dict[int, Set[str]] = {
            n.nid: set(n.writes) for n in ir.nodes
        }

        # rd_out[nid][var] = frozenset of defining nids
        rd_out: Dict[int, Dict[str, FrozenSet[int]]] = {
            n.nid: {} for n in ir.nodes
        }

        wl: deque = deque(n.nid for n in ir.nodes)
        in_wl: Set[int] = set(wl)
        # Safety bound: convergence is guaranteed in O(N × V) iterations
        # where V is the number of distinct variables; N² is conservative.
        max_iters = len(ir.nodes) ** 2 + len(ir.nodes) + 1
        iters = 0

        while wl and iters < max_iters:
            iters += 1
            nid = wl.popleft()
            in_wl.discard(nid)

            # in[n] = ⋃ out[p]
            rd_in: Dict[str, Set[int]] = {}
            for p in pred[nid]:
                for var, defs in rd_out[p].items():
                    if var in rd_in:
                        rd_in[var] |= defs
                    else:
                        rd_in[var] = set(defs)

            # out[n] = gen[n] ∪ (in[n] − kill[n])
            kv = kill_vars[nid]
            new_out: Dict[str, FrozenSet[int]] = {}
            for var, defs in rd_in.items():
                if var not in kv:
                    new_out[var] = frozenset(defs)
            for var, def_nid in gen[nid].items():
                new_out[var] = frozenset({def_nid})

            if new_out != rd_out[nid]:
                rd_out[nid] = new_out
                for s in succ[nid]:
                    if s not in in_wl:
                        wl.append(s)
                        in_wl.add(s)

        # Emit data-flow edges: for each read at node n, find reaching defs
        for n in ir.nodes:
            rd_in_n: Dict[str, Set[int]] = {}
            for p in pred[n.nid]:
                for var, defs in rd_out[p].items():
                    if var in rd_in_n:
                        rd_in_n[var] |= defs
                    else:
                        rd_in_n[var] = set(defs)
            for var in n.reads:
                for def_nid in rd_in_n.get(var, ()):
                    ir.pdg_data.append((def_nid, n.nid, var))

    # ------------------------------------------------------------------ #
    #  Function-level orchestration                                       #
    # ------------------------------------------------------------------ #

    def _build_func(self, f: ast.AST, file_path: str) -> FuncIR:
        name = getattr(f, "name", "<module>")
        first_lineno = getattr(f, "lineno", 1)
        fid = f"{file_path}::{name}@{first_lineno}"
        ir = FuncIR(fid=fid, name=name, first_lineno=first_lineno)
        body = getattr(f, "body", [])

        # Phase 1 – nodes, CFG edges (with branches/loops), control edges
        self._build_stmts(body, ir, ctrl_parent=None, ctrl_tag=None)

        # Phase 2 – reaching-definition data-flow edges
        self._compute_reaching_defs(ir)

        # Phase 3 – effect edges
        for n in ir.nodes:
            if not n.effects:
                continue
            for loc in n.effects.get("reads", []):
                ir.pdg_eff.append((n.nid, loc, "READ"))
            for loc in n.effects.get("writes", []):
                ir.pdg_eff.append((n.nid, loc, "WRITE"))
            for k, v in n.effects.get("flags", {}).items():
                if v:
                    ir.pdg_eff.append((n.nid, f"FLAG:{k}", "FLAG"))

        # Phase 4 – effect signature
        sig = {
            "R_STACK": 0, "W_STACK": 0, "R_GLOBAL": 0, "W_GLOBAL": 0,
            "R_HEAP": 0, "W_HEAP": 0, "FILE_IO": 0, "NET_IO": 0,
            "DB_IO": 0, "ENV": 0, "RNG": 0, "TIME": 0, "EXC": 0,
        }
        flags: set = set()
        for _, res, tag in ir.pdg_eff:
            if res.startswith("FILE"):   sig["FILE_IO"] += 1
            if res.startswith("NET"):    sig["NET_IO"] += 1
            if res.startswith("DB"):     sig["DB_IO"] += 1
            if res.startswith("ENV"):    sig["ENV"] += 1
            if res.startswith("RNG"):    sig["RNG"] += 1
            if res.startswith("TIME"):   sig["TIME"] += 1
            if res.startswith("EXC") or res.startswith("FLAG:exception"):
                sig["EXC"] += 1
            if res.startswith("STACK"):
                sig["R_STACK" if tag == "READ" else "W_STACK"] += 1
            if res.startswith("GLOBAL"):
                sig["R_GLOBAL" if tag == "READ" else "W_GLOBAL"] += 1
            if res.startswith("HEAP"):
                sig["R_HEAP" if tag == "READ" else "W_HEAP"] += 1
            if res.startswith("FLAG:"):
                flags.add(res[5:])
        ir.effect_signature = {"counts": sig, "flags": sorted(flags)}

        # Phase 5 – materialize side-effect nodes for graph similarity
        try:
            from .effect_nodes import materialize_effect_nodes
            materialize_effect_nodes(ir)
        except Exception:
            pass

        return ir

    def _build_module(self, tree: ast.AST, file_path: str) -> FuncIR:
        fake = ast.Module(body=getattr(tree, "body", []), type_ignores=[])
        fake.lineno = 1
        ir = self._build_func(fake, file_path)
        ir.name = "<module>"
        ir.fid = f"{file_path}::<module>@1"
        return ir
