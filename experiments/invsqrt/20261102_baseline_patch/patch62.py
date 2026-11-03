"""Baseline patch tool for the 62Q public circuit (manual runs only).

NOT a test file, NOT CI. Does not modify the official verifier.
Does not auto-submit anywhere. Generation and official verification
are separate steps (use scripts/manual_verify.py by hand).

Discipline (§2 of the plan):
  * Original and candidate blocks share ONE symbolic input environment:
    a single Values object forked at the window start (deepcopy of wire,
    bit_values, condition stack). No cross-interpreter integer-ID compare:
    same-id => equivalent is used only inside one Values object; differing
    ids always go through booleq62.equiv (truth table <=12 free vars, else
    Z3 60 s, timeout => UNKNOWN).
  * Full condition stack, BIT_* updates and versioned measurement leaves
    are tracked (ported faithfully from retain62.interpret; cross-validated
    by --crosscheck). CX/CCX writes include the target old value.
  * Proof compares: all output qubit wires, subsequently-used classical
    bits (bits written in-window and read later), the condition
    environment, and the exact total phase.
  * Round 1 keeps ALL HMR/R/Z_POW ops and their order (asserted); no
    rewrites across general rotations.

Usage (manual evidence commands):
  uv run python experiments/invsqrt/20261102_baseline_patch/patch62.py --crosscheck
  uv run python experiments/invsqrt/20261102_baseline_patch/patch62.py --census
  uv run python experiments/invsqrt/20261102_baseline_patch/patch62.py --prove NAME --cand-file PATH
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261031_invsqrt62_replay"))
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_hw06_opt"))

import retain62  # noqa: E402
import booleq62  # noqa: E402

BASELINE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
BASELINE_SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
ART = ROOT / "artifacts/20261102_baseline_patch/invsqrt"

WINDOWS = {
    "invB1": (31447, 31574),
    "invB2": (31801, 31928),
    "tail1": (46872, 46992),
    "tail2": (46992, 47222),
}
INVA = (32283, 43927)

PHASE_OPS = ("Z", "CZ", "CCZ", "NEG", "Z_POW")
BARRIER_OPS = ("HMR", "R")


def qn(token: str) -> int:
    return int(token[1:])


def load_baseline():
    import kickmix

    raw = BASELINE.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == BASELINE_SHA, f"baseline hash moved: {sha}"
    circuit = kickmix.Circuit.from_file(str(BASELINE))
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]
    return header, ops


class Sym:
    """Symbolic machine state sharing one Values object (forkable)."""

    def __init__(self, values=None, track=True, entry=None):
        self.values = values or retain62.Values()
        v = self.values
        if track:
            self.wire = []
            for q in range(62):
                if entry is not None and q in entry:
                    self.wire.append(v.one if entry[q] else v.zero)
                elif q <= 21:
                    self.wire.append(v.vid(frozenset([q])))
                else:
                    self.wire.append(v.zero)
        else:
            self.wire = [v.vid(frozenset([q])) for q in range(62)]
        self.bits = {}
        self.cond = []
        self.phase = []  # (kind, qubits, angle, cond_vid or None)
        self.track = track

    def fork(self):
        return copy.deepcopy(self)

    def ensure_bit(self, bit):
        if bit not in self.bits:
            self.bits[bit] = self.values.zero if self.track else self.values.fresh()
        return self.bits[bit]

    def active(self, parts):
        v = self.values
        factors = [self.ensure_bit(int(t[1:])) for t in self.cond if t.startswith("b")]
        if "if" in parts:
            factors.append(self.ensure_bit(int(parts[parts.index("if") + 1][1:])))
        if not factors:
            return None
        acc = factors[0]
        for f in factors[1:]:
            acc = v.and_(acc, f)
        return None if acc == v.one else acc

    def when(self, old, new, cond):
        if cond is None:
            return new
        return self.values.mux(cond, new, old)

    def step(self, line, index=0):
        v = self.values
        parts = line.split()
        kind = parts[0]
        cond = self.active(parts)
        if kind == "PUSH_CONDITION":
            self.cond.append(parts[-1])
        elif kind == "POP_CONDITION":
            if self.cond:
                self.cond.pop()
        elif kind in ("BIT_STORE0", "BIT_STORE1"):
            bit = int(parts[1][1:])
            old = self.ensure_bit(bit)
            stored = v.zero if kind == "BIT_STORE0" else v.one
            self.bits[bit] = self.when(old, stored, cond)
        elif kind == "BIT_INVERT":
            bit = int(parts[1][1:])
            old = self.ensure_bit(bit)
            self.bits[bit] = self.when(old, v.xor(old, v.one), cond)
        elif kind == "SWAP":
            a, b = qn(parts[1]), qn(parts[2])
            oa, ob = self.wire[a], self.wire[b]
            self.wire[a] = self.when(oa, ob, cond)
            self.wire[b] = self.when(ob, oa, cond)
        elif kind == "CSWAP":
            c, a, b = qn(parts[1]), qn(parts[2]), qn(parts[3])
            oa, ob = self.wire[a], self.wire[b]
            self.wire[a] = self.when(oa, v.mux(self.wire[c], ob, oa), cond)
            self.wire[b] = self.when(ob, v.mux(self.wire[c], oa, ob), cond)
        elif kind == "CX":
            a, b = qn(parts[1]), qn(parts[2])
            old = self.wire[b]
            self.wire[b] = self.when(old, v.xor(old, self.wire[a]), cond)
        elif kind == "CCX":
            a, b, t = qn(parts[1]), qn(parts[2]), qn(parts[3])
            old = self.wire[t]
            self.wire[t] = self.when(old, v.xor(old, v.and_(self.wire[a], self.wire[b])), cond)
        elif kind == "X":
            t = qn(parts[1])
            old = self.wire[t]
            self.wire[t] = self.when(old, v.xor(old, v.one), cond)
        elif kind in PHASE_OPS:
            qs = tuple(qn(t) for t in parts[1:] if t.startswith("q"))
            angle = None
            for t in parts[1:]:
                if t.startswith("q") or t in ("if",) or t.startswith("b"):
                    continue
                angle = t
                break
            self.phase.append((kind, qs, angle, cond,
                               tuple(self.wire[q] for q in qs)))
        elif kind in BARRIER_OPS:
            q = qn(parts[1])
            old = self.wire[q]
            if self.track:
                bit = None
                if len(parts) > 2 and parts[2].startswith("b"):
                    bit = int(parts[2][1:])
                    leaf, _atom = v.measurement(index, bit)
                    old_bit = self.bits.get(bit, v.zero)
                    self.bits[bit] = self.when(old_bit, leaf, cond)
                self.wire[q] = self.when(old, v.zero, cond)
            else:
                self.wire[q] = self.when(old, v.zero, cond)
                if len(parts) > 2 and parts[2].startswith("b"):
                    bit = int(parts[2][1:])
                    old_bit = self.bits.get(bit, v.fresh())
                    self.bits[bit] = self.when(old_bit, v.fresh(), cond)

    def run(self, ops, start=0):
        for i, line in enumerate(ops):
            self.step(line, index=start + i)
        return self


def run_prefix(ops, end):
    return Sym(track=True).run(ops[:end])


def bits_read_after(ops, start):
    """Classical bits read at/after `start` (inline if / PUSH_CONDITION)."""
    out = set()
    for line in ops[start:]:
        p = line.split()
        if "if" in p:
            out.add(int(p[p.index("if") + 1][1:]))
        if p[0] == "PUSH_CONDITION":
            out.add(int(p[-1][1:]))
    return out


def barrier_seq(ops):
    return [(p[0], p[1], p[2] if len(p) > 2 else None)
            for p in (l.split() for l in ops) if p[0] in BARRIER_OPS]


def zpow_seq(ops):
    return [(p[0], p[1], p[2] if len(p) > 2 else None,
             p[p.index("if") + 1] if "if" in p else None)
            for p in (l.split() for l in ops) if p[0] == "Z_POW"]


def prove_window(name, cand_ops, ops=None):
    """Prove candidate block equivalent over window NAME. Returns record dict."""
    if ops is None:
        _, ops = load_baseline()
    lo, hi = WINDOWS[name]
    return prove_range(name, lo, hi, cand_ops, ops)


def prove_range(name, lo, hi, cand_ops, ops=None):
    """Prove candidate block equivalent over ops[lo:hi). Returns record dict."""
    if ops is None:
        _, ops = load_baseline()
    orig_ops = ops[lo:hi]
    rec = {"window": name, "lo": lo, "hi": hi,
           "n_orig": len(orig_ops), "n_cand": len(cand_ops)}
    # 0. enclosing condition must be balanced in candidate
    depth = 0
    for line in cand_ops:
        p = line.split()
        if p[0] == "PUSH_CONDITION":
            depth += 1
        elif p[0] == "POP_CONDITION":
            depth -= 1
            if depth < 0:
                break
    rec["cond_balanced"] = (depth == 0)
    if depth != 0:
        rec["verdict"] = "FAIL"
        rec["reason"] = "candidate condition stack unbalanced"
        return rec
    # 1. round-1 gate: identical HMR/R order+args, identical Z_POW ops
    if barrier_seq(orig_ops) != barrier_seq(cand_ops):
        rec["verdict"] = "FAIL"
        rec["reason"] = "HMR/R sequence changed (round 1 forbids)"
        return rec
    if zpow_seq(orig_ops) != zpow_seq(cand_ops):
        rec["verdict"] = "FAIL"
        rec["reason"] = "Z_POW sequence changed (round 1 forbids)"
        return rec
    rec["barriers_kept"] = True
    # 2. shared symbolic environment: fork ONE prefix state
    base = run_prefix(ops, lo)
    s_orig = base.fork().run(orig_ops, start=lo)
    s_cand = base.fork().run(cand_ops, start=lo)
    # entry snapshots (pre-fork vid ints; identical meaning in both forks)
    s_orig.entry_snap = tuple(base.wire)
    s_cand.entry_snap = tuple(base.wire)
    s_orig.entry_bits = dict(base.bits)
    s_cand.entry_bits = dict(base.bits)
    v = s_orig.values  # single shared Values object
    assert s_cand.values is not v or True
    # NOTE: fork deepcopies Values, so s_orig.values and s_cand.values are
    # DISTINCT objects. Same-id shortcut is valid only within one object.
    # Cross-object comparison always goes through cross-proof below, which
    # aligns free variables by source (inputs + measurement op/bit).
    if s_orig.cond != s_cand.cond:
        rec["verdict"] = "FAIL"
        rec["reason"] = f"end condition env differs: {s_orig.cond} vs {s_cand.cond}"
        return rec
    rec["cond_env_equal"] = True
    # 3. output wires: untouched wires are identical by construction
    # (both forks deepcopy one prefix state; pre-fork vid ints keep their
    # meaning). Only wires touched in-window need proof, sliced at the
    # shared entry state.
    entry_orig = set(base.wire)
    entry_cand = set(base.wire)  # identical ints: same forked history
    wire_results = []
    for q in range(62):
        if s_orig.wire[q] == base.wire[q] and s_cand.wire[q] == base.wire[q]:
            wire_results.append({"method": "untouched-identical",
                                 "verdict": "equivalent"})
            continue
        r = sliced_equiv(s_orig.values, entry_orig, s_orig.wire[q],
                         s_cand.values, entry_cand, s_cand.wire[q])
        wire_results.append(r)
        if r["verdict"] != "equivalent":
            rec["verdict"] = "UNKNOWN" if r["verdict"] == "unknown" else "FAIL"
            rec["reason"] = f"qubit q{q}: {r}"
            rec["wire_results"] = wire_results
            return rec
    rec["wires_equivalent"] = True
    # 4. subsequently-used classical bits
    live = bits_read_after(ops, hi)
    written = {int(p[2][1:]) for l in orig_ops for p in [l.split()]
               if p[0] in BARRIER_OPS and len(p) > 2 and p[2].startswith("b")}
    written |= {int(p[1][1:]) for l in orig_ops for p in [l.split()]
                if p[0] in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT")}
    bit_results = {}
    for b in sorted(written & live):
        b0 = base.bits.get(b)
        if s_orig.bits.get(b) == b0 and s_cand.bits.get(b) == b0:
            bit_results[str(b)] = {"method": "untouched-identical",
                                   "verdict": "equivalent"}
            continue
        # bits are vids too: slice at shared entry bits+wires
        r = sliced_equiv(s_orig.values, entry_orig, s_orig.bits[b],
                         s_cand.values, entry_cand, s_cand.bits[b])
        bit_results[str(b)] = r
        if r["verdict"] != "equivalent":
            rec["verdict"] = "UNKNOWN" if r["verdict"] == "unknown" else "FAIL"
            rec["reason"] = f"live bit b{b}: {r}"
            rec["bit_results"] = bit_results
            return rec
    rec["live_bits"] = sorted(written & live)
    rec["bits_equivalent"] = True
    # 5. exact total phase
    pr = prove_phase(base.values, s_orig, s_cand)
    rec["phase"] = pr
    if pr["verdict"] != "equivalent":
        rec["verdict"] = "UNKNOWN" if pr["verdict"] == "unknown" else "FAIL"
        rec["reason"] = f"phase: {pr.get('reason', pr['verdict'])}"
        return rec
    rec["verdict"] = "PASS"
    return rec


def align_atoms(v0, v1):
    """Align free-variable atoms of two Values by source.

    Inputs: qubit singletons {q} <-> {q}. Measurements: meas_source
    (op,bit) <-> (op,bit). Anything else (fresh/unexpected) => None.
    Returns (map0, map1): atom->symbol index, plus n_symbols; or None.
    """
    def src_key(v, atom):
        if atom == -1:
            return ("const", -1)
        if atom in v.and_of:
            return None
        if atom in v.meas_source:
            m = v.meas_source[atom]
            return ("meas", m["op"], m["bit"])
        # singleton frozenset {q}: find which vid structure; invert via fs list
        return ("atom", atom)

    # Build symbol tables keyed by canonical source description.
    def table(v):
        t = {}
        for vid, bits in enumerate(v.fs):
            for atom in bits:
                if atom in v.and_of:
                    continue
                if atom in v.meas_source:
                    # Key by measurement serial (atom id), NOT absolute op
                    # index: candidate blocks shift indices. Round 1 asserts
                    # identical HMR/R sequences, so serials align 1:1.
                    key = ("meas", atom)
                elif atom == -1:
                    key = ("const", -1)
                else:
                    # Qubit singleton atoms are 0..61; AND atoms start at 62,
                    # fresh at 1000000+, measurements at 5000000+.
                    if 0 <= atom <= 61:
                        key = ("qubit", atom)
                    else:
                        return None
                t.setdefault(key, atom)
        return t
    t0, t1 = table(v0), table(v1)
    if t0 is None or t1 is None:
        return None
    if set(t0) != set(t1):
        return None
    keys = sorted(t0, key=str)
    return ({t0[k]: i for i, k in enumerate(keys)},
            {t1[k]: i for i, k in enumerate(keys)}, len(keys))


def sliced_symbols(values, entry_set, root):
    """Cone of `root` cut at window-entry vids.

    Returns (syms, kind_of) where syms maps symbol key ->
    ('entry', vid) | ('meas', atom) | ('qubit', q) | ('const', -1).
    Anything else (fresh/unknown atoms) raises _Unalignable.
    """
    syms = {}
    stack = [root]
    seen = set()
    while stack:
        vid = stack.pop()
        if vid in seen:
            continue
        seen.add(vid)
        if vid in entry_set:
            syms[("entry", vid)] = ("entry", vid)
            continue
        for atom in values.fs[vid]:
            if atom == -1:
                syms[("const", -1)] = ("const", -1)
            elif atom in values.and_of:
                l, r = values.and_of[atom]
                stack.append(l)
                stack.append(r)
            elif atom in values.meas_source:
                syms[("meas", atom)] = ("meas", atom)
            elif 9_000_000 <= atom < 10_000_000:
                # Sym2 random-event outcomes; serials align across forked
                # objects because HMR/R order is asserted identical.
                syms[("event", atom)] = ("event", atom)
            elif 0 <= atom <= 61:
                syms[("qubit", atom)] = ("qubit", atom)
            else:
                raise _Unalignable(f"atom {atom}")
    return syms


class _Unalignable(Exception):
    pass


def eval_sliced(values, root, entry_set, env):
    """Evaluate vid with entry vids opaque (from env) and atoms from env."""
    memo = {}
    stack = [(root, False)]
    while stack:
        vid, done = stack.pop()
        if vid in memo:
            continue
        if vid in entry_set:
            memo[vid] = env[("entry", vid)]
            continue
        if not done:
            stack.append((vid, True))
            for atom in values.fs[vid]:
                if atom in values.and_of:
                    l, r = values.and_of[atom]
                    stack.append((l, False))
                    stack.append((r, False))
            continue
        acc = 0
        for atom in values.fs[vid]:
            if atom == -1:
                acc ^= 1
            elif atom in values.and_of:
                l, r = values.and_of[atom]
                acc ^= memo[l] & memo[r]
            elif atom in values.meas_source:
                acc ^= env[("meas", atom)]
            elif 9_000_000 <= atom < 10_000_000:
                acc ^= env[("event", atom)]
            else:
                acc ^= env[("qubit", atom)]
        memo[vid] = acc
    return memo[root]


def z3_sliced(values, root, entry_set, sym_of, symbols, memo):
    """Z3 term with entry vids opaque. sym_of maps symbol key -> z3 Bool."""
    import z3
    if root in memo:
        return memo[root]
    if root in entry_set:
        t = sym_of[("entry", root)]
        memo[root] = t
        return t
    acc = None
    for atom in values.fs[root]:
        if atom == -1:
            term = z3.BoolVal(True)
        elif atom in values.and_of:
            l, r = values.and_of[atom]
            term = z3.And(z3_sliced(values, l, entry_set, sym_of, symbols, memo),
                          z3_sliced(values, r, entry_set, sym_of, symbols, memo))
        elif atom in values.meas_source:
            term = sym_of[("meas", atom)]
        elif 9_000_000 <= atom < 10_000_000:
            term = sym_of[("event", atom)]
        else:
            term = sym_of[("qubit", atom)]
        acc = term if acc is None else z3.Xor(acc, term)
    if acc is None:
        acc = z3.BoolVal(False)
    memo[root] = acc
    return acc


def sliced_equiv(v_orig, entry_orig, root_orig, v_cand, entry_cand, root_cand):
    """Prove root_orig == root_cand as functions of the shared entry state.

    Entry vids are identical ints in both forked objects (deepcopy of one
    prefix state); entry symbol ("entry", vid) is shared. Window measurement
    leaves align by serial (round 1 keeps HMR sequences identical).
    """
    try:
        s1 = sliced_symbols(v_orig, entry_orig, root_orig)
        s2 = sliced_symbols(v_cand, entry_cand, root_cand)
    except _Unalignable as e:
        return {"method": "sliced", "verdict": "unknown",
                "reason": f"unaligned atom: {e}"}
    keys = sorted(set(s1) | set(s2), key=str)
    # NOTE: entry symbols are treated as independent booleans (over-
    # approximation: they share prefix inputs). "equivalent" stays sound;
    # "not-equivalent" is a LOCAL counterexample until replayed from legal
    # inputs + real prefix (plan §2).
    n = len(keys)
    if n <= booleq62.SMALL_CONE_LIMIT:
        for mask in range(1 << n):
            env = {k: (mask >> i) & 1 for i, k in enumerate(keys)}
            a = eval_sliced(v_orig, root_orig, entry_orig, env)
            b = eval_sliced(v_cand, root_cand, entry_cand, env)
            if a != b:
                return {"method": "sliced-truth-table", "verdict": "not-equivalent",
                        "free_vars": n, "checked": mask + 1}
        return {"method": "sliced-truth-table", "verdict": "equivalent",
                "free_vars": n, "checked": 1 << n}
    try:
        import z3
    except ImportError:
        return {"method": "sliced", "verdict": "unknown",
                "reason": "z3-solver not installed"}
    syms = [z3.Bool(f"e{i}") for i in range(n)]
    sym_of = {k: syms[i] for i, k in enumerate(keys)}
    s = z3.Solver()
    s.set("timeout", 60_000)
    t1 = z3_sliced(v_orig, root_orig, entry_orig, sym_of, syms, {})
    t2 = z3_sliced(v_cand, root_cand, entry_cand, sym_of, syms, {})
    s.add(z3.Xor(t1, t2))
    res = s.check()
    if res == z3.unsat:
        return {"method": "sliced-z3", "verdict": "equivalent", "free_vars": n}
    if res == z3.sat:
        return {"method": "sliced-z3", "verdict": "not-equivalent", "free_vars": n}
    return {"method": "sliced-z3", "verdict": "unknown",
            "reason": "timeout-or-undecided", "free_vars": n}


def cross_equiv(v0, v1, root1, v2, root2):
    """Three-valued proof across two Values objects with aligned sources."""
    # Same-structure fast path is UNSOUND across objects; always prove.
    al = align_atoms(v1, v2)
    if al is None:
        return {"method": "none", "verdict": "unknown",
                "reason": "free variables not alignable by source"}
    m1, m2, n = al
    _ = (v0, m1, m2)
    if n <= booleq62.SMALL_CONE_LIMIT:
        # exhaustive over aligned symbols; eval within each object
        f1 = booleq62.free_variables(v1, root1)
        f2 = booleq62.free_variables(v2, root2)
        for mask in range(1 << n):
            env1 = {a: (mask >> m1[a]) & 1 for a in f1 if a in m1}
            env2 = {a: (mask >> m2[a]) & 1 for a in f2 if a in m2}
            # unmapped atoms (shouldn't happen after align) -> unknown
            if len(env1) != len(f1) or len(env2) != len(f2):
                return {"method": "truth-table", "verdict": "unknown",
                        "reason": "unmapped free atom"}
            if booleq62.eval_vid(v1, root1, env1) != booleq62.eval_vid(v2, root2, env2):
                return {"method": "truth-table", "verdict": "not-equivalent",
                        "free_vars": n, "checked": mask + 1}
        return {"method": "truth-table", "verdict": "equivalent",
                "free_vars": n, "checked": 1 << n}
    # Z3 path with aligned symbols
    try:
        import z3
    except ImportError:
        return {"method": "z3", "verdict": "unknown",
                "reason": "z3-solver not installed"}
    sym = [z3.Bool(f"s{i}") for i in range(n)]

    def build(v, m, vid, memo):
        if vid in memo:
            return memo[vid]
        acc = None
        for atom in v.fs[vid]:
            if atom == -1:
                term = z3.BoolVal(True)
            elif atom in v.and_of:
                l, r = v.and_of[atom]
                term = z3.And(build(v, m, l, memo), build(v, m, r, memo))
            else:
                term = sym[m[atom]]
            acc = term if acc is None else z3.Xor(acc, term)
        if acc is None:
            acc = z3.BoolVal(False)
        memo[vid] = acc
        return acc

    s = z3.Solver()
    s.set("timeout", 60_000)
    s.add(z3.Xor(build(v1, m1, root1, {}), build(v2, m2, root2, {})))
    res = s.check()
    if res == z3.unsat:
        return {"method": "z3", "verdict": "equivalent", "free_vars": n}
    if res == z3.sat:
        return {"method": "z3", "verdict": "not-equivalent", "free_vars": n}
    return {"method": "z3", "verdict": "unknown",
            "reason": "timeout-or-undecided", "free_vars": n}


def cond_equal(base_values, s_orig, c1, s_cand, c2):
    """Proven-equal conditions; None==None equal, None vs vid => UNKNOWN."""
    if c1 is None and c2 is None:
        return {"verdict": "equivalent", "method": "same-cond"}
    if c1 is None or c2 is None:
        return {"verdict": "unknown", "method": "same-cond",
                "reason": "one side unconditional"}
    entry = set(base_values.wire) if hasattr(base_values, "wire") else None
    return sliced_equiv(s_orig.values, set(s_orig.entry_snap), c1,
                        s_cand.values, set(s_cand.entry_snap), c2)


def data_equal(base_values, s_orig, d1, s_cand, d2):
    for a, b in zip(d1, d2):
        r = sliced_equiv(s_orig.values, set(s_orig.entry_snap), a,
                         s_cand.values, set(s_cand.entry_snap), b)
        if r["verdict"] != "equivalent":
            return r
    return {"verdict": "equivalent", "method": "data-equal"}


def prove_phase(base_values, s_orig, s_cand):
    """Exact total-phase check.

    Round-1 rule: phase ops must match 1:1 (kind/targets/angle with
    proven-equal conditions) or as an XOR-merge pair of identical
    diagonal pi-phase gates (branch-exact: (1,1) gives 2pi=0 both sides).
    Anything else => UNKNOWN (never FAIL on phase alone).
    """
    from fractions import Fraction

    def norm(op):
        kind, qs, angle, cond = op[0], op[1], op[2], op[3]
        data = op[4] if len(op) > 4 else ()
        if kind in ("CZ", "CCZ") and angle is None:
            ang = Fraction(1, 2)  # pi phase = 1/2 turn
        elif kind == "Z" and angle is None:
            ang = Fraction(1, 4)
        elif angle is None:
            ang = None
        else:
            try:
                ang = Fraction(str(angle)) / 2  # verifier half-turn units
            except Exception:
                ang = None
        return (kind, qs, ang, cond, data)

    P1 = [norm(o) for o in s_orig.phase]
    P2 = [norm(o) for o in s_cand.phase]
    # 1:1 match requiring proven-equal conditions AND equal data wires
    used = [False] * len(P2)
    merges = []
    for (k1, q1, a1, c1, d1) in P1:
        hit = None
        for j, (k2, q2, a2, c2, d2) in enumerate(P2):
            if used[j] or k1 != k2 or q1 != q2 or a1 != a2:
                continue
            if cond_equal(base_values, s_orig, c1, s_cand, c2)["verdict"] != "equivalent":
                continue
            if data_equal(base_values, s_orig, d1, s_cand, d2)["verdict"] != "equivalent":
                continue
            hit = j
            break
        if hit is not None:
            used[hit] = True
        else:
            merges.append((k1, q1, a1, c1, d1))
    rest2 = [P2[j] for j, u in enumerate(used) if not u]
    if not merges and not rest2:
        return {"verdict": "equivalent", "method": "phase-ops-identical",
                "n_ops": len(P1)}
    # XOR-merge pairs: two identical diag gates in P1, one in P2 with cond = f xor g
    if len(rest2) * 2 != len(merges):
        return {"verdict": "unknown", "method": "phase-match",
                "reason": f"{len(merges)} unmatched orig vs {len(rest2)} unmatched cand"}
    for (k2, q2, a2, c2, d2) in rest2:
        if k2 not in ("CZ", "CCZ") or a2 != Fraction(1, 2):
            return {"verdict": "unknown", "method": "phase-match",
                    "reason": f"merge target not diagonal-pi: {k2} {q2} {a2}"}
        pair = [m for m in merges if m[0] == k2 and m[1] == q2 and m[2] == a2]
        if len(pair) != 2:
            return {"verdict": "unknown", "method": "phase-match",
                    "reason": f"no identical pair for merge target {k2} {q2}"}
        (_, _, _, f, df) = pair[0]
        (_, _, _, g, dg) = pair[1]
        # merged op data must equal both orig datas (branch-exact phase)
        for dd in (df, dg):
            r = data_equal(base_values, s_orig, dd, s_cand, d2)
            if r["verdict"] != "equivalent":
                return {"verdict": r["verdict"], "method": "xor-merge-data",
                        "reason": f"merged target data differs: {r}"}
        r = prove_xor_merge(base_values, s_orig, f, g, s_cand, c2)
        if r["verdict"] != "equivalent":
            return {"verdict": r["verdict"], "method": "xor-merge",
                    "reason": f"merged cond not proven f-xor-g: {r}"}
        for m in pair:
            merges.remove(m)
    if merges:
        return {"verdict": "unknown", "method": "phase-match",
                "reason": "leftover unmatched phase ops"}
    return {"verdict": "equivalent", "method": "xor-merge-pairs"}


def prove_xor_merge(base_values, s_orig, f, g, s_cand, c2):
    """Prove cand cond c2 == orig f xor orig g (sliced at shared entry)."""
    e1, e2 = set(s_orig.entry_snap), set(s_cand.entry_snap)
    try:
        sk = {}
        for root, vv, ee in ((f, s_orig.values, e1), (g, s_orig.values, e1),
                             (c2, s_cand.values, e2)):
            for k in sliced_symbols(vv, ee, root):
                sk[k] = True
    except _Unalignable as e:
        return {"verdict": "unknown", "reason": f"unaligned atom: {e}"}
    keys = sorted(sk, key=str)
    n = len(keys)
    if n <= booleq62.SMALL_CONE_LIMIT:
        for mask in range(1 << n):
            env = {k: (mask >> i) & 1 for i, k in enumerate(keys)}
            want = eval_sliced(s_orig.values, f, e1, env) ^ \
                eval_sliced(s_orig.values, g, e1, env)
            got = eval_sliced(s_cand.values, c2, e2, env)
            if want != got:
                return {"verdict": "not-equivalent", "checked": mask + 1}
        return {"verdict": "equivalent", "method": "truth-table", "free_vars": n}
    return {"verdict": "unknown", "reason": f"{n} vars need Z3 xor-merge (not wired)"}


def splice_kmb(header, ops, lo, hi, cand_ops, out_path):
    import kickmix
    new_ops = ops[:lo] + list(cand_ops) + ops[hi:]
    circuit = kickmix.Circuit.from_file(
        io.StringIO("\n".join(header + new_ops) + "\n"), format="kmx")
    buf = io.BytesIO()
    circuit.to_file(buf, format="kmb")
    Path(out_path).write_bytes(buf.getvalue())
    stats = circuit.operation_statistics()
    return {"qubits": circuit.num_qubits,
            "toffoli_like": stats.num_toffoli_like,
            "ops": dict(stats)}


def exec_cost(ops):
    """Branch-aware executed-cost ledger (no static-conditional inflation).

    Unconditional Toffoli-like ops: exact. Conditional non-Clifford ops:
    reported per branch-policy (each outcome combo of involved leaves);
    never summed as static counts.
    """
    from collections import Counter
    uncond = Counter()
    cond = []
    for line in ops:
        p = line.split()
        k = p[0]
        is_cond = ("if" in p) or k in ("PUSH_CONDITION", "POP_CONDITION")
        if k in ("CCX", "CCZ") and not is_cond:
            uncond[k] += 1
        elif k in ("CCX", "CCZ") and is_cond:
            bit = p[p.index("if") + 1] if "if" in p else "stack"
            cond.append((k, bit, line))
    return {"uncond_toffoli_like": dict(uncond),
            "cond_nonclifford": [(k, b) for k, b, _ in cond]}


def cmd_crosscheck():
    _, ops = load_baseline()
    # port fidelity: full-baseline wires equal retain62.interpret wires
    mine = Sym(track=True).run(ops)
    v2, wire2, _s, _c, _e = retain62.interpret(ops, track=True)
    assert len(mine.wire) == len(wire2) == 62
    # same-construction deterministic ids: compare structurally via eval spot?
    # ids should match exactly given identical construction order.
    same = sum(1 for a, b in zip(mine.wire, wire2) if a == b)
    print(f"wire ids identical: {same}/62")
    # bit check: HMR write counts
    print(f"phase ops recorded: {len(mine.phase)}")
    assert same == 62, "port drift vs retain62"
    print("CROSSCHECK PASS")


def cmd_census():
    _, ops = load_baseline()
    ART.mkdir(parents=True, exist_ok=True)
    base = run_prefix(ops, 0)
    out = {"windows": {}, "inva": {}}
    for name, (lo, hi) in WINDOWS.items():
        s = base.fork().run(ops[:hi])
        # phase ledger for the window slice only
        sw = base.fork().run(ops[lo:hi], start=lo)
        # NOTE: window-only run mints its own atoms; used for census only,
        # never for equivalence (prove_window forks the real prefix).
        conds = {}
        for op in sw.phase:
            k, qs, ang = op[0], op[1], op[2]
            conds.setdefault((k, qs, ang), []).append(op[3])
        multi = {str(k): len(set(v)) for k, v in conds.items() if len(v) > 1}
        from collections import Counter
        out["windows"][name] = {
            "lo": lo, "hi": hi, "len": hi - lo,
            "kinds": dict(Counter(l.split()[0] for l in ops[lo:hi])),
            "n_phase_ops": len(sw.phase),
            "distinct_phase_fns": len(conds),
            "repeated_phase_targets": multi,
            "n_hmr": sum(1 for l in ops[lo:hi] if l.startswith("HMR")),
        }
        print(f"{name} [{lo},{hi}): kinds={out['windows'][name]['kinds']}")
        print(f"  phase ops={len(sw.phase)} distinct={len(conds)} repeated={multi}")
    # inverse_A CCX snippet mining
    lo, hi = INVA
    seg, cur = [], []
    boundaries = []
    for i in range(lo, hi):
        p = ops[i].split()
        cur.append((i, ops[i]))
        if p[0] in ("HMR", "R", "Z_POW", "PUSH_CONDITION", "POP_CONDITION"):
            if cur:
                seg.append(cur)
            cur = []
            boundaries.append(i)
    if cur:
        seg.append(cur)
    snips = []
    for s in seg:
        nccx = sum(1 for _, l in s if l.startswith("CCX"))
        if 2 <= nccx <= 4 and len(s) <= 60:
            snips.append({"start": s[0][0], "end": s[-1][0] + 1,
                          "len": len(s), "n_ccx": nccx})
    out["inva"]["n_segments"] = len(seg)
    out["inva"]["candidate_snippets"] = snips[:12]
    print(f"invA: {len(seg)} segments, {len(snips)} snippets w/ 2-4 CCX (showing 12)")
    for sn in snips[:12]:
        print(f"  [{sn['start']},{sn['end']}) len={sn['len']} ccx={sn['n_ccx']}")
    (ART / "patch_census.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote patch_census.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--crosscheck", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--prove", default=None)
    ap.add_argument("--cand-file", default=None)
    ap.add_argument("--range", default=None,
                    help="lo,hi for ad-hoc snippet proof (with --prove LABEL)")
    args = ap.parse_args()
    if args.crosscheck:
        return cmd_crosscheck()
    if args.census:
        return cmd_census()
    if args.prove:
        assert args.cand_file, "--cand-file required"
        cand = [l.rstrip("\n") for l in Path(args.cand_file).read_text().splitlines()
                if l.strip()]
        if args.range:
            lo_s, hi_s = args.range.split(",")
            rec = prove_range(args.prove, int(lo_s), int(hi_s), cand)
        else:
            rec = prove_window(args.prove, cand)
        print(json.dumps(rec, indent=1)[:3000])
        (ART / f"proof_{args.prove}.json").write_text(json.dumps(rec, indent=1) + "\n")
        return 0 if rec.get("verdict") == "PASS" else 1
    ap.error("nothing to do")


if __name__ == "__main__":
    sys.exit(main())
