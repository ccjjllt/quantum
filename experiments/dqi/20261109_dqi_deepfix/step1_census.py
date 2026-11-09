"""Step 1: unified-count census + per-stage-reset affine grouping (read-only).

- Parses cached kmx, tracks stage via INFO_TAG stack, cond = (depth>0 or inline-if).
- Per-stage affine reset (probe semantics): each of unextract/unsynthesis gets fresh
  892-symbol basis at stage entry; X/CX/SWAP unconditional affine updates, HMR/R reset
  to 0, CCX target always dirtied, CSWAP dirties swapped, CCZ diagonal.
- Reports per-stage: total CCX, uncond, cond (inline vs stack), bothclean, strict/mask
  distinct+repeats, literal distinct/repkeys/occ.
- Also reproduces the OLD contaminated single-basis counting (affine_clean.py bug)
  for the evidence chain: one 892-basis at unsynthesis entry, carried into unextract.
- 200k-line window carrier pressure over unextract (q840..891 occ), and literal top
  groups with spans (for step 3 carrier check reuse).
Writes JSON to artifacts/20261109_dqi_deepfix/step1_census.json
"""
from __future__ import annotations
import bisect
import collections
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step1_census.json")

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
                depth += 1
                yield idx, stage, "PUSH_CONDITION", [], None, depth
                continue
            if l.startswith("POP_CONDITION"):
                yield idx, stage, "POP_CONDITION", [], None, depth
                depth -= 1
                continue
            parts = l.split()
            op = parts[0]
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]; args = parts[1:-2]
            else:
                inline = None; args = parts[1:]
            yield idx, stage, op, args, inline, depth

def qid(tok: str) -> int:
    assert tok[0] == "q", tok
    return int(tok[1:])

def run_stage_affine(events, stage):
    """Probe-semantics affine pass restricted to one stage (fresh basis)."""
    mask = {q: 1 << q for q in range(892)}
    const = {q: 0 for q in range(892)}
    dirty: set[int] = set()
    n_ccx = n_both = n_inline = n_stack = 0
    strict = collections.Counter()
    mkey = collections.Counter()
    lit = collections.Counter()
    lit_pos: dict[tuple, list[int]] = {}
    bothclean_pos = []
    for idx, st, op, args, inline, depth in events:
        if st != stage:
            continue
        if op in ("PUSH_CONDITION", "POP_CONDITION"):
            continue
        cond = (depth > 0) or (inline is not None)
        if op == "X":
            q = qid(args[0])
            if cond:
                dirty.add(q); mask.pop(q, None)
            else:
                if q not in dirty:
                    const[q] ^= 1
        elif op == "CX":
            a, b = qid(args[0]), qid(args[1])
            if cond or a in dirty or b in dirty:
                dirty.add(b); mask.pop(b, None)
            else:
                mask[b] ^= mask[a]; const[b] ^= const[a]
        elif op == "SWAP":
            a, b = qid(args[0]), qid(args[1])
            if cond:
                dirty.add(a); dirty.add(b); mask.pop(a, None); mask.pop(b, None)
            else:
                ma, mb = mask.get(a, 1 << a), mask.get(b, 1 << b)
                ca, cb = const.get(a, 0), const.get(b, 0)
                mask[a], mask[b] = mb, ma; const[a], const[b] = cb, ca
                da, db = a in dirty, b in dirty
                if da and not db:
                    dirty.add(b); dirty.discard(a); mask.pop(b, None)
                elif db and not da:
                    dirty.add(a); dirty.discard(b); mask.pop(a, None)
                elif da and db:
                    pass
                else:
                    dirty.discard(a); dirty.discard(b)
        elif op in ("HMR", "R"):
            q = qid(args[0])
            if not cond:
                mask[q] = 0; const[q] = 0; dirty.discard(q)
            else:
                dirty.add(q); mask.pop(q, None)
        elif op == "CCX":
            a, b = qid(args[0]), qid(args[1])
            t = qid(args[2])
            if cond:
                if inline is not None and depth == 0:
                    n_inline += 1
                elif inline is not None:
                    n_inline += 1; n_stack += 1
                elif depth > 0:
                    n_stack += 1
                dirty.add(t); mask.pop(t, None)
                continue
            n_ccx += 1
            k = tuple(sorted((a, b)))
            lit[k] += 1
            lit_pos.setdefault(k, []).append(idx)
            if a not in dirty and b not in dirty:
                n_both += 1
                ka = (mask[a], const[a]); kb = (mask[b], const[b])
                strict[tuple(sorted((ka, kb)))] += 1
                mk = tuple(sorted((mask[a], mask[b])))
                mkey[mk] += 1
                bothclean_pos.append(idx)
            dirty.add(t); mask.pop(t, None)
        elif op == "CSWAP":
            try:
                aa, bb = qid(args[1]), qid(args[2])
                dirty.add(aa); dirty.add(bb); mask.pop(aa, None); mask.pop(bb, None)
            except Exception:
                pass
        # CZ/CCZ/Z/BIT/NEG: no value effect
    rep = lambda c: (len(c), sum(1 for v in c.values() if v >= 2), sum(v for v in c.values() if v >= 2))
    return {
        "uncond_ccx": n_ccx, "bothclean": n_both,
        "cond_inline": n_inline, "cond_stackdepth": n_stack,
        "strict_distinct": len(strict),
        "strict_repkeys": sum(1 for v in strict.values() if v >= 2),
        "strict_repocc": sum(v for v in strict.values() if v >= 2),
        "mask_distinct": len(mkey),
        "mask_repkeys": sum(1 for v in mkey.values() if v >= 2),
        "mask_repocc": sum(v for v in mkey.values() if v >= 2),
        "lit_distinct": len(lit), "lit_repkeys": rep(lit)[1], "lit_repocc": rep(lit)[2],
        "n_affine_end": sum(1 for q in range(892) if q not in dirty),
        "lit": lit, "lit_pos": lit_pos, "bothclean_pos": bothclean_pos,
    }

