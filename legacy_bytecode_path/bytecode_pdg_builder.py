# epdg/bytecode_pdg_builder.py (enhanced)
import types
from typing import List, Dict, Tuple, Any
from epdg.effects_loader import EffectDB
from epdg.ast_pdg_builder import FuncIR, NodeIR  # reuse IR types
from .bytecode_cfg import build_cfg
from .dataflow_bytecode import block_rw_calls
from .dataflow_ssa import forward_dataflow
from .control_dependence import control_dependence_edges

class BytecodeBuilder:
    def __init__(self, effects: EffectDB, unknown_impure: bool=True):
        self.effects = effects
        self.unknown_impure = unknown_impure

    def _effectize_calls(self, calls: List[str]):
        r, w, flags = [], [], {}
        for fq in calls:
            m = self.effects.match(fq)
            if m:
                r += m.reads; w += m.writes; flags.update(m.flags)
            elif self.unknown_impure:
                # conservative upper bound: may write heap and raise
                w.append("HEAP[?]"); flags.setdefault("exception", True)
        return r, w, flags

    def build_from_code(self, file_path: str, root_code: types.CodeType) -> List[FuncIR]:
        funcs: List[FuncIR] = []
        def walk_code_objects(code, qname="<module>"):
            yield code, qname
            for c in code.co_consts:
                if isinstance(c, types.CodeType):
                    yield from walk_code_objects(c, f"{qname}.{c.co_name}")

        for co, qn in walk_code_objects(root_code):
            name = "<module>" if qn=="<module>" else co.co_name
            fid = f"{file_path}::{name}@{co.co_firstlineno}"
            ir = FuncIR(fid=fid, name=name, first_lineno=co.co_firstlineno)

            cfg = build_cfg(co, add_exception_sink=True)

            # Node per basic block
            for b in cfg.blocks:
                reads, writes, calls = block_rw_calls(b)
                er, ew, eflags = self._effectize_calls(calls)
                node = NodeIR(nid=b.bid, kind="BasicBlock", lineno=b.lineno,
                              reads=reads, writes=writes, calls=calls,
                              effects=({"reads":er,"writes":ew,"flags":eflags} if (er or ew or eflags) else {}))
                ir.nodes.append(node)

            # CFG edges
            for a, succs in cfg.succ.items():
                for t in succs:
                    ir.cfg_edges.append((a, t))

            # Dataflow (SSA-ish) def-use
            _, _, defuse = forward_dataflow(cfg)
            # translate (def_bid, use_bid, key) to PDG data edges
            for db, ub, key in defuse:
                ir.pdg_data.append((db, ub, key))

            # Control dependence
            ir.pdg_ctrl = control_dependence_edges(cfg)

            # Effect edges from node.effects
            for n in ir.nodes:
                if not n.effects: continue
                for loc in n.effects.get("reads", []):
                    ir.pdg_eff.append((n.nid, loc, "READ"))
                for loc in n.effects.get("writes", []):
                    ir.pdg_eff.append((n.nid, loc, "WRITE"))
                for k,v in n.effects.get("flags",{}).items():
                    if v: ir.pdg_eff.append((n.nid, f"FLAG:{k}", "FLAG"))

            # effect signature (counts only)
            sig = {"R_STACK":0,"W_STACK":0,"R_GLOBAL":0,"W_GLOBAL":0,"R_HEAP":0,"W_HEAP":0,
                   "FILE_IO":0,"NET_IO":0,"DB_IO":0,"ENV":0,"RNG":0,"TIME":0,"EXC":0}
            for _, res, tag in ir.pdg_eff:
                if res.startswith("FILE"): sig["FILE_IO"] += 1
                if res.startswith("NET"): sig["NET_IO"] += 1
                if res.startswith("DB"): sig["DB_IO"] += 1
                if res.startswith("ENV"): sig["ENV"] += 1
                if res.startswith("RNG"): sig["RNG"] += 1
                if res.startswith("TIME"): sig["TIME"] += 1
                if res.startswith("FLAG:exception"): sig["EXC"] += 1
                if res.startswith("HEAP") and tag=="WRITE": sig["W_HEAP"] += 1
            ir.effect_signature = {"counts": sig, "flags": []}
            funcs.append(ir)
        return funcs
