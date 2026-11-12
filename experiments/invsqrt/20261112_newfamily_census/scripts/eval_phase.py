"""Exact per-x phase evaluation of an invsqrt circuit (1 shot per x).

The 9c708f7b lineage is a classical reversible phase oracle: all qubits are in
computational basis states and the tracked global phase is deterministic in x
(measurement outcomes only drive exact corrections).  One shot per x therefore
reproduces the official error function, which lets us tabulate all 3,133,452
inputs in seconds instead of 64 shots each.

Outputs an .npz with x, error (2^-64 turns), tol (2^-64 turns) and ratio.
"""

from __future__ import annotations

import argparse
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

T_PER_TOFFOLI = 4
BETA = Fraction(1)
WIDTH = 22
DEFAULT_MAX_X = 3 * (2**10 - 2) ** 2
MASK64 = (1 << 64) - 1


def reference_values(xs: np.ndarray, precision_bits: int = 24) -> tuple[np.ndarray, np.ndarray]:
    p, q = BETA.numerator, BETA.denominator
    num, den, shift = p * p << 130, q * q, precision_bits + 1
    rs = [math.isqrt(num // (den * int(x))) for x in xs]
    target = np.array([((r + 1) >> 1) & MASK64 for r in rs], dtype=np.uint64)
    tol = np.array([min(r >> shift, 1 << 63) for r in rs], dtype=np.uint64)
    return target, tol


def half_turns_to_units(v: Fraction | int) -> int:
    n, d = Fraction(v).as_integer_ratio()
    return (((n << 64) // d + 1) >> 1) & MASK64


def count_rotations(circuit) -> tuple[int, int]:
    """(rotations, t-like) over Z_POW exponent classes, per the official rule."""
    rotations = tlike = 0
    for op in circuit_ops(circuit):
        if op[0] != "Z_POW":
            continue
        e = Fraction(op[1])
        if e % Fraction(1, 2) == 0:
            continue
        if e % Fraction(1, 4) == 0:
            tlike += 1
            continue
        rotations += 1
    return rotations, tlike


def circuit_ops(circuit) -> list[tuple[str, str]]:
    import io

    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    out = []
    for line in buf.getvalue().splitlines():
        p = line.split()
        if not p or p[0] in ("APPEND_TO_REGISTER", "REGISTER", "PUSH_CONDITION", "POP_CONDITION"):
            continue
        if p[0] == "Z_POW":
            out.append(("Z_POW", p[2]))
    return out


def evaluate(path: Path, xs: np.ndarray, seed: int, shots_per_x: int = 1,
             batch_size: int = 256) -> dict:
    import kickmix as km

    circuit = km.Circuit.from_file(str(path), format="auto")
    x_reg = km.array([km.q(i) for i in range(WIDTH)])
    scratch = km.array([km.q(i) for i in range(WIDTH, circuit.num_qubits)])
    target, tol = reference_values(xs)
    phases = np.zeros(len(xs), dtype=np.uint64)
    toff = 0
    tlike = 0
    zpow = 0
    nshots = 0
    dirty = 0

    for start in range(0, len(xs), batch_size):
        chunk = xs[start:start + batch_size]
        n = len(chunk)
        sim = km.Simulator(batch_size=n, debug_print=False, counting_operations=True,
                           seed=seed + start)
        for _ in range(shots_per_x):
            sim.clear_for_shot()
            bits = ((chunk[None, :] >> np.arange(WIDTH, dtype=np.uint64)[:, None]) & 1) == 1
            sim.write_across_shots(x_reg, bits)
            sim.do(circuit)
            for i in range(n):
                phases[start + i] = half_turns_to_units(sim.read_shot_phase(i))
            if len(scratch):
                dirty += int(np.count_nonzero(sim.read_across_shots(scratch).any(axis=1)))
            stats = sim.operation_statistics()
            toff += int(stats.num_toffoli_like)
            tlike += int(stats.num_t_like)
            zpow += int(stats.num_z_pow(min_clifford_hierarchy_level=4))
            nshots += n

    err = (phases - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    ratio = used.astype(np.float64) / tol.astype(np.float64)
    return dict(xs=xs, err=err, tol=tol, ratio=ratio, toffoli=toff, tlike=tlike,
                zpow=zpow, nshots=nshots, dirty=dirty)


def score_from(min_margin: float, n_rot: float, toffoli: float, t_base: float) -> tuple[float, float]:
    eps = math.pi * min_margin / 2**64 / n_rot if n_rot else 0.0
    t_count = t_base + (n_rot * (0.56 * math.log2(1 / eps) + 5.3) if n_rot else 0.0)
    c = toffoli + t_count / T_PER_TOFFOLI
    return c * 62, eps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", type=Path)
    ap.add_argument("--max-x", type=int, default=DEFAULT_MAX_X)
    ap.add_argument("--min-x", type=int, default=1)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--shots-per-x", type=int, default=1)
    ap.add_argument("--stride", type=int, default=1, help="Take every STRIDE-th x above --dense-max.")
    ap.add_argument("--dense-max", type=int, default=0, help="Evaluate every x up to this value.")
    ap.add_argument("--sample", type=int, default=0, help="Plus N uniformly random x above --dense-max.")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if args.dense_max and args.sample:
        dense = np.arange(args.min_x, min(args.dense_max, args.max_x) + 1, dtype=np.uint64)
        rng = np.random.default_rng(20261112)
        extra = rng.integers(dense[-1] + 1, args.max_x + 1, size=args.sample, dtype=np.uint64)
        xs = np.unique(np.concatenate([dense, extra]))
    elif args.dense_max and args.stride > 1:
        dense = np.arange(args.min_x, min(args.dense_max, args.max_x) + 1, dtype=np.uint64)
        sparse = np.arange(dense[-1] + args.stride, args.max_x + 1, dtype=np.uint64, step=args.stride)
        xs = np.concatenate([dense, sparse])
    else:
        xs = np.arange(args.min_x, args.max_x + 1, dtype=np.uint64, step=args.stride)
    res = evaluate(args.circuit, xs, args.seed, args.shots_per_x)
    used = np.abs(res["err"]).view(np.uint64)
    margin = res["tol"].astype(np.int64) - used.astype(np.int64)
    imin = int(np.argmin(margin))
    imax = int(np.argmax(res["ratio"]))
    n_rot, n_t = count_rotations(__import__("kickmix").Circuit.from_file(str(args.circuit)))
    toff_mean = res["toffoli"] / res["nshots"]
    t_base = res["tlike"] / res["nshots"]
    if args.out:
        np.savez(args.out, xs=res["xs"], err=res["err"], tol=res["tol"], ratio=res["ratio"],
                 dirty=res["dirty"])
    if margin[imin] <= 0:
        print(f"x=[{args.min_x},{args.max_x}] shots/x={args.shots_per_x} seed={args.seed}")
        print(f"  rotations={n_rot} t_like={n_t} toffoli_mean={toff_mean:.4f} t_base={t_base:.4f}")
        print(f"  FAIL: min margin={int(margin[imin])} units @x={int(xs[imin])}")
        print(f"  worst ratio={res['ratio'][imax]:.10f} @x={int(xs[imax])}")
        print(f"  dirty-scratch shots: {res['dirty']}")
        if args.out:
            print(f"  saved {args.out}")
        return
    sc, eps = score_from(float(margin[imin]), n_rot, toff_mean, t_base)
    print(f"x=[{args.min_x},{args.max_x}] shots/x={args.shots_per_x} seed={args.seed}")
    print(f"  rotations={n_rot} t_like={n_t} toffoli_mean={toff_mean:.4f} t_base={t_base:.4f}")
    print(f"  worst ratio={res['ratio'][imax]:.10f} @x={int(xs[imax])}  (err={res['err'][imax]} units, tol={res['tol'][imax]})")
    print(f"  min margin={int(margin[imin])} units @x={int(xs[imin])}  -> eps={eps:.9e}")
    print(f"  dirty-scratch shots: {res['dirty']}")
    print(f"  score={sc:.6f}  C={sc/62:.6f}")
    if args.out:
        print(f"  saved {args.out}")


if __name__ == "__main__":
    main()
