"""Step 3d: consecutive-pair (sub-gap) cache feasibility + full diagnostics.

For each structural multi group, each consecutive pair (Li,Lj) is an independent
cache opportunity (compute at Li into w, use at Lj, uncompute after Lj; net -1
per pair). Greedy over all pairs by (gap asc). Carrier rule as step3c (global
occ; zeroed-or-pristine; member-exclusion; reservations).
Also dumps per-group diagnostic distributions (idle/usable counts).

Writes artifacts/20261109_dqi_deepfix/step3d_subgap.json
"""
from __future__ import annotations
import array
import bisect
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step3d_subgap.json")

def qid(t): return int(t[1:])

class Hasher:
    def __init__(self):
        self.mask = {q: (1 << q, 0) for q in range(892)}
        self.next_atom = 892
        self.memo: dict = {}
        self.sites = []
    def get_atom(self, prov):
        a = self.memo.get(prov)
        if a is None:
            a = self.next_atom; self.next_atom += 1; self.memo[prov] = a
        return a

def main():
    IN_STAGES = ("unsynthesis", "unextract")
    H = {s: Hasher() for s in IN_STAGES}
    occ = {q: array.array("I") for q in range(840, 892)}
    zero_at = {}
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
            cond = (depth > 0) or (inline is not None)
            if op in ("HMR", "R") and not cond and args and args[0][0] == "q":
                zero_at[idx] = qid(args[0])
            if op in ("X", "CX", "SWAP", "HMR", "R", "CCX", "CCZ", "CSWAP", "CZ"):
                for tok in args:
                    if tok and tok[0] == "q":
                        q = int(tok[1:])
                        if 840 <= q <= 891:
                            occ[q].append(idx)
            if stage not in IN_STAGES:
                continue
            h = H[stage]; mask = h.mask
            if op == "X":
                q = qid(args[0])
                if cond: mask[q] = (1 << h.get_atom(("dirty", idx)), 0)
                else:
                    m, c = mask[q]; mask[q] = (m, c ^ 1)
            elif op == "CX":
                a, b = qid(args[0]), qid(args[1])
                if cond: mask[b] = (1 << h.get_atom(("dirty", idx)), 0)
                else:
                    ma, ca = mask[a]; mb, cb = mask[b]
                    mask[b] = (ma ^ mb, ca ^ cb)
            elif op == "SWAP":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    mask[a] = (1 << h.get_atom(("dirty", idx)), 0)
                    mask[b] = (1 << h.get_atom(("dirty", idx)), 0)
                else:
                    mask[a], mask[b] = mask[b], mask[a]
            elif op in ("HMR", "R"):
                q = qid(args[0])
                if not cond: mask[q] = (0, 0)
                else: mask[q] = (1 << h.get_atom(("dirty", idx)), 0)
            elif op == "CCX":
                a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    mask[t] = (1 << h.get_atom(("dirty", idx)), 0)
                    continue
                ma, ca = mask[a]; mb, cb = mask[b]
                ka, kb = (ma, ca), (mb, cb)
                pk = tuple(sorted((ka, kb)))
                if ka == kb:
                    mt, ct = mask[t]
                    mask[t] = (mt ^ ma, ct ^ ca)
                    h.sites.append((idx, a, b, t))
                else:
                    pa = h.get_atom(("and", pk))
                    mt, ct = mask[t]
                    mask[t] = (mt ^ (1 << pa), ct)
                    h.sites.append((idx, a, b, t))
                # NOTE: key recomputed below from masks; store key now:
                h.sites[-1] = (idx, a, b, t, ("and", pk) if ka != kb else ("affwk", ka))
            elif op == "CCZ":
                a, b = qid(args[0]), qid(args[1])
                if cond: continue
                ma, ca = mask[a]; mb, cb = mask[b]
                pk = tuple(sorted(((ma, ca), (mb, cb))))
                h.sites.append((idx, a, b, qid(args[2]), ("and", pk)))
            elif op == "CSWAP":
                c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    mask[a] = (1 << h.get_atom(("dirty", idx)), 0)
                    mask[b] = (1 << h.get_atom(("dirty", idx)), 0)
                else:
                    fa, fb, fc = mask[a], mask[b], mask[c_]
                    mask[a] = (1 << h.get_atom(("mux", 0, fc, fa, fb)), 0)
                    mask[b] = (1 << h.get_atom(("mux", 1, fc, fa, fb)), 0)
    print("pass done", flush=True)
    O = {q: list(v) for q, v in occ.items()}

    def touches(w, lo, hi):
        lst = O[w]
        i = bisect.bisect_left(lst, lo)
        j = bisect.bisect_right(lst, hi)
        return j - i

    def usable(w, L1):
        lst = O[w]
        i = bisect.bisect_left(lst, L1) - 1
        if i < 0:
            return "pristine"
        return "hmr-zero" if lst[i] in zero_at else None

    pairs = []
    diag = []
    for st in IN_STAGES:
        groups: dict = {}
        for n, s in enumerate(H[st].sites):
            groups.setdefault(s[4], []).append(n)
        for k2, v in groups.items():
            if len(v) < 2:
                continue
            v = sorted(v, key=lambda n: H[st].sites[n][0])
            L = [H[st].sites[n][0] for n in v]
            mw_full = set()
            for n in v:
                mw_full.add(H[st].sites[n][1]); mw_full.add(H[st].sites[n][2]); mw_full.add(H[st].sites[n][3])
            idle_full = sum(1 for w in range(840, 892)
                            if w not in mw_full and touches(w, L[0], L[-1]) == 0)
            use_full = sum(1 for w in range(840, 892)
                           if w not in mw_full and touches(w, L[0], L[-1]) == 0
                           and usable(w, L[0]))
            diag.append({"stage": st, "k": len(v), "span": L[-1] - L[0],
                         "idle_full": idle_full, "usable_full": use_full,
                         "nlits": len({(H[st].sites[n][1], H[st].sites[n][2]) for n in v})})
            for j in range(len(v) - 1):
                a, b = v[j], v[j + 1]
                sa, sb = H[st].sites[a], H[st].sites[b]
                mw = {sa[1], sa[2], sa[3], sb[1], sb[2], sb[3]}
                pairs.append({"stage": st, "Li": sa[0], "Lj": sb[0],
                              "gap": sb[0] - sa[0], "mw": sorted(mw)})
    print(f"consecutive pairs: {len(pairs)}", flush=True)
    import collections
    print("group diag: idle_full dist:",
          sorted(collections.Counter(d["idle_full"] for d in diag).items())[:10], flush=True)
    print("group diag: usable_full>0 count:",
          sum(1 for d in diag if d["usable_full"] > 0), flush=True)
    # gap distribution
    gaps = sorted(p["gap"] for p in pairs)
    print(f"gap min={gaps[0]} median={gaps[len(gaps)//2]} max={gaps[-1]}", flush=True)

    pairs.sort(key=lambda p: p["gap"])
    reserved = {q: [] for q in range(840, 892)}
    feas = []
    for p in pairs:
        L1, Lk, mw = p["Li"], p["Lj"], set(p["mw"])
        hit = None; how = None
        for w in range(840, 892):
            if w in mw or touches(w, L1, Lk) > 0:
                continue
            u = usable(w, L1)
            if not u:
                continue
            if any(not (Lk < s or L1 > e) for s, e in reserved[w]):
                continue
            hit, how = w, u; break
        if hit is not None:
            reserved[hit].append((L1, Lk + 1))
            feas.append({"stage": p["stage"], "Li": L1, "Lj": Lk, "gap": p["gap"],
                         "wire": hit, "how": how})
    print(f"subgap feasible pairs={len(feas)} net={len(feas)}", flush=True)
    for f in feas[:30]:
        print(f"  {f['stage']} gap={f['gap']} wire=q{f['wire']}({f['how']}) Li={f['Li']}", flush=True)
    OUT.write_text(json.dumps({"n_pairs": len(pairs),
                               "gap_min": gaps[0], "gap_med": gaps[len(gaps)//2], "gap_max": gaps[-1],
                               "group_diag": diag,
                               "feasible_pairs": feas, "net": len(feas)}, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
