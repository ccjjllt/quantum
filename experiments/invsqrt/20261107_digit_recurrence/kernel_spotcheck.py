"""Spot check: run the n=28 kernel and compare its phase to the official target.

This is a local check of the gate-level circuit, not the official verifier:
a handful of x values are simulated one at a time, the root/quotient bits are
read out, and the exact phase 2^-k * y is compared with the official integer
target and tolerance (r = isqrt(2^130 // x), target = (r+1)>>1, tol = r>>25).
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import kickmix as km

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kernels import build_recip_recurrence, build_sqrt_recurrence  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_digit_recurrence/kernels'
N = 28


def reference(x):
    r = math.isqrt((1 << 130) // x)
    return (r + 1) >> 1, r >> 25


def main():
    rng = random.Random(20261107)
    xs = [1, 2, 3, 4, 5, 15, 16, 17, 1023, 1024, 1048576,
          3133452, 3133451, 2097151, 2097152] + \
         [rng.randrange(1, 3133453) for _ in range(5)]

    b = km.CircuitBuilder()
    mreg = b.create_quantum_register(23, name='m')
    root, _, _, _ = build_sqrt_recurrence(b, N, mreg)
    c, _, _, _ = build_recip_recurrence(b, N, root)
    circ = b.finish_circuit()

    rows = []
    for x in xs:
        e = x.bit_length() - 1
        k, g = e >> 1, e & 1
        R = x << (21 - 2 * k)
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('m', 0, R)
        sim.do(circ)
        bits = [int(sim.read_within_shot(root[j], 0, out=int)) for j in range(N)]
        cbits = [int(sim.read_within_shot(c[j], 0, out=int)) for j in range(N)]
        Bint = sum(bits[j] * (1 << (N - 1 - j)) for j in range(N))
        S = 2 * Bint + 1                       # s*2^n
        Y = 1 + sum(cbits[j] * (1 << (N - j)) for j in range(1, N))  # y*2^n
        theta = Y << (64 - N - k)
        target, tol = reference(x)
        err = theta - target
        rows.append(dict(x=x, e=e, k=k, g=g, R=R, s=S, y_int=Y,
                         error_turns=err / 2**64, tol_turns=tol / 2**64,
                         error_over_tolerance=abs(err) / tol,
                         passes=abs(err) <= tol))
    bad = [r for r in rows if not r['passes']]
    doc = dict(scope='Local spot check of the n=28 gate-level kernel against the official '
                     'integer target/tolerance; not the official verifier, not all x',
               n=N, cases=len(rows), failures=len(bad), rows=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'spotcheck.json').write_text(json.dumps(doc, indent=2) + '\n')
    for r in rows:
        print(f"x={r['x']:8d} k={r['k']:2d} g={r['g']} err/tol={r['error_over_tolerance']:.6f} "
              f"{'ok' if r['passes'] else 'FAIL'}")
    print(f"{len(rows)} cases, {len(bad)} failures")
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
