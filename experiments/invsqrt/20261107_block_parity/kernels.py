"""Counted cost of the block-parity gadgets, with the official CircuitBuilder.

Everything here is measured on real kickmix circuits via
`Circuit.operation_statistics()`; nothing is estimated from a formula.

1. block indicator  : I_h = AND of the 22-b high bits (X-flips for zero
                      controls), computed and then uncomputed.  Three ways:
                        (a) builder.multi_controlled_x (auto AND ladder, the
                            ladder is uncomputed with HMR = free),
                        (b) manual init_and ladder + del_and chain,
                        (c) builder.unary_iteration (the QROM-style selector).
2. double-controlled rotation : rotation conditioned on (block indicator,
                      local parity).  z_pow has no control argument, so the
                      term is ccx(a, p, t); z_pow(t); del_and(a, p, t).
                      Measured paid cost and rotation count.
3. full exact block-parity phase machine on a small domain (max_x = 16,
                      block size 4): every block is interpolated exactly, so
                      the circuit is correct by construction and can be run
                      through the official verifier.  This validates the
                      half-turn sign convention, the constant term, x
                      restoration, scratch cleanup and the cost formula.

Output: artifacts/20261107_block_parity/kernels.json (+ printed log).
"""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261107_block_parity"
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt.verify_submission_invsqrt import (  # noqa: E402
    ProblemSpecInvSqrt, reference_values, verify)

WIDTH = 22


def stats(circ: km.Circuit) -> dict:
    s = circ.operation_statistics()
    sd = dict(s)
    return {
        "qubits": int(circ.num_qubits),
        "instructions": int(len(circ)),
        "toffoli_like": int(s.num_toffoli_like),
        "t_like": int(s.num_t_like),
        "rotations": int(s.num_z_pow(min_clifford_hierarchy_level=4)),
        "cx": int(sd.get("CX", 0)),
        "hmr": int(sd.get("HMR", 0)),
        "ccx": int(sd.get("CCX", 0)),
    }


def make_x(b, nbits=WIDTH):
    b.set_max_qubits(64)
    return b.create_quantum_register(nbits, name="x")


def pattern_flips(b, x, h, m, b_):
    """X-flip every high bit that must be 0 for block h (all flips free)."""
    hi = [x[q] for q in range(b_, b_ + m)]
    zero = [q for j, q in enumerate(hi) if not (h >> j) & 1]
    for q in zero:
        b.x(q)
    return hi, zero



def and_ladder(b, hi, ladder):
    """r_1 = hi0 hi1, r_2 = r_1 hi2, ... ; returns the top rung."""
    prev = hi[0]
    for j in range(1, len(hi) - 1):
        b.init_and(prev, hi[j], ladder[j - 1])
        prev = ladder[j - 1]
    return prev


def and_ladder_inv(b, hi, ladder):
    """Reverse-order measurement-based uncompute of `and_ladder`."""
    m = len(hi)
    for j in range(m - 2, 0, -1):
        c1 = ladder[j - 2] if j >= 2 else hi[0]
        b.del_and(c1, hi[j], ladder[j - 1])


def indicator_mcx(m: int, b_: int | None = None) -> dict:
    """Block indicator via builder.multi_controlled_x (compute + free uncompute)."""
    b_ = WIDTH - m if b_ is None else b_
    b = km.CircuitBuilder()
    x = make_x(b)
    a = b.alloc_qubits(1)
    hi, zero = pattern_flips(b, x, 1, m, b_)
    b.multi_controlled_x(hi, a[0])
    for q in zero:
        b.x(q)
    return stats(b.finish_circuit())


def indicator_manual(m: int, b_: int | None = None) -> dict:
    """Block indicator by an explicit init_and ladder + del_and chain."""
    b_ = WIDTH - m if b_ is None else b_
    b = km.CircuitBuilder()
    x = make_x(b)
    a = b.alloc_qubits(1)
    hi, zero = pattern_flips(b, x, 1, m, b_)
    ladder = b.alloc_qubits(max(1, m - 2))
    top = and_ladder(b, hi, ladder)
    b.ccx(top, hi[m - 1], a[0])
    # measurement-based uncompute: outer AND first, then the ladder top-down
    b.del_and(top, hi[m - 1], a[0])
    and_ladder_inv(b, hi, ladder)
    for q in zero:
        b.x(q)
    b.free(ladder)
    return stats(b.finish_circuit())


def rotation_double_controlled(n: int = 1) -> dict:
    """n terms of  ccx(a,p,t); z_pow(t); del_and(a,p,t)  (one ancilla reused)."""
    b = km.CircuitBuilder()
    x = make_x(b)
    a = b.alloc_qubits(1)
    p = b.alloc_qubits(1)
    t = b.alloc_qubits(1)
    b.ccx(x[0], x[1], a[0])          # a = block indicator placeholder
    b.cx(x[2], p[0])                 # p = local parity placeholder
    for _ in range(n):
        b.ccx(a[0], p[0], t[0])
        b.z_pow(t[0], -4 * 1.234e-3)
        b.del_and(a[0], p[0], t[0])
    b.cx(x[2], p[0])
    b.del_and(x[0], x[1], a[0])
    return stats(b.finish_circuit())


