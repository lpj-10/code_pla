# Legacy Bytecode Path (archived)

This folder contains the **bytecode-based PDG construction pipeline** that was
previously located in `epdg/`.  It has been superseded by the AST-based builder
(`epdg/ast_pdg_builder.py`) which is more robust across Python versions and now
includes proper reaching-definition dataflow analysis.

## Files

| File | Purpose |
|------|---------|
| `bytecode_cfg.py` | CPython bytecode → basic blocks → CFG (Python 3.11+ specific) |
| `bytecode_pdg_builder.py` | `BytecodeBuilder`: CFG + dataflow + control dep → PDG |
| `dataflow_bytecode.py` | Per-block read/write/call extraction from bytecode |
| `dataflow_ssa.py` | SSA-style worklist dataflow with virtual stack simulation |
| `control_dependence.py` | Post-dominator tree → control dependence edges |
| `asm_frontend.py` | x86/ARM assembly → FuncIR (experimental) |
| `asm_normalize.py` | Assembly instruction normalization |

## Why archived

- CPython bytecode format changes across versions (3.10/3.11/3.12 all differ)
- Stack simulation in `dataflow_ssa.py` is approximate and fragile
- The AST-based builder now has equivalent dataflow quality (reaching definitions)
  with much better cross-version stability
