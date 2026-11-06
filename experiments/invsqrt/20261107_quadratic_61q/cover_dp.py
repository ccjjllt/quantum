"""Exact weighted interval cover of the peak ops left by free parking + commutation.

The q61 free parking options cover 1,918 of the 2,550 value-live 62-peak ops at 0 C.
The q61 sound commutation cover (`commute_v4.json` chosen blocks) adds 54 more ops at 0 C.
Every remaining option covers a contiguous run of the missing ops (in peak-op order), so the
minimum-cost cover is a shortest path / interval DP, not a greedy heuristic.

Costs come from a JSON map (wire, gap) -> cost; missing entries are unusable (infinite).
Use `--uniform 1` to price every candidate at 1 C (optimistic lower bound).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261106_q61"))
import common  # noqa: E402

OUT = ROOT / "artifacts/20261107_quadratic_61q"


def intervals(cands, missing):
    """For each candidate, the inclusive index range it covers in `missing`."""
    idx = {op: i for i, op in enumerate(missing)}
    out = []
    for o in cands:
        left, right = o["gap"]
        # peak ops strictly inside the gap
        ops = [i for i in o["covered"] if left < i < right and i in idx]
        if not ops:
            continue
        out.append((min(idx[i] for i in ops), max(idx[i] for i in ops), o))
    return out


def solve(missing, ivs):
    n = len(missing)
    INF = float("inf")
    dp = [INF] * (n + 1)
    prev = [None] * (n + 1)
    dp[0] = 0
    by_l = defaultdict(list)
    for l, r, o in ivs:
        by_l[l].append((r, o))
    for i in range(n):
        if dp[i] == INF:
            continue
        # any interval that starts at or before i and covers i
        for l in range(0, i + 1):
            for r, o in by_l[l]:
                if r < i:
                    continue
                c = o["_cost"]
                if dp[i] + c < dp[r + 1]:
                    dp[r + 1] = dp[i] + c
                    prev[r + 1] = (i, o)
    if dp[n] == INF:
        return None, None
    chosen = []
    j = n
    while j > 0:
        i, o = prev[j]
        chosen.append(o)
        j = i
    chosen.reverse()
    return dp[n], chosen


def commutation_ops():
    v4 = json.loads((common.OUT / "commute_v4.json").read_text())
    out = set()
    for c in v4["chosen"]:
        a, b = c["block"]
        out |= set(range(a, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--costs", default=str(OUT / "fit_sample.json"))
    ap.add_argument("--uniform", type=float, default=None)
    ap.add_argument("--no-commutation", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pm = json.loads((common.OUT / "park_missing.json").read_text())
    cands = pm["candidates"]
    peak = set(pm["peak_ops"])
    free = set(pm["free_covered"])
    comm = set() if args.no_commutation else commutation_ops()
    free |= comm
    missing = sorted(peak - free)
    costs = {}
    if args.uniform is None:
        rows = json.loads(open(args.costs).read())
        for r in rows:
            key = (r["wire"], tuple(r["gap"]))
            if r.get("cost") is not None and all(r.get("branch_ok", {}).values()):
                costs[key] = r["cost"]
        # reject options that failed exact full-domain verification
        vpath = OUT / "verify_full.json"
        if vpath.exists():
            for r in json.loads(vpath.read_text()):
                if not r["ok"]:
                    costs[(r["wire"], tuple(r["gap"]))] = float("inf")
    for o in cands:
        key = (o["wire"], tuple(o["gap"]))
        o["_cost"] = args.uniform if args.uniform is not None else costs.get(key, float("inf"))
    usable = [o for o in cands if o["_cost"] != float("inf")]
    print(f"peak {len(peak)}  free parking {len(pm['free_covered'])}  "
          f"free commutation {len(comm & peak)}  union {len(free & peak)}  "
          f"missing {len(missing)}  candidates {len(cands)}  usable {len(usable)}")
    ivs = intervals(usable, missing)
    cost, chosen = solve(missing, ivs)
    if cost is None:
        print("NO COVER")
        return
    print(f"minimum added C = {cost:.4f}  (budget 25.833098, 61Q)")
    for o in chosen:
        print(f"  q{o['wire']:>2} gap {o['gap']} cost {o['_cost']:>4} "
              f"covers {o['gain']:>3} peak ops, exit {o['next_instr']}")
    covered = set()
    for o in chosen:
        left, right = o["gap"]
        covered |= {i for i in missing if left < i < right}
    left = sorted(set(missing) - covered)
    print(f"covered {len(covered)}/{len(missing)} missing; leftover {len(left)}")
    if left:
        runs = []
        for i in left:
            if runs and runs[-1][1] == i:
                runs[-1][1] = i + 1
            else:
                runs.append([i, i + 1])
        print("leftover runs", runs[:20])
    if args.out:
        json.dump({"cost": cost,
                   "free_covered": len(free & peak),
                   "commutation_covered": len(comm & peak),
                   "missing": len(missing),
                   "chosen": [{k: v for k, v in o.items() if k != "covered"}
                              for o in chosen]},
                  open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
