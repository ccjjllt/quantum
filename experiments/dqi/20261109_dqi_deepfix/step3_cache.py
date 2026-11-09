"""Step 3: cache feasibility — carriers + net savings.

Pass 1: per-stage literal occ (uncond CCX), uncond CCX site list, ancilla
  (q840..891) touch lists, zero events (uncond HMR/R).
Pass 2: write positions for wires appearing in literal top keys (X/CX-tgt/
  SWAP-either/CCX-tgt/CSWAP-swapped/cond-writes/HMR/R count as writes).
Then:
  A. literal top-20 by span per stage: carrier-exists check + run-split
     (split at writes of a/b) + feasible sub-run count.
  B. structural groups (re-run atom hasher, keep ALL multi groups):
     greedy carrier assignment by (k desc, span asc); report feasible + net.
Carrier rule (Isabe V12 style): w in 840..891, w not among member wires,
  no original touch in [L1,Lk], last touch before L1 is uncond HMR/R zero,
  reserved intervals non-overlapping. Net per group: k-1.

Writes artifacts/20261109_dqi_deepfix/step3_cache.json
"""
from __future__ import annotations
import array
import bisect
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step3_cache.json")

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

def qid(t): return int(t[1:])

def main():
    IN_STAGES = ("unsynthesis", "unextract")
    lit_pos = {s: {} for s in IN_STAGES}   # key -> [idx]
    sites = {s: [] for s in IN_STAGES}     # (idx,a,b,t)
    occ = {q: array.array("I") for q in range(840, 892)}
    zero_at = {}  # idx -> q (uncond HMR/R on any wire)
    for idx, st, op, args, inline, depth in parse():
        cond = (depth > 0) or (inline is not None)
        if op in ("HMR", "R") and not cond and args and args[0][0] == "q":
            zero_at[idx] = qid(args[0])
        if st not in IN_STAGES:
            continue
        if op in ("X", "CX", "SWAP", "HMR", "R", "CCX", "CCZ", "CSWAP", "CZ"):
            for tok in args:
                if tok and tok[0] == "q":
                    q = int(tok[1:])
                    if 840 <= q <= 891:
                        occ[occ and q].append(idx)
        if op == "CCX":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            if cond:
                continue
            k = tuple(sorted((a, b)))
            lit_pos[st].setdefault(k, []).append(idx)
            sites[st].append((idx, a, b, t))
    occ_lists = {q: list(v) for q, v in occ.items()}
    print("pass1 done", flush=True)
    for st in IN_STAGES:
        rep = {k: v for k, v in lit_pos[st].items() if len(v) >= 2}
        print(f"{st}: literal distinct={len(lit_pos[st])} repkeys={len(rep)} "
              f"repocc={sum(len(v) for v in rep.values())} uncond_sites={len(sites[st])}", flush=True)

    # literal top-20 by span per stage
    def span(v): return v[-1] - v[0]
    lit_top = {}
    for st in IN_STAGES:
        rep = [(k, v) for k, v in lit_pos[st].items() if len(v) >= 2]
        rep.sort(key=lambda kv: -span(kv[1]))
        lit_top[st] = rep[:20]
        print(f"== {st} literal top-20 by span:", flush=True)
        for k, v in rep[:20]:
            print(f"   key={k} k={len(v)} span={span(v)} L1={v[0]} Lk={v[-1]}", flush=True)
        rep2 = sorted(rep, key=lambda kv: -len(kv[1]))[:10]
        print(f"== {st} literal top-10 by k:", flush=True)
        for k, v in rep2:
            print(f"   key={k} k={len(v)} span={span(v)}", flush=True)

    # pass 2: write positions for watch wires (top-span + top-k keys)
    watch = set()
    for st in IN_STAGES:
        rep = {k: v for k, v in lit_pos[st].items() if len(v) >= 2}
        byk = sorted(rep.items(), key=lambda kv: -len(kv[1]))[:20]
        for k, v in lit_top[st] + byk:
            watch.add(k[0]); watch.add(k[1])
    print(f"watch wires: {len(watch)}", flush=True)
    writes = {q: [] for q in watch}
    for idx, st, op, args, inline, depth in parse():
        if st not in IN_STAGES:
            continue
        cond = (depth > 0) or (inline is not None)
        touched = set()
        if op == "X":
            touched.add(qid(args[0]))
        elif op == "CX":
            touched.add(qid(args[1]))
        elif op == "SWAP":
            touched.add(qid(args[0])); touched.add(qid(args[1]))
        elif op in ("HMR", "R"):
            touched.add(qid(args[0]))
        elif op == "CCX":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            touched.add(t)
            if cond:
                pass
        elif op == "CSWAP":
            touched.add(qid(args[1])); touched.add(qid(args[2]))
        for q in touched:
            if q in writes:
                writes[q].append(idx)
    print("pass2 done", flush=True)

    def has_touch_in(w, lo, hi):
        lst = occ_lists[w]
        i = bisect.bisect_left(lst, lo)
        return i < len(lst) and lst[i] <= hi

    def last_touch_before(w, pos):
        lst = occ_lists[w]
        i = bisect.bisect_left(lst, pos) - 1
        return lst[i] if i >= 0 else -1

    def carrier_for(L1, Lk, member_wires, reserved):
        cands = []
        for w in range(840, 892):
            if w in member_wires:
                continue
            if has_touch_in(w, L1, Lk):
                continue
            if last_touch_before(w, L1) not in zero_at:
                continue
            if any(not (Lk < s or L1 > e) for s, e in reserved[w]):
                continue
            cands.append(w)
        return cands

    # A. literal top-20: carrier over full span + run-split analysis
    lit_report = {}
    for st in IN_STAGES:
        rows = []
        for k, v in lit_top[st]:
            a, b = k
            L1, Lk = v[0], v[-1]
            mw = {a, b}
            res0 = {q: [] for q in range(840, 892)}
            c0 = carrier_for(L1, Lk, mw, res0)
            # run split at writes of a or b strictly inside (pi, pj)
            wa, wb = writes[a], writes[b]
            runs = [[v[0]]]
            for p in v[1:]:
                prev = runs[-1][-1]
                ia = bisect.bisect_right(wa, prev); ja = bisect.bisect_left(wa, p)
                ib = bisect.bisect_right(wb, prev); jb = bisect.bisect_left(wb, p)
                if ja > ia or jb > ib:
                    runs.append([p])
                else:
                    runs[-1].append(p)
            runs = [r for r in runs if len(r) >= 2]
            rows.append({"key": list(k), "k": len(v), "span": span(v), "L1": L1, "Lk": Lk,
                         "n_carriers_fullspan": len(c0),
                         "n_runs": len(runs),
                         "run_ks": sorted([len(r) for r in runs], reverse=True)[:6]})
            print(f"{st} key={k} k={len(v)} span={span(v)} carriers_full={len(c0)} "
                  f"runs={len(runs)} runks={sorted([len(r) for r in runs], reverse=True)[:6]}", flush=True)
        lit_report[st] = rows

    # B. structural groups (re-run hasher, keep all multi groups)
    struct_all = {}
    for st in IN_STAGES:
        mask = {q: (1 << q, 0) for q in range(892)}
        next_atom = 892
        memo: dict = {}
        def get_atom(prov):
            nonlocal next_atom
            a = memo.get(prov)
            if a is None:
                a = next_atom; next_atom += 1; memo[prov] = a
            return a
        ss = []
        for idx, s2, op, args, inline, depth in parse():
            if s2 != st:
                continue
            cond = (depth > 0) or (inline is not None)
            if op == "X":
                q = qid(args[0])
                if cond: mask[q] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    m, c = mask[q]; mask[q] = (m, c ^ 1)
            elif op == "CX":
                a, b = qid(args[0]), qid(args[1])
                if cond: mask[b] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    ma, ca = mask[a]; mb, cb = mask[b]
                    mask[b] = (ma ^ mb, ca ^ cb)
            elif op == "SWAP":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    mask[a] = (1 << get_atom(("dirty", idx)), 0)
                    mask[b] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    mask[a], mask[b] = mask[b], mask[a]
            elif op in ("HMR", "R"):
                q = qid(args[0])
                if not cond: mask[q] = (0, 0)
                else: mask[q] = (1 << get_atom(("dirty", idx)), 0)
            elif op == "CCX":
                a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    mask[t] = (1 << get_atom(("dirty", idx)), 0)
                    continue
                ma, ca = mask[a]; mb, cb = mask[b]
                ka, kb = (ma, ca), (mb, cb)
                pk = tuple(sorted((ka, kb)))
                if ka == kb:
                    mt, ct = mask[t]
                    mask[t] = (mt ^ ma, ct ^ ca)
                    ss.append((idx, a, b, t, ("affwk", ka)))
                else:
                    pa = get_atom(("and", pk))
                    mt, ct = mask[t]
                    mask[t] = (mt ^ (1 << pa), ct)
                    ss.append((idx, a, b, t, ("and", pk)))
            elif op == "CCZ":
                a, b = qid(args[0]), qid(args[1])
                if cond: continue
                ma, ca = mask[a]; mb, cb = mask[b]
                pk = tuple(sorted(((ma, ca), (mb, cb))))
                ss.append((idx, a, b, qid(args[2]), ("and", pk)))
            elif op == "CSWAP":
                c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    mask[a] = (1 << get_atom(("dirty", idx)), 0)
                    mask[b] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    fa, fb, fc = mask[a], mask[b], mask[c_]
                    mask[a] = (1 << get_atom(("mux", 0, fc, fa, fb)), 0)
                    mask[b] = (1 << get_atom(("mux", 1, fc, fa, fb)), 0)
        groups: dict = {}
        for n, s in enumerate(ss):
            groups.setdefault(s[4], []).append(n)
        struct_all[st] = (ss, groups)
        multi = {k2: v for k2, v in groups.items() if len(v) >= 2}
        print(f"{st} structural: sites={len(ss)} multi={len(multi)}", flush=True)

    # greedy carrier assignment over structural groups
    reserved = {q: [] for q in range(840, 892)}
    feas = []
    cands = []
    for st in IN_STAGES:
        ss, groups = struct_all[st]
        for k2, v in groups.items():
            if len(v) < 2:
                continue
            v = sorted(v, key=lambda n: ss[n][0])
            L = [ss[n][0] for n in v]
            cands.append((st, k2, v, L))
    cands.sort(key=lambda c: (-len(c[2]), c[3][-1] - c[3][0]))
    for st, k2, v, L in cands:
        ss = struct_all[st][0]
        L1, Lk = L[0], L[-1]
        mw = set()
        for n in v:
            mw.add(ss[n][1]); mw.add(ss[n][2]); mw.add(ss[n][3])
        hit = None
        for w in range(840, 892):
            if w in mw or has_touch_in(w, L1, Lk) or last_touch_before(w, L1) not in zero_at:
                continue
            if any(not (Lk < s or L1 > e) for s, e in reserved[w]):
                continue
            hit = w; break
        if hit is not None:
            reserved[hit].append((L1, Lk + 1))
            feas.append({"stage": st, "k": len(v), "L1": L1, "Lk": Lk,
                         "span": Lk - L1, "wire": hit, "save": len(v) - 1,
                         "nlits": len({(ss[n][1], ss[n][2]) for n in v})})
    total = sum(f["save"] for f in feas)
    print(f"structural feasible groups={len(feas)} net={total}", flush=True)
    for f in feas[:30]:
        print(f"  {f['stage']} k={f['k']} save={f['save']} wire=q{f['wire']} "
              f"span={f['span']} nlits={f['nlits']} L1={f['L1']}", flush=True)

    OUT.write_text(json.dumps({
        "literal_unified_counts": {
            st: {"distinct": len(lit_pos[st]),
                 "repkeys": sum(1 for v in lit_pos[st].values() if len(v) >= 2),
                 "repocc": sum(len(v) for v in lit_pos[st].values() if len(v) >= 2)}
            for st in IN_STAGES},
        "literal_top20_byspan": lit_report,
        "structural_gross": {
            st: {"multi": sum(1 for v in struct_all[st][1].values() if len(v) >= 2),
                 "repocc": sum(len(v) for v in struct_all[st][1].values() if len(v) >= 2),
                 "max_gross_save": sum(len(v) - 1 for v in struct_all[st][1].values() if len(v) >= 2)}
            for st in IN_STAGES},
        "structural_feasible": feas,
        "structural_net": total,
    }, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
