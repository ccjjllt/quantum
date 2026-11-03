"""Round-2 baseline patch prover: fixed semantics (manual runs only).

NOT a test file, NOT CI. No verifier modification, no auto-submit.
Generation and official verification stay separate (scripts/manual_verify.py).

Semantic fixes vs round-1 patch62.py (all cross-checked against real
kickmix behavior in probe_km.py / probe_sim.py / probe_phase.py /
probe_stack.py, artifacts/20261103_baseline_patch_round2/invsqrt/):
  * Cond stack stores (bit, SAVED vid); later writes to the same bit do not
    change stacked conditions (E6r/E6r2). PUSH/POP never gated.
  * HMR/R allocate independent random event vars (serials); phase ledger
    term = cond x preval x outcome, in HALF-TURN units (E2/E4).
    Cond-off: wires and HMR output bits unchanged (E5).
  * Phase units are half-turns, exact Fractions, compared mod 1 turn
    (= 2 half-turns): Z/CZ/CCZ/NEG = 1, Z_POW = written angle (E7).
    No float compares, no gate-list-only equivalence.
  * Exit state = union of write sets: qubit wires, live classical bits,
    AND saved stack values.
  * Random events: HMR/R order+args asserted AND per-event exec conditions
    proven equal; events aligned by serial.
  * Exec cost: per-op condition vids for CCX/CCZ/CSWAP/T/rotations;
    branch-exact ledgers, never inline-if counting (E1: static 2 vs
    executed mean 1.4525).

Verdicts: PASS / FAIL (local counterexample = proven not-equivalent on a
sliced input assignment; only a replay from legal inputs + real prefix
promotes it to a real-circuit counterexample) / UNKNOWN (60 s cap).
"""
from __future__ import annotations
import argparse, copy, hashlib, io, json, sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_baseline_patch"))
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_hw06_opt"))

import patch62 as P61  # noqa: E402
import booleq62  # noqa: E402

BASELINE = P61.BASELINE
BASELINE_SHA = P61.BASELINE_SHA
ART = ROOT / "artifacts/20261103_baseline_patch_round2/invsqrt"
WINDOWS = P61.WINDOWS
Z3_MS = 60_000


def qn(t):
    return int(t[1:])


class Sym2:
    """Symbolic state, fixed semantics. Shares Values lineage for forking."""

    def __init__(self, values=None):
        self.values = values or P61.retain62.Values()
        v = self.values
        self.wire = []
        for q in range(62):
            self.wire.append(v.vid(frozenset([q])) if q <= 21 else v.zero)
        self.bits = {}
        self.stack = []   # list of (bit, saved_vid)
        self.phase = []   # (kind, targets, angleFrac|None, cond, data, event|None)
        self.events = []  # (kind, qubit, bit|None, cond, outcome_atom, index)

    def fork(self):
        return copy.deepcopy(self)

    def ensure_bit(self, bit):
        if bit not in self.bits:
            self.bits[bit] = self.values.zero
        return self.bits[bit]

    def active(self, parts):
        v = self.values
        factors = [saved for _, saved in self.stack]
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
            # snapshot current value; never gated (handled: no `when` here)
            bit = int(parts[-1][1:])
            self.stack.append((bit, self.ensure_bit(bit)))
        elif kind == "POP_CONDITION":
            if self.stack:
                self.stack.pop()
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
        elif kind in ("Z", "CZ", "CCZ", "NEG"):
            qs = tuple(qn(t) for t in parts[1:] if t.startswith("q"))
            self.phase.append((kind, qs, Fraction(1), cond,
                               tuple(self.wire[q] for q in qs), None))
        elif kind == "Z_POW":
            qs = tuple(qn(t) for t in parts[1:] if t.startswith("q"))
            ang = next((t for t in parts[1:]
                        if not t.startswith("q") and t != "if" and not t.startswith("b")), None)
            self.phase.append((kind, qs, Fraction(str(ang)), cond,
                               tuple(self.wire[q] for q in qs), None))
        elif kind in ("HMR", "R"):
            q = qn(parts[1])
            old = self.wire[q]
            bit = None
            if len(parts) > 2 and parts[2].startswith("b"):
                bit = int(parts[2][1:])
            # independent random event var, always allocated (even cond-off:
            # the event exists, it just doesn't affect state). Aligned across
            # forked objects by SERIAL (HMR/R order asserted identical).
            serial = len(self.events)
            outcome = v.vid(frozenset([9_000_000 + serial]))
            self.events.append((kind, q, bit, cond, serial, index))
            if bit is not None:
                old_bit = self.bits.get(bit, v.zero)
                # cond-off: output bit keeps old value (E5)
                self.bits[bit] = self.when(old_bit, outcome, cond)
            # cond-off: wire keeps old value (E5)
            self.wire[q] = self.when(old, v.zero, cond)
            # phase: cond x preval x outcome, half-turn units (E2/E4)
            self.phase.append((kind, (q,), Fraction(1), cond, (old,),
                               ("event", serial)))

    def run(self, ops, start=0):
        for i, line in enumerate(ops):
            self.step(line, index=start + i)
        return self


