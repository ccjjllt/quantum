"""Step 3c: final carrier analysis with FULL-FILE occ + pristine rule.

One pass collects: global ancilla touches (all stages), global zero events,
per-stage literal occ; per-stage atom-hasher states updated inline.
Carrier rule (fixed): w in 840..891, not a member wire, no touch in [L1,Lk],
and (last touch before L1 is uncond HMR/R zero OR no touch at all before L1
=> pristine |0>). Greedy over all structural multi groups by (k desc, span asc).
Also recounts literal top-20 (HMR-zeroed vs pristine).

Writes artifacts/20261109_dqi_deepfix/step3c_carriers.json
"""
from __future__ import annotations
import array
import bisect
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step3c_carriers.json")

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
    lit_pos = {s: {} for s in IN_STAGES}
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
            # global ancilla occ (all value-touching op types)
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
                if not cond:
                    lit_pos[stage].setdefault(tuple(sorted((a, b))), []).append(idx)
                if cond:
                    mask[t] = (1 << h.get_atom(("dirty", idx)), 0)
                    continue
                ma, ca = mask[a]; mb, cb = mask[b]
                ka, kb = (ma, ca), (mb, cb)
                pk = tuple(sorted((ka, kb)))
                if ka == kb:
                    mt, ct = mask[t]
                    mask[t] = (mt ^ ma, ct ^ ca)
                    h.sites.append((idx, a, b, t, ("affwk", ka)))
                else:
                    pa = h.get_atom(("and", pk))
                    mt, ct = mask[t]
                    mask[t] = (mt ^ (1 << pa), ct)
                    h.sites.append((idx, a, b, t, ("and", pk)))
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

    def carrier_ok(w, L1):
        lst = O[w]
        i = bisect.bisect_left(lst, L1) - 1
        if i < 0:
            return True, "pristine"
        return (lst[i] in zero_at), ("hmr-zero" if lst[i] in zero_at else "touched")

    # structural groups
    cands = []
    for st in IN_STAGES:
        groups: dict = {}
        for n, s in enumerate(H[st].sites):
            groups.setdefault(s[4], []).append(n)
        for k2, v in groups.items():
            if len(v) < 2:
                continue
            v = sorted(v, key=lambda n: H[st].sites[n][0])
            L = [H[st].sites[n][0] for n in v]
            cands.append((st, v, L, H[st].sites))
    cands.sort(key=lambda c: (-len(c[1]), c[2][-1] - c[2][0]))
    print(f"structural multi groups: {len(cands)}", flush=True)
    reserved = {q: [] for q in range(840, 892)}
    feas = []
    for st, v, L, ss in cands:
        L1, Lk = L[0], L[-1]
        mw = set()
        for n in v:
            mw.add(ss[n][1]); mw.add(ss[n][2]); mw.add(ss[n][3])
        hit = None; how = None
        for w in range(840, 892):
            if w in mw or touches(w, L1, Lk) > 0:
                continue
            ok, why = carrier_ok(w, L1)
            if not ok:
                continue
            if any(not (Lk < s or L1 > e) for s, e in reserved[w]):
                continue
            hit, how = w, why; break
        if hit is not None:
            reserved[hit].append((L1, Lk + 1))
            feas.append({"stage": st, "k": len(v), "L1": L1, "Lk": Lk,
                         "span": Lk - L1, "wire": hit, "how": how,
                         "save": len(v) - 1,
                         "nlits": len({(ss[n][1], ss[n][2]) for n in v})})
    total = sum(f["save"] for f in feas)
    print(f"feasible={len(feas)} net={total}", flush=True)
    for f in feas[:30]:
        print(f"  {f['stage']} k={f['k']} save={f['save']} wire=q{f['wire']}({f['how']}) span={f['span']}", flush=True)

    # literal top-20 by span recount with both rules
    litrep = {}
    for st in IN_STAGES:
        rep = [(k, v) for k, v in lit_pos[st].items() if len(v) >= 2]
        rep.sort(key=lambda kv: -(kv[1][-1] - kv[1][0]))
        rows = []
        for k, v in rep[:20]:
            L1, Lk = v[0], v[-1]
            mw = {k[0], k[1]}
            idle = [w for w in range(840, 892) if w not in mw and touches(w, L1, Lk) == 0]
            hz = [w for w in idle if carrier_ok(w, L1) == (True, "hmr-zero")]
            pr = [w for w in idle if carrier_ok(w, L1) == (True, "pristine")]
            rows.append({"key": list(k), "k": len(v), "span": Lk - L1,
                         "n_idle": len(idle), "n_hmrzero": len(hz), "n_pristine": len(pr)})
        litrep[st] = {"distinct": len(lit_pos[st]),
                      "repkeys": len(rep), "repocc": sum(len(v) for v in rep),
                      "top20": rows}
        print(f"{st} literal: distinct={len(lit_pos[st])} repkeys={len(rep)}", flush=True)
    OUT.write_text(json.dumps({"structural_feasible": feas, "structural_net": total,
                               "literal": litrep}, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
