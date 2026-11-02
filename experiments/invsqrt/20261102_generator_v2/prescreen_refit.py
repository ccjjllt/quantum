"""Manual prescreens for refit_variant62 (NOT a test file, NOT CI).

Run manually (evidence commands, see refit_layout.md)::

    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_refit.py --cand A20 --a --b --c --dump-v
    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_refit.py --cand BOTH --a --b --c --dump-v

Same 16 samples and same criteria as prescreen_width_opt.py; oracle is the
quantized integer contract (refit_variant62.q_model_phase with per-candidate
shifts), margins vs official reference_values. No official verifier call.
"""

from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

import refit_variant62 as Q  # noqa: E402
import width_opt62 as W  # noqa: E402

SAMPLES = [1, 2, 3, 8, 31, 32, 63, 128, 161, 888, 2047, 2048,
           2097151, 2097152, 2506015, 3133452]


def _run_sim(circuit, xs):
    sim = km.Simulator(batch_size=len(xs))
    sim.use_same_registers_as(circuit)
    for i, x in enumerate(xs):
        sim.write_within_shot("x", i, x)
    sim.do(circuit)
    return sim


def prescreen_a(cand) -> int:
    t = Q.load_qtables(cand)
    c1 = Q.build_circuit_q(cand)
    c2 = Q.build_circuit_q(cand)
    s1, s2 = Q.circuit_sha_q(c1), Q.circuit_sha_q(c2)
    ok = (str(c1) == str(c2)) and (s1 == s2)
    print(f"cand={cand} sha1={s1}\nsha2={s2}")
    print("PRESCREEN-A " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def prescreen_b(cand) -> int:
    circuit = Q.build_circuit_q(cand)
    nq = circuit.num_qubits
    sim = _run_sim(circuit, SAMPLES)
    fails = 0
    for i, x in enumerate(SAMPLES):
        got = sim.read_within_shot("x", i, out=int)
        if got != x:
            print(f"X-RECOVERY FAIL shot={i} in={x} out={got}")
            fails += 1
    for qq in range(nq):
        across = sim.read_across_shots(km.q(qq))
        for i, x in enumerate(SAMPLES):
            want = ((x >> qq) & 1) == 1 if qq < 22 else False
            if bool(across[i]) != want:
                print(f"SCRATCH FAIL q{qq} shot={i} x={x}")
                fails += 1
                if fails > 20:
                    print("PRESCREEN-B FAIL")
                    return 1
    print(f"checked {len(SAMPLES)} samples x {nq} qubits: "
          f"x-recovery ok, scratch all zero: {fails == 0}")
    print("PRESCREEN-B " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def prescreen_c(cand) -> int:
    import numpy as np

    cfg = Q.CANDS[cand]
    t = Q.load_qtables(cand)
    B, A, R = (list(t.B), list(t.A), list(t.R))
    circuit = Q.build_circuit_q(cand)
    sim = _run_sim(circuit, SAMPLES)
    from invsqrt import verify_submission_invsqrt as official
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    xs = np.array(SAMPLES, dtype=np.uint64)
    tgt_all, tol_all = official.reference_values(spec, xs)
    tgt = np.asarray(tgt_all, dtype=np.float64) / 2**64
    tol = np.asarray(tol_all, dtype=np.float64) / 2**64
    fails = 0
    for i, x in enumerate(SAMPLES):
        V, tt, P = Q.q_model_phase(x, B, A, R, cfg["sA"], cfg["sR"])
        want = Fraction(P, 2**35) % 2
        got = sim.read_shot_phase(i)
        got = got % 2 if isinstance(got, Fraction) else Fraction(got, 1) % 2
        dphase = (got - want) % 2
        pha = float(want) / 2
        err = (pha - tgt[i] + 0.5) % 1.0 - 0.5
        ae = abs(err)
        margin = (tol[i] - ae) * 2**64
        ok = (dphase == 0) and (margin > 0)
        print(f"x={x:>8} t={tt:>2} P={P:>12} dphase={dphase} "
              f"ae={ae:.3e} tol={tol[i]:.3e} margin_units={margin:.1f} "
              f"{'OK' if ok else 'FAIL'}")
        if not ok:
            fails += 1
    print("PRESCREEN-C " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def dump_v(cand) -> int:
    cfg = Q.CANDS[cand]
    t = Q.load_qtables(cand)
    B, A, R = (list(t.B), list(t.A), list(t.R))
    b = km.CircuitBuilder()
    regs = W.create_regs(b)
    x, lz, coef, v = (regs[k] for k in ("x", "lz", "coef", "v"))
    e = b.alloc_qubits(2); h = b.alloc_qubits(1)
    W.build_lz_norm(b, x, lz, e, h)
    b.free(e); b.free(h)
    W.build_normalize(b, x, lz)
    b.isub(8192, target=x[0:W.W_DELTA])
    W.mini_pass(b, x, lz, t.B, W.W_B, v[12:W.W_VHI])
    W.mini_pass(b, x, lz, t.A, cfg["wA"], coef[0:cfg["wA"]])
    Q.build_a1_q(b, x, coef, v, cfg["wA"], cfg["sA"])
    W.mini_pass(b, x, lz, t.A, cfg["wA"], coef[0:cfg["wA"]])
    W.build_square2(b, x, coef)
    W.mini_pass(b, x, lz, t.R, cfg["wR"], coef[0:cfg["wR"]])
    Q.build_r1_q(b, coef, v, cfg["wR"], cfg["nR"], cfg["sR"])
    W.mini_pass(b, x, lz, t.R, cfg["wR"], coef[0:cfg["wR"]])
    circ = b.finish_circuit()
    sim = km.Simulator(batch_size=len(SAMPLES))
    sim.use_same_registers_as(circ)
    for i, xx in enumerate(SAMPLES):
        sim.write_within_shot("x", i, xx)
    sim.do(circ)
    V_BASE = W.W_X + W.W_LZ + W.W_B
    fails = 0
    for i, xx in enumerate(SAMPLES):
        V, tt, _P = Q.q_model_phase(xx, B, A, R, cfg["sA"], cfg["sR"])
        gotV = 0
        for k in range(W.W_V):
            across = sim.read_across_shots(km.q(V_BASE + k))
            if bool(across[i]):
                gotV |= (1 << k)
        status = "OK" if gotV == V else "FAIL"
        if gotV != V:
            fails += 1
        print(f"x={xx:>8} Vwant={V:>15} Vgot={gotV:>15} t={tt} {status}")
    print("DUMP-V " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="A20")
    ap.add_argument("--a", action="store_true")
    ap.add_argument("--b", action="store_true")
    ap.add_argument("--c", action="store_true")
    ap.add_argument("--dump-v", action="store_true")
    args = ap.parse_args()
    rc = 0
    if args.a:
        rc |= prescreen_a(args.cand)
    if args.b:
        rc |= prescreen_b(args.cand)
    if args.c:
        rc |= prescreen_c(args.cand)
    if args.dump_v:
        rc |= dump_v(args.cand)
    if not any([args.a, args.b, args.c, args.dump_v]):
        ap.print_help()
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