def run_prefix2(ops, end):
    return Sym2().run(ops[:end])


def barrier_sig(ops):
    return [(p[0], p[1], p[2] if len(p) > 2 else None)
            for p in (l.split() for l in ops) if p[0] in ("HMR", "R")]


def bit_write_sig(ops):
    """All classical-bit writes (HMR targets + BIT ops), in order."""
    out = []
    for p in (l.split() for l in ops):
        if p[0] in ("HMR", "R") and len(p) > 2 and p[2].startswith("b"):
            out.append((p[0], p[2]))
        elif p[0] in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            out.append((p[0], p[1]))
    return out


def prove_range2(name, lo, hi, cand_ops, ops=None):
    if ops is None:
        _, ops = P61.load_baseline()
    orig_ops = ops[lo:hi]
    rec = {"window": name, "lo": lo, "hi": hi,
           "n_orig": len(orig_ops), "n_cand": len(cand_ops)}
    depth = 0
    for line in cand_ops:
        k = line.split()[0]
        if k == "PUSH_CONDITION":
            depth += 1
        elif k == "POP_CONDITION":
            depth -= 1
            if depth < 0:
                break
    rec["cond_balanced"] = (depth == 0)
    if depth != 0:
        return {**rec, "verdict": "FAIL", "reason": "stack unbalanced"}
    if barrier_sig(orig_ops) != barrier_sig(cand_ops):
        return {**rec, "verdict": "FAIL",
                "reason": "HMR/R order/args changed (round keeps them)"}
    if bit_write_sig(orig_ops) != bit_write_sig(cand_ops):
        return {**rec, "verdict": "FAIL",
                "reason": "classical-bit write set changed (new writes forbidden)"}
    zp1 = P61.zpow_seq(orig_ops)
    zp2 = P61.zpow_seq(cand_ops)
    if zp1 != zp2:
        return {**rec, "verdict": "FAIL", "reason": "Z_POW sequence changed"}
    rec["gates_kept"] = True
    base = run_prefix2(ops, lo)
    s_orig = base.fork().run(orig_ops, start=lo)
    s_cand = base.fork().run(cand_ops, start=lo)
    s_orig.entry_snap = tuple(base.wire)
    s_cand.entry_snap = tuple(base.wire)
    if [b for b, _ in s_orig.stack] != [b for b, _ in s_cand.stack]:
        return {**rec, "verdict": "FAIL", "reason": "exit stack depth/bits differ"}
    # exit stack saved values
    for (b1, v1), (b2, v2) in zip(s_orig.stack, s_cand.stack):
        r = P61.sliced_equiv(s_orig.values, set(s_orig.entry_snap), v1,
                             s_cand.values, set(s_cand.entry_snap), v2)
        if r["verdict"] != "equivalent":
            return {**rec, "verdict": r["verdict"],
                    "reason": "saved stack value b%d: %s" % (b1, r)}
    rec["stack_equal"] = True
    # wires
    entry_o, entry_c = set(s_orig.entry_snap), set(s_cand.entry_snap)
    for q in range(62):
        if s_orig.wire[q] == base.wire[q] and s_cand.wire[q] == base.wire[q]:
            continue
        r = P61.sliced_equiv(s_orig.values, entry_o, s_orig.wire[q],
                             s_cand.values, entry_c, s_cand.wire[q])
        if r["verdict"] != "equivalent":
            return {**rec, "verdict": r["verdict"],
                    "reason": "qubit q%d: %s (local counterexample)" % (q, r)}
    rec["wires_equivalent"] = True
    # live bits
    live = P61.bits_read_after(ops, hi)
    for b, vb in s_orig.bits.items():
        if b not in live:
            continue
        vc = s_cand.bits.get(b)
        if vc is None:
            return {**rec, "verdict": "FAIL",
                    "reason": "live bit b%d missing in candidate" % b}
        if vb == base.bits.get(b) and vc == base.bits.get(b):
            continue
        r = P61.sliced_equiv(s_orig.values, entry_o, vb,
                             s_cand.values, entry_c, vc)
        if r["verdict"] != "equivalent":
            return {**rec, "verdict": r["verdict"],
                    "reason": "live bit b%d: %s (local counterexample)" % (b, r)}
    rec["bits_equivalent"] = True
    # random events: same count (barrier sig equal => same HMR/R count/order)
    if len(s_orig.events) != len(s_cand.events):
        return {**rec, "verdict": "FAIL", "reason": "event count differs"}
    for (k1, q1, b1, c1, s1, _), (k2, q2, b2, c2, s2, _) in zip(s_orig.events, s_cand.events):
        if (k1, q1, b1, s1) != (k2, q2, b2, s2):
            return {**rec, "verdict": "FAIL", "reason": "event mismatch"}
        if c1 is None and c2 is None:
            r = {"verdict": "equivalent"}
        elif c1 is None or c2 is None:
            r = {"verdict": "unknown", "reason": "one side unconditional"}
        else:
            r = P61.sliced_equiv(s_orig.values, entry_o, c1,
                                 s_cand.values, entry_c, c2)
        if r["verdict"] != "equivalent":
            return {**rec, "verdict": r["verdict"],
                    "reason": "event exec-cond differs: %s" % (r,)}
    rec["events_aligned"] = True
    # phase, termwise (exact half-turn Fractions; equality by construction)
    pr = prove_phase2(s_orig, s_cand)
    rec["phase"] = pr
    if pr["verdict"] != "equivalent":
        return {**rec, "verdict": pr["verdict"],
                "reason": "phase: %s" % pr.get("reason", pr["verdict"])}
    rec["verdict"] = "PASS"
    return rec


