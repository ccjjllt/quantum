"""Manual semantic checks for the round-2 prover (manual runs only).

NOT a test file, NOT CI, no auto-gating. Run by hand:
  uv run python experiments/invsqrt/20261103_baseline_patch_round2/check_semantics.py --all
  uv run --offline --with z3-solver python ... (for the Z3-backed cases)

Covers (plan §3):
  E1 three historical bugs: HMR phase omission, candidate-added bit writes,
     PUSH-then-modify-condition-bit.
  E2 R random phase, cond-off HMR no-write, nested cond stack, bit reuse.
  E3 Z/CZ/CCZ/NEG + exact Z_POW units (vs probe JSON ground truth).
  E4 two correct rewrites must PASS: dual-target common-product reuse,
     same-target common-factor merge (uncompute recognition).
  E5 broken variants must NOT pass: deleted fixup, broken borrow restore.
  E6 cond-stack gate cost vs kickmix operation_statistics.
"""
from __future__ import annotations
import argparse, io, json, sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261103_baseline_patch_round2"))
ART = ROOT / "artifacts/20261103_baseline_patch_round2/invsqrt"

import patch62r2 as R2  # noqa: E402

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append({"name": name, "verdict": PASS if cond else FAIL,
                    "detail": detail})
    print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail else ""))


def prove(lo_lines, hi_lines_extra=None):
    """Prove tiny synthetic window: orig vs cand, fresh Sym2 pair."""
    base = R2.Sym2()
    o = base.fork()
    c = base.fork()
    return o, c


def run_pair(orig, cand):
    b = R2.Sym2()
    so = b.fork().run(orig)
    sc = b.fork().run(cand)
    so.entry_snap = tuple(b.wire)
    sc.entry_snap = tuple(b.wire)
    return b, so, sc


def wires_equal(so, sc, qubits):
    import patch62 as P61
    eo, ec = set(so.entry_snap), set(sc.entry_snap)
    for q in qubits:
        if so.wire[q] == sc.wire[q]:
            continue
        r = P61.sliced_equiv(so.values, eo, so.wire[q],
                             sc.values, ec, sc.wire[q])
        if r["verdict"] != "equivalent":
            return False, (q, r)
    return True, None


def E1_hmr_phase_ledger():
    # HMR must contribute a phase term cond x preval x event (was omitted r1)
    s = R2.Sym2().run(["X q0", "HMR q0 b0"])
    terms = [t for t in s.phase if t[0] == "HMR"]
    ok = (len(terms) == 1 and terms[0][2] == Fraction(1)
          and terms[0][5] == ("event", 0))
    check("E1a HMR phase term present", ok, str(terms[0][2:3]) if terms else "none")
    # candidate that drops nothing but reorders must keep the term
    b, so, sc = run_pair(["X q0", "HMR q0 b0", "X q1"],
                         ["X q1", "X q0", "HMR q0 b0"])
    r = R2.prove_phase2(so, sc)
    check("E1b HMR phase survives reorder", r["verdict"] == "equivalent", r.get("method", ""))
    # candidate that CHANGES preval (extra X before HMR) must NOT pass phase
    b, so, sc = run_pair(["HMR q0 b0"], ["X q0", "HMR q0 b0"])
    r = R2.prove_phase2(so, sc)
    check("E1c preval change caught", r["verdict"] != "equivalent", r.get("method", ""))


def E1_added_bit_writes():
    _, ops = R2.P61.load_baseline()
    lo, hi = 35331, 35379
    cand = list(ops[lo:hi]) + ["BIT_STORE1 b9999"]
    rec = R2.prove_range2("selftest", lo, hi, cand, ops)
    check("E1d added bit-write rejected",
          rec["verdict"] == "FAIL" and "bit" in rec.get("reason", ""),
          rec.get("reason", ""))


def E1_push_modify():
    # PUSH snapshot: stack keeps old value after BIT_STORE (E6r ground truth)
    s = R2.Sym2().run(["BIT_STORE1 b0", "PUSH_CONDITION if b0",
                       "BIT_STORE0 b0", "X q30", "POP_CONDITION"])
    import kickmix as km
    HDR = ("APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\nREGISTER r0 \"x\"\n"
           "APPEND_TO_REGISTER b0 r1\nREGISTER r1 \"c\"\n")
    circ = km.Circuit.from_file(io.StringIO(HDR + "\n".join(
        ["BIT_STORE1 b0", "PUSH_CONDITION if b0", "BIT_STORE0 b0",
         "X q1", "POP_CONDITION"]) + "\n"), format="kmx")
    sim = km.Simulator(50, seed=3)
    sim.do(circ)
    import numpy as np
    q1 = float(np.asarray(sim.read_across_shots(km.q(1))).astype(int).mean())
    # symbolic: q30 (zero-init both sides) must equal ONE
    v = s.values
    check("E1e PUSH snapshot models kickmix", q1 == 1.0 and s.wire[30] == v.one,
          "sim q1=%s sym==one:%s" % (q1, s.wire[30] == v.one))


def E2_r_phase_and_no_write():
    s = R2.Sym2().run(["X q0", "R q0"])
    terms = [t for t in s.phase if t[0] == "R"]
    check("E2a R phase term present",
          len(terms) == 1 and terms[0][2] == Fraction(1), str(len(terms)))
    # cond-off HMR: wire + bit unchanged (E5 ground truth).
    # Witness q30 (zero-init): X first so pre-value is ONE, then cond-off HMR.
    s = R2.Sym2().run(["BIT_STORE1 b0", "X q30", "PUSH_CONDITION if b1",
                       "HMR q30 b0", "POP_CONDITION"])
    v = s.values
    check("E2b cond-off no-write", s.wire[30] == v.one and s.bits[0] == v.one, "")
    # nested stack + bit reuse resolve without crash, stack balanced
    s = R2.Sym2().run(["BIT_STORE1 b0", "PUSH_CONDITION if b0",
                       "BIT_STORE1 b1", "PUSH_CONDITION if b1",
                       "BIT_STORE0 b1", "BIT_STORE0 b0", "X q1",
                       "POP_CONDITION", "POP_CONDITION"])
    check("E2c nested+reuse balanced", s.stack == [], str(s.stack))


