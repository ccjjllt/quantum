"""Centered-cubic classical branch, plus the official Newton pipeline as a control.

The quadratic schedule already spends more Toffolis than the formal cost budget
allows at its measured width. This script checks whether a coarser cubic table
can pass numerically, and what an extra Horner multiply does to that budget.
It does not call the official verifier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import model as M  # noqa: E402

VERIFIER = ROOT.parents[2] / "data" / "competition" / "verifiers"


def cubic_tables(seg_bits: int, f0: int, ft: int, f2: int, f3: int):
    prm = M.Params(F0=f0, FT=ft, F2=f2, G0=1, sd=True, tcap=True, seg_bits=seg_bits,
                   rowsA=tuple(range(prm_rows(seg_bits))), rowsB=tuple(range(prm_rows(seg_bits))))
    xs = np.arange(1, M.MAX_X + 1, dtype=np.int64)
    _t, xn, p, _s = M.decompose(xs)
    a = (p << seg_bits) | ((xn >> prm.delta_bits) & ((1 << seg_bits) - 1))
    order = np.argsort(a, kind="stable")
    a, p, xn = a[order], p[order], xn[order]
    bounds = np.searchsorted(a, np.arange(prm.n_segments + 1))
    tables = np.zeros((prm.n_segments, 4), dtype=np.int64)
    center = 1 << (prm.delta_bits - 1)
    for seg in range(prm.n_segments):
        lo, hi = int(bounds[seg]), int(bounds[seg + 1])
        if lo == hi:
            continue
        b = xn[lo:hi] & ((1 << prm.delta_bits) - 1)
        dc = (b - (center - 0.5)) * 2.0 ** -21
        y = np.where(p[lo:hi] == 1, 1.0, 2 ** -0.5) * 2 ** 10.5 / np.sqrt(xn[lo:hi].astype(np.float64))
        idx = np.unique(np.linspace(0, len(dc) - 1, min(400, len(dc))).astype(int))
        d, yy = dc[idx], y[idx]
        # y ~ c0 - c1 d + c2 d^2 - c3 d^3
        cols = [np.ones_like(d), -d, d * d, -(d ** 3)]
        A = np.c_[*cols, -yy]
        B = np.c_[*[-c for c in cols], -yy]
        r = linprog([0, 0, 0, 0, 1], A_ub=np.r_[A, B], b_ub=np.r_[yy, -yy],
                    bounds=[(None, None)] * 4 + [(0, None)], method="highs")
        c0, c1, c2, c3 = r.x[:4]
        tables[seg] = (0, int(round(c1 * 2 ** ft)),
                       int(round(c2 * 2 ** f2)), int(round(c3 * 2 ** f3)))
    # C0 is chosen from the integer Horner residual, not by truncating a saved quadratic table.
    xs = np.arange(1, M.MAX_X + 1, dtype=np.int64)
    residual, _s = eval_cubic(xs, prm, tables, f3)
    _t, xn, p, _s = M.decompose(xs)
    address = (p << seg_bits) | ((xn >> prm.delta_bits) & ((1 << seg_bits) - 1))
    y = np.where(p == 1, 1.0, 2 ** -0.5) * 2 ** 10.5 / np.sqrt(xn.astype(np.float64))
    target = (y - 0.5) * 2 ** f0
    for seg in range(prm.n_segments):
        mask = address == seg
        if not np.any(mask):
            continue
        gap = residual[mask] - target[mask]
        tables[seg, 0] = int(np.rint(-0.5 * (gap.max() + gap.min())))
    return prm, tables


def prm_rows(seg_bits: int) -> int:
    return 21 - seg_bits


def eval_cubic(xs, prm, tables, f3):
    """Signed-digit Horner. With a zero cubic column this matches model_Yp."""
    _t, xn, p, s = M.decompose(xs)
    a = (p << prm.seg_bits) | ((xn >> prm.delta_bits) & ((1 << prm.seg_bits) - 1))
    b = xn & ((1 << prm.delta_bits) - 1)
    C0, C1, C2, C3 = (tables[a, i] for i in range(4))
    rows = prm.rowsA

    def e3(i):
        return 21 + f3 - prm.F2 - i

    curvature = M.sd_apply(C2.copy(), C3, b, rows, e3)
    derivative = M.sd_apply(C1.copy(), curvature, b, rows, prm.eA)
    value = M.sd_apply(C0.copy(), derivative, b, rows, prm.eB)
    return value, s


def ratio(xs, prm, tables, f3):
    y, s = eval_cubic(xs, prm, tables, f3)
    target, tol = M.reference()
    # Same phase assembly as the quadratic model: (Y + 2^(F0-1)) << (s + 64 - 10 - F0), G0=1.
    y = np.clip(y, 0, (1 << (prm.F0 - 1)) - 1)
    r0 = prm.F0 - prm.G0
    v = ((y >> prm.G0) + (1 << (r0 - 1))).astype(np.uint64)
    sh = (64 - 10 - r0 + s).astype(np.uint64)
    phase = v << sh
    err = np.abs((phase - target[xs - 1]).view(np.int64)).view(np.uint64)
    ratios = err / tol[xs - 1].astype(np.float64)
    k = int(np.argmax(ratios))
    bad = np.flatnonzero(ratios > 1)
    first_bad = None if bad.size == 0 else int(xs[int(bad[0])])
    return ratios, int(xs[k]), float(ratios[k]), first_bad


def newton_control():
    sys.path.insert(0, str(VERIFIER))
    from invsqrt.nr_reference_circuit import Precision, build_nr_circuit, relative_error
    prec = Precision()
    xs = np.arange(1, M.MAX_X + 1, 64, dtype=np.int64)
    err = relative_error(10, prec, xs)
    k = int(np.argmax(err))
    circ = build_nr_circuit(10, prec=prec)
    stats = circ.operation_statistics()
    return {
        "role": "control only; not the candidate algorithm",
        "source": "data/competition/verifiers/invsqrt/nr_reference_circuit.py",
        "sample_stride": 64,
        "sample_worst_x": int(xs[k]),
        "sample_max_relative_error": float(err[k]),
        "tolerance_relative": 2 ** -24,
        "under_tolerance": bool(err[k] < 2 ** -24),
        "qubits": circ.num_qubits,
        "static_toffoli_like": int(stats.num_toffoli_like),
        "documented_pipeline_toffolis_per_direction": 3900,
        "counterexample": "none on this stride; the control is the width and Toffoli count, not a tolerance failure",
    }


def screen_cubic(seg, f0, ft, f2, f3, stride):
    prm, tables = cubic_tables(seg, f0, ft, f2, f3)
    xs = np.arange(1, M.MAX_X + 1, stride, dtype=np.int64)
    _ratios, worst_x, worst, first_bad = ratio(xs, prm, tables, f3)
    return {
        "segment_bits": seg, "F0": f0, "FT": ft, "F2": f2, "F3": f3,
        "stride": stride, "segments": prm.n_segments,
        "horner_multiplies": 3, "quadratic_multiplies": 2,
        "worst_ratio": worst, "worst_x": worst_x, "first_bad_x": first_bad,
        "pass": first_bad is None,
    }


def main() -> int:
    out = Path(sys.argv[1])
    rows = []
    # Recipe-width cubics, then one wider fraction setting. Both segment sizes
    # fail at the first setting, so there is no lower precision to step back to.
    probes = [(4, 28, 19, 8, 6), (5, 28, 19, 8, 6), (4, 36, 28, 16, 12), (5, 36, 28, 16, 12), (7, 28, 19, 8, 4)]
    for seg, f0, ft, f2, f3 in probes:
        item = screen_cubic(seg, f0, ft, f2, f3, 32)
        rows.append(item)
        print(json.dumps(item), flush=True)
    payload = {
        "rows": rows,
        "step_back": "no {4,5}-bit probe passed, including the wider fraction setting, so there is no feasible point to step back to",
        "newton": newton_control(),
        "official_verifier_called": False,
        "five_percent_target": "still open",
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["newton"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