def _peq(s_orig, s_cand, a, b):
    return P61.sliced_equiv(s_orig.values, set(s_orig.entry_snap), a,
                            s_cand.values, set(s_cand.entry_snap), b)


def prove_phase2(s_orig, s_cand):
    """Termwise exact-phase proof. HMR/R terms use aligned event serials."""
    used = [False] * len(s_cand.phase)
    leftovers = []
    for (k1, q1, a1, c1, d1, e1) in s_orig.phase:
        hit = None
        for j, (k2, q2, a2, c2, d2, e2) in enumerate(s_cand.phase):
            if used[j] or k1 != k2 or q1 != q2 or a1 != a2:
                continue
            if (e1 is None) != (e2 is None):
                continue
            if e1 is not None and e1 != e2:
                # event serials align by asserted HMR/R order
                continue
            ok = _cond_eq(s_orig, s_cand, c1, c2)
            if ok["verdict"] != "equivalent":
                continue
            okd = all(_peq(s_orig, s_cand, x, y)["verdict"] == "equivalent"
                      for x, y in zip(d1, d2))
            if not okd:
                continue
            hit = j
            break
        if hit is not None:
            used[hit] = True
        else:
            leftovers.append((k1, q1, a1, c1, d1, e1))
    rest = [s_cand.phase[j] for j, u in enumerate(used) if not u]
    if not leftovers and not rest:
        return {"verdict": "equivalent", "method": "phase-terms-identical",
                "n_terms": len(s_orig.phase)}
    # XOR-merge fallback for diagonal-pi pairs (data + xor-cond proven)
    if len(rest) * 2 != len(leftovers):
        return {"verdict": "unknown", "method": "phase-match",
                "reason": "%d vs %d unmatched terms" % (len(leftovers), len(rest))}
    for (k2, q2, a2, c2, d2, e2) in rest:
        if k2 not in ("CZ", "CCZ") or a2 != Fraction(1) or e2 is not None:
            return {"verdict": "unknown", "method": "phase-match",
                    "reason": "merge target not diagonal-pi: %s" % (k2,)}
        pair = [m for m in leftovers
                if m[0] == k2 and m[1] == q2 and m[2] == a2 and m[5] is None]
        if len(pair) != 2:
            return {"verdict": "unknown", "method": "phase-match",
                    "reason": "no identical pair for %s %s" % (k2, q2)}
        (_, _, _, f, df, _), (_, _, _, g, dg, _) = pair
        for dd in (df, dg):
            if any(_peq(s_orig, s_cand, x, y)["verdict"] != "equivalent"
                   for x, y in zip(dd, d2)):
                return {"verdict": "unknown", "method": "xor-merge-data",
                        "reason": "merged target data differs"}
        r = P61.prove_xor_merge(None, s_orig, f, g, s_cand, c2)
        if r["verdict"] != "equivalent":
            return {"verdict": r["verdict"], "method": "xor-merge",
                    "reason": "xor-cond unproven: %s" % (r,)}
        for m in pair:
            leftovers.remove(m)
    if leftovers:
        return {"verdict": "unknown", "method": "phase-match",
                "reason": "leftover terms"}
    return {"verdict": "equivalent", "method": "xor-merge-pairs"}


