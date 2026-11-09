"""Exact affine-canonical product grouping for unsynthesis+unextract.

Single forward pass over kmx lines with F2-affine symbolic tracking:
- basis = symbolic values at unsynthesis entry (892 vars as int masks)
- X/CX/SWAP (unconditional, stack-free): affine update
- HMR/R (unconditional, stack-free): clean 0; else dirty
- any value-op under stack or with inline-if: dirty its value-targets
- CSWAP: dirty swapped wires (nonlinear select)
- CCX (unconditional, stack-free): record site if controls clean; target
  handled by exact compute/uncompute pairing (same unordered {a,b},t with
  no value-writes to {a,b,t} between -> t restored to pre-first snapshot).
  a==b degenerates to linear (CX); t in {a,b} never pairs (guard).
- CCZ/CZ/Z: diagonal, no value change (CCZ sites grouped by listed pair).

Grouping key (strict, exact-function): sorted ((ma,ca),(mb,cb)).
Reuse template per group (cache wire w, fresh bit m):
  L1: CCX a1 b1 t1 -> CCX a1 b1 w ; CX w t1
  Li: CCX ai bi ti -> CX w ti              (-1 Toffoli each)
  after Lk: HMR w m ; CZ ak bk if m
Net per group: -(k-1) static Toffoli-like. All exact, no simulation.
"""
from __future__ import annotations

import array
import bisect
import io
import json
import pickle
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
PKL = Path("artifacts/20261109_affine_cache/sim_out.pkl")
OUT = Path("artifacts/20261109_affine_cache/affine_groups.json")
PLAN = Path("artifacts/20261109_affine_cache/affine_plan.json")
BIT_BASE = 200003


def parse_lines():
    """Yield (idx, stage, op, args, inline, depth) for value-relevant lines."""
    stage = "header"
    stack: list[str] = []
    depth = 0
    with open(KMX) as f:
        for idx, raw in enumerate(f):
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                    stage = stack[0]
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    stage = stack[0] if stack else "header"
                continue
            if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
                continue
            if l.startswith("PUSH_CONDITION"):
                depth += 1
                continue
            if l.startswith("POP_CONDITION"):
                depth -= 1
                continue
            parts = l.split()
            op = parts[0]
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]
                args = parts[1:-2]
            else:
                inline = None
                args = parts[1:]
            yield idx, stage, op, args, inline, depth


def qid(tok: str) -> int:
    assert tok[0] == "q"
    return int(tok[1:])


