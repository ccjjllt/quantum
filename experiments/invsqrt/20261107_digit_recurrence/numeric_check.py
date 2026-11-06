"""Full-domain integer check of a non-restoring digit-recurrence invsqrt.

Architecture modelled here (radix 2):
  x(22 bits) -> e = floor(log2 x), k = e//2, g = e&1
             -> R = x << (21 - 2k) in [2^21, 2^23),  m = R / 2^21 in [1,4)
  sqrt recurrence (n non-restoring digits, digit = sign of residual):
        W_0 = m - 1
        d_i = +1 if W_{i-1} >= 0 else -1
        W_i = 2 W_{i-1} - d_i (2 s_{i-1}) - 2^-i,   s_i = 1 + sum_{j<=i} d_j 2^-j
  conversion (exact, no adder):  s = 2B + 2^-n,  B = sum b_j 2^-j, b_j=(d_j+1)/2
  reciprocal recurrence on s:
        r_0 = 1,  q_i = sign(r_{i-1}),  r_i = 2 r_{i-1} - q_i s
  conversion:  y = 2C - 1 + 2^-n = sum_{j=2..n} c_j 2^-j + 2^-n   (c_1 == 1)
  phase applied by fixed-angle Z_POWs on the aligned bits of y:
        phase = 2^-k y = Y / 2^(n+k),  Y = (bits c_2..c_n as integer) + 1

Everything is exact integer arithmetic at the register scale the circuit uses
(F fractional bits).  The check compares against the official verifier's
integer target / tolerance (copied formula: r = isqrt(2^130 // x),
target = (r+1)>>1, tol = r>>25, units of 2^-64 turns).  The competition
verifier module is not imported (it would load the Kaggle kickmix.so).

This script says nothing about gate costs or scratch restoration; it only
decides whether the digit recurrence, as specified, meets the numerical
contract on all 3,133,452 inputs.
"""
from __future__ import annotations

import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_digit_recurrence/numeric'
MAX_X = 3 * (2**10 - 2) ** 2          # 3,133,452
MASK64 = (1 << 64) - 1
PRECISION_BITS = 24


