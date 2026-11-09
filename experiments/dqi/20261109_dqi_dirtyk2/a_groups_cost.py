"""DQI dirty-borrow study A: full k>=3 structural groups + per-group cost table.

Single pass over the frontier .kmx (same exact atom-hash semantics as
20261109_dqi_deepfix/step2a_struct.py, including exact SWAP and mux-CSWAP):
 - per-stage sites (uncond CCX/CCZ only) with structural keys
 - ancilla (840..891) full-file occ + opcode at each touch (for last/next-touch)
 - data (0..839) in-stage occ (idx only)
 - uncond HMR/R zero_at map
Then:
 - ALL k>=3 groups with full members (unextract 150xk3+12xk4+30xk5 expected)
 - per-group: k, span, gaps, opmix, literals, full-span idle ancilla,
   clean-carrier check (pristine / last-touch HMR-zero), dirty-idle count
 - hypothesized dirty-hold cost (task model): gross -(k-1), overhead +2,
   net -(k-3); correct per-site identity cost: +k (each site +1 CCX)
 - overlap/concurrency among k>=4 groups (distinct carriers needed)
 - all consecutive pairs with gap<=200 (small-gap pool)
 - CCZ-only grouping by pk + cross CCX-CCZ keys + exact literal triple repeats

Writes artifacts/20261109_dqi_dirtyk2/{a_groups.json,a_cost.json,a_smallgap.json,a_ccz.json}
"""
from __future__ import annotations
import array
import bisect
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
ART = Path("artifacts/20261109_dqi_dirtyk2")
IN_STAGES = ("unsynthesis", "unextract")

OPC = {"X": 1, "CX": 2, "SWAP": 3, "HMR": 4, "R": 5, "CCX": 6, "CCZ": 7,
       "CSWAP": 8, "CZ": 9, "OTHER": 10}


def qid(t):
    return int(t[1:])


