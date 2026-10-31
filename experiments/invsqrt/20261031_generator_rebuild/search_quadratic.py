"""Classical refit of the first quadratic grid.

Every precision is refit from the truncated signed-digit model. The published
table is not truncated. Circuit cost is attached only for the one schedule
whose executed gates were measured. Other rows are numeric results.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import fit as Fm  # noqa: E402
import model as M  # noqa: E402

# Measured on the emitted recipe circuit (6-point and 256-shot diagnoses agree).
MEASURED_Q = 87
MEASURED_TOFFOLI = 1341.5546875
MEASURED_T_LIKE = 1.0
RECORDED_BASELINE = 100940.61
THRESHOLD = 0.95 * RECORDED_BASELINE


def one(f0, ft, f2, g0):
    prm = M.Params(
        F0=f0, FT=ft, F2=f2, G0=g0, sd=True, tcap=True, booth=False,
        rowsA=tuple(i for i in range(14) if i != 5), rowsB=tuple(range(14)),
    )
    tables, proxy = Fm.fit_all(prm, rad1=6, rad2=3, workers=8)
    # Exact-angle phase. A later angle fit can only spend the margin this leaves.
    result = M.full_check(tables, prm)
    row = {
        "segment_bits": 7,
        "F0": f0, "FT": ft, "F2": f2, "G0": g0,
        "fit_proxy": proxy,
        "model": result,
        "refit": True,
        "truncated_from_recipe": False,
    }
    if result.get("pass"):
        # Positions that are neither Clifford nor T still have to be synthesized.
        nrot = max(1, f0 - g0 + 7)
        rot_t = M.rotation_cost(nrot, result["min_margin"])
        # Width stays at the measured schedule width: smaller F0 does not by
        # itself free the adder-carry peak. Using that width is the optimistic
        # direction for a precision-only change.
        cost = MEASURED_Q * (MEASURED_TOFFOLI + MEASURED_T_LIKE / 4 + rot_t / 4)
        row.update({
            "assumed_qubits": MEASURED_Q,
            "assumed_toffoli": MEASURED_TOFFOLI,
            "rotation_T": rot_t,
            "cost_if_width_unchanged": cost,
            "beats_formal_threshold": cost <= THRESHOLD,
            "rejected_reason": None if cost <= THRESHOLD else "width-fixed cost stays above 0.95 of the recorded baseline; margin cannot pay for the measured Toffolis",
        })
    else:
        row["rejected_reason"] = "numeric tolerance failure at " + str(result.get("first_bad_x"))
    return row


def main() -> int:
    out = Path(sys.argv[1])
    rows = []
    for seg in (7,):
        for f0 in (27, 28, 29):
            for ft in (18, 19, 20):
                for f2 in (7, 8, 9, 10):
                    for g0 in (0, 1, 2):
                        row = one(f0, ft, f2, g0)
                        row["segment_bits"] = seg
                        rows.append(row)
                        print(json.dumps({k: row[k] for k in row if k != "model"} | {"pass": row["model"].get("pass"), "worst": row["model"].get("worst"), "margin": row["model"].get("min_margin")}), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "order": "segment bits, then F0, FT, F2, G0; each cell refit",
        "formal_threshold": THRESHOLD,
        "recorded_baseline": RECORDED_BASELINE,
        "rows": rows,
    }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
