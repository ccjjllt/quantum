"""Manual actual-prefix probe for a zeroable idle wire in two AND-recompute gaps.

All proposed relations are discovery hypotheses until a full-prefix SAT proof.
No candidate is submitted and the official verifier is never called here.
"""
from __future__ import annotations
import argparse
import io
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import approx_window as A

ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
WINDOWS = ((25215, 25229), (25333, 25345))


def idle_lines(ops, lo, hi):
    touched = {int(t[1:]) for line in ops[lo:hi] for t in line.split() if t.startswith("q")}
    return [q for q in range(62) if q not in touched]


def unchanged_lines(ops, lo, hi):
    written=set()
    for line in ops[lo:hi]:
        p=line.split();qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if p[0] in ('X','CX','CCX','HMR','R'):written.update(qs[-1:])
        elif p[0] in ('SWAP','CSWAP'):written.update(qs[-2:])
    return [q for q in range(62) if q not in written]


def kickmix_snapshots(n,seed,indices):
    import kickmix as km
    header,ops=A.P.load_baseline()
    xs,_=A.packed_inputs(n,seed)
    snapshots={}
    for lo in indices:
        c=km.Circuit.from_file(io.StringIO('\n'.join(header+ops[:lo])+'\n'),format='kmx')
        sim=km.Simulator(batch_size=256,seed=seed)
        sim.use_same_registers_as(c)
        packed=[0]*62
        for start in range(0,len(xs),256):
            chunk=xs[start:start+256]
            sim.clear_for_shot()
            for shot in range(256):sim.write_within_shot('x',shot,chunk[shot] if shot<len(chunk) else 1)
            sim.do(c)
            for q in range(62):
                out=sim.read_across_shots(km.q(q))
                packed[q] |= sum(int(bool(out[j])) << (start+j) for j in range(len(chunk)))
        snapshots[lo]=packed
    return xs,snapshots


def snapshots(n, seed, indices):
    _, ops = A.P.load_baseline()
    xs, wire = A.packed_inputs(n, seed)
    one = (1 << len(xs)) - 1
    rng = random.Random(seed ^ 0x1D1E)
    bits, stack, result = {}, [], {}
    for i, line in enumerate(ops[:max(indices) + 1]):
        if i in indices:
            result[i] = list(wire)
        p = line.split(); k = p[0]
        if k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0)); continue
        if k == "POP_CONDITION":
            stack.pop(); continue
        active = one
        for b in stack:
            active &= b
        if "if" in p:
            active &= bits.get(int(p[p.index("if") + 1][1:]), 0)
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        if k == "X": wire[qs[0]] ^= active
        elif k == "CX": wire[qs[1]] ^= wire[qs[0]] & active
        elif k == "CCX": wire[qs[2]] ^= wire[qs[0]] & wire[qs[1]] & active
        elif k in ("SWAP", "CSWAP"):
            a, b = qs[-2:]; ctl = active if k == "SWAP" else active & wire[qs[0]]
            d = (wire[a] ^ wire[b]) & ctl; wire[a] ^= d; wire[b] ^= d
        elif k in ("R", "HMR"):
            outcome = rng.getrandbits(len(xs))
            wire[qs[0]] &= one ^ active
            if k == "HMR":
                b = int(p[2][1:]);old=bits.get(b,0);bits[b]=old ^ ((old ^ outcome) & active)
        elif k in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            b = int(p[1][1:]);old=bits.get(b,0)
            new=0 if k=="BIT_STORE0" else one if k=="BIT_STORE1" else old ^ one
            bits[b]=old ^ ((old ^ new) & active)
        elif k not in ("Z", "CZ", "CCZ", "NEG", "Z_POW", "INFO_TAG"):
            raise ValueError((i,line))
    return xs, result


def relations(values, idle, one):
    basis, nulls = {}, []
    for j, q in enumerate(idle + [-1]):
        value = one if q == -1 else values[q]
        mask = 1 << j
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value, mask
                break
            b, m = basis[pivot];value ^= b;mask ^= m
        if not value:
            nulls.append([q for k,q in enumerate(idle + [-1]) if mask >> k & 1])
    return len(basis), nulls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=8192)
    ap.add_argument("--seeds", default="20261111,20261112,20261113")
    ap.add_argument("--kickmix", action="store_true")
    args = ap.parse_args()
    _, ops = A.P.load_baseline()
    seeds = [int(s) for s in args.seeds.split(",")]
    first = None
    rows = []
    for seed in seeds:
        xs, snaps = (kickmix_snapshots if args.kickmix else snapshots)(args.samples, seed, [lo for lo, _ in WINDOWS])
        one = (1 << len(xs)) - 1
        this = {}
        for lo,hi in WINDOWS:
            idle = idle_lines(ops,lo,hi)
            rank, found = relations(snaps[lo],idle,one)
            rec = {"window": [lo,hi], "idle_wires": idle, "n_idle": len(idle),
                   "rank_with_constant": rank, "null_relations": found}
            unchanged=unchanged_lines(ops,lo,hi)
            urank,urels=relations(snaps[lo],unchanged,one)
            rec['unchanged_including_read_controls']={'wires':unchanged,'n':len(unchanged),
                'rank_with_constant':urank,'null_relations':urels}
            if first is not None:
                checks=[]
                for relation in first[str(lo)]["null_relations"]:
                    value=0
                    for q in relation:value ^= one if q == -1 else snaps[lo][q]
                    checks.append({"relation":relation,"n_fail":value.bit_count(),
                                   "first_fail_x":xs[(value & -value).bit_length()-1] if value else None})
                rec["fixed_first_seed_relations"] = checks
            this[str(lo)] = rec
        if first is None:first=this
        rows.append({"seed":seed,"samples":len(xs),"windows":this})
    result={"baseline_sha256":A.P.BASELINE_SHA,"backend":"kickmix actual prefix" if args.kickmix else "packed boolean prefix", "rows":rows,
            "scope":"sampled legal x and independent measurement outcomes; rank deficiency is only a hypothesis; -1 denotes constant one"}
    ART.mkdir(parents=True,exist_ok=True)
    path=ART/('idle_cache_probe_kickmix.json' if args.kickmix else 'idle_cache_probe.json');path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':main()