def E3_units():
    d = json.loads((ART / "probe_kickmix.json").read_text())
    exp = {"ccx": 1, "ccz": 1, "cswap": 1, "hmr": 0, "r": 0, "z": 0,
           "cz": 0, "neg": 0}
    ok = all(d[k]["toffoli_like"] == v for k, v in exp.items())
    check("E3a gate classes", ok, "")
    ok = (d["zpow_half"]["t_like"] == 0
          and d["zpow_quarter"]["t_like"] == 1
          and d["zpow_tenth"]["t_like"] == 0)
    check("E3b Z_POW classes (rot vs T)", ok, "")
    # prover ledger uses half-turn units: Z/CZ/CCZ/NEG = 1
    s = R2.Sym2().run(["X q0", "X q1", "X q2", "Z q0", "CZ q0 q1",
                       "CCZ q0 q1 q2", "NEG", "Z_POW q0 0.25"])
    angs = [t[2] for t in s.phase]
    check("E3c ledger units exact",
          angs == [Fraction(1)] * 4 + [Fraction(1, 4)], str(angs))


def E4_correct_rewrites():
    # dual-target common-product reuse (zero temps q30/q31)
    orig = ["CCX q0 q1 q30", "CCX q0 q1 q31"]
    cand = ["CCX q0 q1 q30", "CX q30 q31"]
    b, so, sc = run_pair(orig, cand)
    ok, _ = wires_equal(so, sc, [30, 31])
    r = R2.prove_phase2(so, sc)
    check("E4a dual-target reuse passes", ok and r["verdict"] == "equivalent",
          r.get("method", ""))
    # same-target common factor (double CCX = identity)
    orig = ["CCX q0 q1 q30", "CCX q0 q1 q30"]
    cand = []
    b, so, sc = run_pair(orig, cand)
    ok, _ = wires_equal(so, sc, [30])
    check("E4b double-CCX identity passes", ok, "")


def E5_broken_variants():
    # deleted fixup: CZ present in orig, dropped in cand, data live
    orig = ["X q0", "X q1", "CZ q0 q1", "CX q0 q2"]
    cand = ["X q0", "X q1", "CX q0 q2"]
    b, so, sc = run_pair(orig, cand)
    r = R2.prove_phase2(so, sc)
    check("E5a deleted fixup not passing", r["verdict"] != "equivalent",
          r.get("method", ""))
    # broken borrow restore: temp left dirty
    orig = ["CCX q0 q1 q30", "CX q30 q2", "CCX q0 q1 q30"]
    cand = ["CCX q0 q1 q30", "CX q30 q2"]
    b, so, sc = run_pair(orig, cand)
    ok, info = wires_equal(so, sc, [30])
    check("E5b dirty borrow caught", not ok, str(info[0]) if info else "")


def E6_cost_vs_stats():
    import kickmix as km
    import numpy as np
    HDR = ("APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\n"
           "APPEND_TO_REGISTER q2 r0\nAPPEND_TO_REGISTER q3 r0\nREGISTER r0 \"x\"\n"
           "APPEND_TO_REGISTER b0 r1\nAPPEND_TO_REGISTER b1 r1\nREGISTER r1 \"c\"\n")
    lines = ["X q0", "HMR q0 b0", "X q1",
             "PUSH_CONDITION if b0", "CCX q0 q1 q2", "POP_CONDITION",
             "CCX q1 q2 q3"]
    circ = km.Circuit.from_file(io.StringIO(HDR + "\n".join(lines) + "\n"), format="kmx")
    N = 2000
    sim = km.Simulator(N, counting_operations=True, seed=11)
    sim.do(circ)
    est = sim.operation_statistics().num_toffoli_like / N
    p = float(np.asarray(sim.read_across_shots(km.b(0))).astype(int).mean())
    # ledger: 1 uncond CCX + 1 stack-cond CCX
    s = R2.Sym2().run(lines)
    led = R2.cost_ledger(R2.Sym2(), lines)
    kinds = sorted(k for k, _, _ in led)
    pred = 1 + p
    check("E6 stack-cond cost agrees",
          kinds == ["CCX", "CCX"] and abs(est - pred) < 0.05,
          "exec=%.4f pred=1+P=%.4f" % (est, pred))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    if not (args.all or args.only):
        ap.error("pass --all or --only NAME")
    table = {"E1": [E1_hmr_phase_ledger, E1_added_bit_writes, E1_push_modify],
             "E2": [E2_r_phase_and_no_write], "E3": [E3_units],
             "E4": [E4_correct_rewrites], "E5": [E5_broken_variants],
             "E6": [E6_cost_vs_stats]}
    names = [args.only] if args.only else ["E1", "E2", "E3", "E4", "E5", "E6"]
    for n in names:
        for fn in table[n]:
            fn()
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "semantics_checks.json").write_text(
        json.dumps(results, indent=1) + "\n")
    nfail = sum(1 for r in results if r["verdict"] == "FAIL")
    print("CHECKS: %d/%d pass" % (len(results) - nfail, len(results)))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
