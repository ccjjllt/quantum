"""Step 2a: exact structural (formula-identity) product grouping, per stage.

Value model (exact, no simulation):
- Each wire holds an affine combination (mask over atom space + const bit).
- Atoms: 0..891 = stage-entry qubit values (fresh per stage); product atoms
  allocated memo-wise per canonical product key; mux atoms for CSWAP (memoized
  by provenance); unique atoms for conditional writes (sound: never shared).
- X/CX/SWAP/HMR-R: exact affine updates. HMR/R uncond -> constant 0 (shared).
- CCX a b t uncond: pk = canonical((ma,ca),(mb,cb)); site key = pk;
  target update: mask[t] ^= 1<<prodatom(pk) (a==b degenerates: prod = affine).
- CCZ: site key = ('ccz', pk); no value change.
- Cond value-write: fresh unique atom (sound under-approximation of sharing).
- CSWAP uncond: memoized mux atoms (exact mux formula identity).
Equal site key ==> provably equal boolean product function (same affine combo
of same atoms; affine relations collapse automatically via mask xor).

Writes artifacts/20261109_dqi_deepfix/step2a_struct.json + top-group detail.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step2a_struct.json")
DET = Path("artifacts/20261109_dqi_deepfix/step2a_topgroups.json")

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
    per_stage = {}
    all_sites = []  # (idx, stage, op, a, b, t, key)
    for stage in IN_STAGES:
        mask = {q: (1 << q, 0) for q in range(892)}  # q -> (mask_int, const)
        next_atom = 892
        memo: dict = {}  # provenance -> atom idx
        def get_atom(prov):
            nonlocal next_atom
            a = memo.get(prov)
            if a is None:
                a = next_atom; next_atom += 1; memo[prov] = a
            return a
        sites = []
        n_cond = 0; n_dirty_ops = 0
        for idx, st, op, args, inline, depth in parse():
            if st != stage:
                continue
            cond = (depth > 0) or (inline is not None)
            if op == "X":
                q = qid(args[0])
                if cond:
                    mask[q] = (1 << get_atom(("dirty", idx)), 0); n_dirty_ops += 1
                else:
                    m, c = mask[q]; mask[q] = (m, c ^ 1)
            elif op == "CX":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    mask[b] = (1 << get_atom(("dirty", idx)), 0); n_dirty_ops += 1
                else:
                    ma, ca = mask[a]; mb, cb = mask[b]
                    mask[b] = (ma ^ mb, ca ^ cb)
            elif op == "SWAP":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    mask[a] = (1 << get_atom(("dirty", idx)), 0)
                    mask[b] = (1 << get_atom(("dirty", idx)), 0); n_dirty_ops += 1
                else:
                    mask[a], mask[b] = mask[b], mask[a]
            elif op in ("HMR", "R"):
                q = qid(args[0])
                if not cond:
                    mask[q] = (0, 0)
                else:
                    mask[q] = (1 << get_atom(("dirty", idx)), 0); n_dirty_ops += 1
            elif op == "CCX":
                a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    n_cond += 1
                    mask[t] = (1 << get_atom(("dirty", idx)), 0); n_dirty_ops += 1
                    continue
                ma, ca = mask[a]; mb, cb = mask[b]
                ka, kb = (ma, ca), (mb, cb)
                pk = tuple(sorted((ka, kb)))
                if ka == kb:  # a==b as functions: prod = affine itself
                    mt, ct = mask[t]
                    mask[t] = (mt ^ ma, ct ^ ca)
                    sites.append((idx, stage, "CCX", a, b, t, ("aff wk", ka)))
                else:
                    pa = get_atom(("and", pk))
                    mt, ct = mask[t]
                    mask[t] = (mt ^ (1 << pa), ct)
                    sites.append((idx, stage, "CCX", a, b, t, ("and", pk)))
            elif op == "CCZ":
                a, b = qid(args[0]), qid(args[1])
                if cond:
                    n_cond += 1; continue
                ma, ca = mask[a]; mb, cb = mask[b]
                pk = tuple(sorted(((ma, ca), (mb, cb))))
                sites.append((idx, stage, "CCZ", a, b, qid(args[2]), ("and", pk)))
            elif op == "CSWAP":
                c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
                if cond:
                    mask[a] = (1 << get_atom(("dirty", idx)), 0)
                    mask[b] = (1 << get_atom(("dirty", idx)), 0); n_dirty_ops += 1
                else:
                    fa, fb, fc = mask[a], mask[b], mask[c_]
                    mask[a] = (1 << get_atom(("mux", 0, fc, fa, fb)), 0)
                    mask[b] = (1 << get_atom(("mux", 1, fc, fa, fb)), 0)
            # CZ/Z/BIT/NEG: no value effect
        # group by site key
        groups: dict = {}
        for n, s in enumerate(sites):
            groups.setdefault(s[6], []).append(n)
        multi = {k: v for k, v in groups.items() if len(v) >= 2}
        # literal-diverse groups: same function, >1 distinct literal
        litdiv = {}
        for k, v in multi.items():
            lits = {(sites[n][3], sites[n][4]) for n in v}
            if len(lits) >= 2:
                litdiv[k] = v
        all_sites.extend(sites)
        per_stage[stage] = {
            "n_sites": len(sites),
            "n_cond_ccx_ccz": n_cond,
            "n_dirty_ops": n_dirty_ops,
            "n_atoms": next_atom,
            "distinct_keys": len(groups),
            "repkeys": len(multi),
            "repocc": sum(len(v) for v in multi.values()),
            "litdiv_groups": len(litdiv),
            "litdiv_occ": sum(len(v) for v in litdiv.values()),
        }
        print(f"== {stage}: sites={len(sites)} cond={n_cond} dirtyops={n_dirty_ops} atoms={next_atom}", flush=True)
        print(f"   distinct={len(groups)} repkeys={len(multi)} repocc={sum(len(v) for v in multi.values())} "
              f"litdiv_groups={len(litdiv)} litdiv_occ={sum(len(v) for v in litdiv.values())}", flush=True)
        # size histogram
        print(f"   size hist: {sorted(Counter(len(v) for v in multi.values()).items())[:12]}", flush=True)
        # top groups detail
        cands = sorted(multi.items(), key=lambda kv: (-len(kv[1]), min(sites[n][0] for n in kv[1])))
        for k, v in cands[:8]:
            L = [sites[n][0] for n in v]
            lits = Counter((sites[n][3], sites[n][4]) for n in v)
            print(f"   k={len(v)} span={max(L)-min(L)} nlits={len(lits)} toplits={lits.most_common(3)} "
                  f"L1={min(L)} Lk={max(L)}", flush=True)
        per_stage[stage]["_sites"] = sites

    # save top-25 groups per stage with full member lists
    det = {}
    for stage in IN_STAGES:
        sites = per_stage[stage].pop("_sites")
        groups: dict = {}
        for n, s in enumerate(sites):
            groups.setdefault(s[6], []).append(n)
        cands = sorted(groups.items(), key=lambda kv: (-len(kv[1]), min(sites[n][0] for n in kv[1])))[:25]
        det[stage] = [{
            "k": len(v),
            "L1": min(sites[n][0] for n in v),
            "Lk": max(sites[n][0] for n in v),
            "nlits": len({(sites[n][3], sites[n][4]) for n in v}),
            "members": [{"idx": sites[n][0], "op": sites[n][2], "a": sites[n][3],
                         "b": sites[n][4], "t": sites[n][5]} for n in sorted(v, key=lambda n: sites[n][0])],
        } for k, v in cands]
    OUT.write_text(json.dumps({s: {k: v for k, v in per_stage[s].items()} for s in IN_STAGES}, indent=1) + "\n")
    DET.write_text(json.dumps(det, indent=1) + "\n")
    print(f"wrote {OUT} {DET}", flush=True)

if __name__ == "__main__":
    main()
