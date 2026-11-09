"""Step 2b: verify structural repeat candidates with km.Simulator stage slices.

For each selected site pair (Li<Lj, same stage, equal structural key):
  slice1 = file header + stage[entry..Li], slice2 = header + stage[entry..Lj];
  random 4-shot inputs (all 892 qubits + all bits, rng seed fixed);
  compare (a&b) products across shots. Equal on all shots => supports exact
  formula identity (structural proof is primary; this cross-checks implementation).
Also: determinism sanity (repeat one slice, expect identical reads).

Writes artifacts/20261109_dqi_deepfix/step2b_verify.json
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

import numpy as np

import kickmix as km

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_deepfix/step2b_verify.json")

HEADER_END = 54145  # first top-level @enter (mask_projection)
BOUNDS = {"unsynthesis": (46497681, 52196516), "unextract": (52196517, 57991316)}

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

def hash_stage(stage):
    mask = {q: (1 << q, 0) for q in range(892)}
    next_atom = 892
    memo: dict = {}
    def get_atom(prov):
        nonlocal next_atom
        a = memo.get(prov)
        if a is None:
            a = next_atom; next_atom += 1; memo[prov] = a
        return a
    sites = []
    for idx, st, op, args, inline, depth in parse():
        if st != stage:
            continue
        cond = (depth > 0) or (inline is not None)
        if op == "X":
            q = qid(args[0])
            if cond:
                mask[q] = (1 << get_atom(("dirty", idx)), 0)
            else:
                m, c = mask[q]; mask[q] = (m, c ^ 1)
        elif op == "CX":
            a, b = qid(args[0]), qid(args[1])
            if cond:
                mask[b] = (1 << get_atom(("dirty", idx)), 0)
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
            if not cond:
                mask[q] = (0, 0)
            else:
                mask[q] = (1 << get_atom(("dirty", idx)), 0)
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
                sites.append((idx, stage, "CCX", a, b, t, ("affwk", ka)))
            else:
                pa = get_atom(("and", pk))
                mt, ct = mask[t]
                mask[t] = (mt ^ (1 << pa), ct)
                sites.append((idx, stage, "CCX", a, b, t, ("and", pk)))
        elif op == "CCZ":
            a, b = qid(args[0]), qid(args[1])
            if cond:
                continue
            ma, ca = mask[a]; mb, cb = mask[b]
            pk = tuple(sorted(((ma, ca), (mb, cb))))
            sites.append((idx, stage, "CCZ", a, b, qid(args[2]), ("and", pk)))
        elif op == "CSWAP":
            c_, a, b = qid(args[0]), qid(args[1]), qid(args[2])
            if cond:
                mask[a] = (1 << get_atom(("dirty", idx)), 0)
                mask[b] = (1 << get_atom(("dirty", idx)), 0)
            else:
                fa, fb, fc = mask[a], mask[b], mask[c_]
                mask[a] = (1 << get_atom(("mux", 0, fc, fa, fb)), 0)
                mask[b] = (1 << get_atom(("mux", 1, fc, fa, fb)), 0)
    return sites

def load_lines(lo, hi):
    with open(KMX) as f:
        lines = f.readlines()
    return lines

def sim_slice(text, seed, qb, bb, nbits):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(892)]), qb)
    sim.write_across_shots(km.array([km.b(i) for i in range(nbits)]), bb)
    sim.do(c)
    return sim, c

def read_prod(sim, a, b):
    va = [bool(v) for v in sim.read_across_shots(km.q(a))]
    vb = [bool(v) for v in sim.read_across_shots(km.q(b))]
    return [int(x and y) for x, y in zip(va, vb)]

def main():
    results = {"pairs": []}
    for stage in ("unsynthesis", "unextract"):
        print(f"hashing {stage}...", flush=True)
        sites = hash_stage(stage)
        groups: dict = {}
        for n, s in enumerate(sites):
            groups.setdefault(s[6], []).append(n)
        multi = [(k, v) for k, v in groups.items() if len(v) >= 2]
        multi.sort(key=lambda kv: (-len(kv[1]), min(sites[n][0] for n in kv[1])))
        print(f"{stage}: {len(multi)} multi groups", flush=True)
        # selection
        same = [kv for kv in multi if len({(sites[n][3], sites[n][4]) for n in kv[1]}) == 1]
        litdiv = [kv for kv in multi if len({(sites[n][3], sites[n][4]) for n in kv[1]}) >= 2]
        litdiv.sort(key=lambda kv: max(sites[n][0] for n in kv[1]))
        same.sort(key=lambda kv: (-len(kv[1]), min(sites[n][0] for n in kv[1])))
        picks = []
        for kv in same[:2]:
            v = sorted(kv[1], key=lambda n: sites[n][0])
            picks.append((v[0], v[1], "same-literal"))
        for kv in litdiv[:2]:
            v = sorted(kv[1], key=lambda n: sites[n][0])
            picks.append((v[0], v[1], "litdiv"))
        print(f"{stage} picks: {[(sites[a][0], sites[b][0], t) for a, b, t in picks]}", flush=True)
        results[stage + "_picks"] = [
            {"Li": sites[a][0], "Lj": sites[b][0], "kind": t,
             "ai": sites[a][3], "bi": sites[a][4], "ti": sites[a][5],
             "aj": sites[b][3], "bj": sites[b][4], "tj": sites[b][5],
             "k": len(multi[0][1])} for (a, b, t) in picks for multi in [[]]
        ] if False else [
            {"Li": sites[a][0], "Lj": sites[b][0], "kind": t,
             "ai": sites[a][3], "bi": sites[a][4], "ti": sites[a][5],
             "aj": sites[b][3], "bj": sites[b][4], "tj": sites[b][5]}
            for (a, b, t) in picks
        ]
    # persist picks early
    OUT.write_text(json.dumps(results, indent=1) + "\n")

    print("loading file lines...", flush=True)
    with open(KMX) as f:
        lines = f.readlines()
    print(f"total lines {len(lines)}", flush=True)
    header = lines[:HEADER_END]
    rng = np.random.default_rng(0xD91)
    qb = rng.integers(0, 2, size=(892, 4)).astype(np.bool_)
    # bits: discover num_bits from a probe circuit later; use max 200003+ margin via first slice
    first_stage = "unsynthesis"
    entry, _ = BOUNDS[first_stage]
    probe_c = km.Circuit("".join(header + lines[entry:entry + 5000]))
    nbits = probe_c.num_bits
    print(f"num_bits={nbits}", flush=True)
    bb = rng.integers(0, 2, size=(nbits, 4)).astype(np.bool_)

    for stage in ("unsynthesis", "unextract"):
        entry, exit_ = BOUNDS[stage]
        for p in results[stage + "_picks"]:
            Li, Lj = p["Li"], p["Lj"]
            t1 = "".join(header + lines[entry:Li + 1])
            t2 = "".join(header + lines[entry:Lj + 1])
            sim1, _ = sim_slice(t1, 99, qb, bb, nbits)
            r1 = read_prod(sim1, p["ai"], p["bi"])
            sim2, _ = sim_slice(t2, 99, qb, bb, nbits)
            r2 = read_prod(sim2, p["aj"], p["bj"])
            # determinism repeat of slice1
            sim1b, _ = sim_slice(t1, 99, qb, bb, nbits)
            r1b = read_prod(sim1b, p["ai"], p["bi"])
            p["prod_Li"] = r1
            p["prod_Lj"] = r2
            p["agree"] = (r1 == r2)
            p["deterministic"] = (r1 == r1b)
            print(f"{stage} {p['kind']} Li={Li} Lj={Lj} agree={p['agree']} det={p['deterministic']} "
                  f"prod={r1} vs {r2}", flush=True)
            OUT.write_text(json.dumps(results, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
