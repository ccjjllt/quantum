"""Manual prescreens for narrow_v62 (NOT a test file, NOT CI).

Run manually (evidence commands, see narrow_v.md)::

    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_narrow_v.py --contract-full
    uv run python experiments/invsqrt/20261102_generator_v2/prescreen_narrow_v.py --a --b --c --dump-v

(a) double-build SHA consistency (rebuild twice, compare with recorded SHA).
(b) kickmix Simulator on 16 directed samples: x recovery + ALL scratch zero.
(c) actual shot phase vs nv_model_phase oracle (EXACTLY equal mod 2
    half-turns); plus margin>0 vs official reference_values on samples.
--dump-v: forward-prefix circuit (up to R unload) simulator dump of Vn
    vs nv_model_phase (debug aid; not part of pass criteria).
--contract-full: vectorized full-domain (3,133,452 inputs) integer check of
    nv_model_phase vs official reference_values: fails / maxrel / min_margin /
    Vn bounds / deviation bound. Gate: maxrel<1 (else STOP, record).

SHA note: REC_SHA below is the narrow-V line's own SHA. Old SHAs
(0075e006 HMR mainline Q=149; da9d9491 BOTH variant Q=149) remain valid
for their own files and are NOT superseded — they simply do not apply
to this circuit (narrow_v.md §3 作废声明：旧 SHA 对本线作废，即本线不沿用旧值）。
No official verifier 200M-shot run in this round (gate: prescreen only).
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

import narrow_v62 as NV  # noqa: E402
import width_opt62 as W  # noqa: E402

SAMPLES = [1, 2, 3, 8, 31, 32, 63, 128, 161, 888, 2047, 2048,
           2097151, 2097152, 2506015, 3133452]

REC_SHA = "e036965d725fbe195605f1306cc6435f24dabf36008703a53fbb9537a36cac8d"

X_MAX = 3_133_452


def prescreen_a() -> int:
    tables = NV.load_tables()
    c1 = NV.build_circuit_nv(tables)
    c2 = NV.build_circuit_nv(tables)
    s1, s2 = NV.circuit_sha_nv(c1), NV.circuit_sha_nv(c2)
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
    tables = NV.load_tables()
    circuit = NV.build_circuit_nv(tables)
    nq = circuit.num_qubits
    sim = _run_sim(circuit, SAMPLES)
    fails = 0
    for i, x in enumerate(SAMPLES):
        got = sim.read_within_shot("x", i, out=int)
        if got != x:
            print(f"X-RECOVERY FAIL shot={i} in={x} out={got}")
            fails += 1
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

    tables = NV.load_tables()
    B, A, R = (list(tables.B), list(tables.A), list(tables.R))
    circuit = NV.build_circuit_nv(tables)
    sim = _run_sim(circuit, SAMPLES)
    from invsqrt import verify_submission_invsqrt as official
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    xs = np.array(SAMPLES, dtype=np.uint64)
    tgt_all, tol_all = official.reference_values(spec, xs)
    tgt = np.asarray(tgt_all, dtype=np.float64) / 2**64
    tol = np.asarray(tol_all, dtype=np.float64) / 2**64
    fails = 0
    for i, x in enumerate(SAMPLES):
        _Vn, _Vd, t, P = NV.nv_model_phase(x, B, A, R)
        want = Fraction(P, 2**35) % 2
        got = sim.read_shot_phase(i)
        got = got % 2 if isinstance(got, Fraction) else Fraction(got, 1) % 2
        dphase = (got - want) % 2
        pha = float(want) / 2
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
    tables = NV.load_tables()
    B, A, R = (list(tables.B), list(tables.A), list(tables.R))
    b = km.CircuitBuilder()
    regs = NV.create_regs_nv(b)
    x, lz, coef, vn = (regs[k] for k in ("x", "lz", "coef", "vn"))
    carry = regs["carry"]
    e = b.alloc_qubits(2)
    h = b.alloc_qubits(1)
    W.build_lz_norm(b, x, lz, e, h)
    b.free(e)
    b.free(h)
    W.build_normalize(b, x, lz)
    b.isub(8192, target=x[0:W.W_DELTA])
    NV.mini_pass_off(b, x, lz, tables.B, NV.B_LO, NV.W_VN - 1, vn[0:NV.W_VN - 1])
    W.mini_pass(b, x, lz, tables.A, NV.W_A, coef[0:NV.W_A])
    NV.build_a1_nv(b, x, coef, vn, carry)
    W.mini_pass(b, x, lz, tables.A, NV.W_A, coef[0:NV.W_A])
    W.build_square2(b, x, coef)
    W.mini_pass(b, x, lz, tables.R, NV.W_R, coef[0:NV.W_R])
    NV.build_r1_nv(b, coef, vn, carry)
    W.mini_pass(b, x, lz, tables.R, NV.W_R, coef[0:NV.W_R])
    NV.merge_carry_fwd(b, vn, carry)
    circ = b.finish_circuit()
    sim = km.Simulator(batch_size=len(SAMPLES))
    sim.use_same_registers_as(circ)
    for i, xx in enumerate(SAMPLES):
        sim.write_within_shot("x", i, xx)
    sim.do(circ)
    V_BASE = NV.W_X + NV.W_LZ + NV.W_B + NV.V_LO  # vn 视图基址（vd[16:46)，x22+lz5+coef33+16）
    fails = 0
    for i, xx in enumerate(SAMPLES):
        Vn_want, _Vd, t, _P = NV.nv_model_phase(xx, B, A, R)
        gotV = 0
        for k in range(NV.W_VN):
            across = sim.read_across_shots(km.q(V_BASE + k))
            if bool(across[i]):
                gotV |= (1 << k)
        status = "OK" if gotV == Vn_want else "FAIL"
        if gotV != Vn_want:
            fails += 1
        print(f"x={xx:>8} Vnwant={Vn_want:>10} Vngot={gotV:>10} t={t} {status}")
    print("DUMP-V " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


def contract_full() -> int:
    """向量化全域整数合同（3,133,452 输入）：nv 模型 vs 官方 reference_values."""
    import numpy as np

    from invsqrt import verify_submission_invsqrt as official

    tables = NV.load_tables()
    Barr = np.array(list(tables.B), dtype=np.uint64)
    Aarr = np.array(list(tables.A), dtype=np.uint64)
    Rarr = np.array(list(tables.R), dtype=np.uint64)
    sA, sR, nR = NV.S_A, NV.S_R, NV.N_R

    xs = np.arange(1, X_MAX + 1, dtype=np.uint64)
    bl = np.floor(np.log2(xs.astype(np.float64))).astype(np.int64) + 1
    lz = 22 - bl
    m = np.left_shift(xs, lz.astype(np.uint64))
    p = lz & 1
    a = ((p.astype(np.uint64) << np.uint64(7)) | ((m >> np.uint64(14)) & np.uint64(127))).astype(np.int64)
    delta = (m & 16383).astype(np.int64)
    D = delta - 8192
    U = (delta >> 5) - 256
    S = U * U
    Bv = Barr[a]
    Av = (Aarr[a].astype(np.uint64) << sA).astype(np.int64)
    Ah = Aarr[a].astype(np.int64)
    Rh = Rarr[a].astype(np.int64)
    # 真 V（偏差统计用）
    Vtrue = (Bv << 12).astype(np.int64) - 2 * Av * D + (Rh << sR) * S
    # 窄 Vn（int64；行截短逐行对应电路）
    Vn = (Bv >> NV.B_LO).astype(np.int64)
    D14 = D & 0x3FFF
    for j in range(13):
        o = j + 1 + sA
        assert o < NV.V_LO
        Vn -= np.where(((D14 >> j) & 1) == 1, Ah >> (NV.V_LO - o), 0)
    Vn += np.where(((D14 >> 13) & 1) == 1, Ah, 0)
    for j in range(nR):
        o = j + sR
        assert o < NV.V_LO
        Vn += np.where(((Rh >> j) & 1) == 1, S >> (NV.V_LO - o), 0)
    t = 8 - ((lz >> 1) + p - 11)
    assert bool(np.all((8 <= t) & (t <= 19)))
    Vd = Vn << NV.V_LO

    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    tgt_all, tol_all = official.reference_values(spec, xs)
    tgt = np.asarray(tgt_all, dtype=np.float64) / 2**64
    tol = np.asarray(tol_all, dtype=np.float64) / 2**64

    fails, maxrel, min_margin, worst = 0, 0.0, None, None
    for tt in range(8, 20):
        mk = t == tt
        P = ((Vd[mk] + 2 ** (tt - 1)) >> tt) & (2**36 - 1)
        err = (P.astype(np.float64) / 2**36 - tgt[mk] + 0.5) % 1.0 - 0.5
        ae = np.abs(err)
        rel = ae / tol[mk]
        k = int(np.argmax(rel))
        if float(rel[k]) > maxrel:
            maxrel = float(rel[k])
            xx = int(xs[mk][k])
            worst = (xx, float(ae[k]))
        margin = (tol[mk] - ae) * 2**64
        mm = float(np.min(margin))
        min_margin = mm if min_margin is None else min(min_margin, mm)
        fails += int(np.sum(ae > tol[mk]))
    Vn_lo, Vn_hi = int(np.min(Vn)), int(np.max(Vn))
    n_bad = int(np.sum((Vn < 0) | (Vn >= 2**29)))
    dev = Vn - (Vtrue >> NV.V_LO)
    print(f"checked={X_MAX} fails={fails} maxrel={maxrel:.10f} worst={worst} "
          f"min_margin_units={min_margin:.1f}")
    print(f"Vn_range=({Vn_lo},{Vn_hi}) out_of_[0,2^29)={n_bad} "
          f"max|Vn-(Vtrue>>16)|={int(np.max(np.abs(dev)))}")
    ok = (fails == 0) and (maxrel < 1) and (n_bad == 0)
    print("CONTRACT-FULL " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", action="store_true")
    ap.add_argument("--b", action="store_true")
    ap.add_argument("--c", action="store_true")
    ap.add_argument("--dump-v", action="store_true")
    ap.add_argument("--contract-full", action="store_true")
    args = ap.parse_args()
    rc = 0
    if args.contract_full:
        rc |= contract_full()
    if args.a:
        rc |= prescreen_a()
    if args.b:
        rc |= prescreen_b()
    if args.c:
        rc |= prescreen_c()
    if args.dump_v:
        rc |= dump_v()
    if not any([args.a, args.b, args.c, args.dump_v, args.contract_full]):
        ap.print_help()
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
