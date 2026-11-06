"""Full-domain integer check of table-initialized Newton / Goldschmidt reciprocal sqrt.

Architecture modelled here:
  x (22 bits) -> e = floor(log2 x), k = e // 2
              -> R = x << (21 - 2k) in [2^21, 2^23),  m = R / 2^21 in [1, 4)
              -> QROM seed y0 = 1/sqrt(m_mid) of the 256/1024-entry segment
                 holding m, stored with B fractional bits
  Newton     y' = y (3 - m y^2) / 2
  Goldschmidt (rsqrt form, e_k = 1 - m y_k^2):
             y' = y (1 + e/2),  e' = (3/4) e^2 + (1/4) e^3
  phase = 2^-k y, applied by fixed-angle Z_POWs on the aligned bits of y.

Every arithmetic step is the exact fixed-point operation a reversible
multiplier produces:  prod = a * b, result = floor(prod / 2^(a_frac+b_frac-out_frac)),
i.e. the low bits of the product are simply not computed (the same convention as
`multiplier()` in experiments/invsqrt/20261106_piecewise_cost/kernels.py, whose
paid cost is measured with km.CircuitBuilder).  Nothing here is a floating-point
model and nothing rounds up.

Target / tolerance come from the official verifier formula (r = isqrt(2^130//x),
target = (r+1)>>1, tol = r>>25, units of 2^-64 turns).  The competition verifier
module is not imported (it loads the Kaggle kickmix.so); the formula is copied.

This script says nothing about gate costs or scratch restoration.
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
OUT = ROOT / 'artifacts/20261107_newton_goldschmidt/numeric'
MAX_X = 3 * (2**10 - 2) ** 2          # 3,133,452
MASK64 = (1 << 64) - 1
PRECISION_BITS = 24
FINAL_FRAC = 28                       # y output: 28 fractional bits


# ---------------------------------------------------------------- reference ---

def reference_values(xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Official integer target and tolerance (beta=1), units of 2^-64 turns."""
    num = 1 << 130
    rs = np.fromiter((math.isqrt(num // int(x)) for x in xs), dtype=object, count=xs.shape[0])
    r = np.array(rs, dtype=object)
    target = np.array([((int(v) + 1) >> 1) & MASK64 for v in r], dtype=np.uint64)
    tol = np.array([min(int(v) >> (PRECISION_BITS + 1), 1 << 63) for v in r], dtype=np.uint64)
    return target, tol


# ------------------------------------------------------------------ helpers ---

def normalize(xs: np.ndarray):
    """e = floor(log2 x), k = e//2, R = x << (21-2k) in [2^21, 2^23)."""
    x = xs.astype(np.int64)
    e = np.zeros(xs.shape[0], dtype=np.int64)
    for bit in range(21, -1, -1):
        e += (x >= (np.int64(1) << bit)).astype(np.int64)
    e -= 1
    k = e >> 1
    R = x << (21 - 2 * k)
    assert np.all(R >= (1 << 21)) and np.all(R < (1 << 23))
    return e, k, R


def fmul(a: np.ndarray, a_frac: int, b: np.ndarray, b_frac: int, out_frac: int) -> np.ndarray:
    """floor(a * b) at `out_frac` fractional bits, exact integer arithmetic."""
    s = a_frac + b_frac - out_frac
    prod = a * b
    if s >= 0:
        return prod >> s
    return prod << (-s)


def build_table(E: int, B: int):
    """Segment midpoints and the stored seed, for E entries over m in [1,4).

    m spans 3 (R spans 3*2^21), so a dyadic address slice needs
    2^sh >= 3*2^21/E; only 3E/4 of the entries are reachable.
    """
    sh = int(math.ceil(math.log2(3 * 2**21 / E)))
    assert E * (1 << sh) >= 3 * 2**21, (E, sh)
    addrs = np.arange(E, dtype=np.int64)
    mid = (1 << 21) + addrs * (1 << sh) + (1 << (sh - 1))
    m_mid = mid / 2.0**21
    y0 = np.array([round(2.0**B / math.sqrt(v)) for v in m_mid], dtype=np.int64)
    # y0^2 as stored in the circuit: exact square of the *stored* B-bit value,
    # truncated to YSQ_FRAC fractional bits.  Table output width is free.
    ysq = np.array([(int(v) * int(v)) << (YSQ_FRAC - 2 * B) for v in y0], dtype=np.int64)
    return sh, y0, ysq


YSQ_FRAC = 32


# ------------------------------------------------------------- iterations ---

def newton(y, y_frac, R, sq_frac, u_frac, out_frac):
    """One Newton step y' = y (3 - m y^2)/2 with circuit truncation."""
    m = R                                        # m_frac = 21
    sq = fmul(y, y_frac, y, y_frac, sq_frac)
    u = fmul(m, 21, sq, sq_frac, u_frac)
    e = (np.int64(1) << u_frac) - u              # 1 - m y^2, at u_frac
    p = fmul(y, y_frac, e, u_frac, out_frac)     # y*e at out_frac
    y1 = (y << (out_frac - y_frac)) + (p >> 1)   # y + y*e/2 at out_frac
    return y1, e


def goldschmidt_from_e(y, y_frac, e, e_frac, out_frac):
    """y' = y + y e/2 given e = 1 - m y^2."""
    p = fmul(y, y_frac, e, e_frac, out_frac)
    return (y << (out_frac - y_frac)) + (p >> 1)


def square_e(e, e_frac, out_frac):
    """e^2 truncated to out_frac (e is signed, small)."""
    return fmul(e, e_frac, e, e_frac, out_frac)


def rsqrt_goldschmidt_e(e, e_frac, out_frac):
    """e' = (3/4) e^2 + (1/4) e^3 for the rsqrt iteration, truncated to out_frac.

    e2 and e3 are carried at out_frac+2 so that (3 e2 + e3) >> 4 lands on out_frac.
    """
    e2 = fmul(e, e_frac, e, e_frac, out_frac + 2)
    e3 = fmul(e2, out_frac + 2, e, e_frac, out_frac + 2)
    return (3 * e2 + e3) >> 4


# ------------------------------------------------------------------ configs ---

def run_config(cfg: dict, xs: np.ndarray, target: np.ndarray, tol: np.ndarray):
    E = cfg['entries']
    B = cfg['seed_bits']
    sh, y0_tab, ysq_tab = build_table(E, B)
    e, k, R = normalize(xs)
    addr = (R - (1 << 21)) >> sh
    y0 = y0_tab[addr]
    ysq = ysq_tab[addr]
    m = R

    W = cfg['work_frac']                       # working fractional bits of y
    S = cfg['sq_frac']                         # y^2 fractional bits
    U = cfg['u_frac']                          # m*y^2 fractional bits
    E1F = cfg['e_frac']                        # e fractional bits

    notes = {}
    if cfg['method'] == 'newton':
        sq1 = cfg['sq1'] if cfg.get('sq1') else cfg['sq_frac']
        u1 = cfg['u1'] if cfg.get('u1') else cfg['u_frac']
        y, _ = newton(y0, B, m, sq1, u1, W)
        if cfg['iterations'] >= 2:
            y, _ = newton(y, W, m, S, U, W)
    else:                                       # goldschmidt
        # step 1: e0 = 1 - m y0^2, y1 = y0(1+e0/2)
        sq = fmul(y0, B, y0, B, S)
        u = fmul(m, 21, sq, S, U)
        e0 = (np.int64(1) << U) - u
        y1 = goldschmidt_from_e(y0, B, e0, U, W)
        notes['e0_frac'] = U
        y = y1
        if cfg['iterations'] >= 2:
            e1 = rsqrt_goldschmidt_e(e0, U, E1F)
            y = goldschmidt_from_e(y1, W, e1, E1F, W)
            notes['e1_frac'] = E1F
    # final quantisation of y to FINAL_FRAC fractional bits (floor)
    Y = y >> (W - FINAL_FRAC) if W >= FINAL_FRAC else y << (FINAL_FRAC - W)
    notes['y_frac_internal'] = W

    shift = 64 - FINAL_FRAC - k
    assert np.all(shift >= 0), shift.min()
    theta = (Y << shift).astype(np.uint64)
    err = (theta - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    bad = used > tol
    ratio = np.divide(used, tol, out=np.zeros(xs.shape[0]), where=tol > 0)
    margin = tol.astype(np.int64) - used.astype(np.int64)
    worst = int(np.argmax(ratio))
    return dict(
        name=cfg['name'], entries=E, seed_bits=B, method=cfg['method'],
        iterations=cfg['iterations'],
        work_frac=W, sq_frac=S, u_frac=U, e_frac=cfg['e_frac'],
        tolerance_failures=int(bad.sum()),
        worst_error_over_tolerance=float(ratio[worst]),
        worst_x=int(xs[worst]),
        min_margin_units=int(margin.min()),
        min_margin_turns=float(margin.min() / 2**64),
        max_error_turns=float(np.abs(err).max() / 2**64),
        notes=notes,
    )


CONFIGS = [
    # ---- Newton: one iteration is not enough ------------------------------
    dict(name='newton1_E256_B10_W28', method='newton', entries=256, seed_bits=10,
         iterations=1, work_frac=28, sq_frac=28, u_frac=28, e_frac=28, sq1=None, u1=None),
    # ---- Newton: two iterations, the design used in the ledger ------------
    dict(name='newton2_E256_B10_W28', method='newton', entries=256, seed_bits=10,
         iterations=2, work_frac=28, sq_frac=28, u_frac=28, e_frac=28, sq1=None, u1=None),
    dict(name='newton2_E256_B12_W30', method='newton', entries=256, seed_bits=12,
         iterations=2, work_frac=30, sq_frac=30, u_frac=30, e_frac=30, sq1=None, u1=None),
    dict(name='newton2_E1024_B12_W30', method='newton', entries=1024, seed_bits=12,
         iterations=2, work_frac=30, sq_frac=30, u_frac=30, e_frac=30, sq1=None, u1=None),
    # ---- Newton with a cheap first iteration (design B widths) ------------
    dict(name='newton2_E256_B10_W28_iter1_16_14', method='newton', entries=256, seed_bits=10,
         iterations=2, work_frac=28, sq_frac=28, u_frac=24, e_frac=24, sq1=16, u1=14),
    # ---- how low can the second iteration go? -----------------------------
    dict(name='newton2_E256_B10_W28_u24', method='newton', entries=256, seed_bits=10,
         iterations=2, work_frac=28, sq_frac=28, u_frac=24, e_frac=24, sq1=None, u1=None),
    dict(name='newton2_E256_B10_W28_u20', method='newton', entries=256, seed_bits=10,
         iterations=2, work_frac=28, sq_frac=28, u_frac=20, e_frac=20, sq1=None, u1=None),
    # ---- Goldschmidt: the e-recurrence needs e at full precision ----------
    dict(name='goldschmidt2_E256_B12_e16', method='goldschmidt', entries=256, seed_bits=12,
         iterations=2, work_frac=30, sq_frac=30, u_frac=30, e_frac=16, sq1=None, u1=None),
    dict(name='goldschmidt2_E256_B12_e30', method='goldschmidt', entries=256, seed_bits=12,
         iterations=2, work_frac=30, sq_frac=30, u_frac=30, e_frac=30, sq1=None, u1=None),
    dict(name='goldschmidt3_E256_B12_e30', method='goldschmidt', entries=256, seed_bits=12,
         iterations=3, work_frac=30, sq_frac=30, u_frac=30, e_frac=30, sq1=None, u1=None),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xs = np.arange(1, MAX_X + 1, dtype=np.uint64)
    t0 = time.time()
    target, tol = reference_values(xs)
    t_ref = time.time() - t0
    print(f'reference values: {t_ref:.1f} s', flush=True)
    doc = dict(
        scope=('Exact integer model of table-initialized Newton / Goldschmidt reciprocal '
               'sqrt on all inputs; official integer target/tolerance; truncating '
               'fixed-point arithmetic; no gate costs, no candidate circuit'),
        python=platform.python_version(), max_x=MAX_X, inputs=int(xs.shape[0]),
        reference_seconds=round(t_ref, 1), final_frac=FINAL_FRAC, results=[],
    )
    for cfg in CONFIGS:
        t = time.time()
        r = run_config(cfg, xs, target, tol)
        r['seconds'] = round(time.time() - t, 1)
        doc['results'].append(r)
        print(json.dumps({k: v for k, v in r.items() if k != 'notes'}), flush=True)
    doc['wall_seconds'] = round(time.time() - t0, 1)
    (OUT / 'numeric_check.json').write_text(json.dumps(doc, indent=2) + '\n')
    passing = [i for i, r in enumerate(doc['results']) if r['tolerance_failures'] == 0]
    print(f"\ndone in {doc['wall_seconds']} s; passing configs = {passing}")
    for r in doc['results']:
        print(f"  {r['name']:34s} fail={r['tolerance_failures']:7d} "
              f"err/tol={r['worst_error_over_tolerance']:.4f} "
              f"margin={r['min_margin_turns']:.4e} turns")
    return 0


if __name__ == '__main__':
    sys.exit(main())