def reference_values(xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Official integer target and tolerance (beta=1), units of 2^-64 turns."""
    num = 1 << 130
    rs = [math.isqrt(num // int(x)) for x in xs]
    target = np.array([((r + 1) >> 1) & MASK64 for r in rs], dtype=np.uint64)
    tol = np.array([r >> (PRECISION_BITS + 1) for r in rs], dtype=np.uint64)
    return target, tol


def sqrt_digits(xs: np.ndarray, n: int):
    """Exact non-restoring sqrt recurrence; returns k, digit bits b (n, Nx), and |W| max."""
    N = xs.shape[0]
    x = xs.astype(np.int64)

    # e = floor(log2 x), k = e//2, g = e&1
    e = np.zeros(N, dtype=np.int64)
    for bit in range(21, -1, -1):
        e += (x >= (np.int64(1) << bit)).astype(np.int64)
    e -= 1                                    # x >= 1 so e >= 0
    k = e >> 1
    g = e & 1
    assert np.all(x >= (np.int64(1) << e)) and np.all(x < (np.int64(1) << (e + 1)))

    R = x << (21 - 2 * k)                     # in [2^21, 2^23); m = R / 2^21
    assert np.all(R >= (1 << 21)) and np.all(R < (1 << 23))

    F = n + 2                                 # fractional bits of the W register
    w = (R - (1 << 21)) << (F - 21)           # W_0 = m-1, units of 2^-F
    two_s = np.full(N, 2 << F, dtype=np.int64)   # 2*s_0, units of 2^-F
    b = np.zeros((n, N), dtype=np.uint8)
    wmax = 0
    for i in range(1, n + 1):
        d = np.where(w >= 0, np.int64(1), np.int64(-1))
        b[i - 1] = (d > 0)
        w = 2 * w - d * two_s - (np.int64(1) << (F - i))
        # 2*s_i = 2*s_{i-1} + 2*d_i*2^-i
        two_s = two_s + (d << (F + 1 - i))
        wmax = max(wmax, int(np.abs(w).max()))
    # |W_i| < 4 must hold for an I=2 integer part
    assert wmax < (1 << (F + 2)) + (1 << F), (wmax, F)

    # s = 2B + 2^-n  ->  S_int = s*2^n = 2*Bint + 1
    Bint = np.zeros(N, dtype=np.int64)
    for j in range(1, n + 1):
        Bint += b[j - 1].astype(np.int64) << (n - j)
    S_int = 2 * Bint + 1
    assert np.all(S_int >= (1 << n)) and np.all(S_int <= (2 << n))
    return k, g, e, b, S_int, wmax


def reciprocal_digits(S_int: np.ndarray, n: int, truncate: bool = False):
    """Exact non-restoring division y = 1/s; returns quotient bits c (n, Nx) and |r| max.

    With `truncate=True`, step i uses s truncated below 2^-(n-i) (the bits that
    can no longer influence a future digit decision).  This is the optimistic
    narrow-divisor variant; it must still meet the tolerance to be usable.
    """
    N = S_int.shape[0]
    F = n + 2
    r = np.full(N, 1 << F, dtype=np.int64)        # r_0 = 1
    c = np.zeros((n, N), dtype=np.uint8)
    s_scaled = S_int << (F - n)                   # s in units of 2^-F
    rmax = 0
    for i in range(1, n + 1):
        q = np.where(r >= 0, np.int64(1), np.int64(-1))
        c[i - 1] = (q > 0)
        s_used = s_scaled
        if truncate and i > 1:
            # drop bits below weight 2^-(n-i): in units of 2^-F that is (F-(n-i)) low bits
            keep = F - (n - i)
            s_used = (s_scaled >> keep) << keep
        r = 2 * r - q * s_used
        rmax = max(rmax, int(np.abs(r).max()))
    assert np.all(c[0] == 1), 'leading quotient bit must be 1'
    return c, rmax, bool(rmax < (1 << (F + 2)))


def phase_and_check(xs: np.ndarray, n: int, truncate: bool = False):
    k, g, e, b, S_int, wmax = sqrt_digits(xs, n)
    c, rmax, residual_bound_ok = reciprocal_digits(S_int, n, truncate=truncate)

    # y = 2C-1+2^-n = sum_{j=2..n} c_j 2^(1-j) + 2^-n
    # -> Y = y*2^n = sum_{j=2..n} c_j 2^(n+1-j) + 1
    Y = np.ones(xs.shape[0], dtype=np.int64)
    for j in range(2, n + 1):
        Y += c[j - 1].astype(np.int64) << (n + 1 - j)
    assert np.all(Y >= (1 << (n - 1))) and np.all(Y < (1 << n))

    # phase = 2^-k * Y / 2^n, exact in units of 2^-64 turns when n+k <= 64
    shift = 64 - n - k
    assert np.all(shift >= 0)
    theta = (Y << shift).astype(np.uint64)
    target, tol = reference_values(xs)
    err = (theta - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    bad = used > tol
    ratio = np.divide(used, tol, out=np.zeros(xs.shape[0]), where=tol > 0)
    margin = (tol.astype(np.int64) - used.astype(np.int64))
    worst = int(np.argmax(ratio))
    return dict(
        n=n, F=n + 2,
        max_abs_W=wmax, max_abs_r=rmax, residual_bound_ok=residual_bound_ok,
        tolerance_failures=int(bad.sum()),
        worst_error_over_tolerance=float(ratio[worst]),
        worst_x=int(xs[worst]),
        min_margin_units=int(margin.min()),
        min_margin_turns=float(margin.min() / 2**64),
        max_error_turns=float(np.abs(err).max() / 2**64),
        theta_width_bits=int(max(1, int(theta.max()).bit_length())),
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xs = np.arange(1, MAX_X + 1, dtype=np.uint64)
    doc = dict(
        scope=('Exact integer model of the radix-2 non-restoring digit-recurrence '
               'invsqrt on all inputs; official integer target/tolerance; '
               'no gate costs, no candidate circuit, no verifier run'),
        python=platform.python_version(), max_x=MAX_X,
        inputs=int(xs.shape[0]), results=[],
    )
    t0 = time.time()
    for n in (24, 25, 26, 27, 28, 29, 30):
        r = phase_and_check(xs, n)
        doc['results'].append(r)
        print(json.dumps(r), flush=True)
    # Optimistic narrow-divisor variant: the reciprocal uses only the bits of s
    # that can still influence future digits (the counted kernel in kernels.py
    # uses the full width; this variant is a lower bound on any truncating design).
    doc['optimistic_truncated_divisor'] = []
    for n in (26, 27, 28):
        r = phase_and_check(xs, n, truncate=True)
        doc['optimistic_truncated_divisor'].append(r)
        print('trunc', json.dumps(r), flush=True)
    doc['wall_seconds'] = round(time.time() - t0, 2)
    (OUT / 'numeric_check.json').write_text(json.dumps(doc, indent=2) + '\n')

    r28 = next(r for r in doc['results'] if r['n'] == 28)
    passing = [r['n'] for r in doc['results'] if r['tolerance_failures'] == 0]
    print(f"\ndone in {doc['wall_seconds']} s; passing n = {passing}; "
          f"n=28 worst error/tolerance {r28['worst_error_over_tolerance']:.6f}, "
          f"failures {r28['tolerance_failures']}; "
          f"truncated-divisor variant residual bound ok: "
          f"{[r['residual_bound_ok'] for r in doc['optimistic_truncated_divisor']]}")
    return 0 if r28['tolerance_failures'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
