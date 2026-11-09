"""s5_fullstable.py: stability screen over ALL structural consecutive pairs.

Uses dirtyk2 a_groups.json (op-separated structural groups, members with
idx/op/a/b/t). For each group, greedy non-overlapping consecutive pairing;
each pair needs: both unconditional CCX (members are, by construction) and
no writes to L1's literals {a1,b1} in (L1, Lj] (Lj itself reads them).
Counts feasible pairs (= CCX saving with fresh-ancilla broadcast), and
reports net score with Q+1 penalty.

Writes artifacts/20261109_dqi_decoder_struct/s5_fullstable.json
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
GROUPS = Path("artifacts/20261109_dqi_dirtyk2/a_groups.json")
OUT = Path("artifacts/20261109_dqi_decoder_struct/s5_fullstable.json")

PER_GATE = 947843.0
Q = 892
R = 1.19126046
T_MEAN = 395356.94


def load_window(need):
    want = set(need)
    got = {}
    with open(KMX) as f:
        for idx, raw in enumerate(f):
            if idx in want:
                got[idx] = raw.strip()
                if len(got) == len(want):
                    break
    return got


def written_wires(op, args):
    if op == "CCX":
        return args[2:3]
    if op == "CX":
        return args[1:2]
    if op in ("X", "HMR", "R"):
        return args[0:1]
    if op == "SWAP":
        return args[0:2]
    if op == "CSWAP":
        return args[1:3]
    return []


def main() -> None:
    g = json.loads(GROUPS.read_text())
    all_feas = []
    for stage in ("unextract", "unsynthesis"):
        grps = g[stage]
        print(f"[{stage}] groups: {len(grps)}", flush=True)
        # collect all consecutive index pairs + all in-between lines
        cand = []  # (gid, i, m1, m2)
        need = set()
        for gid, grp in enumerate(grps):
            mem = sorted(grp["members"], key=lambda m: m["idx"])
            i = 0
            while i + 1 < len(mem):
                m1, m2 = mem[i], mem[i + 1]
                if m1["op"] == "CCX" and m2["op"] == "CCX":
                    cand.append((gid, i, m1, m2))
                    for x in range(m1["idx"] + 1, m2["idx"] + 1):
                        need.add(x)
                i += 2  # greedy non-overlapping
        print(f"[{stage}] candidate pairs: {len(cand)}, lines to load: {len(need)}", flush=True)
        txt = load_window(need)
        for gid, i, m1, m2 in cand:
            L1, L2 = m1["idx"], m2["idx"]
            a1, b1 = f"q{m1['a']}", f"q{m1['b']}"
            bad = []
            for x in range(L1 + 1, L2 + 1):
                s = txt[x]
                q = s.split()
                o = q[0]
                if o in ("PUSH_CONDITION", "POP_CONDITION", "INFO_TAG"):
                    bad.append((x, s[:60], "boundary"))
                    continue
                args = q[1:-2] if (len(q) >= 3 and q[-2] == "if") else q[1:]
                for w in written_wires(o, args):
                    if w in (a1, b1):
                        bad.append((x, s[:60], "write"))
                        break
            all_feas.append({"stage": stage, "gid": gid, "i": i, "L1": L1, "L2": L2,
                             "gap": L2 - L1,
                             "a1": m1["a"], "b1": m1["b"], "t1": m1["t"],
                             "a2": m2["a"], "b2": m2["b"], "t2": m2["t"],
                             "same_literal": {m1["a"], m1["b"]} == {m2["a"], m2["b"]},
                             "k": len(grps[gid].get("members", [])),
                             "stable": len(bad) == 0, "hits": bad[:3]})
    n_ok = sum(1 for r in all_feas if r["stable"])
    gaps = Counter(r["gap"] for r in all_feas if r["stable"])
    by_stage = Counter(r["stage"] for r in all_feas if r["stable"])
    saving = n_ok  # 1 CCX per pair
    out = {"n_candidate_pairs": len(all_feas), "n_stable": n_ok,
           "stable_by_stage": dict(by_stage),
           "saving_ccx": saving,
           "saving_score": saving * PER_GATE,
           "q_penalty": R * T_MEAN * ((Q + 1) ** 2 - Q ** 2),
           "stable_gap_hist": sorted(gaps.items())[:20],
           "stable_gap_max": max(gaps) if gaps else None,
           "pairs": all_feas}
    out["net_score"] = out["q_penalty"] - out["saving_score"]
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"stable: {n_ok}/{len(all_feas)} {dict(by_stage)} -> saving {saving} CCX = {out['saving_score']:.3e}")
    print(f"Q+1 penalty: {out['q_penalty']:.3e}  NET: {out['net_score']:+.3e} ({'BETTER' if out['net_score']<0 else 'WORSE'})")
    print(f"wrote {OUT}")


def grp_k(grps, gid):
    m = grps[gid].get("members", [])
    return len(m)


if __name__ == "__main__":
    main()
