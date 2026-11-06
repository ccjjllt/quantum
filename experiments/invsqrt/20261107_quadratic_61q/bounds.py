"""Lower bounds and reference covers for the 61Q budget."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261106_q61"))
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261107_quadratic_61q"))
import common  # noqa: E402
import cover_dp  # noqa: E402

OUT = ROOT / "artifacts/20261107_quadratic_61q"


def main():
    pm = json.loads((common.OUT / "park_missing.json").read_text())
    peak = set(pm["peak_ops"])
    free = set(pm["free_covered"])
    v4 = json.loads((common.OUT / "commute_v4.json").read_text())
    comm = set()
    for c in v4["chosen"]:
        a, b = c["block"]
        comm |= set(range(a, b))
    missing = sorted(peak - free - comm)
    fit = json.loads((OUT / "fit_sample.json").read_text())
    verify = json.loads((OUT / "verify_full.json").read_text())
    failed = {(r["wire"], tuple(r["gap"])) for r in verify if not r["ok"]}
    rank = {}
    for r in fit:
        k = (r["wire"], tuple(r["gap"]))
        if r["cost"] is not None and k not in failed:
            rank[k] = r["cost"]

    def solve(costfn, target):
        for o in pm["candidates"]:
            k = (o["wire"], tuple(o["gap"]))
            o["_cost"] = costfn(k) if k in rank else float("inf")
        usable = [o for o in pm["candidates"] if o["_cost"] != float("inf")]
        c, chosen = cover_dp.solve(target, cover_dp.intervals(usable, target))
        return c, len(chosen) if chosen else None

    bounds = {}
    bounds["exact_fit_ranks"] = solve(lambda k: rank[k], missing)
    bounds["rank1_free_rank5_floor"] = solve(
        lambda k: 0 if rank[k] == 1 else 5, missing)
    bounds["rank1_one_rank5_floor"] = solve(
        lambda k: 1 if rank[k] == 1 else 5, missing)
    bounds["all_cost_one"] = solve(lambda k: 1, missing)

    cs = json.loads((common.OUT / "commute_summary.json").read_text())
    q61_missing = set()
    for a, b in cs["uncovered_runs"]:
        q61_missing |= set(range(a, b))
    bounds["q61_9C_base_extension"] = solve(lambda k: rank[k], sorted(q61_missing))
    bounds["q61_9C_base_total"] = bounds["q61_9C_base_extension"][0] + 9

    bounds["budget"] = 25.833098
    (OUT / "bounds.json").write_text(json.dumps(bounds, indent=1) + "\n")
    print(json.dumps(bounds, indent=1))


if __name__ == "__main__":
    main()