def selection_unary_iteration(entries: int, with_term: bool = True) -> dict:
    """Cost of walking an `entries`-way block selector (QROM-style unary walk)."""
    b = km.CircuitBuilder()
    x = make_x(b)
    addr = km.array([x[q] for q in range(10)])
    t = b.alloc_qubits(1)
    with b.unary_iteration(addr, range(entries)) as it:
        for v, mq in it:
            if with_term:
                b.ccx(mq, x[12], t[0])
                b.z_pow(t[0], -4 * 1e-3)
                b.del_and(mq, x[12], t[0])
    return stats(b.finish_circuit())


def build_block_parity(maxx: int, bbits: int, coeffs: dict[int, dict[int, float]]) -> km.Circuit:
    """p(x) = sum_h I_h * f_h(L) with f_h the exact local parity expansion.

    Phase convention (verified by the official verifier below):
      * S = empty: a single rotation on the block indicator `a` gives
        (h/2)*[a=1] = c turns in the active block, so exponent 2c.  Cheap:
        1 rotation, no CCX.
      * S != empty: t = a AND chi_S needs one CCX; Z_POW(t, -4c) contributes
        -c + c*chi_S in the active block, so the -c parts are absorbed into the
        same block-constant rotation as the S = empty coefficient.  One more
        rotation per term and 1 CCX.
    Hence exactly K rotations (K = number of nonzero c_{h,S}) and, with the
    per-block indicator ladder, B*(m-1) + #(S != empty) CCX.
    """
    b = km.CircuitBuilder()
    x = make_x(b)
    m = WIDTH - bbits
    a = b.alloc_qubits(1)
    p = b.alloc_qubits(1)
    t = b.alloc_qubits(1)
    ladder = b.alloc_qubits(max(1, m - 2))
    hi = [x[q] for q in range(bbits, WIDTH)]
    for h, terms in coeffs.items():
        zero = []
        for j, q in enumerate(hi):
            if not (h >> j) & 1:
                b.x(q)
                zero.append(q)
        top = and_ladder(b, hi, ladder)
        b.ccx(top, hi[m - 1], a[0])
        nz = {S: c for S, c in terms.items() if S != 0}
        c0 = terms.get(0, 0.0) + sum(nz.values())
        if abs(c0) > 0:
            b.z_pow(a[0], 2 * c0)
        for S, c in sorted(nz.items()):
            bits = [x[j] for j in range(bbits) if (S >> j) & 1]
            for q in bits:
                b.cx(q, p[0])
            b.ccx(a[0], p[0], t[0])
            b.z_pow(t[0], -4 * c)
            b.del_and(a[0], p[0], t[0])
            for q in reversed(bits):
                b.cx(q, p[0])
        b.del_and(top, hi[m - 1], a[0])
        and_ladder_inv(b, hi, ladder)
        for q in zero:
            b.x(q)
    b.free(ladder)
    return b.finish_circuit()


