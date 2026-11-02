"""Manual prescreens for generator62_v2 (NOT a test file, NOT CI).

Run manually (evidence commands, see gen2_build.md)::

    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_gen2.py --a
    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_gen2.py --b
    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_gen2.py --c
    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_gen2.py --dump-v

(a) double-build SHA consistency (rebuild twice, compare with recorded SHA).
(b) kickmix Simulator on >=12 directed samples: x recovery + ALL scratch zero
    (reads every qubit index q0..num_qubits-1 across shots; x-bits must equal
    the input, everything else must be 0). True inputs only, no padding shots.
(c) actual shot phase vs contract62.model_phase oracle (must be EXACTLY equal
    mod 2 half-turns); plus margin>0 vs official reference_values on samples.
--dump-v: forward-prefix circuit (up to R unload) simulator dump of V/S/coef
    vs model_phase (debug aid; not part of pass criteria).
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

import width_opt62 as G  # noqa: E402
import contract62 as C62  # noqa: E402

SAMPLES = [1, 2, 3, 8, 31, 32, 63, 128, 161, 888, 2047, 2048,
           2097151, 2097152, 2506015, 3133452]

REC_SHA = "0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d"


def prescreen_a() -> int:
    tables = G.load_tables()
    c1 = G.build_circuit(tables)
    c2 = G.build_circuit(tables)
    s1, s2 = G.circuit_sha(c1), G.circuit_sha(c2)
    ok = (str(c1) == str(c2)) and (s1 == s2 == REC_SHA)
    print(f"sha1={s1}\nsha2={s2}\nrecorded={REC_SHA}")
    print("PRESCREEN-A " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def _run_sim(circuit, xs):
    sim = km.Simulator(batch_size=len(xs))
    sim.use_same_registers_as(circuit)
    for i, x in enumerate(xs):
        sim.write_within_shot("x", i, x)
    sim.do(circuit)
    return sim


def prescreen_b() -> int:
    tables = G.load_tables()
    circuit = G.build_circuit(tables)
    nq = circuit.num_qubits
    sim = _run_sim(circuit, SAMPLES)
    fails = 0
    # x lives in q0..21 (creation order: x first). Verify by register read.
    for i, x in enumerate(SAMPLES):
        got = sim.read_within_shot("x", i, out=int)
        if got != x:
            print(f"X-RECOVERY FAIL shot={i} in={x} out={got}")
            fails += 1
    # every qubit index: x-bits must equal input bits, all else zero.
    for q in range(nq):
        across = sim.read_across_shots(km.q(q))
        for i, x in enumerate(SAMPLES):
            want = ((x >> q) & 1) == 1 if q < 22 else False
            if bool(across[i]) != want:
                print(f"SCRATCH FAIL q{q} shot={i} x={x} got={bool(across[i])} want={want}")
                fails += 1
                if fails > 20:
                    print("... (truncated)")
                    print(f"PRESCREEN-B FAIL ({fails}+ failures)")
                    return 1
    print(f"checked {len(SAMPLES)} samples x {nq} qubits: "
          f"x-recovery ok, scratch all zero: {fails == 0}")
    print("PRESCREEN-B " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def prescreen_c() -> int:
    import numpy as np

    tables = G.load_tables()
    B, A, R = (list(tables.B), list(tables.A), list(tables.R))
    circuit = G.build_circuit(tables)
    sim = _run_sim(circuit, SAMPLES)
    from invsqrt import verify_submission_invsqrt as official
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    xs = np.array(SAMPLES, dtype=np.uint64)
    tgt_all, tol_all = official.reference_values(spec, xs)
    tgt = np.asarray(tgt_all, dtype=np.float64) / 2**64
    tol = np.asarray(tol_all, dtype=np.float64) / 2**64
    fails = 0
    for i, x in enumerate(SAMPLES):
        V, t, P = C62.model_phase(x, B, A, R)
        want = Fraction(P, 2**35) % 2  # half-turns, canonical
        got = sim.read_shot_phase(i)
        got = got % 2 if isinstance(got, Fraction) else Fraction(got, 1) % 2
        dphase = (got - want) % 2
        perr = float(dphase) if dphase <= 1 else float(2 - dphase)
        pha = float(want) / 2  # turns
        err = (pha - tgt[i] + 0.5) % 1.0 - 0.5
        ae = abs(err)
        margin = (tol[i] - ae) * 2**64
        ok = (dphase == 0) and (margin > 0)
        print(f"x={x:>8} t={t:>2} P={P:>12} dphase={dphase} "
              f"ae={ae:.3e} tol={tol[i]:.3e} margin_units={margin:.1f} "
              f"{'OK' if ok else 'FAIL'}")
        if not ok:
            fails += 1
    print("PRESCREEN-C " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def dump_v() -> int:
    """Forward-prefix (through R unload) V/S/coef dump vs model_phase."""
    tables = G.load_tables()
    B, A, R = (list(tables.B), list(tables.A), list(tables.R))
    b = km.CircuitBuilder()
    regs = G.create_regs(b)
    x, lz, coef, v = (regs[k] for k in ("x", "lz", "coef", "v"))
    e = b.alloc_qubits(2)
    h = b.alloc_qubits(1)
    G.build_lz_norm(b, x, lz, e, h)
    b.free(e)
    b.free(h)
    G.build_normalize(b, x, lz)
    b.isub(8192, target=x[0:G.W_DELTA])
    G.mini_pass(b, x, lz, tables.B, G.W_B, v[12:G.W_VHI])
    G.mini_pass(b, x, lz, tables.A, G.W_A, coef[0:G.W_A])
    G.build_a1(b, x, coef, v)
    G.mini_pass(b, x, lz, tables.A, G.W_A, coef[0:G.W_A])
    G.build_square2(b, x, coef)
    G.mini_pass(b, x, lz, tables.R, G.W_R, coef[0:G.W_R])
    G.build_r1(b, coef, v)
    G.mini_pass(b, x, lz, tables.R, G.W_R, coef[0:G.W_R])
    circ = b.finish_circuit()
    sim = km.Simulator(batch_size=len(SAMPLES))
    sim.use_same_registers_as(circ)
    for i, xx in enumerate(SAMPLES):
        sim.write_within_shot("x", i, xx)
    sim.do(circ)
    # NOTE (2026-11-02 bugfix): v/lz/coef are anonymous scratch (create_regs
    # allocs them), so read_within_shot("v") raises IndexError. V stably sits
    # at q60..q114 (x22 + lz5 + coef33 allocated first, v never freed here);
    # reconstruct the int from per-index across-shots reads (same API as
    # prescreen_b). Circuit untouched, read path only.
    V_BASE = G.W_X + G.W_LZ + G.W_B
    fails = 0
    for i, xx in enumerate(SAMPLES):
        V, t, P = C62.model_phase(xx, B, A, R)
        gotV = 0
        for k in range(G.W_V):
            across = sim.read_across_shots(km.q(V_BASE + k))
            if bool(across[i]):
                gotV |= (1 << k)
        status = "OK" if gotV == V else "FAIL"
        if gotV != V:
            fails += 1
        print(f"x={xx:>8} Vwant={V:>15} Vgot={gotV:>15} t={t} {status}")
    print("DUMP-V " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", action="store_true")
    ap.add_argument("--b", action="store_true")
    ap.add_argument("--c", action="store_true")
    ap.add_argument("--dump-v", action="store_true")
    args = ap.parse_args()
    rc = 0
    if args.a:
        rc |= prescreen_a()
    if args.b:
        rc |= prescreen_b()
    if args.c:
        rc |= prescreen_c()
    if args.dump_v:
        rc |= dump_v()
    if not any([args.a, args.b, args.c, args.dump_v]):
        ap.print_help()
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
