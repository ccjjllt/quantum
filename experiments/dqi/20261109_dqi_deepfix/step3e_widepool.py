"""Step 3e: wide-pool (all 892 wires) carrier check for small-gap pairs.

Single pass: unextract+unsynthesis atom-hashers (pair locations), ancilla
full-file occ, data-wire (0..839) touches within target stages only, global
zero_at. Then: pairs with gap<=200 -> check ALL 892 wires for
idle-in-[Li,Lj] + (last-touch-zero (global for ancillas; in-target-stages
for data wires)). Sound (may miss earlier-stage-zeroed data wires).

Writes artifacts/20261109_dqi_deepfix/step3e_widepool.json
"""
from __future__ import annotations
import array
import bisect
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step3e_widepool.json")

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

UNEXT = (52196517, 57991316)
UNSYN = (46497681, 52196516)

def main():
    IN_STAGES = ("unsynthesis", "unextract")
    H = {s: Hasher() for s in IN_STAGES}
    occA = {q: array.array("I") for q in range(840, 892)}   # full-file
    occD = {q: array.array("I") for q in range(840)}        # target stages only
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
                qs = []
                for tok in args:
                    if tok and tok[0] == "q":
                        qs.append(int(tok[1:]))
                for q in qs:
                    if 840 <= q <= 891:
                        occA[q].append(idx)
                    elif stage in IN_STAGES and q < 840:
                        occD[q].append(idx)
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
                    h.sites.append((idx, a, b, t, ("aff wk", ka)))
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
    OA = {q: list(v) for q, v in occA.items()}
    OD = {q: list(v) for q, v in occD.items()}

    def touches(lst, lo, hi):
        i = bisect.bisect_left(lst, lo)
        j = bisect.bisect_right(lst, hi)
        return j - i

    pairs = []
    for st in IN_STAGES:
        groups: dict = {}
        for n, s in enumerate(H[st].sites):
            groups.setdefault(s[4], []).append(n)
        for k2, v in groups.items():
            if len(v) < 2:
                continue
            v = sorted(v, key=lambda n: H[st].sites[n][0])
            L = [H[st].sites[n][0] for n in v]
            for j in range(len(v) - 1):
                sa, sb = H[st].sites[v[j]], H[st].sites[v[j + 1]]
                pairs.append((st, sa[0], sb[0], sb[0] - sa[0],
                              {sa[1], sa[2], sa[3], sb[1], sb[2], sb[3]}))
    small = [p for p in pairs if p[3] <= 200]
    print(f"pairs<=200 lines: {len(small)}/{len(pairs)}", flush=True)
    rows = []
    for st, L1, Lj, gap, mw in sorted(small, key=lambda p: p[3])[:40]:
        idleA = [w for w in range(840, 892) if w not in mw and touches(OA[w], L1, Lj) == 0]
        useA = []
        for w in idleA:
            lst = OA[w]
            i = bisect.bisect_left(lst, L1) - 1
            if i < 0:
                useA.append((w, "pristine"))
            elif lst[i] in zero_at:
                useA.append((w, "hmr-zero"))
        idleD = [w for w in range(840) if w not in mw and touches(OD[w], L1, Lj) == 0]
        useD = []
        for w in idleD:
            lst = OD[w]
            i = bisect.bisect_left(lst, L1) - 1
            if i >= 0 and lst[i] in zero_at:
                useD.append(w)
        rows.append({"stage": st, "Li": L1, "Lj": Lj, "gap": gap,
                     "n_idleA": len(idleA), "useA": useA,
                     "n_idleD": len(idleD), "useD": useD[:8], "n_useD": len(useD)})
        print(f"{st} gap={gap} idleA={len(idleA)} useA={useA} idleD={len(idleD)} useD={len(useD)}", flush=True)
    OUT.write_text(json.dumps({"n_small": len(small), "rows": rows}, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
