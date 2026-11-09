"""Step 1b: TRUE fixed affine_clean — exact affine_clean.py rules, per-stage reset.

Copies affine_clean.py tracking rules verbatim (X/CX/SWAP cond->dirty, HMR/R,
CCX pairing + a==b + constprod, CCZ diagonal, CSWAP dirties, inline-or-depth cond,
occ/zero-event bookkeeping), with the ONE fix: when a new target stage block is
entered (unsynthesis, then unextract), reset the 892-symbol basis
(mask/const/clean/last_write/pending). Sites grouped per stage (strict + mask-only).

Writes artifacts/20261109_dqi_deepfix/step1b_fixed_affine.json
"""
from __future__ import annotations
import array
import bisect
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step1b_fixed_affine.json")
DET = Path("artifacts/20261109_dqi_deepfix/step1b_sites.json")

def parse_lines():
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
    mask: dict[int, int] = {}
    const: dict[int, int] = {}
    clean: set[int] = set()
    last_write: dict[int, int] = {}
    pending: dict[tuple, tuple[int, int, int]] = {}
    cur_block: str | None = None
    n_pair = n_constprod = 0
    n_cond_ccx: dict[str, int] = Counter()
    sites: list[tuple] = []
    sites_by_stage: dict[str, list[int]] = {s: [] for s in IN_STAGES}
    zero_events: list[tuple[int, int]] = []
    occ: dict[int, array.array] = {q: array.array("I") for q in range(840, 892)}

    def reset_basis() -> None:
        mask.clear(); const.clear(); clean.clear(); last_write.clear(); pending.clear()
        for q in range(892):
            mask[q] = 1 << q
            const[q] = 0
            clean.add(q)
            last_write[q] = -1

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
        if stage != cur_block:
            reset_basis()  # THE FIX: fresh 892-symbol basis at each stage entry
            cur_block = stage
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
                n_cond_ccx[stage] += 1
                dirty(t, idx)
                continue
            if a == b:
                if a in clean and t in clean:
                    mask[t] ^= mask[a]
                    const[t] ^= const[a]
                    last_write[t] = idx
                else:
                    dirty(t, idx)
                continue
            ka = (mask[a], const[a]) if a in clean else None
            kb = (mask[b], const[b]) if b in clean else None
            if a in clean and b in clean:
                sites_by_stage[stage].append(len(sites))
                sites.append((idx, stage, "CCX", a, b, t, ka, kb))
            if t not in (a, b):
                key = (tuple(sorted((a, b))), t)
                if (key in pending and last_write[a] < pending[key][0]
                        and last_write[b] < pending[key][0]
                        and last_write[t] == pending[key][0]):
                    _, em, ec = pending.pop(key)
                    set_affine(t, em, ec, idx)
                    n_pair += 1
                else:
                    em, ec = ((mask[t], const[t]) if t in clean else (None, None))
                    pending.pop(key, None)
                    if ka is not None and kb is not None and ka[0] == 0 and kb[0] == 0 and t in clean:
                        const[t] ^= ka[1] & kb[1]
                        last_write[t] = idx
                        pending[key] = (idx, em, ec)
                        n_constprod += 1
                    else:
                        dirty(t, idx)
            else:
                dirty(t, idx)
        elif op == "CCZ":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            if not cond and a in clean and b in clean:
                sites_by_stage[stage].append(len(sites))
                sites.append((idx, stage, "CCZ", a, b, t,
                              (mask[a], const[a]), (mask[b], const[b])))
        elif op == "CSWAP":
            c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
            dirty(a, idx)
            dirty(b, idx)
        elif op in ("CZ", "Z", "NEG", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            pass
        else:
            raise RuntimeError(f"unexpected op {op}")
        if op in ("X", "CX", "SWAP", "HMR", "R", "CCZ", "CSWAP"):
            for tok in args:
                if tok[0] == "q":
                    q = int(tok[1:])
                    if 840 <= q <= 891:
                        occ[q].append(idx)

    print(f"cond_ccx per stage: {dict(n_cond_ccx)} pairings={n_pair} constprod={n_constprod}", flush=True)
    per = {}
    for stage in IN_STAGES:
        ns = [sites[n] for n in sites_by_stage[stage]]
        groups: dict[tuple, list[int]] = {}
        for n in sites_by_stage[stage]:
            s = sites[n]
            groups.setdefault(tuple(sorted((s[6], s[7]))), []).append(n)
        multi = {k: v for k, v in groups.items() if len(v) >= 2}
        mgroups: dict[tuple, list[int]] = {}
        for n in sites_by_stage[stage]:
            s = sites[n]
            mgroups.setdefault(tuple(sorted((s[6][0], s[7][0]))), []).append(n)
        mmulti = {k: v for k, v in mgroups.items() if len(v) >= 2}
        per[stage] = {
            "n_sites": len(ns),
            "n_ccx": sum(1 for s in ns if s[2] == "CCX"),
            "n_ccz": sum(1 for s in ns if s[2] == "CCZ"),
            "strict_distinct": len(groups),
            "strict_repkeys": len(multi),
            "strict_repocc": sum(len(v) for v in multi.values()),
            "mask_distinct": len(mgroups),
            "mask_repkeys": len(mmulti),
            "mask_repocc": sum(len(v) for v in mmulti.values()),
        }
        print(f"== {stage}: sites={len(ns)} (ccx={per[stage]['n_ccx']} ccz={per[stage]['n_ccz']}) "
              f"strict distinct={len(groups)} rep={len(multi)} "
              f"mask distinct={len(mgroups)} rep={len(mmulti)}", flush=True)
    OUT.write_text(json.dumps({
        "n_sites_total": len(sites),
        "n_pairings": n_pair, "n_constprod": n_constprod,
        "n_cond_ccx": dict(n_cond_ccx),
        "per_stage": per,
    }, indent=1) + "\n")
    DET.write_text(json.dumps([
        {"idx": s[0], "stage": s[1], "op": s[2], "a": s[3], "b": s[4], "t": s[5]}
        for s in sites], indent=1) + "\n")
    print(f"wrote {OUT} {DET}", flush=True)

if __name__ == "__main__":
    main()