def main():
    # ---- pass 1: hash + occ ----
    mask = {}
    nxt = {}
    memo = {}
    sites = {s: [] for s in IN_STAGES}
    occA = {q: array.array("I") for q in range(840, 892)}
    opcA = {q: array.array("B") for q in range(840, 892)}
    occD = {q: array.array("I") for q in range(840)}
    zero_op = {}  # idx -> 'HMR'/'R'
    val_ops = ("X", "CX", "SWAP", "HMR", "R", "CCX", "CCZ", "CSWAP", "CZ")
    for s in IN_STAGES:
        mask[s] = {q: (1 << q, 0) for q in range(892)}
        nxt[s] = 892
        memo[s] = {}
    stage = "header"
    stack: list[str] = []
    depth = 0
    n_cond = {s: 0 for s in IN_STAGES}
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
            cond = (depth > 0) or (inline is not None)
            if op in ("HMR", "R") and not cond and args and args[0][0] == "q":
                zero_op[idx] = op
            qs = []
            if op in val_ops:
                for tok in args:
                    if tok and tok[0] == "q":
                        try:
                            qs.append(int(tok[1:]))
                        except ValueError:
                            pass
                for q in qs:
                    if 840 <= q <= 891:
                        occA[q].append(idx)
                        opcA[q].append(OPC.get(op, 10))
                    elif q < 840 and stage in IN_STAGES:
                        occD[q].append(idx)
            if stage not in IN_STAGES:
                continue
            m = mask[stage]

            def get_atom(prov):
                mm = memo[stage]
                a = mm.get(prov)
                if a is None:
                    a = nxt[stage]
                    nxt[stage] += 1
                    mm[prov] = a
                return a

            if op == "X":
                q = qid(args[0])
                if cond:
                    m[q] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    mm_, c = m[q]
                    m[q] = (mm_, c ^ 1)
            elif op == "CX":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    m[b] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    ma, ca = m[a]
                    mb, cb = m[b]
                    m[b] = (ma ^ mb, ca ^ cb)
            elif op == "SWAP":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    m[a] = (1 << get_atom(("dirty", idx)), 0)
                    m[b] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    m[a], m[b] = m[b], m[a]
            elif op in ("HMR", "R"):
                q = qid(args[0])
                if not cond:
                    m[q] = (0, 0)
                else:
                    m[q] = (1 << get_atom(("dirty", idx)), 0)
            elif op == "CCX":
                a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    n_cond[stage] += 1
                    m[t] = (1 << get_atom(("dirty", idx)), 0)
                    continue
                ma, ca = m[a]
                mb, cb = m[b]
                ka, kb = (ma, ca), (mb, cb)
                pk = tuple(sorted((ka, kb)))
                if ka == kb:
                    mt, ct = m[t]
                    m[t] = (mt ^ ma, ct ^ ca)
                    sites[stage].append((idx, "CCX", a, b, t, ("affwk", ka)))
                else:
                    pa = get_atom(("and", pk))
                    mt, ct = m[t]
                    m[t] = (mt ^ (1 << pa), ct)
                    sites[stage].append((idx, "CCX", a, b, t, ("and", pk)))
            elif op == "CCZ":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    n_cond[stage] += 1
                    continue
                ma, ca = m[a]
                mb, cb = m[b]
                pk = tuple(sorted(((ma, ca), (mb, cb))))
                sites[stage].append((idx, "CCZ", a, b, qid(args[2]), ("ccz", pk)))
            elif op == "CSWAP":
                c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    m[a] = (1 << get_atom(("dirty", idx)), 0)
                    m[b] = (1 << get_atom(("dirty", idx)), 0)
                else:
                    fa, fb, fc = m[a], m[b], m[c_]
                    m[a] = (1 << get_atom(("mux", 0, fc, fa, fb)), 0)
                    m[b] = (1 << get_atom(("mux", 1, fc, fa, fb)), 0)
    print("pass done", flush=True)

    OA = {q: list(v) for q, v in occA.items()}
    PA = {q: list(v) for q, v in opcA.items()}

    def touches(lst, lo, hi):
        i = bisect.bisect_left(lst, lo)
        j = bisect.bisect_right(lst, hi)
        return j - i

    # ---- grouping ----
    out_groups = {}
    smallgap = []
    for st in IN_STAGES:
        S = sites[st]
        g: dict = {}
        for n, s in enumerate(S):
            g.setdefault(s[5], []).append(n)
        multi = {k: v for k, v in g.items() if len(v) >= 2}
        print(f"{st}: sites={len(S)} distinct={len(g)} repkeys={len(multi)} "
              f"repocc={sum(len(v) for v in multi.values())} "
              f"hist={sorted(Counter(len(v) for v in multi.values()).items())}", flush=True)
        det = []
        for key, v in sorted(multi.items(), key=lambda kv: (-len(kv[1]), min(S[n][0] for n in kv[1]))):
            v = sorted(v, key=lambda n: S[n][0])
            L = [S[n][0] for n in v]
            members = [{"idx": S[n][0], "op": S[n][1], "a": S[n][2], "b": S[n][3],
                        "t": S[n][4]} for n in v]
            mw = set()
            for n in v:
                mw.update((S[n][2], S[n][3], S[n][4]))
            L1, Lk = L[0], L[-1]
            idleA = [w for w in range(840, 892) if w not in mw and touches(OA[w], L1, Lk) == 0]
            clean = []
            for w in idleA:
                lst = OA[w]
                i = bisect.bisect_left(lst, L1) - 1
                if i < 0:
                    clean.append([w, "pristine"])
                elif lst[i] in zero_op:
                    clean.append([w, "hmr-zero"])
            gaps = [L[j + 1] - L[j] for j in range(len(L) - 1)]
            det.append({"k": len(v), "L1": L1, "Lk": Lk, "span": Lk - L1,
                        "gaps": gaps, "opmix": dict(Counter(S[n][1] for n in v)),
                        "nlits": len({(S[n][2], S[n][3]) for n in v}),
                        "lits": sorted({(S[n][2], S[n][3]) for n in v}),
                        "targets": sorted({S[n][4] for n in v}),
                        "n_idleA": len(idleA), "idleA": idleA, "clean": clean,
                        "n_dirty_idleA": len(idleA) - len(clean),
                        "members": members})
            for j in range(len(v) - 1):
                sa, sb = S[v[j]], S[v[j + 1]]
                gap = sb[0] - sa[0]
                if gap <= 200:
                    smallgap.append({"stage": st, "Li": sa[0], "Lj": sb[0], "gap": gap,
                                     "wires": sorted({sa[2], sa[3], sa[4], sb[2], sb[3], sb[4]}),
                                     "ops": [sa[1], sb[1]], "group_k": len(v)})
        out_groups[st] = det
    smallgap.sort(key=lambda r: r["gap"])
    print(f"small-gap pairs total: {len(smallgap)}", flush=True)

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "a_groups.json").write_text(json.dumps(out_groups, indent=1) + "\n")

    # ---- cost table for k>=3 (unextract) ----
    rows = []
    for st in ("unextract",):
        for gi, d in enumerate(out_groups[st]):
            if d["k"] < 3:
                continue
            gross = -(d["k"] - 1)
            overhead = 2
            net_hyp = gross + overhead  # -(k-3)
            net_correct = d["k"]  # per-site identity +1 each
            rows.append({"stage": st, "gid": gi, "k": d["k"], "L1": d["L1"],
                         "Lk": d["Lk"], "span": d["span"], "gaps": d["gaps"],
                         "opmix": d["opmix"], "nlits": d["nlits"],
                         "n_idleA": d["n_idleA"], "n_clean": len(d["clean"]),
                         "n_dirty_idleA": d["n_dirty_idleA"],
                         "gross": gross, "overhead_hyp": overhead,
                         "net_hyp": net_hyp, "net_correct": net_correct,
                         "score_hyp": net_hyp * 947843,
                         "score_correct": net_correct * 947843})
    rows.sort(key=lambda r: (r["k"], r["span"]))
    short_k3 = [r for r in rows if r["k"] == 3 and r["span"] < 200000]
    print(f"k>=3 rows={len(rows)} k5={sum(1 for r in rows if r['k']==5)} "
          f"k4={sum(1 for r in rows if r['k']==4)} k3={sum(1 for r in rows if r['k']==3)} "
          f"k3_short={len(short_k3)}", flush=True)
    print(f"hyp sum net (task model) = {sum(r['net_hyp'] for r in rows)}", flush=True)
    print(f"correct-model sum (+k each) = {sum(r['net_correct'] for r in rows)}", flush=True)
    (ART / "a_cost.json").write_text(
        json.dumps({"rows": rows, "short_k3_gids": [r["gid"] for r in short_k3],
                    "R": 1.19126046, "Q2": 795664, "per_toffoli": 947843}, indent=1) + "\n")
    (ART / "a_smallgap.json").write_text(json.dumps(
        {"n": len(smallgap), "pairs": smallgap}, indent=1) + "\n")

    # ---- overlap / concurrency for k>=4 ----
    segs = sorted([(r["L1"], r["Lk"], r["gid"], r["k"]) for r in rows if r["k"] >= 4])
    ev = []
    for a, b, gid, k in segs:
        ev.append((a, 1))
        ev.append((b + 1, -1))
    ev.sort()
    cur = mx = 0
    for _, d_ in ev:
        cur += d_
        mx = max(mx, cur)
    print(f"k>=4 segs={len(segs)} max_concurrency={mx}", flush=True)
    active = []  # (end, color)
    ncol = 0
    color_of = {}
    for a, b, gid, k in segs:
        active = [(e, c) for e, c in active if e >= a]
        used = {c for _, c in active}
        c = None
        for cand in range(ncol):
            if cand not in used:
                c = cand
                break
        if c is None:
            c = ncol
            ncol += 1
        color_of[gid] = c
        active.append((b, c))
    print(f"k>=4 greedy colors needed={ncol}", flush=True)
    (ART / "a_overlap.json").write_text(json.dumps(
        {"k4plus_segs": [{"L1": a, "Lk": b, "gid": gid, "k": k} for a, b, gid, k in segs],
         "max_concurrency": mx, "greedy_colors": ncol,
         "color_of": {str(g): c for g, c in color_of.items()}}, indent=1) + "\n")

    # ---- CCZ-only grouping ----
    ccz_out = {}
    for st in IN_STAGES:
        S = [s for s in sites[st] if s[1] == "CCZ"]
        g: dict = {}
        for n, s in enumerate(S):
            g.setdefault(s[5], []).append(n)
        multi = {k: v for k, v in g.items() if len(v) >= 2}
        det = []
        for key, v in sorted(multi.items(), key=lambda kv: (-len(kv[1]), min(S[n][0] for n in kv[1])))[:25]:
            v = sorted(v, key=lambda n: S[n][0])
            L = [S[n][0] for n in v]
            det.append({"k": len(v), "L1": L[0], "Lk": L[-1], "span": L[-1] - L[0],
                        "nlits": len({(S[n][2], S[n][3]) for n in v}),
                        "members": [{"idx": S[n][0], "a": S[n][2], "b": S[n][3], "t": S[n][4]}
                                    for n in v]})
        lit: dict = {}
        for n, s in enumerate(S):
            lit.setdefault((s[2], s[3], s[4]), []).append(s[0])
        litmulti = {k: v for k, v in lit.items() if len(v) >= 2}
        ccxkeys = {s[5] for s in sites[st] if s[1] == "CCX"}
        cczkeys = set(g)
        pk_ccx = {k[1] for k in ccxkeys if k[0] == "and"}
        pk_ccz = {k[1] for k in cczkeys if k[0] == "ccz"}
        cross = len(pk_ccx & pk_ccz)
        ccz_out[st] = {"n_ccz": len(S), "distinct": len(g), "repkeys": len(multi),
                       "repocc": sum(len(v) for v in multi.values()),
                       "hist": sorted(Counter(len(v) for v in multi.values()).items()),
                       "litdiv_groups": sum(1 for k, v in multi.items()
                                            if len({(S[n][2], S[n][3]) for n in v}) >= 2),
                       "exact_triple_repkeys": len(litmulti),
                       "exact_triple_repocc": sum(len(v) for v in litmulti.values()),
                       "cross_ccx_ccz_pk": cross, "top": det}
        print(f"{st} CCZ: n={len(S)} repkeys={len(multi)} repocc={sum(len(v) for v in multi.values())} "
              f"hist={sorted(Counter(len(v) for v in multi.values()).items())} "
              f"exact_triple={len(litmulti)}/{sum(len(v) for v in litmulti.values())} cross={cross}", flush=True)
    (ART / "a_ccz.json").write_text(json.dumps(ccz_out, indent=1) + "\n")
    print("wrote artifacts", flush=True)


if __name__ == "__main__":
    main()
