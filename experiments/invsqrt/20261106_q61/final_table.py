"""Final summary table for the 61Q investigation (read-only over the baseline)."""
from __future__ import annotations

import collections
import json

import common

CANDIDATES = [49, 34, 53, 35, 33, 23, 59, 56, 24]


def main():
    _, ops, gates, stacks = common.load_ops()
    vl = {int(k[1:]): [tuple(x) for x in v]
          for k, v in json.loads((common.OUT / "value_liveness.json").read_text())["value_liveness"].items()}
    agg = json.loads((common.OUT / "park_cover_cost.json").read_text())
    eff = json.loads((common.OUT / "effective_use.json").read_text())
    span = {r["q"]: set(r["hit_ops"])
            for r in json.loads((common.OUT / "span_test.json").read_text())}
    bound = {r["q"]: r for r in json.loads((common.OUT / "peak_bound.json").read_text())}

    rows = []
    for q in CANDIDATES:
        segs = common.conservative_segments(gates, stacks, q)
        kinds = collections.Counter()
        roles = collections.Counter()
        clears = []
        cond_depth = collections.Counter()
        writes = []
        for i, (k, qs, p) in enumerate(gates):
            if q not in qs:
                continue
            kinds[k] += 1
            cond_depth[len(stacks[i])] += 1
            if q in common.written(k, qs):
                roles["write"] += 1
                writes.append(i)
                if k in common.PAID:
                    roles["paid_write"] += 1
            elif k in {"CX", "CCX", "CSWAP"}:
                roles["qcontrol"] += 1
            elif k in {"CZ", "CCZ"}:
                roles["phase"] += 1
            else:
                roles["other"] += 1
            if k in {"HMR", "R"} and qs[0] == q:
                clears.append([i, k, "unconditional" if not stacks[i] and "if" not in p else "conditional"])
        rows.append({
            "q": q, "segments": [[a, b] for a, b, _ in segs],
            "value_intervals": vl[q],
            "uses": sum(kinds.values()), "kinds": dict(kinds), "roles": dict(roles),
            "clears": clears,
            "uses_in_cond_stack": sum(v for d, v in cond_depth.items() if d),
            "peak_uses": bound[q]["peak_uses"], "peak_paid": bound[q]["peak_paid"],
            "peak_linear": bound[q]["peak_linear"], "peak_nonlinear": bound[q]["peak_nonlinear"],
            "total_linear_uses_all_seeds": len(span[q]),
            "const0_uses": eff[f"q{q}"]["const0"], "const1_uses": eff[f"q{q}"]["const1"],
        })
    print(f"{'q':>3} {'uses':>5} {'paid':>5} {'writes':>6} {'pw':>3} {'qctl':>5} {'phase':>5} "
          f"{'HMR/R':>5} {'cond':>4} {'peak':>5} {'pkpaid':>6} {'pklin':>5} {'pknonlin':>8} "
          f"{'lin_all':>7} {'const0':>6}")
    for r in rows:
        ro = r["roles"]
        print(f"{r['q']:>3} {r['uses']:>5} {sum(r['kinds'].get(k,0) for k in common.PAID):>5} "
              f"{ro.get('write',0):>6} {ro.get('paid_write',0):>3} {ro.get('qcontrol',0):>5} "
              f"{ro.get('phase',0):>5} {len(r['clears']):>5} {r['uses_in_cond_stack']:>4} "
              f"{r['peak_uses']:>5} {r['peak_paid']:>6} {r['peak_linear']:>5} "
              f"{r['peak_nonlinear']:>8} {r['total_linear_uses_all_seeds']:>7} {r['const0_uses']:>6}")
    (common.OUT / "final_table.json").write_text(json.dumps(rows, indent=1) + "\n")
    print("\npark cover (greedy, cost model: free reinit/linear vs >=1 C read):")
    for c in agg["chosen"]:
        print(f"  q{c['wire']} gap {c['gap']} covers {len(c['covered'])} cost={c['cost']} {c['why']}")


if __name__ == "__main__":
    main()
