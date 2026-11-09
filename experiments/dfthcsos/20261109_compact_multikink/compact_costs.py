"""Exact SpinFreeData_V1 + PSD evaluation for compact rank shapes.

No training, no circuits, no verifier shots. Reads the saved
shifted-target eigenvalues for PSD necessary bounds and calls the
official SpinFreeData_V1 cost model for exact heuristic T/Q.
ANGLE costs for new shapes are planner-dependent and NOT claimed;
this script reports heuristic-exact numbers plus README budgets
as clearly labeled budgets.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers" / "dfthcsos"))
from scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402


BASE_SCORE = 299657851.0779786  # b9eced3e 78,080-shot PASS
BASE_LE = 46.89127534949298
BASE_T, BASE_Q = 14966, 427
BASE_TQ = BASE_T * BASE_Q
ANGLES_MEASURED = 8304.0  # from verify.log, b9eced3e


def heuristic(shape):
    R, B, C = shape
    m = SpinFreeData_V1(R=R, B=B, C=C, N=76, chi=10, beta=8)
    ht = m.outer_state_prep() + m.inner_state_prep() + m.givens_rotations()
    oq = m.outer_state_prep_qubit_cost()
    iq = m.inner_state_prep_qubit_cost()
    persist = oq["persistent"] + iq["persistent"]
    temp = max(oq["temporary"], iq["temporary"])
    return ht, persist, temp


def main() -> None:
    out_dir = ROOT / "artifacts" / "20261109_compact_multikink"
    out_dir.mkdir(parents=True, exist_ok=True)
    eig = np.load(
        ROOT / "artifacts" / "20261106_high_yield" / "numerical"
        / "shifted_target_eigenvalues.npy"
    )
    s = np.sort(np.asarray(eig, dtype=np.float64))[::-1]
    pos = s[s > 0]
    neg = s[s < 0]
    neg_sq = float(np.sum(neg**2))

    rows = []
    for name, R, B, C in [
        ("current 8/143/44", 8, 143, 44),
        ("R5/B135/C70", 5, 135, 70),
        ("R5/B135/C69", 5, 135, 69),
        ("R4/B131/C83", 4, 131, 83),
        ("R4/B131/C82", 4, 131, 82),
        ("R4/B131/C84", 4, 131, 84),
        ("R6/B143/C59", 6, 143, 59),
    ]:
        ht, persist, temp = heuristic((R, B, C))
        # PSD necessary bound for rank RC
        k = R * C
        tail = pos[k:] if len(pos) > k else np.zeros(0)
        psd = math.sqrt(float(np.sum(tail**2)) + neg_sq)
        # conservative T/Q: angles unchanged (no new circuits measured)
        T_cons = ANGLES_MEASURED + ht
        Q_cons = persist + 40 + max(temp, 77)  # 40=J*brot, 77=angles temp
        # NOTE: temp max is inner temp (303) in all cases; keep exact:
        Q_cons = persist + 40 + max(temp, 77)
        TQ_cons = T_cons * Q_cons
        rows.append({
            "shape": name, "R": R, "B": B, "C": C,
            "A": 76 + R * B, "addr_bits": (76 + R * B - 1).bit_length(),
            "RC": k, "PSD_mHa": psd * 1000.0,
            "heur_T": ht, "heur_persist": persist, "heur_temp": temp,
            "T_cons_angles_unchanged": T_cons, "Q_cons": Q_cons,
            "TQ_cons": TQ_cons,
            "dTQ_cons_pct": 100.0 * (TQ_cons - BASE_TQ) / BASE_TQ,
            "breakeven_le_cons": BASE_SCORE / TQ_cons,
        })
    # README planner budgets (not measured here)
    budgets = {
        "R5/B135/C70": (14177, 427),
        "R4/B131/C83": (13722, 426),
        "R4/B131/C82": (13683, 426),
        "R6/B143/C59": (14592, 427),
    }
    for r in rows:
        key = r["shape"]
        if key in budgets:
            T, Q = budgets[key]
            TQ = T * Q
            r["T_budget_README"] = T
            r["Q_budget_README"] = Q
            r["TQ_budget"] = TQ
            r["dTQ_budget_pct"] = 100.0 * (TQ - BASE_TQ) / BASE_TQ
            r["breakeven_le_budget"] = BASE_SCORE / TQ
    (out_dir / "compact_costs.json").write_text(
        json.dumps({
            "base": {"score": BASE_SCORE, "le": BASE_LE,
                     "T": BASE_T, "Q": BASE_Q, "TQ": BASE_TQ},
            "note": ("T_cons/Q_cons use measured angles 8304 (no new circuits). "
                     "T_budget_README needs new shared-planner circuits and is NOT measured."),
            "rows": rows,
        }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
