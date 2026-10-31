"""Re-evaluate the former 7-bit numeric passes on the corrected fit and angles.

A cell that fails the constrained model is kept as a failure with a reason.
It is not dropped because an earlier width-fixed illustration was expensive.
This script does not call the official verifier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import model as M  # noqa: E402
import fit as Fm  # noqa: E402
import hsplit as H  # noqa: E402
from generate_circuit import build_from_tables, resolve_angles  # noqa: E402
from recipe_io import load_recipe  # noqa: E402
from search_grid_margin import full_margin, is_truncation  # noqa: E402

ART = ROOT.parents[2] / "artifacts" / "20261031_invsqrt_generator_rebuild"
GRID = ART / "grid_margin.json"
LAYOUTS = ((21, 20), (21, 19), (22, 20), (22, 19), (22, 21))


def params_for(seg: int, f0: int, ft: int, f2: int, g0: int) -> M.Params:
    rows = tuple(range(21 - seg))
    return M.Params(
        F0=f0, FT=ft, F2=f2, G0=g0, sd=True, tcap=True, booth=False, seg_bits=seg,
        rowsA=tuple(i for i in rows if i != 5), rowsB=rows,
    )


def window_plan(prm: M.Params) -> str:
    default = "17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0"
    if prm.nT - 1 >= 17:
        return default
    parts = []
    cursor = prm.nT - 1
    for low in (11, 9, 7, 5, 3, 1):
        if cursor < low:
            break
        parts.append(f"{cursor}:{low},{low - 1}")
        cursor -= 2
    return ";".join(parts)


def virtual_ok(tables: np.ndarray, prm: M.Params) -> bool:
    return all(Fm.row_obeys_virtual_bits(int(r[0]), int(r[1]), int(r[2]), prm) for r in tables)


def adder_peak(recipe: dict) -> list[dict]:
    from recipe_io import params_from_recipe, phase_angles, tables_from_recipe
    prm = params_from_recipe(recipe)
    tables = tables_from_recipe(recipe, even_c0=True)
    angles = phase_angles()
    rows = []
    for prefix in (0, 8):
        circ, resources = build_from_tables(
            tables, prm, angles, lb=21, s=20,
            plan="17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0",
            retire=3, initial_lookup=True, last=False, prefix=prefix,
        )
        del circ
        rows.append({
            "prefix": prefix,
            "qubits": resources["qubits"],
            "static_toffoli_like": resources["static_toffoli_like"],
            "peak_allocated": resources["peak_allocated"],
            "peak_qubits": resources["peak_allocated"][0],
        })
    return rows


def evaluate_cell(spec: dict, recipe: dict) -> dict:
    seg, f0, ft, f2, g0 = (spec[k] for k in ("segment_bits", "F0", "FT", "F2", "G0"))
    prm = params_for(seg, f0, ft, f2, g0)
    tables, proxy = Fm.fit_all(prm, rad1=6, rad2=3, workers=4, verbose=False)
    adjusted = tables.copy()
    adjusted[:, 0] += adjusted[:, 0] & 1
    row = {
        "segment_bits": seg, "F0": f0, "FT": ft, "F2": f2, "G0": g0,
        "previously_numeric_pass": True,
        "refit": True,
        "fit_radius": [6, 3],
        "fit_proxy": proxy,
        "constraint_satisfying_refit": bool(virtual_ok(tables, prm)),
        "all_constant_words_even": bool(np.all((tables[:, 0] & 1) == 0)),
        "even_adjustment_changes_any_word": bool(np.any(adjusted[:, 0] != tables[:, 0])),
        "is_truncation_of_published_table": is_truncation(tables),
        "excluded_for_earlier_illustration": False,
    }
    if not row["constraint_satisfying_refit"]:
        row["status"] = "fail"
        row["reason"] = "refit did not meet the even-constant and derivative-parity constraints"
        return row
    # full_margin uses model.phase_units. A diagnosis may install PHASE_FN;
    # that override must not leak into the next cell's numeric margin.
    saved_phase = M.PHASE_FN
    M.PHASE_FN = None
    try:
        margin = full_margin(tables, prm)
    finally:
        M.PHASE_FN = saved_phase
    row.update(margin)
    if not margin["pass"]:
        row["status"] = "fail"
        row["reason"] = (
            f"constrained model failed: violations {margin['violations']}, "
            f"overflows {margin['overflows']}, margin {margin['absolute_margin_units']}, "
            f"first_bad_x {margin['first_bad_x']}"
        )
        return row
    layout = None
    for lb, s in LAYOUTS:
        layout = H.layout(tables, prm, lb, s)
        if layout is not None:
            row["LB"], row["S"] = lb, s
            break
    if layout is None:
        row["status"] = "fail"
        row["reason"] = "no high/low layout at the tried (LB, S) pairs"
        return row
    try:
        angles, info = resolve_angles(tables, prm, row["LB"], row["S"], None, recipe)
    except SystemExit as exc:
        row["status"] = "fail"
        row["reason"] = f"angle calibration failed: {exc}"
        return row
    row["angle_source"] = info["angle_source"]
    row["angles_differ_from_published"] = info.get("angles_differ_from_published")
    row["calibration_margin"] = info.get("calibration_margin")
    plan = window_plan(prm)
    row["plan"] = plan
    try:
        circ, resources = build_from_tables(
            tables, prm, angles, lb=row["LB"], s=row["S"], plan=plan,
            retire=3, initial_lookup=True, last=False, prefix=0,
        )
    except (SystemExit, AssertionError) as exc:
        row["status"] = "fail"
        row["reason"] = f"circuit build failed: {exc}"
        return row
    row["peak_allocated"] = resources["peak_allocated"]
    # G0=0 phases the low-word LSB. The split register omits that bit, and a
    # constant stand-in does not match the model when the word is odd.
    if prm.G0 == 0:
        import diagnose_circuit as diag
        diag._STREAMS.clear()
        saved_phase = M.PHASE_FN
        M.PHASE_FN = lambda xs, _tables=tables, _prm=prm, _lay=layout, _angles=angles: H.phases_multi(
            H.regs(_tables, _prm, _lay, xs), _angles)
        sample = np.array([1, 2, 161, 888, 1024, 3133452], dtype=np.int64)
        try:
            checked = diag.run_batch(circ, tables, prm, sample, 101)
        finally:
            M.PHASE_FN = saved_phase
        del circ
        if checked["phase_mismatches_vs_model"] or checked["x_restoration_errors"] or checked["dirty_scratch_shots"]:
            row["status"] = "fail"
            row["reason"] = (
                "G0=0 build does not match the model phase "
                "(low-word LSB is not the virtual split bit); "
                "phase_mismatches %s, restoration %s, dirty %s. No accepted circuit cost."
                % (checked["phase_mismatches_vs_model"], checked["x_restoration_errors"], checked["dirty_scratch_shots"])
            )
            return row
    else:
        del circ
    row["status"] = "measured"
    row["qubits"] = resources["qubits"]
    row["static_toffoli_like"] = resources["static_toffoli_like"]
    row["reason"] = "corrected refit, matched angles, and a built circuit; not excluded by the old illustration"
    return row


def main() -> int:
    grid = json.loads(GRID.read_text())
    passes = [r for r in grid["rows"] if r.get("pass") and r.get("segment_bits") == 7]
    recipe = load_recipe()["recipe"]
    peaks = adder_peak(recipe)
    cells = []
    out = ART / "corrected_grid.json"
    for i, spec in enumerate(passes, start=1):
        cell = evaluate_cell(spec, recipe)
        cells.append(cell)
        print(json.dumps({k: cell.get(k) for k in (
            "segment_bits", "F0", "FT", "F2", "G0", "status", "qubits",
            "static_toffoli_like", "absolute_margin_units", "reason")}), flush=True)
        payload = {
            "previously_passing_7bit_cells": len(passes),
            "cells_evaluated": i,
            "five_percent_target": "still open",
            "portfolio_zip": None,
            "official_verifier_called": False,
            "adder_peak": peaks,
            "note": "A cell is not excluded only because an earlier mismatched-angle or width-fixed illustration was expensive.",
            "rows": cells,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", out, "cells", len(cells), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
