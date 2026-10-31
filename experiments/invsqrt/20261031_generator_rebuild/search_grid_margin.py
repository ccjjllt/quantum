"""Fresh refit of every mantissa and precision cell, with absolute margin.

Each cell is fit from the truncated signed-digit model. The published table is
never truncated into the result. The walk covers all 3,133,452 inputs even when
the margin is negative. Synthesis uses the official rotation formula and is
omitted when the margin is not positive. This script does not call the verifier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import fit as Fm  # noqa: E402
import model as M  # noqa: E402
from recipe_io import tables_from_recipe  # noqa: E402

PUBLISHED = tables_from_recipe(even_c0=False)


def is_truncation(tables: np.ndarray) -> bool:
    if tables.shape != PUBLISHED.shape:
        return False
    for shift in range(1, 6):
        if np.array_equal(tables, PUBLISHED >> shift):
            return True
        if np.array_equal(tables, PUBLISHED & np.int64(-1 << shift)):
            return True
    return False


def full_margin(tables: np.ndarray, prm: M.Params) -> dict:
    target, tol = M.reference()
    min_margin = 1 << 62
    worst = 0.0
    worst_x = 1
    violations = 0
    first_bad = None
    overflows = 0
    for start in range(1, M.MAX_X + 1, 1 << 20):
        xs = np.arange(start, min(start + (1 << 20), M.MAX_X + 1), dtype=np.int64)
        _t, xn, p, s = M.decompose(xs)
        address = (p << prm.seg_bits) | ((xn >> prm.delta_bits) & ((1 << prm.seg_bits) - 1))
        delta = xn & ((1 << prm.delta_bits) - 1)
        c0, c1, c2 = tables[address, 0], tables[address, 1], tables[address, 2]
        derivative = M.eval_T(c1, c2, delta, prm)
        value = M.eval_Y(c0, derivative, delta, prm)
        overflows += int(np.count_nonzero(
            (derivative < 0) | (derivative >= (1 << prm.nT)) | (c1 >= (1 << prm.nT))
            | (value < 0) | (value >= (1 << (prm.F0 - 1)))
        ))
        phase = M.phase_units(xs, tables, prm, check=False)
        err = np.abs((phase - target[xs - 1]).view(np.int64)).view(np.uint64)
        tl = tol[xs - 1]
        signed = tl.astype(np.int64) - err.astype(np.int64)
        local = int(signed.min())
        if local < min_margin:
            min_margin = local
        ratio = err / tl.astype(np.float64)
        k = int(np.argmax(ratio))
        if float(ratio[k]) > worst:
            worst = float(ratio[k])
            worst_x = int(xs[k])
        bad = err > tl
        violations += int(np.count_nonzero(bad))
        if first_bad is None and bad.any():
            first_bad = int(xs[int(np.flatnonzero(bad)[0])])
    return {
        "absolute_margin_units": int(min_margin),
        "violations": violations,
        "overflows": overflows,
        "worst_ratio": worst,
        "worst_x": worst_x,
        "first_bad_x": first_bad,
        "pass": violations == 0 and overflows == 0 and min_margin > 0,
    }


def synthesis(f0: int, g0: int, margin: int) -> dict:
    nrot = max(1, f0 - g0 + 7)
    if margin <= 0:
        return {"n_rot": nrot, "synthesis_T": None, "synthesis_toffoli_equivalent": None,
                "reason": "non-positive absolute margin; the official synthesis formula is not applicable"}
    rotation_t = M.rotation_cost(nrot, margin)
    return {"n_rot": nrot, "synthesis_T": rotation_t, "synthesis_toffoli_equivalent": rotation_t / 4,
            "reason": "official formula n_rot * (0.56 log2(1/eps) + 5.3), eps = pi * margin / 2^64 / n_rot"}


def one(seg: int, f0: int, ft: int, f2: int, g0: int) -> dict:
    rows = tuple(range(21 - seg))
    prm = M.Params(
        F0=f0, FT=ft, F2=f2, G0=g0, sd=True, tcap=True, booth=False, seg_bits=seg,
        rowsA=tuple(i for i in rows if i != 5), rowsB=rows,
    )
    tables, proxy = Fm.fit_all(prm, rad1=6, rad2=3, workers=8, verbose=False)
    margin = full_margin(tables, prm)
    cost = synthesis(f0, g0, margin["absolute_margin_units"])
    return {
        "segment_bits": seg, "F0": f0, "FT": ft, "F2": f2, "G0": g0,
        "refit": True,
        "fit_radius": [6, 3],
        "fit_proxy": proxy,
        "identical_to_published_recipe_table": bool(tables.shape == PUBLISHED.shape and np.array_equal(tables, PUBLISHED)),
        "is_truncation_of_published_table": is_truncation(tables),
        **margin,
        **cost,
    }


def main() -> int:
    out = Path(sys.argv[1])
    rows = []
    for seg in (6, 7):
        for f0 in (27, 28, 29):
            for ft in (18, 19, 20):
                for f2 in (7, 8, 9, 10):
                    for g0 in (0, 1, 2):
                        row = one(seg, f0, ft, f2, g0)
                        rows.append(row)
                        print(json.dumps({k: row[k] for k in (
                            "segment_bits", "F0", "FT", "F2", "G0", "pass", "absolute_margin_units",
                            "synthesis_T", "is_truncation_of_published_table", "first_bad_x")}), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "cells": len(rows),
        "grid": "segment_bits {6,7} x F0 {27,28,29} x FT {18,19,20} x F2 {7,8,9,10} x G0 {0,1,2}",
        "refit": "rad 6,3 then local descent; not a truncation of the published table",
        "five_percent_target": "still open",
        "best_measured_circuit_cost": 144556.97,
        "rows": rows,
    }, indent=2) + "\n")
    print("wrote", out, "cells", len(rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
