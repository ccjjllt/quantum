"""Emit the final cost table, cover summary and per-run assignment."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261106_q61"))
import common  # noqa: E402

OUT = ROOT / "artifacts/20261107_quadratic_61q"
BUDGET = 25.833098


def runs_of(ops):
    ops = sorted(ops)
    out = []
    for i in ops:
        if out and out[-1][1] == i:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return out


def main():
    pm = json.loads((common.OUT / "park_missing.json").read_text())
    peak = set(pm["peak_ops"])
    v4 = json.loads((common.OUT / "commute_v4.json").read_text())
    comm = set()
    for c in v4["chosen"]:
        a, b = c["block"]
        comm |= set(range(a, b))
    free = set(pm["free_covered"]) | comm
    missing = set(peak - free)
    fit = json.loads((OUT / "fit_sample.json").read_text())
    cover = json.loads((OUT / "cover_fit_sample.json").read_text())
    verify = json.loads((OUT / "verify_full.json").read_text())
    vmap = defaultdict(list)
    for r in verify:
        vmap[(r["wire"], tuple(r["gap"]))].append(r)
    failed = {(r["wire"], tuple(r["gap"])) for r in verify if not r["ok"]}

    chosen = cover["chosen"]
    for o in chosen:
        o["missing_gain"] = len({i for i in missing if o["gap"][0] < i < o["gap"][1]})
    total = sum(o["_cost"] for o in chosen)
    covered = set()
    for o in chosen:
        covered |= {i for i in missing if o["gap"][0] < i < o["gap"][1]}
    assert covered == missing

    # per-run assignment
    runs = runs_of(missing)
    assign = []
    for a, b in runs:
        opts = [o for o in chosen if any(a <= i < b for i in
                [j for j in missing if o["gap"][0] < j < o["gap"][1]])]
        assign.append({"run": [a, b], "len": b - a,
                       "options": [{"wire": o["wire"], "gap": o["gap"],
                                    "cost": o["_cost"]} for o in opts]})

    # CSV of all options
    with open(OUT / "cost_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wire", "gap_left", "gap_right", "exit_op", "next_instr",
                    "monomials", "rank_products", "sample_branch_ok",
                    "full_domain_verified"])
        for r in fit:
            key = (r["wire"], tuple(r["gap"]))
            checks = vmap.get(key, [])
            w.writerow([r["wire"], r["gap"][0], r["gap"][1], r["gap"][1],
                        r["next_instr"], r["monomials"], r["cost"],
                        "" if r["branch_ok"] is None else all(r["branch_ok"].values()),
                        (all(c["ok"] for c in checks) if checks else "")])

    summary = {
        "peak_ops": len(peak),
        "free_parking": len(pm["free_covered"]),
        "free_commutation": len(comm & peak),
        "free_union": len(free & peak),
        "missing": len(missing),
        "candidate_options": len(fit),
        "usable_options": sum(1 for r in fit if r["cost"] is not None
                              and (r["wire"], tuple(r["gap"])) not in failed),
        "cost_histogram": {},
        "minimum_cover_C": total,
        "budget_C": BUDGET,
        "shortfall_C": total - BUDGET,
        "chosen": [{k: v for k, v in o.items() if k != "covered"} for o in chosen],
        "missing_runs": runs,
        "run_assignment": assign,
        "notes": ("Minimum exact interval cover using ranks fitted on 4096 x, the q61 "
                  "free-parking set and the q61 sound commutation blocks. All chosen "
                  "rebuilds were verified on all 3,133,452 legal x on the all-zero branch "
                  "and two random condition-aware HMR branches."),
    }
    from collections import Counter
    summary["cost_histogram"] = dict(Counter(r["cost"] for r in fit))
    (OUT / "cover_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("chosen", "run_assignment", "missing_runs")}, indent=1))
    print("\nchosen:")
    for o in chosen:
        print(f"  q{o['wire']:>2} gap {o['gap']} cost {o['_cost']} "
              f"missing_gain {o['missing_gain']} exit {o['next_instr']}")


if __name__ == "__main__":
    main()
