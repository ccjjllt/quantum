"""Combine parking + commutation + nonlinear rebuild into the final 61Q budget table."""
from __future__ import annotations

import json

import common


def main():
    peak = set(json.loads((common.OUT / "commute_summary.json").read_text())["uncovered_runs"]
               and [])
    cs = json.loads((common.OUT / "commute_summary.json").read_text())
    peak = set()
    for a, b in cs["uncovered_runs"]:
        peak |= set(range(a, b))
    # reconstruct the full peak set from commute_v4 rows
    v4 = json.loads((common.OUT / "commute_v4.json").read_text())
    allpeak = set()
    for r in v4["rows"]:
        a, b = r["block"]
        allpeak |= set(range(a, b))
    covered_before = allpeak - peak          # parking + commutation
    assert len(covered_before) == cs["union_ops"]
    ri = json.loads((common.OUT / "rebuild_intervals.json").read_text())
    added_ops, added_cost = 0, 0
    parts = []
    for r in ri:
        a, b = r["interval"]
        good = [c for c in r["cands"] if c["k"] is not None and c["k"] <= 2]
        if not good:
            continue
        best = min(good, key=lambda c: (c["k"], c["rebuild_op"]))
        parts.append({"interval": [a, b], "len": b - a, "wire": best["wire"],
                      "rebuild_op": best["rebuild_op"], "k": best["k"]})
        added_ops += b - a
        added_cost += best["k"]
    total_ops = len(covered_before) + added_ops
    total_cost = cs["parking_cost_C"] + added_cost
    print(f"peak ops                          {len(allpeak)}")
    print(f"parking + commutation             {len(covered_before)} ops, {cs['parking_cost_C']} C")
    print(f"nonlinear rebuild                 {added_ops} ops, {added_cost} C  {parts}")
    print(f"total covered                     {total_ops} ops")
    print(f"total cost                        {total_cost} C   (budget {cs['budget_C']})")
    print(f"uncovered                         {len(allpeak) - total_ops} ops")
    left = sorted(allpeak - covered_before)
    covered_extra = set()
    for p in parts:
        covered_extra |= set(range(*p["interval"]))
    left = sorted(set(left) - covered_extra)
    runs = []
    for i in left:
        if runs and runs[-1][1] == i:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    print(f"remaining runs                    {len(runs)}")
    for a, b in runs:
        print(f"   [{a},{b}) len {b-a}")
    out = {"peak_ops": len(allpeak), "parking_commutation_ops": len(covered_before),
           "parking_commutation_C": cs["parking_cost_C"],
           "nonlinear_ops": added_ops, "nonlinear_C": added_cost,
           "nonlinear_parts": parts, "total_ops": total_ops, "total_C": total_cost,
           "budget_C": cs["budget_C"], "remaining_ops": len(allpeak) - total_ops,
           "remaining_runs": runs,
           "verdict": "no 61Q schedule: remaining peak ops have no cheap rebuild"}
    (common.OUT / "nonlinear_summary.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
