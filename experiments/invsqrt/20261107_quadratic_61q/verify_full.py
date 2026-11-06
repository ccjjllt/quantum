"""Exact full-domain + random-branch verification of selected quadratic rebuilds.

For each (wire, gap), refit on the 4096-x all-zero branch, then evaluate the SAME polynomial
on all 3,133,452 legal x on:
  * the all-zero HMR branch (condition-aware),
  * two random HMR branches (condition-aware).
A sample fit that fails any of these is rejected.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

import branchsim
import common
import quadfit

OUT = common.ROOT / "artifacts/20261107_quadratic_61q"
MAXX = 3133452
NS = 4096


def main():
    # Options to verify: chosen cover + six reported positives + all cost-1 options.
    chosen = json.loads((OUT / "cover_fit_sample.json").read_text())["chosen"]
    rows = json.loads((OUT / "fit_sample.json").read_text())
    specs = {(o["wire"], tuple(o["gap"])) for o in chosen}
    for r in rows:
        if r["cost"] is not None and r["cost"] <= 1:
            specs.add((r["wire"], tuple(r["gap"])))
    for w, g in [(42, (16652, 16877)), (40, (17586, 17921)), (52, (18473, 18483)),
                 (61, (16712, 16886)), (43, (15211, 16222)), (57, (15243, 15306))]:
        specs.add((w, g))
    specs = sorted(specs, key=lambda x: (x[1][1], x[0]))
    print(f"verifying {len(specs)} options", flush=True)

    _, ops, gates, stacks = common.load_ops()
    stops = sorted({g[1] for _, g in specs})
    xs_sample = quadfit.sample_xs(NS)
    t = time.time()
    zero_sample = branchsim.snapshot(gates, stacks, stops, xs_sample, branch="zero")
    print(f"sample zero snapshot {time.time()-t:.1f}s", flush=True)

    fits = {}
    for w, g in specs:
        op = g[1]
        res = quadfit.fit_snapshot(zero_sample[op], w, NS)
        assert res is not None
        fits[(w, g)] = res

    xs_full = np.arange(1, MAXX + 1, dtype=np.int64)
    results = []
    for branch, seed in [("zero", 0), ("random", 101), ("random", 202)]:
        t = time.time()
        snaps = branchsim.snapshot(gates, stacks, stops, xs_full, branch=branch, seed=seed)
        print(f"full {branch} {seed} snapshot {time.time()-t:.1f}s", flush=True)
        full = (1 << MAXX) - 1
        for w, g in specs:
            op = g[1]
            V = snaps[op]
            res = fits[(w, g)]
            got = quadfit.eval_poly(res["coef"], res["feats"], V, MAXX)
            ok = got == V[w]
            results.append({"wire": w, "gap": list(g), "op": op, "branch": branch,
                            "seed": seed, "ok": bool(ok), "rank": res["rank"],
                            "monomials": res["monomials"]})
            print(f"  q{w} gap {g} op {op}: {branch}/{seed} {'PASS' if ok else 'FAIL'} "
                  f"(rank {res['rank']}, {res['monomials']} monomials)", flush=True)
        del snaps
    (OUT / "verify_full.json").write_text(json.dumps(results, indent=1) + "\n")
    bad = [r for r in results if not r["ok"]]
    print(f"\n{len(results)-len(bad)}/{len(results)} checks PASS; {len(bad)} FAIL")


if __name__ == "__main__":
    main()
