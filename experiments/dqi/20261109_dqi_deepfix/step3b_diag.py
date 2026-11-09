"""Step 3b: carrier-gap diagnostic + finder sanity.

- Finder sanity: known-easy short interval in a quiet window must return carriers.
- For top structural groups: #idle wires in span, #HMR-zeroed idle, min touches.
Writes artifacts/20261109_dqi_deepfix/step3b_diag.json
"""
from __future__ import annotations
import array
import bisect
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step3b_diag.json")
TOP = Path("artifacts/20261109_dqi_deepfix/step2a_topgroups.json")

def parse():
    stage = "header"; stack: list[str] = []; depth = 0
    with open(KMX) as f:
        for idx, raw in enumerate(f):
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:]); stage = stack[0]
                elif tag.startswith("@exit:") and stack:
                    stack.pop(); stage = stack[0] if stack else "header"
                continue
            if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
                continue
            if l.startswith("PUSH_CONDITION"):
                depth += 1; continue
            if l.startswith("POP_CONDITION"):
                depth -= 1; continue
            parts = l.split(); op = parts[0]
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]; args = parts[1:-2]
            else:
                inline = None; args = parts[1:]
            yield idx, stage, op, args, inline, depth

def main():
    occ = {q: array.array("I") for q in range(840, 892)}
    zero_at = {}
    for idx, st, op, args, inline, depth in parse():
        cond = (depth > 0) or (inline is not None)
        if op in ("HMR", "R") and not cond and args and args[0][0] == "q":
            from collections import namedtuple
            zero_at[idx] = int(args[0][1:])
        if st not in ("unsynthesis", "unextract"):
            continue
        if op in ("X", "CX", "SWAP", "HMR", "R", "CCX", "CCZ", "CSWAP", "CZ"):
            for tok in args:
                if tok and tok[0] == "q":
                    q = int(tok[1:])
                    if 840 <= q <= 891:
                        occ[q].append(idx)
    O = {q: list(v) for q, v in occ.items()}

    def touches(w, lo, hi):
        lst = O[w]
        i = bisect.bisect_left(lst, lo)
        j = bisect.bisect_right(lst, hi)
        return j - i

    def last_before(w, pos):
        lst = O[w]
        i = bisect.bisect_left(lst, pos) - 1
        return lst[i] if i >= 0 else -1

    # sanity: quiet early-unextract window (from 200k scan: 3 windows with 24 busy).
    # find first 200k window with <52 busy, take a 10k sub-interval, expect carriers.
    lo_all = min(v[0] for v in O.values())
    w = lo_all
    found = None
    while w < lo_all + 30 * 200_000:
        busy = [q for q in range(840, 892)
                if bisect.bisect_right(O[q], w) < len(O[q]) and O[q][bisect.bisect_right(O[q], w)] < w + 200_000]
        if len(busy) < 52:
            found = (w, busy)
            break
        w += 200_000
    print(f"first non-full 200k window at {found[0] if found else None} busy={len(found[1]) if found else None}", flush=True)
    sanity = {}
    if found:
        w0, _ = found
        L1, Lk = w0 + 1000, w0 + 11000
        idle = [q for q in range(840, 892) if touches(q, L1, Lk) == 0]
        zeroed = [q for q in idle if last_before(q, L1) in zero_at]
        sanity = {"L1": L1, "Lk": Lk, "n_idle": len(idle), "n_zeroed": len(zeroed),
                  "zeroed": zeroed[:8]}
        print(f"sanity 10k interval: idle={len(idle)} zeroed={len(zeroed)} e.g.{zeroed[:8]}", flush=True)

    det = json.load(open(TOP))
    rows = []
    for st in ("unsynthesis", "unextract"):
        for g in det[st][:10]:
            L1, Lk = g["L1"], g["Lk"]
            mw = {(m["a"], m["b"], m["t"]) for m in g["members"]}
            flat = set()
            for a, b, t in mw:
                flat.add(a); flat.add(b); flat.add(t)
            tc = [touches(q, L1, Lk) for q in range(840, 892)]
            idle = [q for q in range(840, 892) if tc[q - 840] == 0 and q not in flat]
            zeroed = [q for q in idle if last_before(q, L1) in zero_at]
            rows.append({"stage": st, "k": g["k"], "span": Lk - L1, "L1": L1,
                         "nlits": g["nlits"], "min_touch": min(tc),
                         "n_idle": len(idle), "n_zeroed_idle": len(zeroed)})
            print(f"{st} k={g['k']} span={Lk-L1} min_touch={min(tc)} idle={len(idle)} zeroed={len(zeroed)}", flush=True)
    OUT.write_text(json.dumps({"sanity": sanity, "groups": rows}, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