def main():
    events = list(parse())
    print(f"parsed events: {len(events)}", flush=True)
    per = {}
    for stage in ("unextract", "unsynthesis"):
        r = run_stage_affine(events, stage)
        lit, lit_pos = r.pop("lit"), r.pop("lit_pos")
        both = r.pop("bothclean_pos")
        per[stage] = r
        print(f"== {stage}: uncond CCX={r['uncond_ccx']} bothclean={r['bothclean']} "
              f"cond_inline={r['cond_inline']} cond_stack={r['cond_stackdepth']}", flush=True)
        print(f"   strict distinct={r['strict_distinct']} repkeys={r['strict_repkeys']} repocc={r['strict_repocc']}", flush=True)
        print(f"   mask distinct={r['mask_distinct']} repkeys={r['mask_repkeys']} repocc={r['mask_repocc']}", flush=True)
        print(f"   literal distinct={r['lit_distinct']} repkeys={r['lit_repkeys']} occ={r['lit_repocc']} affine_end={r['n_affine_end']}", flush=True)
        # stash for later steps
        import pickle
        with open(f"artifacts/20261109_dqi_deepfix/lit_{stage}.pkl", "wb") as f:
            pickle.dump({"lit": lit, "lit_pos": lit_pos, "bothclean_pos": both}, f)

    # OLD buggy single-basis pass (unsynthesis basis carried into unextract)
    mask = {q: 1 << q for q in range(892)}
    const = {q: 0 for q in range(892)}
    dirty: set[int] = set()
    old_both = collections.Counter()
    for idx, st, op, args, inline, depth in events:
        if st not in ("unsynthesis", "unextract"):
            continue
        cond = (depth > 0) or (inline is not None)
        if op == "X":
            q = qid(args[0])
            if cond:
                dirty.add(q); mask.pop(q, None)
            elif q not in dirty:
                const[q] ^= 1
        elif op == "CX":
            a, b = qid(args[0]), qid(args[1])
            if cond or a in dirty or b in dirty:
                dirty.add(b); mask.pop(b, None)
            else:
                mask[b] ^= mask[a]; const[b] ^= const[a]
        elif op == "SWAP":
            a, b = qid(args[0]), qid(args[1])
            if cond:
                dirty.add(a); dirty.add(b); mask.pop(a, None); mask.pop(b, None)
            else:
                ma, mb = mask.get(a, 1 << a), mask.get(b, 1 << b)
                ca, cb = const.get(a, 0), const.get(b, 0)
                mask[a], mask[b] = mb, ma; const[a], const[b] = cb, ca
        elif op in ("HMR", "R"):
            q = qid(args[0])
            if not cond:
                mask[q] = 0; const[q] = 0; dirty.discard(q)
            else:
                dirty.add(q); mask.pop(q, None)
        elif op == "CCX":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            if cond:
                dirty.add(t); mask.pop(t, None); continue
            if a not in dirty and b not in dirty:
                old_both[st] += 1
            dirty.add(t); mask.pop(t, None)
        elif op == "CSWAP":
            try:
                aa, bb = qid(args[1]), qid(args[2])
                dirty.add(aa); dirty.add(bb); mask.pop(aa, None); mask.pop(bb, None)
            except Exception:
                pass
    print(f"OLD single-basis bothclean: {dict(old_both)} (bug: unextract carries unsynthesis dirt)", flush=True)

    # combined literal stats (both stages, uncond only)
    import pickle
    allt = collections.Counter(); allo = sum(p["uncond_ccx"] for p in per.values())
    for stage in ("unextract", "unsynthesis"):
        d = pickle.load(open(f"artifacts/20261109_dqi_deepfix/lit_{stage}.pkl", "rb"))
        allt.update(d["lit"])
    print(f"COMBINED literal: distinct={len(allt)} repkeys={sum(1 for v in allt.values() if v>=2)} "
          f"repocc={sum(v for v in allt.values() if v>=2)} total_uncond={allo}", flush=True)
    top = allt.most_common(30)
    print("top-30 literal groups (a,b):count:", flush=True)
    for k, v in top:
        print(f"  {k}: {v}", flush=True)

    # 200k-line window carrier pressure over unextract (q840..891 any-touch busy)
    occ: dict[int, list[int]] = {q: [] for q in range(840, 892)}
    stage_of = {}
    for idx, st, op, args, inline, depth in events:
        if st != "unextract":
            continue
        if op in ("X", "CX", "SWAP", "HMR", "R", "CCX", "CCZ", "CSWAP", "CZ"):
            for tok in args:
                if tok and tok[0] == "q":
                    q = int(tok[1:])
                    if 840 <= q <= 891:
                        occ[q].append(idx)
    # window over global line idx range covering unextract
    lo = min(v[0] for v in occ.values() if v)
    hi = max(v[-1] for v in occ.values() if v)
    W = 200_000
    nwin = busy = 0; dist = collections.Counter()
    w = lo
    while w <= hi:
        nwin += 1
        nbusy = 0
        for q in range(840, 892):
            lst = occ[q]
            import bisect as bs
            i = bs.bisect_right(lst, w)
            touched = i < len(lst) and lst[i] < w + W
            if touched:
                nbusy += 1
        dist[nbusy] += 1
        if nbusy == 52:
            busy += 1
        w += W
    print(f"200k-window pressure unextract: windows={nwin} full52={busy} dist={sorted(dist.items())}", flush=True)

    OUT.write_text(json.dumps({
        "per_stage": per,
        "old_single_basis_bothclean": dict(old_both),
        "combined_literal": {"distinct": len(allt),
                             "repkeys": sum(1 for v in allt.values() if v >= 2),
                             "repocc": sum(v for v in allt.values() if v >= 2),
                             "total_uncond": allo,
                             "top30": [[list(k), v] for k, v in top]},
        "window200k": {"nwin": nwin, "full52": busy, "dist": sorted(dist.items())},
    }, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
