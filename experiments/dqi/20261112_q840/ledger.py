"""T/Q ledger for the 'Q=840, recompute the 48-bit bank on demand' proposal.

All T figures are the measured eae396ba static counts (401,313 total). The bank
touch counts come from experiments/dqi/20261112_q840/{ancilla_role.txt,
cond_load.txt, region_census.txt}. Output: results/ledger.json + stdout table.
"""
from __future__ import annotations

import json
from pathlib import Path

R = 1.19126046            # verifier R(eps+) at 102,400 shots, 0 failures
Q0, STATIC0, MEAN0 = 892, 401_313, 394_089
COST0 = R * Q0 * Q0 * MEAN0            # 3.7353e11
RATIO = MEAN0 / STATIC0                 # 0.98200 measured

# measured bank census (see ancilla_role.txt)
PAID_BY_STAGE = {"extract": 58_742, "synthesis": 31_635, "convert": 60_663,
                 "scan": 44_275, "unconvert": 62_534, "unsynthesis": 40_429,
                 "unextract": 103_035}
BANK_PAID_BY_STAGE = {"extract": 57_204, "synthesis": 16_767, "convert": 22_811,
                      "scan": 44_275, "unconvert": 26_155, "unsynthesis": 14_035,
                      "unextract": 101_497}
# paid gates where a bank qubit is a *control* (value is read to compute something)
BANK_CTRL_BY_STAGE = {"extract": 44_086, "synthesis": 1_788, "convert": 5_141,
                      "scan": 0, "unconvert": 6_366, "unsynthesis": 2_598,
                      "unextract": 74_480}


def cost(q: float, mean_t: float) -> float:
    return R * q * q * mean_t


def main() -> None:
    out = {}
    print(f"R={R}  eae: Q={Q0} static={STATIC0} mean={MEAN0:.0f} cost={COST0:.4e}")
    print(f"mean/static = {RATIO:.5f}\n")

    print("### 1. cost-neutral T ceiling at each Q (same cost as eae)")
    print(f"{'Q':>5s} {'meanT_max':>10s} {'static_max':>11s} {'vs eae mean':>12s} {'-11.3% cost if T same':>24s}")
    for q in (892, 888, 868, 864, 860, 852, 848, 844, 840):
        mt = COST0 / (R * q * q)
        print(f"{q:5d} {mt:10.0f} {mt / RATIO:11.0f} {mt - MEAN0:+12.0f} "
              f"{cost(q, MEAN0) / 1e11:11.4f}e11 ({(cost(q, MEAN0) / COST0 - 1) * 100:+6.2f}%)")
        out.setdefault("ceiling", {})[q] = {"mean_max": mt, "static_max": mt / RATIO,
                                            "cost_at_current_T": cost(q, MEAN0)}
    mt840 = COST0 / (R * 840 * 840)
    slack = mt840 - MEAN0
    print(f"\nQ=840: meanT ceiling {mt840:.0f}  (static {mt840 / RATIO:.0f}); "
          f"slack over eae = {slack:+.0f} mean T ({slack / MEAN0 * 100:+.2f}%)")
    out["q840_ceiling"] = {"mean_max": mt840, "static_max": mt840 / RATIO, "slack_mean": slack,
                           "slack_pct": slack / MEAN0}

    bank_paid = sum(BANK_PAID_BY_STAGE.values())
    bank_ctrl = sum(BANK_CTRL_BY_STAGE.values())
    print(f"\n### 2. measured bank census (52 ancilla)")
    print(f"paid gates touching bank : {bank_paid} = {bank_paid / STATIC0 * 100:.1f}% of all T")
    print(f"paid gates with bank as control (value read): {bank_ctrl}")
    print(f"equivalent 24-bit multiplication reads @99 control-CCX each: {bank_ctrl / 99:.0f}")
    print(f"equivalent 12-bit multiplication reads @42 control-CCX each: {bank_ctrl / 42:.0f}")
    out["bank"] = {"paid_touching": bank_paid, "pct_of_T": bank_paid / STATIC0,
                   "paid_control_only": bank_ctrl,
                   "equiv_24bit_mul_reads": bank_ctrl / 99,
                   "equiv_12bit_mul_reads": bank_ctrl / 42}

    print("\n### 3. recompute price per 24-bit word, and the net cost at Q=840")
    print(f"{'scenario':52s} {'static':>8s} {'mean':>9s} {'cost':>10s} {'vs eae':>8s}")
    rows = []

    def add(name, static):
        mean = static * RATIO
        c = cost(840, mean)
        rows.append((name, static, mean, c))
        print(f"{name:52s} {static:8.0f} {mean:9.0f} {c / 1e11:9.4f}e11 {(c / COST0 - 1) * 100:+7.2f}%")

    add("Q=840, bank dropped for free (upper bound)", STATIC0)
    for per_use, label in ((99, "99 T/mul24"), (190, "190 T/inverse24 fwd"), (290, "290 T/jet fwd")):
        for uses, ulabel in ((bank_ctrl / 99, f"{bank_ctrl / 99:.0f} 24-bit reads"),
                             (7 * 2, "1 regen/word/stage = 14")):
            add(f"regen per use @{label}, {ulabel}", STATIC0 + per_use * uses)
    add("regen once per direction from syndrome (extract T)", STATIC0 + PAID_BY_STAGE["extract"])
    add("regen twice (before convert, before unconvert)", STATIC0 + 2 * PAID_BY_STAGE["extract"])

    print(f"\ncheapest recompute row: {min(rows, key=lambda r: r[3])[0]} "
          f"-> {min(rows, key=lambda r: r[3])[3] / 1e11:.4f}e11")
    print(f"budget available for ALL extra T at Q=840 before par: {slack * 1.0:.0f} mean T "
          f"= {slack / RATIO:.0f} static T")
    out["recompute_rows"] = [{"name": n, "static": s, "mean": m, "cost": c} for n, s, m, c in rows]

    print("\n### 4. what the 4 flags alone are worth (drop 52->48 ancilla)")
    for q in (888, 840):
        print(f"Q={q}: cost x (Q/892)^2 = {(q / Q0) ** 2:.5f} -> {cost(q, MEAN0) / 1e11:.4f}e11 "
              f"({(cost(q, MEAN0) / COST0 - 1) * 100:+.2f}%)")
    out["q_scale"] = {q: {"factor": (q / Q0) ** 2, "cost": cost(q, MEAN0)} for q in (888, 840)}

    print("\n### 5. how much T a Q drop must buy (T budget multiplier)")
    print(f"{(840 / 892) ** 2:.5f} = Q^2 factor at Q=840 -> T may grow {1 / (840 / 892) ** 2 - 1:+.5f} "
          f"({(1 / (840 / 892) ** 2 - 1) * 100:+.2f}%) at par")
    out["q_factor"] = (840 / Q0) ** 2

    Path("experiments/dqi/20261112_q840/results").mkdir(parents=True, exist_ok=True)
    (Path("experiments/dqi/20261112_q840/results") / "ledger.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print("\nwrote experiments/dqi/20261112_q840/results/ledger.json")


if __name__ == "__main__":
    main()
