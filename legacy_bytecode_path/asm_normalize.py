# epdg/asm_normalize.py
from __future__ import annotations

"""
Assembly parsing + normalization utilities.

目标：
- 把“机器汇编”规整成稳定的 tokens_norm 序列，尽量屏蔽寄存器改名、立即数变化、
  小幅地址偏移等噪声，从而更适合做相似度/查重。
- 同时给 asm_frontend 提供 read/write 抽取所需的“location key”（内存位置键），
  用于 def-use/DFG/PDG。

覆盖点（这一轮补齐）：
1) stack offset 分桶 / base+disp location key
2) ARM64 / x86 两套 normalize 分支框架（含注释符、寄存器、内存寻址差异）
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

# ----------------------------
# Arch detection
# ----------------------------

def detect_arch(lines: List[str]) -> str:
    """Best-effort detect arch from assembly text. Returns 'x86' or 'arm64'."""
    # quick scan for arm64-only registers/instructions patterns
    arm_hits = 0
    x86_hits = 0
    for ln in lines[:2000]:
        s = ln.strip()
        if not s:
            continue
        # ARM immediates use '#', but x86 comments also use '#'; so look at regs/instrs too
        if re.search(r"\b(x[0-9]{1,2}|w[0-9]{1,2}|sp|fp|lr|xzr|wzr)\b", s):
            arm_hits += 1
        if re.search(r"\b(stp|ldp|ldr|str|adrp|cbz|tbz)\b", s):
            arm_hits += 2
        if re.search(r"\b(rip|rbp|rsp|rax|rcx|rdx|r[89]|r1[0-5])\b", s, flags=re.I):
            x86_hits += 1
        if re.search(r"\b(jmp|je|jne|jg|jl|callq|retq)\b", s, flags=re.I):
            x86_hits += 2
    return "arm64" if arm_hits > x86_hits else "x86"


# ----------------------------
# Comment / directive / label
# ----------------------------

# x86 intel: clang often uses '#' comments; ';' also common.
# arm64: GAS uses '@' comments; clang also emits '//' comments.
_DIRECTIVE_RE = re.compile(r"^\s*\.[A-Za-z]")
_LABEL_RE = re.compile(r"^\s*([A-Za-z_.$][\w.$@]*)\s*:\s*$")

def strip_comment(line: str, arch: str = "x86") -> str:
    s = line.rstrip("\n")
    # Always handle C++-style line comments, very common in clang asm dumps
    if "//" in s:
        s = s.split("//", 1)[0]
    if arch.startswith("arm"):
        # ARM: '@' is comment delimiter; DO NOT treat '#' as comment because '#imm'
        if "@" in s:
            s = s.split("@", 1)[0]
        if ";" in s:
            s = s.split(";", 1)[0]
        return s.rstrip()
    # x86
    # treat ';' and '#' as comment
    # (we already stripped '//' above)
    s = re.sub(r"[;#].*$", "", s)
    return s.rstrip()

def is_directive(line: str) -> bool:
    return bool(_DIRECTIVE_RE.match(line))

def parse_label(line: str) -> Optional[str]:
    m = _LABEL_RE.match(line)
    return m.group(1) if m else None


# ----------------------------
# Operand splitting helpers
# ----------------------------

def split_operands(ops: str) -> List[str]:
    """Split operands by commas, being bracket-aware."""
    out: List[str] = []
    cur: List[str] = []
    depth = 0
    for ch in ops:
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            s = "".join(cur).strip()
            if s:
                out.append(s)
            cur = []
        else:
            cur.append(ch)
    s = "".join(cur).strip()
    if s:
        out.append(s)
    return out


# ----------------------------
# Register canonicalization
# ----------------------------

_X86_FAMILY: Dict[str, str] = {}
def _add_x86_family(base: str, alts: List[str]) -> None:
    for a in alts:
        _X86_FAMILY[a] = base

# classic
_add_x86_family("rax", ["rax","eax","ax","al","ah"])
_add_x86_family("rbx", ["rbx","ebx","bx","bl","bh"])
_add_x86_family("rcx", ["rcx","ecx","cx","cl","ch"])
_add_x86_family("rdx", ["rdx","edx","dx","dl","dh"])
_add_x86_family("rsi", ["rsi","esi","si","sil"])
_add_x86_family("rdi", ["rdi","edi","di","dil"])
_add_x86_family("rbp", ["rbp","ebp","bp","bpl"])
_add_x86_family("rsp", ["rsp","esp","sp","spl"])
# r8-r15
for i in range(8, 16):
    base = f"r{i}"
    for suf in ["", "d", "w", "b"]:
        _X86_FAMILY[base + suf] = base

# xmm/ymm/zmm families: keep as-is
_FLAGS = {"eflags","rflags","nzcv"}  # nzcv for arm64

def _normalize_x86_reg(r: str) -> str:
    rr = r.lower().lstrip("%")
    # strip size keywords possibly attached
    rr = rr.strip()
    rr = rr.strip(",")
    return _X86_FAMILY.get(rr, rr)

def _normalize_arm_reg(r: str) -> str:
    rr = r.lower().strip()
    rr = rr.strip(",")
    if rr in {"fp"}:
        return "x29"
    if rr in {"lr"}:
        return "x30"
    if rr == "wzr":
        return "xzr"
    # unify wN -> xN
    m = re.match(r"^[wx]([0-9]{1,2})$", rr)
    if m:
        return "x" + m.group(1)
    return rr

def _is_arm_gpr(rr: str) -> bool:
    if rr in {"sp","xzr"}:
        return True
    m = re.match(r"^x([0-9]{1,2})$", rr)
    if m:
        n = int(m.group(1))
        return 0 <= n <= 30
    return False

def _is_arm_vec(rr: str) -> bool:
    # v0-v31, q0-q31, d0-d31, s0-s31
    return bool(re.match(r"^[vqds]([0-9]{1,2})$", rr)) and int(re.match(r"^[vqds]([0-9]{1,2})$", rr).group(1)) <= 31

def _is_x86_gpr(rr: str) -> bool:
    return rr in _X86_FAMILY.values() or rr in _X86_FAMILY.keys()

def _is_x86_vec(rr: str) -> bool:
    return bool(re.match(r"^(xmm|ymm|zmm)[0-9]{1,2}$", rr))

def _is_reg_name(rr: str, arch: str) -> bool:
    if rr in _FLAGS:
        return True
    if arch.startswith("arm"):
        rr2 = _normalize_arm_reg(rr)
        return _is_arm_gpr(rr2) or _is_arm_vec(rr2)
    rr2 = _normalize_x86_reg(rr)
    return _is_x86_gpr(rr2) or _is_x86_vec(rr2)


@dataclass
class RegState:
    """Per-function canonicalization state (stable renaming)."""
    arch: str = "x86"
    reg_map: Dict[str, str] = None
    counters: Dict[str, int] = None

    def __post_init__(self) -> None:
        self.reg_map = {}
        self.counters = {}

    def _next(self, cls: str) -> int:
        v = self.counters.get(cls, 0)
        self.counters[cls] = v + 1
        return v

    def canon_reg(self, raw: str) -> str:
        r0 = raw.lower().lstrip("%").strip()
        if self.arch.startswith("arm"):
            r = _normalize_arm_reg(r0)
            if r not in self.reg_map:
                if _is_arm_gpr(r):
                    self.reg_map[r] = f"GPR{self._next('gpr')}"
                elif _is_arm_vec(r):
                    self.reg_map[r] = f"VEC{self._next('vec')}"
                elif r in _FLAGS:
                    self.reg_map[r] = "FLAGS"
                else:
                    self.reg_map[r] = "REG"
            return self.reg_map[r]
        # x86
        r = _normalize_x86_reg(r0)
        if r not in self.reg_map:
            if _is_x86_gpr(r):
                self.reg_map[r] = f"GPR{self._next('gpr')}"
            elif _is_x86_vec(r):
                # keep class by prefix
                if r.startswith("xmm"):
                    self.reg_map[r] = f"XMM{self._next('xmm')}"
                elif r.startswith("ymm"):
                    self.reg_map[r] = f"YMM{self._next('ymm')}"
                elif r.startswith("zmm"):
                    self.reg_map[r] = f"ZMM{self._next('zmm')}"
                else:
                    self.reg_map[r] = f"VEC{self._next('vec')}"
            elif r in _FLAGS:
                self.reg_map[r] = "FLAGS"
            else:
                self.reg_map[r] = "REG"
        return self.reg_map[r]


# ----------------------------
# Immediate + memory parsing
# ----------------------------

_IMM_RE = re.compile(r"^[-+]?((0x[0-9a-fA-F]+)|([0-9]+))$")
_HEX_RE = re.compile(r"^[-+]?0x([0-9a-fA-F]+)$")
_DEC_RE = re.compile(r"^[-+]?[0-9]+$")

def parse_imm(s: str, arch: str = "x86") -> Optional[int]:
    t = s.strip().lower()
    if arch.startswith("arm") and t.startswith("#"):
        t = t[1:].strip()
    if not _IMM_RE.match(t):
        return None
    if _HEX_RE.match(t):
        return int(t, 16)
    if _DEC_RE.match(t):
        return int(t, 10)
    return None

def _bucket_abs(v: int) -> str:
    # offset buckets: 0, 8,16,32,64,128,256,512,1024+
    if v == 0:
        return "O0"
    for b in [8, 16, 32, 64, 128, 256, 512, 1024]:
        if v <= b:
            return f"O{b}"
    return "O1024P"

def imm_bucket(v: int) -> str:
    av = abs(v)
    if av == 0:
        return "IMM_0"
    if av <= 8:
        return "IMM_S8"
    if av <= 16:
        return "IMM_S16"
    if av <= 256:
        return "IMM_BYTE"
    if av <= 65536:
        return "IMM_WORD"
    return "IMM_LARGE"


_MEM_RE_X86 = re.compile(r"\[(?P<body>[^\]]+)\]")
_RIP_REL_RE = re.compile(r"\brip\b", re.I)
_STACK_BASE_X86 = re.compile(r"\b(rbp|rsp|ebp|esp)\b", re.I)

def _parse_x86_mem_body(body: str) -> Tuple[Optional[str], Optional[str], Optional[int], int, bool, bool]:
    """
    Returns (base_reg, idx_reg, scale, disp, has_symbol, rip_rel)
    Very lightweight parsing for [base + idx*scale + disp + sym]
    """
    b = body.strip()
    rip_rel = bool(_RIP_REL_RE.search(b))
    # unify '-' into '+-' for splitting
    # keep '*' for index
    b2 = b.replace("-", "+-")
    parts = [p.strip() for p in b2.split("+") if p.strip()]
    base = None
    idx = None
    scale = None
    disp = 0
    has_sym = False
    for p in parts:
        # strip relocation suffixes
        p0 = re.sub(r"@PLT|@GOTPCREL|@GOTOFF", "", p, flags=re.I).strip()
        # index*scale
        m = re.match(r"^([A-Za-z0-9_.$%]+)\s*\*\s*([1248])$", p0)
        if m:
            idx = m.group(1)
            try:
                scale = int(m.group(2))
            except Exception:
                scale = None
            continue
        # pure reg?
        if re.match(r"^[A-Za-z%][A-Za-z0-9]*$", p0) and not _IMM_RE.match(p0.lower()):
            # could be a symbol too; we'll decide later
            # treat known regs as base if empty
            rr = p0.lower().lstrip("%")
            if rr in _X86_FAMILY or rr in _X86_FAMILY.values() or rr.startswith(("xmm","ymm","zmm")):
                if base is None:
                    base = p0
                else:
                    # second reg without scale: treat as idx
                    if idx is None:
                        idx = p0
                continue
            # not a reg -> symbol
            has_sym = True
            continue
        # immediate
        iv = parse_imm(p0, "x86")
        if iv is not None:
            disp += iv
        else:
            # unknown token -> symbol-ish
            has_sym = True
    return base, idx, scale, disp, has_sym, rip_rel


def _mem_key_x86(op: str, rs: RegState) -> str:
    m = _MEM_RE_X86.search(op)
    if not m:
        return "MEM"
    body = m.group("body")
    base, idx, scale, disp, has_sym, rip_rel = _parse_x86_mem_body(body)
    # stack?
    if _STACK_BASE_X86.search(body):
        # keep raw base type for stability (RBP/RSP)
        base_raw = "RBP" if re.search(r"\brbp|ebp\b", body, re.I) else "RSP"
        sign = "P" if disp >= 0 else "N"
        buck = _bucket_abs(abs(disp))
        return f"STACK_{base_raw}_{sign}_{buck}"
    if rip_rel or has_sym:
        return "MEM_GLOBAL"
    # base+disp
    sign = "P" if disp >= 0 else "N"
    buck = _bucket_abs(abs(disp))
    if base:
        bcanon = rs.canon_reg(base)
        suffix = "_IDX" if idx else ""
        return f"MEM_{bcanon}_{sign}_{buck}{suffix}"
    return "MEM_PTR"


_MEM_RE_ARM = re.compile(r"\[(?P<body>[^\]]+)\]")

def _parse_arm_mem_body(body: str) -> Tuple[Optional[str], int, bool]:
    """
    Parse ARM64 mem operand body: 'sp, #-16' or 'x0, #32' or 'x1, x2, lsl #2'
    Returns (base_reg, disp, has_index)
    """
    b = body.strip()
    parts = [p.strip() for p in b.split(",") if p.strip()]
    base = parts[0] if parts else None
    disp = 0
    has_index = False
    if len(parts) >= 2:
        p1 = parts[1]
        # immediate offset
        iv = parse_imm(p1, "arm64")
        if iv is not None:
            disp = iv
        else:
            # index register form
            has_index = True
    return base, disp, has_index

def _mem_key_arm(op: str, rs: RegState) -> str:
    m = _MEM_RE_ARM.search(op)
    if not m:
        return "MEM"
    body = m.group("body")
    base, disp, has_idx = _parse_arm_mem_body(body)
    # stack uses sp or fp
    if base and base.strip().lower() in {"sp","fp","x29"}:
        base_raw = "SP" if base.strip().lower() == "sp" else "FP"
        sign = "P" if disp >= 0 else "N"
        buck = _bucket_abs(abs(disp))
        return f"STACK_{base_raw}_{sign}_{buck}"
    if base:
        bcanon = rs.canon_reg(base)
        sign = "P" if disp >= 0 else "N"
        buck = _bucket_abs(abs(disp))
        suffix = "_IDX" if has_idx else ""
        return f"MEM_{bcanon}_{sign}_{buck}{suffix}"
    return "MEM_PTR"


def mem_key(op: str, rs: RegState, arch: str = "x86") -> str:
    if arch.startswith("arm"):
        return _mem_key_arm(op, rs)
    return _mem_key_x86(op, rs)


def canon_operand(op: str, rs: RegState, arch: str = "x86") -> str:
    o = op.strip()
    # strip common x86 size annotations: 'qword ptr'
    o2 = re.sub(r"\b(byte|word|dword|qword)\s+ptr\b", "", o, flags=re.I).strip()
    # strip leading '*' deref in x86
    if o2.startswith("*"):
        o2 = o2.lstrip("*").strip()

    # ARM pre/post-indexing: [sp, #-16]!
    o2 = o2.rstrip("!").strip()

    # register?
    raw = o2.lstrip("%")
    # strip braces (rare)
    raw = raw.strip("{}")
    if _is_reg_name(raw.lower(), arch):
        return rs.canon_reg(raw)

    # immediate
    iv = parse_imm(o2, arch)
    if iv is not None:
        return imm_bucket(iv)

    # memory
    if "[" in o2 and "]" in o2:
        return mem_key(o2, rs, arch)

    # symbol / label / other
    sym = re.sub(r"@PLT|@GOTPCREL|@GOTOFF", "", o2, flags=re.I).strip()
    # ARM: strip :lo12: / :got: etc
    sym = re.sub(r":[A-Za-z0-9_]+:", ":", sym)
    # strip # in immediate-like symbols? keep conservative
    if sym:
        return "SYM"
    return "OP"


def normalize_instruction(op: str, operands: List[str], rs: RegState, arch: str = "x86") -> str:
    """Return a single canonical token for this instruction."""
    op_l = op.lower()
    cops = [canon_operand(o, rs, arch) for o in operands]
    if cops:
        return f"{op_l.upper()}(" + ",".join(cops) + ")"
    return op_l.upper()


# ----------------------------
# Read/Write extraction (DFG/PDG)
# ----------------------------

_JCC_PREFIX = "j"  # for x86
_ARM_B_PREFIX = "b"  # for arm64

def _rw_mov(dst: str, src: str) -> Tuple[Set[str], Set[str]]:
    reads: Set[str] = set()
    writes: Set[str] = set()
    # dst is written, src is read
    if dst:
        writes.add(dst)
    if src:
        reads.add(src)
    # if dst is memory, treat as write to that location; if src is memory, treat as read
    return reads, writes

def _rw_bin(dst: str, src: str) -> Tuple[Set[str], Set[str]]:
    reads: Set[str] = set()
    writes: Set[str] = set()
    if dst:
        reads.add(dst)
        writes.add(dst)
    if src:
        reads.add(src)
    return reads, writes

def _rw_cmp(a: str, b: str) -> Tuple[Set[str], Set[str]]:
    reads = {a, b} if a and b else set()
    writes = {"FLAGS"}
    return reads, writes

def extract_reads_writes(op: str, operands: List[str], rs: RegState, arch: str = "x86") -> Tuple[Set[str], Set[str], List[str]]:
    """Extract canonical read/write variable names for a single instruction.

    Returns (reads, writes, calls)
    - reads/writes: canonical vars (GPR0, MEM_GPR1_P_O16, STACK_RBP_N_O32, FLAGS, ...)
    - calls: extracted call target names (best effort)
    """
    op_l = op.lower()
    calls: List[str] = []
    cops = [canon_operand(o, rs, arch) for o in operands]

    reads: Set[str] = set()
    writes: Set[str] = set()

    if arch.startswith("arm"):
        # ARM64 minimal families
        if op_l in {"mov", "movz", "movn", "movk"} and len(cops) >= 2:
            r, w = _rw_mov(cops[0], cops[1])
            reads |= r; writes |= w
        elif op_l in {"add","sub","and","orr","eor","mul","madd","msub"} and len(cops) >= 3:
            # add dst, src1, src2
            reads.add(cops[1]); reads.add(cops[2]); writes.add(cops[0])
        elif op_l in {"cmp","cmn"} and len(cops) >= 2:
            r, w = _rw_cmp(cops[0], cops[1])
            reads |= r; writes |= w
        elif op_l in {"ldr","ldrb","ldrh","ldrsw"} and len(cops) >= 2:
            # ldr dst, [mem]
            reads.add(cops[1]); writes.add(cops[0])
        elif op_l in {"str","strb","strh"} and len(cops) >= 2:
            reads.add(cops[0]); writes.add(cops[1])
        elif op_l in {"ldp"} and len(cops) >= 3:
            # ldp dst1, dst2, [mem]
            reads.add(cops[2]); writes.add(cops[0]); writes.add(cops[1])
        elif op_l in {"stp"} and len(cops) >= 3:
            reads.add(cops[0]); reads.add(cops[1]); writes.add(cops[2])
        elif op_l in {"bl","blr"} and len(operands) >= 1:
            # call
            tgt = operands[0].strip()
            tgt = tgt.split()[0]
            tgt = tgt.replace("@PLT","")
            if tgt:
                calls.append(tgt)
            # conservative: calls touch stack and flags
            reads.add("STACK_SP_P_O0"); writes.add("STACK_SP_P_O0"); writes.add("FLAGS")
        elif op_l.startswith("b") or op_l in {"cbz","cbnz","tbz","tbnz"}:
            # conditional branch may consult FLAGS; cbz/tbz consult a register too
            if op_l.startswith("b.") and op_l != "b":
                reads.add("FLAGS")
            if op_l in {"cbz","cbnz"} and len(cops) >= 1:
                reads.add(cops[0])
            if op_l in {"tbz","tbnz"} and len(cops) >= 1:
                reads.add(cops[0])
        elif op_l == "ret":
            reads.add("STACK_SP_P_O0")
        return reads, writes, calls

    # x86 families
    if op_l in {"mov","movzx","movsx","lea"} and len(cops) >= 2:
        r, w = _rw_mov(cops[0], cops[1]); reads |= r; writes |= w
    elif op_l in {"add","sub","xor","or","and","imul"} and len(cops) >= 2:
        r, w = _rw_bin(cops[0], cops[1]); reads |= r; writes |= w
    elif op_l in {"inc","dec","neg","not"} and len(cops) >= 1:
        r, w = _rw_bin(cops[0], ""); reads |= r; writes |= w
    elif op_l in {"cmp","test"} and len(cops) >= 2:
        r, w = _rw_cmp(cops[0], cops[1]); reads |= r; writes |= w
    elif op_l == "push" and len(cops) >= 1:
        reads.add(cops[0]); writes.add("STACK_RSP_P_O0")
    elif op_l == "pop" and len(cops) >= 1:
        reads.add("STACK_RSP_P_O0"); writes.add(cops[0])
    elif op_l in {"call","callq"} and len(operands) >= 1:
        target = operands[0].strip()
        target = re.sub(r"\b(qword|dword|word|byte)\b\s*ptr\s*", "", target, flags=re.I).strip()
        target = target.replace("*", "").strip()
        target = re.sub(r"@PLT.*$", "", target)
        target = re.sub(r"\+.*$", "", target).strip()
        if target:
            calls.append(target)
        reads.add("STACK_RSP_P_O0"); writes.add("STACK_RSP_P_O0"); writes.add("FLAGS")
    elif op_l.startswith(_JCC_PREFIX):
        if op_l != "jmp":
            reads.add("FLAGS")
    elif op_l in {"ret","retq"}:
        reads.add("STACK_RSP_P_O0")

    return reads, writes, calls
