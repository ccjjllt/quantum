"""Classify every scratch wire of the baseline by lifecycle pattern (read-only)."""
from __future__ import annotations

import collections
import json

import common


def main():
    _, ops, gates, stacks = common.load_ops()
    table = []
    for q in range(22, 62):
        segs = common.conservative_segments(gates, stacks, q)
        kinds = collections.Counter()
        roles = collections.Counter()
        first_instr = None
        for i, (k, qs, p) in enumerate(gates):
            if q not in qs:
                continue
            if first_instr is None:
                first_instr = ops[i]
            kinds[k] += 1
            if q in common.written(k, qs):
                roles["write"] += 1
                if k in common.PAID:
                    roles["paid_write"] += 1
            elif k in {"CX", "CCX", "CSWAP"}:
                roles["qcontrol"] += 1
            elif k in {"CZ", "CCZ"}:
                roles["phase"] += 1
            else:
                roles["other"] += 1
        touches = sum(kinds.values())
        table.append({
            "q": q, "first": first_instr, "nseg": len(segs),
            "segments": [[a, b] for a, b, _ in segs],
            "touches": touches, "roles": dict(roles), "kinds": dict(kinds),
            "paid": sum(kinds[k] for k in common.PAID),
        })
    print(f"{'q':>3} {'first op':<14} {'seg':>3} {'touch':>6} {'paid':>5} {'w':>4} {'pw':>4} "
          f"{'qctl':>5} {'phase':>5} {'other':>5}  segments")
    for r in table:
        rr = r["roles"]
        print(f"{r['q']:>3} {r['first'][:14]:<14} {r['nseg']:>3} {r['touches']:>6} {r['paid']:>5} "
              f"{rr.get('write',0):>4} {rr.get('paid_write',0):>4} {rr.get('qcontrol',0):>5} "
              f"{rr.get('phase',0):>5} {rr.get('other',0):>5}  {r['segments'][:4]}")
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "scratch_table.json").write_text(json.dumps(table, indent=1) + "\n")


if __name__ == "__main__":
    main()