def _cond_eq(s_orig, s_cand, c1, c2):
    if c1 is None and c2 is None:
        return {"verdict": "equivalent"}
    if c1 is None or c2 is None:
        return {"verdict": "unknown", "reason": "one side unconditional"}
    return _peq(s_orig, s_cand, c1, c2)


def cost_ledger(sym, ops):
    """Branch-exact exec-cost ledger for non-Clifford ops.

    Returns list of (kind, cond_vid|None, angleFrac|None). CCX/CCZ/CSWAP
    count 1 toffoli-like iff executed; T-class Z_POW (angle % 1/2 != 0 and
    % 1/4 == 0) counts 1 T iff executed; general rotations listed
    separately (never rewritten round 1).
    """
    out = []
    s = sym.fork()
    for i, line in enumerate(ops):
        p = line.split()
        k = p[0]
        if k in ("CCX", "CCZ", "CSWAP"):
            out.append((k, s.active(p), None))
        elif k == "Z_POW":
            ang = Fraction(str(next(t for t in p[1:]
                                     if not t.startswith("q") and t != "if"
                                     and not t.startswith("b"))))
            cls = "clifford" if ang % Fraction(1, 2) == 0 else \
                  ("T" if ang % Fraction(1, 4) == 0 else "rotation")
            if cls != "clifford":
                out.append(("ZPOW_" + cls, s.active(p), ang))
        s.step(line, index=i)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prove-window", default=None)
    ap.add_argument("--cand-file", default=None)
    ap.add_argument("--range", default=None)
    args = ap.parse_args()
    if args.prove_window:
        assert args.cand_file, "--cand-file required"
        cand = [l.rstrip("\n") for l in Path(args.cand_file).read_text().splitlines()
                if l.strip()]
        if args.range:
            lo_s, hi_s = args.range.split(",")
            rec = prove_range2(args.prove_window, int(lo_s), int(hi_s), cand)
        else:
            lo, hi = WINDOWS[args.prove_window]
            _, ops = P61.load_baseline()
            rec = prove_range2(args.prove_window, lo, hi, cand, ops)
        print(json.dumps(rec, indent=1)[:3000])
        ART.mkdir(parents=True, exist_ok=True)
        (ART / ("proof_%s.json" % args.prove_window)).write_text(
            json.dumps(rec, indent=1) + "\n")
        return 0 if rec.get("verdict") == "PASS" else 1
    ap.error("nothing to do")


if __name__ == "__main__":
    sys.exit(main())
