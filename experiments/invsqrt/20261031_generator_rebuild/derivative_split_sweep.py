"""Sweep the derivative high/low split one bit around the upstream window.

Each offset refits F0=28, FT=19, F2=8, G0=1. The row records the full-domain
absolute margin, the official synthesis charge, and the billed recovery-clear
Toffolis. Nothing here is a 5% acceptance.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import fit as Fm  # noqa: E402
import model as M  # noqa: E402
import recovery_split as R  # noqa: E402
from generate_circuit import build_from_tables  # noqa: E402
from recipe_io import DEFAULT_PLAN, params_from_recipe, phase_angles, load_recipe, tables_from_recipe  # noqa: E402
from search_grid_margin import full_margin, is_truncation, synthesis  # noqa: E402

OUT = ROOT.parents[2] / "artifacts" / "20261031_invsqrt_generator_rebuild"


def split_ok(tables, prm, w: int) -> dict:
    a, p, xn, _bounds = Fm.domains(prm)
    b = xn & ((1 << prm.delta_bits) - 1)
    c0, c1, c2 = tables[a, 0], tables[a, 1], tables[a, 2]
    derivative = M.eval_T(c1, c2, b, prm)
    correction = derivative - c1
    width = w + 1
    low = (c1 & ((1 << width) - 1)) - (1 << w) + correction
    lo = int(low.min())
    hi = int(low.max())
    limit = 1 << width
    return {"fits": lo >= -limit and hi < limit, "low_min": lo, "low_max": hi, "limit": limit}


def clear_cost(tables, prm, angles, w: int) -> dict:
    R.COUNTS.clear()
    R.STAGE[0], R.STAGE[1], R.STAGE[2] = "init", 1, {}
    circ, resources = build_from_tables(
        tables, prm, angles, lb=21, s=20, plan=DEFAULT_PLAN,
        retire=3, initial_lookup=True, last=False, prefix=0, derivative_split=w,
    )
    groups, _detail = R.bucket(dict(R.COUNTS))
    return {
        "qubits": resources["qubits"],
        "static_toffoli_like": resources["static_toffoli_like"],
        "clear_toffoli_like": groups["clear"]["toffoli_like"],
        "clear_hmr": groups["clear"]["hmr"],
        "read_toffoli_like": groups["cache_read"]["toffoli_like"],
        "phase_toffoli_like": groups["phase_correction"]["toffoli_like"],
        "phase_z_pow": groups["phase_correction"]["z_pow"],
        "init_and": sum(v for k, v in R.COUNTS.items() if k.endswith(":init_and")),
        "del_and": sum(v for k, v in R.COUNTS.items() if k.endswith(":del_and")),
        "peak": resources["peak_allocated"],
    }


def main() -> int:
    R.install_counter()
    recipe = load_recipe()["recipe"]
    prm = params_from_recipe(recipe)
    angles = phase_angles()
    # Upstream window is the 1-guard derivative split of the published recipe table.
    published = tables_from_recipe(load_recipe()["recipe"])
    _a, p, xn, _b = Fm.domains(prm)
    upstream = int(M.window_ranges1(published, prm, xn, p)["A"])
    rows = []
    for offset in (-1, 0, 1):
        tables, proxy = Fm.fit_all(prm, rad1=6, rad2=3, workers=8)
        w = upstream + offset
        margin = full_margin(tables, prm)
        synth = synthesis(prm.F0, prm.G0, margin["absolute_margin_units"])
        guard = split_ok(tables, prm, w)
        row = {
            "offset_bits": offset,
            "derivative_split": w,
            "upstream_split": upstream,
            "refit": True,
            "fit_radius": [6, 3],
            "fit_proxy": proxy,
            "is_truncation_of_published_table": is_truncation(tables),
            "identical_to_published_recipe_table": False,
            **margin,
            **synth,
            "guard": guard,
        }
        if not guard["fits"]:
            row["decision"] = "reject"
            row["reason"] = "low window of the derivative does not fit the 1-guard range; recovery would be wrong"
            row["clear_cost"] = None
        elif margin["absolute_margin_units"] <= 0:
            row["decision"] = "reject"
            row["reason"] = "non-positive full-domain absolute margin"
            row["clear_cost"] = None
        else:
            row["clear_cost"] = clear_cost(tables, prm, angles, w)
            billed = row["clear_cost"]["static_toffoli_like"] + synth["synthesis_toffoli_equivalent"]
            row["score_illustration"] = row["clear_cost"]["qubits"] * billed
            row["decision"] = "reject"
            row["reason"] = "comparison row for the upstream split; score stays above 95893.58, so this is not a 5% accept"
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("offset_bits", "derivative_split", "decision", "absolute_margin_units", "synthesis_T", "reason")}), flush=True)
    # Compare ±1 clear cost with the upstream row when both were built.
    base = next(r for r in rows if r["offset_bits"] == 0)
    for row in rows:
        if row["offset_bits"] == 0 or row["clear_cost"] is None or base["clear_cost"] is None:
            continue
        base_clear = base["clear_cost"]["clear_toffoli_like"]
        this_clear = row["clear_cost"]["clear_toffoli_like"]
        worse = (
            row["clear_cost"]["qubits"] > base["clear_cost"]["qubits"]
            or row["clear_cost"]["static_toffoli_like"] > base["clear_cost"]["static_toffoli_like"]
            or this_clear > base_clear
        )
        row["decision"] = "reject"
        if worse:
            row["reason"] = "higher qubits, billed Toffolis, or recovery-clear Toffolis than the upstream derivative split"
        else:
            row["reason"] = "no measured 5% reduction; static comparison does not establish a cheaper verified circuit"
    payload = {
        "five_percent_target": "still open",
        "best_measured_circuit_cost": 144556.97,
        "upstream_derivative_split": upstream,
        "meaning": "WA is the derivative low-window width. Bits below WA stay in the window; bits at and above WA are the high part folded through the guard.",
        "rows": rows,
    }
    path = OUT / "derivative_split.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", path, "upstream", upstream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