def exact_block_coeffs(maxx: int, bbits: int) -> tuple[dict, float]:
    """Exact per-block interpolation of the official target on [1, maxx]."""
    nb = 1 << bbits
    tgt, tol = reference_values(
        ProblemSpecInvSqrt(width=WIDTH, max_x=maxx, beta=Fraction(1),
                           precision_bits=24, shots_per_x=1, system_qubits=0),
        np.arange(1, maxx + 1, dtype=np.uint64))
    g = tgt.astype(np.float64) / 2.0**64
    g[0] = 0.0                       # x = 1 -> 1 turn == 0
    coeffs: dict[int, dict[int, float]] = {}
    for h in range((maxx >> bbits) + 1):
        lo, hi = h * nb, min((h + 1) * nb, maxx + 1)
        xs = np.arange(max(lo, 1), hi)          # x = 0 is not part of the domain
        if xs.size == 0:
            continue
        vals = g[xs - 1]
        off = xs - lo
        if xs.size == nb:
            c = np.array([np.sum(vals * ((-1.0) ** np.bitwise_count(
                S & np.arange(nb)))) / nb for S in range(nb)])
        else:
            # exact interpolation on the legal points (min-norm solution)
            Amat = np.array([[(-1.0) ** int(np.bitwise_count(
                S & int(o))) for S in range(nb)] for o in off])
            c = np.linalg.pinv(Amat) @ vals
        coeffs[h] = {S: float(c[S]) for S in range(nb) if abs(c[S]) > 1e-18}
    return coeffs, 0.0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res: dict = {"width": WIDTH}

    print("1. block indicator, I_h = AND of m high bits (compute + uncompute)")
    ind = {}
    for m in (8, 9, 10, 11, 12, 14, 16, 18, 20):
        r1 = indicator_mcx(m)
        r2 = indicator_manual(m)
        ind[m] = {"mcx": r1, "manual": r2,
                  "predicted_m_minus_1": m - 1}
        print(f"  m={m:2d}: multi_controlled_x paid={r1['toffoli_like']:3d} "
              f"(m-2={m-2}) Q={r1['qubits']:2d} CCX={r1['ccx']:3d} | "
              f"manual paid={r2['toffoli_like']:3d} Q={r2['qubits']:2d} "
              f"hmr={r2['hmr']:2d} rot={r2['rotations']}")
    res["indicator"] = {str(k): v for k, v in ind.items()}

    print("\n2. double-controlled rotation: ccx(a,p,t); z_pow(t); del_and(a,p,t)")
    r = rotation_double_controlled(1)
    r8 = rotation_double_controlled(8)
    print(f"  n=1: paid={r['toffoli_like']} rot={r['rotations']} "
          f"cx={r['cx']} hmr={r['hmr']} Q={r['qubits']}")
    print(f"  n=8: paid={r8['toffoli_like']} rot={r8['rotations']} "
          f"cx={r8['cx']} hmr={r8['hmr']}")
    print(f"  => marginal paid per term = "
          f"{(r8['toffoli_like']-r['toffoli_like'])/7:.3f}, "
          f"marginal rotations = {(r8['rotations']-r['rotations'])/7:.3f}")
    res["rotation2"] = {"n1": r, "n8": r8,
                        "marginal_paid": (r8["toffoli_like"] - r["toffoli_like"]) / 7}

    print("\n3. unary-iteration selector (alternative block selector)")
    ui = {}
    for entries in (16, 64, 256, 1024):
        sa = selection_unary_iteration(entries, with_term=False)
        sb = selection_unary_iteration(entries, with_term=True)
        ui[entries] = {"walk_only": sa, "with_term": sb,
                       "walk_per_entry": sa["toffoli_like"] / entries,
                       "term_per_entry": (sb["toffoli_like"] - sa["toffoli_like"]) / entries}
        print(f"  entries={entries:4d}: walk {sa['toffoli_like']:5d} "
              f"({sa['toffoli_like']/entries:.3f}/entry), with one term per "
              f"entry {sb['toffoli_like']:5d} "
              f"(+{(sb['toffoli_like']-sa['toffoli_like'])/entries:.3f}/term) "
              f"Q={sa['qubits']}")
    res["unary_iteration"] = {str(k): v for k, v in ui.items()}

    print("\n4. exact block-parity phase machine, max_x=16, block size 4")
    maxx, bb = 16, 2
    coeffs, _ = exact_block_coeffs(maxx, bb)
    circ = build_block_parity(maxx, bb, coeffs)
    s = stats(circ)
    K = sum(len(v) for v in coeffs.values())
    Bb = len(coeffs)
    print(f"  blocks={Bb} terms K={K} : counted {s}")
    circ.to_file(OUT / "block_parity_exact_x16.kmb", format="kmb")
    spec = ProblemSpecInvSqrt(width=WIDTH, max_x=maxx, beta=Fraction(1),
                              precision_bits=24, shots_per_x=8, system_qubits=0)
    out = verify(circ, spec, seed=20261107, batch_size=8)
    print("  official verifier:", json.dumps(
        {k: out[k] for k in ("status", "score", "toffoli_equivalent",
                             "toffoli_count", "t_count", "rotation_count",
                             "rotation_eps", "worst_error_over_tolerance",
                             "worst_x", "num_qubits", "num_ops")}, indent=2))
    m_ = WIDTH - bb
    nz = sum(1 for v in coeffs.values() for S in v if S != 0)
    predicted_paid = Bb * (m_ - 1) + nz
    print(f"  predicted paid = B(m-1)+#(S!=0) = {Bb}*{m_-1}+{nz} = "
          f"{predicted_paid}; counted {s['toffoli_like']}")
    print(f"  predicted rotations = K = {K}; counted generic {s['rotations']} "
          f"+ t_like {s['t_like']}")
    res["exact_x16"] = {"blocks": Bb, "K": K, "nz": nz, "counted": s,
                        "verifier": {k: out[k] for k in
                                     ("status", "score", "toffoli_equivalent",
                                      "toffoli_count", "t_count", "rotation_count",
                                      "rotation_eps", "worst_error_over_tolerance",
                                      "worst_x", "num_qubits", "num_ops")},
                        "predicted_paid": predicted_paid,
                        "predicted_rotations": K,
                        "m": WIDTH - bb}

    print("\n5. Q of the real b=12 shape (10 high-bit controls, 3 blocks)")
    coeffs2 = {0: {0: 1e-3, 1: 2e-4}, 1: {0: 5e-4}, 2: {0: 1e-4, 3: 1e-4}}
    c3 = build_block_parity(1 << 20, 12, coeffs2)
    s3 = stats(c3)
    print(f"  Q = {s3['qubits']}  instructions {s3['instructions']}")
    res["b12_shape_Q"] = s3

    (OUT / "kernels.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT/'kernels.json'}")


if __name__ == "__main__":
    main()