def main() -> None:
    IN_STAGES = ("unsynthesis", "unextract")
    mask = {q: 1 << q for q in range(892)}
    const = {q: 0 for q in range(892)}
    clean = set(range(892))
    last_write = {q: -1 for q in range(892)}  # value-write line idx
    pending: dict[tuple, tuple[int, int, int]] = {}  # (fa,fb,t) -> (line, emask, econst)
    n_pair = 0
    n_constprod = 0
    sites: list[tuple] = []  # (idx, stage, op, a, b, t, ka, kb)
    zero_events: list[tuple[int, int]] = []
    occ: dict[int, array.array] = {q: array.array("I") for q in range(840, 892)}
    n_cond_ccx = 0

    def dirty(q: int, idx: int) -> None:
        clean.discard(q)
        mask.pop(q, None)
        last_write[q] = idx

    def set_affine(q: int, m: int, c: int, idx: int) -> None:
        mask[q] = m
        const[q] = c
        clean.add(q)
        last_write[q] = idx

    for idx, stage, op, args, inline, depth in parse_lines():
        if stage not in IN_STAGES:
            continue
        cond = (depth > 0) or (inline is not None)
        if op == "X":
            q = qid(args[0])
            if cond:
                dirty(q, idx)
            else:
                if q in clean:
                    const[q] ^= 1
                    last_write[q] = idx
                else:
                    last_write[q] = idx
        elif op == "CX":
            a, b = qid(args[0]), qid(args[1])
            if cond or a not in clean or b not in clean:
                dirty(b, idx)
            else:
                mask[b] ^= mask[a]
                const[b] ^= const[a]
                last_write[b] = idx
        elif op == "SWAP":
            a, b = qid(args[0]), qid(args[1])
            if cond:
                dirty(a, idx)
                dirty(b, idx)
            else:
                if a in clean and b in clean:
                    mask[a], mask[b] = mask[b], mask[a]
                    const[a], const[b] = const[b], const[a]
                    last_write[a] = last_write[b] = idx
                else:
                    dirty(a, idx)
                    dirty(b, idx)
        elif op in ("HMR", "R"):
            q = qid(args[0])
            if not cond:
                set_affine(q, 0, 0, idx)
                zero_events.append((idx, q))
            else:
                dirty(q, idx)
        elif op == "CCX":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            for tok in args:
                if tok[0] == "q":
                    qq = int(tok[1:])
                    if 840 <= qq <= 891:
                        occ[qq].append(idx)
            if cond:
                n_cond_ccx += 1
                dirty(t, idx)
                continue
            if a == b:  # degenerates to linear CX a->t
                if a in clean and t in clean:
                    mask[t] ^= mask[a]
                    const[t] ^= const[a]
                    last_write[t] = idx
                else:
                    dirty(t, idx)
                continue
            if a in clean and b in clean:
                ka = (mask[a], const[a])
                kb = (mask[b], const[b])
                sites.append((idx, stage, "CCX", a, b, t, ka, kb))
            # pairing (value-level, independent of affinity)
            if t not in (a, b):
                key = (tuple(sorted((a, b))), t)
                if (key in pending and last_write[a] < pending[key][0]
                        and last_write[b] < pending[key][0]
                        and last_write[t] == pending[key][0]):
                    _, em, ec = pending.pop(key)
                    set_affine(t, em, ec, idx)  # restored
                    n_pair += 1
                else:
                    em, ec = ((mask[t], const[t]) if t in clean else (None, None))
                    pending.pop(key, None)
                    if ka[0] == 0 and kb[0] == 0 and t in clean:
                        # constant product: target stays affine
                        const[t] ^= ka[1] & kb[1]
                        last_write[t] = idx
                        pending[key] = (idx, em, ec)
                        n_constprod += 1
                    else:
                        # t ^= nonlinear product -> dirty (pre-value kept
                        # only in the pairing-restore path above)
                        dirty(t, idx)
            else:
                dirty(t, idx)
        elif op == "CCZ":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            if not cond and a in clean and b in clean:
                sites.append((idx, stage, "CCZ", a, b, t,
                              (mask[a], const[a]), (mask[b], const[b])))
            # diagonal: no value change, no writes
        elif op == "CSWAP":
            c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
            dirty(a, idx)
            dirty(b, idx)
        elif op in ("CZ", "Z", "NEG", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            pass
        else:
            raise RuntimeError(f"unexpected op {op}")
        # occurrence index for ancillas (CCX recorded earlier due to `continue`)
        if op in ("X", "CX", "SWAP", "HMR", "R", "CCZ", "CSWAP"):
            for tok in args:
                if tok[0] == "q":
                    q = int(tok[1:])
                    if 840 <= q <= 891:
                        occ[q].append(idx)

    print(f"sites(clean,uncond)={len(sites)} cond_ccx_skipped={n_cond_ccx} "
          f"zero_events={len(zero_events)} pending_left={len(pending)} "
          f"pairings={n_pair} constprod={n_constprod}")
    n_aff = sum(1 for q in range(892) if q in clean)
    print(f"wires still affine at unextract end: {n_aff}/892")

    # cross-check occ/zero vs value-sim pkl (parse-level agreement)
    d = pickle.load(open(PKL, "rb"))
    oz = set(d["zero_events"])
    mz = set(zero_events)
    print(f"zero_events agree with sim pkl: {len(oz & mz)}/{len(oz | mz)}")
    occ_agree = all(list(occ[q]) == list(d["occ"][q]) for q in occ)
    print(f"occ lists agree with sim pkl: {occ_agree}")

    groups: dict[tuple, list[int]] = {}
    for n, s in enumerate(sites):
        key = tuple(sorted((s[6], s[7])))
        groups.setdefault(key, []).append(n)
    multi = {k: v for k, v in groups.items() if len(v) >= 2}
    # complement-folded (mask-only) grouping: same masks, possibly different
    # consts -> would need complemented-product expansion (q855-style)
    mgroups: dict[tuple, list[int]] = {}
    for n, s in enumerate(sites):
        mkey = tuple(sorted((s[6][0], s[7][0])))
        mgroups.setdefault(mkey, []).append(n)
    mmulti = {k: v for k, v in mgroups.items() if len(v) >= 2}
    print(f"mask-only groups: distinct={len(mgroups)} multi={len(mmulti)} "
          f"covered={sum(len(v) for v in mmulti.values())}")
    print("mask-only sizes:", sorted(Counter(len(v) for v in mmulti.values()).items()))
    for k, v in list(mmulti.items())[:10]:
        ss = [sites[n] for n in v]
        print(f"  k={len(v)} consts={[(s[6][1], s[7][1]) for s in ss]} "
              f"lits={[(s[3], s[4], s[5]) for s in ss][:4]}")
    print(f"distinct strict keys={len(groups)} multi={len(multi)} "
          f"covered={sum(len(v) for v in multi.values())}")
    print("group sizes:", sorted(Counter(len(v) for v in multi.values()).items()))

    occ_lists = {q: list(v) for q, v in occ.items()}
    zero_at = set(zero_events)

    def last_touch_before(w, pos):
        lst = occ_lists[w]
        i = bisect.bisect_left(lst, pos) - 1
        return lst[i] if i >= 0 else -1

    def has_touch_in(w, lo, hi):
        lst = occ_lists[w]
        i = bisect.bisect_right(lst, lo)
        return i < len(lst) and lst[i] < hi

    cands = []
    for key, members in multi.items():
        members.sort(key=lambda n: sites[n][0])
        L = [sites[n][0] for n in members]
        cands.append({"key": [str(k) for k in key], "members": members, "L": L,
                      "k": len(members)})
    cands.sort(key=lambda c: (-c["k"], c["L"][0]))
    reserved: dict[int, list[tuple[int, int]]] = {q: [] for q in occ_lists}
    chosen = []
    diag = []
    for c in cands:
        L1, Lk = c["L"][0], c["L"][-1]
        # diagnostics: wires with no touch in window / with proven zero
        no_touch = [w for w in range(840, 892)
                    if not has_touch_in(w, L1, Lk)
                    and all(sites[n][3] != w and sites[n][4] != w and sites[n][5] != w
                            for n in c["members"])]
        zeroed = [w for w in no_touch
                  if last_touch_before(w, L1) in zero_at]
        diag.append({"k": c["k"], "L1": L1, "Lk": Lk, "span": Lk - L1,
                     "n_no_touch": len(no_touch), "n_zeroed": len(zeroed)})
        hit = None
        for w in zeroed:
            if any(not (Lk + 1 <= s or L1 >= e) for s, e in reserved[w]):
                continue
            hit = w
            break
        if hit is not None:
            reserved[hit].append((L1, Lk + 1))
            c["wire"] = hit
            c["save"] = c["k"] - 1
            chosen.append(c)
    total = sum(c["save"] for c in chosen)
    print(f"feasible groups={len(chosen)} predicted net saving={total}")
    for c in chosen[:40]:
        print(f"  k={c['k']} save={c['save']} wire=q{c['wire']} L1={c['L'][0]} Lk={c['L'][-1]}")

    OUT.write_text(json.dumps({
        "n_sites": len(sites),
        "n_pairings": n_pair,
        "n_constprod": n_constprod,
        "n_cond_ccx_skipped": n_cond_ccx,
        "n_wires_affine_at_end": n_aff,
        "n_distinct_keys": len(groups),
        "n_multi": len(multi),
        "n_feasible": len(chosen),
        "predicted_net_saving": total,
        "diag": diag,
        "groups": [{k: v for k, v in c.items() if k != "members"} for c in chosen],
    }, indent=1) + "\n")
    # full member detail for the record (site idx/stage/op/wires)
    DET = Path("artifacts/20261109_affine_cache/affine_group_detail.json")
    DET.write_text(json.dumps([
        {"k": c["k"], "L": c["L"],
         "key": c["key"],
         "sites": [{"idx": sites[n][0], "stage": sites[n][1], "op": sites[n][2],
                     "a": sites[n][3], "b": sites[n][4], "t": sites[n][5]}
                    for n in c["members"]],
         "wire": c.get("wire"), "save": c.get("save", 0)}
        for c in cands], indent=1) + "\n")
    # all clean sites (evidence even when no groups form)
    ST = Path("artifacts/20261109_affine_cache/affine_clean_sites.json")
    ST.write_text(json.dumps([
        {"idx": s[0], "stage": s[1], "op": s[2], "a": s[3], "b": s[4], "t": s[5],
         "ka_mask_pop": bin(s[6][0]).count("1"), "ka_const": s[6][1],
         "kb_mask_pop": bin(s[7][0]).count("1"), "kb_const": s[7][1]}
        for s in sites], indent=1) + "\n")
    plan = []
    for j, c in enumerate(chosen):
        plan.append({"group": j, "wire": c["wire"], "bit": BIT_BASE + j,
                     "save": c["save"],
                     "sites": [{"idx": sites[n][0], "stage": sites[n][1], "op": sites[n][2],
                                "a": sites[n][3], "b": sites[n][4], "t": sites[n][5]}
                               for n in c["members"]]})
    PLAN.write_text(json.dumps(plan, indent=1) + "\n")
    print(f"wrote {OUT} {PLAN}")


if __name__ == "__main__":
    main()
