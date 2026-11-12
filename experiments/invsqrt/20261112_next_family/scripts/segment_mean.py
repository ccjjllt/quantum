"""Per-segment mean Toffoli cost of an invsqrt circuit (prefix-simulation differencing).

For a list of op cuts, simulate the circuit prefix ending at each cut on a fixed
sample of x (default: all x <= 6000 plus random samples above) with 1 shot/x and
read `num_toffoli_like`.  Differences between consecutive cuts give the mean cost
of each segment.  Conditional (branch) gates are executed per shot, so this is the
same expectation the official verifier averages over 64 shots/x.

Usage:
    uv run python segment_mean.py CIRCUIT.kmb CUT1,CUT2,... [--n-sample N] [--dense-max X]
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import numpy as np


def to_bit_matrix(xs: np.ndarray, width: int) -> np.ndarray:
    return ((xs[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1) == 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", type=Path)
    ap.add_argument("cuts", type=str, help="comma separated op indices, ascending")
    ap.add_argument("--n-sample", type=int, default=6000)
    ap.add_argument("--dense-max", type=int, default=20000)
    ap.add_argument("--width", type=int, default=22)
    ap.add_argument("--seed", type=int, default=20261112)
    args = ap.parse_args()

    import kickmix as km

    circuit = km.Circuit.from_file(str(args.circuit), format="auto")
    ops = km.Circuit.from_file(str(args.circuit), format="auto")
    # Truncate through the kmx text form (kickmix exposes slicing via kmx editing).
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()

    # Map flat op index -> line index (APPEND/REGISTER/PUSH/POP are structural).
    flat = []
    for i, line in enumerate(lines):
        head = line.split()[0] if line else ""
        if head in ("APPEND_TO_REGISTER", "REGISTER"):
            continue
        flat.append(i)
    assert len(flat) == len(circuit), (len(flat), len(circuit))

    max_x = 3 * (2**10 - 2) ** 2
    rng = np.random.default_rng(args.seed)
    dense = np.arange(1, min(args.dense_max, max_x) + 1, dtype=np.uint64)
    extra = rng.integers(dense[-1] + 1, max_x + 1, size=args.n_sample, dtype=np.uint64)
    xs = np.unique(np.concatenate([dense, extra]))
    width = args.width
    x_reg = km.array([km.q(i) for i in range(width)])
    bits = to_bit_matrix(xs, width)

    cuts = [int(c) for c in args.cuts.split(",") if c.strip()]
    prev = 0
    prev_toff = 0.0
    print(f"sample: {len(xs)} x ({len(dense)} dense + {len(extra)} random), 1 shot/x")
    print(f"{'cut':>7} {'CCX':>5} {'CCZ':>4} {'CSWAP':>5} {'static':>6} "
          f"{'mean_toff':>10} {'seg_mean':>9}")
    for cut in cuts:
        n_lines = flat[cut - 1] + 1
        text = "\n".join(lines[:n_lines]) + "\n"
        sub = km.Circuit.from_file(io.StringIO(text), format="kmx")
        tot = 0
        nshots = 0
        for start in range(0, len(xs), 256):
            chunk = xs[start:start + 256]
            sim = km.Simulator(batch_size=len(chunk), debug_print=False,
                               counting_operations=True, seed=args.seed + start)
            sim.clear_for_shot()
            sim.write_across_shots(x_reg, bits[:, start:start + 256])
            sim.do(sub)
            tot += int(sim.operation_statistics().num_toffoli_like)
            nshots += len(chunk)
        mean = tot / nshots
        static = {"CCX": 0, "CCZ": 0, "CSWAP": 0}
        buf2 = io.StringIO()
        sub.to_file(buf2, format="kmx")
        for line in buf2.getvalue().splitlines():
            k = line.split()[0] if line else ""
            if k in static:
                static[k] += 1
        print(f"{cut:7d} {static['CCX']:5d} {static['CCZ']:4d} {static['CSWAP']:5d} "
              f"{sum(static.values()):6d} {mean:10.4f} {mean - prev_toff:9.4f}")
        prev = cut
        prev_toff = mean


if __name__ == "__main__":
    main()
