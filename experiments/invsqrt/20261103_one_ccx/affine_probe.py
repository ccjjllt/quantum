"""Manual discovery of one CCX replaced by an affine update on bce/62Q.

This is a candidate finder, never an equivalence certificate. Basis values
are traced in parallel as Python bitsets; measurement outcomes are independent
bits and PUSH captures its current value. Candidate generation and validation
are separate manual actions. No official verifier runs here.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import random
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
OUT = ROOT / "artifacts/20261103_one_ccx/invsqrt"
MAXX = 3133452


def load():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    c = km.Circuit.from_file(BASE)
    s = io.StringIO()
    c.to_file(s, format="kmx")
    lines = s.getvalue().splitlines()
    hdr = [s for s in lines if s.startswith(("REGISTER", "APPEND"))]
    ops = [s for s in lines if not s.startswith(("REGISTER", "APPEND"))]
    return hdr, ops


def inputs(seed, n):
    rng = random.Random(seed)
    xs = set(range(1, 4097))
    xs.update(rng.randrange(1, MAXX + 1) for _ in range(n))
    for bit in range(22):
        xs.update(x for x in (2**bit-2, 2**bit-1, 2**bit, 2**bit+1, 2**bit+2)
                  if 1 <= x <= MAXX)
    for a in range(256):
        for d in (0,1,8191,8192,16382,16383):
            m = (1<<21) | ((a&127)<<14) | d
            for lz in (a>>7, 2+(a>>7)):
                if not m % (1<<lz) and 1 <= m>>lz <= MAXX:
                    xs.add(m>>lz)
    return sorted(xs)


def trace_candidates(ops, xs, seed, prior=None, discover_kind='CCX'):
    n = len(xs)
    mask = (1 << n) - 1
    rng = random.Random(seed)
    q = [sum(((x >> j) & 1) << i for i, x in enumerate(xs)) for j in range(22)] + [0]*40
    bits = {}
    stack = []
    hits = []
    allowed = None if prior is None else {r['op']: r for r in prior}
    for i, line in enumerate(ops):
        p = line.split(); k=p[0]
        active = mask
        for c in stack: active &= c
        if 'if' in p: active &= bits.get(int(p[-1][1:]), 0)
        qs = [int(t[1:]) for t in p[1:] if t.startswith('q')]
        if k == 'PUSH_CONDITION': stack.append(bits.get(int(p[-1][1:]),0))
        elif k == 'POP_CONDITION':
            if stack: stack.pop()
        elif k in ('BIT_STORE0','BIT_STORE1','BIT_INVERT'):
            b = int(p[1][1:]); old = bits.get(b,0)
            bits[b] = old & ~active if k=='BIT_STORE0' else old | active if k=='BIT_STORE1' else old ^ active
        elif k == 'X': q[qs[0]] ^= active
        elif k == 'CX': q[qs[1]] ^= q[qs[0]] & active
        elif k == 'CCX':
            a,b,t = qs; delta = q[a] & q[b] & active
            if discover_kind=='CCX' and active and (allowed is None or i in allowed):
                proposal = None
                if allowed is not None:
                    r = allowed[i]; v = active if r['constant'] else 0
                    for w in r['wires']: v ^= q[w] & active
                    if v == delta: proposal=(r['constant'],r['wires'])
                else:
                    vals = {q[w]&active:w for w in range(62) if w != t}
                    for const in (False,True):
                        want = delta ^ (active if const else 0)
                        if want == 0: proposal=(const,[]); break
                        if want in vals: proposal=(const,[vals[want]]); break
                        for v,w in vals.items():
                            if want^v in vals and vals[want^v] != w:
                                proposal=(const,[w,vals[want^v]]);break
                        if proposal is not None: break
                if proposal is not None:
                    hits.append({'op':i,'old':line,'constant':proposal[0],
                                 'wires':proposal[1],'active_samples':active.bit_count(),
                                 'flip_samples':delta.bit_count()})
            q[t] ^= delta
        elif k == 'SWAP':
            a,b=qs; d=(q[a]^q[b])&active;q[a]^=d;q[b]^=d
        elif k == 'CSWAP':
            c,a,b=qs;d=(q[a]^q[b])&q[c]&active
            if discover_kind=='CSWAP' and active and (allowed is None or i in allowed):
                proposal=None
                if allowed is not None:
                    r=allowed[i];v=active if r['constant'] else 0
                    for w in r['wires']:v ^= q[w]&active
                    if v==d:proposal=(r['constant'],r['wires'])
                else:
                    vals={q[w]&active:w for w in range(62) if w not in (a,b)}
                    for const in (False,True):
                        want=d^(active if const else 0)
                        if want==0:proposal=(const,[]);break
                        if want in vals:proposal=(const,[vals[want]]);break
                        for v,w in vals.items():
                            if want^v in vals and vals[want^v]!=w:
                                proposal=(const,[w,vals[want^v]]);break
                        if proposal is not None:break
                if proposal is not None:
                    hits.append({'op':i,'old':line,'constant':proposal[0],
                                 'wires':proposal[1],'active_samples':active.bit_count(),
                                 'flip_samples':d.bit_count()})
            q[a]^=d;q[b]^=d
        elif k in ('HMR','R'):
            outcome = rng.getrandbits(n)
            if k == 'HMR':
                b=int(p[2][1:]);bits[b]=(bits.get(b,0)&~active)|(outcome&active)
            q[qs[0]] &= ~active
        elif k not in ('Z','CZ','CCZ','NEG','Z_POW','INFO_TAG'):
            raise ValueError((i,line))
    assert not stack
    return hits


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=16384)
    ap.add_argument('--swaps',action='store_true')
    args=ap.parse_args();_,ops=load()
    kind='CSWAP' if args.swaps else 'CCX'
    first=trace_candidates(ops,inputs(20261103,args.n),101,discover_kind=kind)
    second=trace_candidates(ops,inputs(20261104,args.n),202,first,discover_kind=kind)
    OUT.mkdir(parents=True,exist_ok=True)
    doc={'baseline_sha256':SHA,'kind':'discovery-only; NOT a proof',
         'first_count':len(first),'second_count':len(second),'candidates':second}
    (OUT/('affine_swap_probe.json' if args.swaps else 'affine_probe.json')).write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps(doc,indent=2))


if __name__ == '__main__':main()
