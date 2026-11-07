"""Full-domain integer check of the hyperbolic-CORDIC reciprocal square root.

Algorithm modelled here (all exact integer fixed point, scale 1/4 so every
working register needs one sign bit):

  x (22 bits) -> e = floor(log2 x), k = e//2
              -> M = m * 2^G,  m = x / 4^k in [1,4)
  prep:  b0 = (M - 2^G) >> 2          # (m-1)/4
         a0 = b0 + 2^(G-2)            # (m+1)/4
         p0 = round(2^(G-2) / K), q0 = 0

  CORDIC step i with sigma = -sign(b):
         a <- a + sigma*(b >> i)
         b <- b + sigma*(a_old >> i)
         p <- p + sigma*(q >> i)
         q <- q + sigma*(p_old >> i)

  Two subsystems share the *same* sigma sequence.  Because every step is the
  matrix [[1, sigma 2^-i],[sigma 2^-i, 1]] = sqrt(1-4^-i) * R(phi_i),
  phi_i = sigma*atanh(2^-i), both subsystems accumulate the same angle
  Theta = sum sigma_i atanh(2^-i).  Vectoring drives b -> 0, hence
  Theta = -atanh((m-1)/(m+1)) = -ln(m)/2, and with the constant prescale
  p0 = 1/K,  p+q = K * (1/K) * exp(Theta) = exp(-ln(m)/2) = 1/sqrt(m).
  No angle register, no angle table, no comparison: sigma is the sign bit of b.

  phase = 2^-k / sqrt(m) applied as fixed-angle rotations on the 28 top
  fractional bits of y = 1/sqrt(m) (leading bit at 2^-1; the 2^0 bit that
  appears only for the 11 exact powers of four rotates by a full turn and is
  free).

Variant B (comparison point) uses the same vectoring subsystem to get
a_N = K*sqrt(m)/2 and then a non-restoring digit recurrence for (K/2)/a_N.

Compared against the official verifier's integer target / tolerance
(r = isqrt(2^130 // x), target = (r+1)>>1, tol = r>>25, units of 2^-64 turns).
The competition verifier module is not imported (it would load the Kaggle
kickmix.so).  This script says nothing about gate costs.
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
OUT = ROOT / 'artifacts/20261107_cordic/numeric'
MAX_X = 3 * (2**10 - 2) ** 2          # 3,133,452
MASK64 = (1 << 64) - 1
PRECISION_BITS = 24
OUT_BITS = 28                          # fractional bits of y used for rotations


def reference_values(xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Official integer target and tolerance (beta=1), units of 2^-64 turns."""
    num = 1 << 130
    rs = [math.isqrt(num // int(x)) for x in xs]
    target = np.array([((r + 1) >> 1) & MASK64 for r in rs], dtype=np.uint64)
    tol = np.array([r >> (PRECISION_BITS + 1) for r in rs], dtype=np.uint64)
    return target, tol


def iteration_index_set(N: int) -> list[int]:
    """Hyperbolic set: i = 1..N with i repeated for i = 4, 7, 10, ... (i = 3k+1)."""
    out = []
    for i in range(1, N + 1):
        out.append(i)
        if i >= 4 and (i - 1) % 3 == 0:
            out.append(i)
    return out


def scale_constant(idx: list[int]) -> float:
    k = 1.0
    for i in idx:
        k *= math.sqrt(1.0 - 4.0 ** (-i))
    return k


def normalized(xs: np.ndarray, G: int):
    """M = m*2^G with m = x/4^k in [1,4); returns M, k."""
    x = xs.astype(np.int64)
    e = np.zeros(x.shape[0], dtype=np.int64)
    for bit in range(21, -1, -1):
        e += (x >= (np.int64(1) << bit)).astype(np.int64)
    e -= 1
    k = e >> 1
    M = x << (G - 2 * k)                       # exact: m has <= 22 significant bits
    if not (np.all(M >= (1 << G)) and np.all(M < (1 << (G + 2)))):
        raise AssertionError('normalization range')
    return M, k


def cordic_forward(M: np.ndarray, G: int, idx: list[int], K: float):
    """Run the two shared-sigma CORDIC subsystems; returns integer registers."""
    b = (M - np.int64(1 << G)) >> 2            # (m-1)/4
    a = b + np.int64(1 << (G - 1))             # (m+1)/4
    p = np.full(M.shape[0], int(round((1 << (G - 2)) / K)), dtype=np.int64)
    q = np.zeros(M.shape[0], dtype=np.int64)
    stats = dict(max_abs_a=0, max_abs_b=0, max_abs_p=0, max_abs_q=0)
    for i in idx:
        s = np.where(b >= 0, np.int64(-1), np.int64(1))
        a_old, p_old = a, p
        a = a + s * (b >> i)
        b = b + s * (a_old >> i)
        p = p + s * (q >> i)
        q = q + s * (p_old >> i)
        stats['max_abs_a'] = max(stats['max_abs_a'], int(np.abs(a).max()))
        stats['max_abs_b'] = max(stats['max_abs_b'], int(np.abs(b).max()))
        stats['max_abs_p'] = max(stats['max_abs_p'], int(np.abs(p).max()))
        stats['max_abs_q'] = max(stats['max_abs_q'], int(np.abs(q).max()))
    return a, b, p, q, stats


def phase_check(Yint: np.ndarray, k: np.ndarray, G: int, target, tol,
                frac_shift: int):
    """Yint holds y*2^frac_shift (y = 1/sqrt(m)); truncate to OUT_BITS, rotate."""
    ytr = Yint >> (frac_shift - OUT_BITS)       # truncation, as the circuit does
    if ytr.max() >= (1 << (OUT_BITS + 1)):
        raise AssertionError('y truncated above 2^0 bit')
    shift = 64 - OUT_BITS - k
    if np.any(shift < 0):
        raise AssertionError('phase shift negative')
    theta = (ytr << shift).astype(np.uint64)
    err = (theta - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    bad = used > tol
    ratio = np.divide(used, tol, out=np.zeros(target.shape[0]), where=tol > 0)
    margin = tol.astype(np.int64) - used.astype(np.int64)
    worst = int(np.argmax(ratio))
    return dict(
        tolerance_failures=int(bad.sum()),
        worst_error_over_tolerance=float(ratio[worst]),
        worst_x=int(worst) + 1,
        min_margin_units=int(margin.min()),
        min_margin_turns=float(margin.min() / 2**64),
        max_error_turns=float(np.abs(err).max() / 2**64),
        y_bits_used=OUT_BITS,
        y_trunc_max=int(ytr.max()),
    )


def variant_a(xs, target, tol, G, N):
    idx = iteration_index_set(N)
    K = scale_constant(idx)
    M, k = normalized(xs, G)
    a, b, p, q, st = cordic_forward(M, G, idx, K)
    Y = p + q                                   # = 4*y*2^G  -> y = 4Y/2^G
    res = phase_check(4 * Y, k, G, target, tol, frac_shift=G)
    res.update(mode='A_dual_shared_sigma', G=G, N=N, iterations=len(idx),
               K=K, residual_max_turns=float(np.abs(b).max() / 2**G),
               a_max=st['max_abs_a'] / 2**G, b_max=st['max_abs_b'] / 2**G,
               p_max=st['max_abs_p'] / 2**G, q_max=st['max_abs_q'] / 2**G,
               y_min=float(Y.min() * 4 / 2**G), y_max=float(Y.max() * 4 / 2**G))
    return res


def variant_b(xs, target, tol, G, N, n_digits):
    """CORDIC vectoring gives a_N = K*sqrt(m)/2; non-restoring division (K/2)/a_N."""
    idx = iteration_index_set(N)
    K = scale_constant(idx)
    M, k = normalized(xs, G)
    a, b, p, q, st = cordic_forward(M, G, idx, K)
    s = a | 1                                   # force LSB = 1 (free X; 2^-G rel.)
    C = int(round((K / 2) * (1 << G))) - 8      # 8 ulp below nominal: |r_0| <= s holds
    deficit = C - s
    conv_ok = bool(np.all(deficit <= 0))
    r = np.full(xs.shape[0], C, dtype=np.int64)
    bits = np.zeros((n_digits, xs.shape[0]), dtype=np.uint8)
    rmax = 0
    for i in range(1, n_digits + 1):
        sg = np.where(r >= 0, np.int64(1), np.int64(-1))
        bits[i - 1] = (sg > 0)
        r = 2 * r - sg * s
        rmax = max(rmax, int(np.abs(r).max()))
    # on-the-fly value: y = sum_{i=1..n} q_i 2^-i = Yint / 2^n, q_i = 2c_i-1
    Yint = np.zeros(xs.shape[0], dtype=np.int64)
    for i in range(1, n_digits + 1):
        q_i = 2 * bits[i - 1].astype(np.int64) - 1
        Yint += q_i << (n_digits - i)
    leads = bool(np.all(bits[0] == 1))
    res = phase_check(Yint, k, G, target, tol, frac_shift=n_digits)
    res['leading_digit_one'] = leads
    res.update(mode='B_cordic_plus_digit_reciprocal', G=G, N=N, iterations=len(idx),
               n_digits=n_digits, K=K, residual_bound_ok=bool(rmax < (1 << (G + 1))),
               max_abs_r=rmax, C_over_s_ok=conv_ok,
               C_over_s_failures=int((deficit > 0).sum()),
               worst_C_over_s_deficit_ulp=int(max(0, deficit.max())),
               a_max=st['max_abs_a'] / 2**G, b_max=st['max_abs_b'] / 2**G)
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xs = np.arange(1, MAX_X + 1, dtype=np.int64)
    doc = dict(
        scope=('Exact integer model of the hyperbolic-CORDIC reciprocal square root '
               'on all inputs; official integer target/tolerance; no gate costs, '
               'no candidate circuit, no verifier run'),
        python=platform.python_version(), max_x=MAX_X, inputs=int(xs.shape[0]),
        rotation_bits=OUT_BITS, results=[], variant_b=[],
    )
    t0 = time.time()
    target, tol = reference_values(xs)
    doc['reference_seconds'] = round(time.time() - t0, 2)
    print('reference done', doc['reference_seconds'], flush=True)

    # iteration-count sweep at fixed precision
    for G in (30, 31, 32, 33, 34, 36):
        for N in (28,):
            r = variant_a(xs, target, tol, G, N)
            doc['results'].append(r)
            print(f"A G={G} N={N} iters={r['iterations']}: fail={r['tolerance_failures']} "
                  f"worst={r['worst_error_over_tolerance']:.4f} "
                  f"margin={r['min_margin_turns']:.4e} "
                  f"a<={r['a_max']:.3f} b<={r['b_max']:.3f} "
                  f"p<={r['p_max']:.3f} q<={r['q_max']:.3f} "
                  f"y=[{r['y_min']:.4f},{r['y_max']:.4f}]", flush=True)

    # iteration-count sweep at the chosen precision
    for N in (24, 25, 26, 27):
        r = variant_a(xs, target, tol, 34, N)
        doc['results'].append(r)
        print(f"A G=34 N={N} iters={r['iterations']}: fail={r['tolerance_failures']} "
              f"worst={r['worst_error_over_tolerance']:.4f} "
              f"margin={r['min_margin_turns']:.4e}", flush=True)

    for n_digits in (28, 30, 32):
        r = variant_b(xs, target, tol, 34, 28, n_digits)
        doc['variant_b'].append(r)
        print(f"B n_digits={n_digits}: fail={r['tolerance_failures']} "
              f"worst={r['worst_error_over_tolerance']:.4f} "
              f"margin={r['min_margin_turns']:.4e} "
              f"conv={r['C_over_s_ok']} rbound={r['residual_bound_ok']}", flush=True)

    doc['wall_seconds'] = round(time.time() - t0, 2)
    (OUT / 'numeric_check.json').write_text(json.dumps(doc, indent=2) + '\n')

    passing = [r for r in doc['results'] if r['tolerance_failures'] == 0]
    print(f"\ndone in {doc['wall_seconds']} s; variant-A configs with 0 failures: "
          f"{[(r['G'], r['N']) for r in passing]}")
    return 0 if passing else 1


if __name__ == '__main__':
    sys.exit(main())
