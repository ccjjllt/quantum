"""Screen every parking candidate (wire, gap) for a quadratic rebuild at its gap exit.

Sample size 4096 legal x.  All-zero HMR branch is used for the fit; the *same* coefficient
set is then evaluated on two random condition-aware HMR branches (sample-level check).
Result: cost = rank (products/CCX), or null when no quadratic form exists.
"""
from __future__ import annotations

import json
import time

import branchsim
import common
import quadfit

OUT = common.ROOT / "artifacts/20261107_quadratic_61q"
NS = 4096


def main():
    pm = json.loads((common.OUT / "park_missing.json").read_text())
    cands = pm["candidates"]
    _, ops, gates, stacks = common.load_ops()
    stops = sorted({o["gap"][1] for o in cands})
    xs = quadfit.sample_xs(NS)
    print(f"candidates {len(cands)} exit ops {len(stops)}", flush=True)

    t = time.time()
    zero = branchsim.snapshot(gates, stacks, stops, xs, branch="zero")
    print(f"zero snapshot {time.time()-t:.1f}s", flush=True)
    rand = {}
    for seed in (101, 202):
        t = time.time()
        rand[seed] = branchsim.snapshot(gates, stacks, stops, xs, branch="random", seed=seed)
        print(f"random branch {seed} snapshot {time.time()-t:.1f}s", flush=True)

    rows = []
    t0 = time.time()
    for k, o in enumerate(cands):
        op, w = o["gap"][1], o["wire"]
        V = zero[op]
        res = quadfit.fit_snapshot(V, w, NS)
        row = {"wire": w, "gap": o["gap"], "gain": o["gain"], "next_instr": o["next_instr"]}
        if res is None:
            row.update({"cost": None, "rank": None, "monomials": None,
                        "branch_ok": None})
        else:
            coef, feats = res["coef"], res["feats"]
            branch_ok = {}
            for seed in (101, 202):
                Vr = rand[seed][op]
                branch_ok[str(seed)] = (quadfit.eval_poly(coef, feats, Vr, NS) == Vr[w])
            row.update({"cost": res["rank"], "rank": res["rank"],
                        "monomials": res["monomials"], "branch_ok": branch_ok})
        rows.append(row)
        if (k + 1) % 100 == 0:
            ok = sum(1 for r in rows if r["cost"] is not None and r["cost"] <= 7)
            print(f"  {k+1}/{len(cands)} fitted, <=7 products {ok}, "
                  f"{time.time()-t0:.0f}s", flush=True)
    (OUT / "fit_sample.json").write_text(json.dumps(rows, indent=1) + "\n")
    from collections import Counter
    c = Counter(r["cost"] for r in rows)
    print("cost histogram", dict(sorted(c.items(), key=lambda kv: (kv[0] is None, kv[0]))))
    bad = [r for r in rows if r["cost"] is not None and not all(r["branch_ok"].values())]
    print("branch-failing", len(bad))
    for r in bad[:20]:
        print("  ", r["wire"], r["gap"], r["rank"], r["branch_ok"])


if __name__ == "__main__":
    main()
