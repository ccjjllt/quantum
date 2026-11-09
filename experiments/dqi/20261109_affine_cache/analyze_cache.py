"""Pass 2: group CCX/CCZ sites by product fingerprint, check idle-wire
feasibility, greedy cache-wire assignment, emit predicted savings + rewrite plan.

Rewrite template per group (sites L1..Lk, cache wire w, fresh bit m):
  L1: CCX a1 b1 t1  ->  CCX a1 b1 w ; CX w t1        (Toffoli-neutral, +1 CX)
      CCZ a1 b1 t1  ->  CCX a1 b1 w ; CZ w t1        (Toffoli-neutral, +1 CZ)
  Li: CCX ai bi ti  ->  CX w ti                      (-1 Toffoli)
      CCZ ai bi ti  ->  CZ w ti   (ti = the wire not in the matched pair)
  after Lk: HMR w m ; CZ ak bk if m                  (~free erase)
Net per group: -(k-1) static Toffoli-like.
"""
from __future__ import annotations

import bisect
import json
import pickle
from pathlib import Path

INP = Path("artifacts/20261109_affine_cache/sim_out.pkl")
OUT = Path("artifacts/20261109_affine_cache/cache_analysis.json")
PLAN = Path("artifacts/20261109_affine_cache/rewrite_plan.json")
BIT_BASE = 200003  # first fresh classical bit (frontier num_bits == 200003)


def main() -> None:
    with open(INP, "rb") as f:
        d = pickle.load(f)
    sites = d["sites"]          # (idx, stage, op, a, b, t, fa, fb)
    zero_events = d["zero_events"]
    occ = d["occ"]              # ancilla -> array('I')
    print(f"sites={len(sites)} zero_events={len(zero_events)} "
          f"s_lo={d['s_lo']} a_lo={d['a_lo']} unknown={d['unknown']}")
    assert d["s_lo"] == 0 and d["a_lo"] == 0, "simulator self-check FAILED"

    zero_at = {}  # line idx -> q (unconditional HMR/R)
    for idx, q in zero_events:
        zero_at[idx] = q
    occ_lists = {q: list(v) for q, v in occ.items()}

    # Group by product fingerprint. CCZ: pair as listed (a&b); record all pairs.
    groups: dict[int, list[int]] = {}
    site_prod = {}
    for n, s in enumerate(sites):
        idx, stage, op, a, b, t, fa, fb = s
        fp = fa & fb
        site_prod[n] = fp
        groups.setdefault(fp, []).append(n)
    multi = {fp: v for fp, v in groups.items() if len(v) >= 2}
    print(f"distinct products={len(groups)} groups(k>=2)={len(multi)} "
          f"covered_sites={sum(len(v) for v in multi.values())}")

    # size histogram
    from collections import Counter
    print("group-size histogram:", sorted(Counter(len(v) for v in multi.values()).items()))

    # Zero-state helper: last original touch of w before L1.
    def last_touch_before(w: int, pos: int) -> int:
        lst = occ_lists[w]
        i = bisect.bisect_left(lst, pos) - 1
        return lst[i] if i >= 0 else -1

    def has_touch_in(w: int, lo_excl: int, hi_excl: int) -> bool:
        lst = occ_lists[w]
        i = bisect.bisect_right(lst, lo_excl)
        return i < len(lst) and lst[i] < hi_excl

    cands = []
    for fp, members in multi.items():
        members.sort(key=lambda n: sites[n][0])
        L = [sites[n][0] for n in members]
        ops = [sites[n][2] for n in members]
        cands.append({"fp": fp, "members": members, "L": L, "k": len(members),
                      "n_ccx": sum(1 for o in ops if o == "CCX"),
                      "n_ccz": sum(1 for o in ops if o == "CCZ")})
    # biggest groups first (more savings), tie-break by earliest start
    cands.sort(key=lambda c: (-c["k"], c["L"][0]))

    reserved: dict[int, list[tuple[int, int]]] = {q: [] for q in occ_lists}
    chosen = []
    for c in cands:
        L1, Lk = c["L"][0], c["L"][-1]
        best = None
        for w in range(840, 892):
            if any(not (Lk + 1 <= s or L1 >= e) for s, e in reserved[w]):
                continue
            if has_touch_in(w, L1, Lk):
                continue
            if any(sites[n][3] == w or sites[n][4] == w or sites[n][5] == w
                   for n in c["members"]):
                continue
            o0 = last_touch_before(w, L1)
            if o0 >= 0 and o0 not in zero_at:
                continue
            best = w
            break
        if best is not None:
            reserved[best].append((L1, Lk + 1))
            c["wire"] = best
            c["save"] = c["k"] - 1
            chosen.append(c)

    total = sum(c["save"] for c in chosen)
    print(f"feasible groups={len(chosen)} predicted net Toffoli-like saving={total}")
    for c in chosen[:40]:
        print(f"  k={c['k']} save={c['save']} wire=q{c['wire']} "
              f"L1={c['L'][0]} Lk={c['L'][-1]} ccx={c['n_ccx']} ccz={c['n_ccz']}")

    OUT.write_text(json.dumps({
        "n_sites": len(sites),
        "n_distinct_products": len(groups),
        "n_multi_groups": len(multi),
        "n_feasible_groups": len(chosen),
        "predicted_net_saving": total,
        "groups": [{k: (v if k != "members" else None) for k, v in c.items()
                    if k != "fp"} | {"fp_hex": hex(c["fp"])}
                   for c in chosen],
    }, indent=1) + "\n")

    plan = []
    for j, c in enumerate(chosen):
        plan.append({"group": j, "wire": c["wire"], "bit": BIT_BASE + j,
                     "save": c["save"],
                     "sites": [
                         {"idx": sites[n][0], "stage": sites[n][1], "op": sites[n][2],
                          "a": sites[n][3], "b": sites[n][4], "t": sites[n][5]}
                         for n in c["members"]]})
    PLAN.write_text(json.dumps(plan, indent=1) + "\n")
    print(f"wrote {OUT} and {PLAN}")


if __name__ == "__main__":
    main()
