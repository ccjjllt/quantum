"""Reproduce the k=4 Maoxin loader generator set (193 products + 75 cache) and
measure the *subspace structure* that governs how many products are really needed.

Model (truth tables over the address register):
  * 11 selection qubits -> 2048 addresses; only a = 0..1219 are real (don't-care above).
  * every qubit holds a GF(2) function of a; replay is exact.
  * a CCX into a word bit is a "product" (1 T), a CCX into an ancilla is a "cache" monomial (1 T).

Outputs (printed):
  dim V, dim G0 = span(cache, 1, addr bits), dim(V cap G0), dim(V + G0),
  how many of the 193 products already lie in V + G0 (i.e. are "free directions"),
  greedy minimal subset of the 193 that covers V mod G0.

Usage: python repro.py [angle_k_4.kmx]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
KMX = ROOT / '.worktree/dfthcsos/artifacts/20261112_loader_re/kmx_maoxin/angle_k_4.kmx'
N = 2048
ALL = (1 << N) - 1
NREAL = 1220
REAL = (1 << NREAL) - 1            # addresses 0..1219 are the real ones


def var_tt(i: int) -> int:
    period = 1 << i
    block = ((1 << period) - 1) << period
    out = 0
    for s in range(0, N, 2 * period):
        out |= block << s
    return out


VAR = [var_tt(i) for i in range(11)]


def replay(path: Path):
    lines = path.read_text().splitlines()
    names, regs = {}, {}
    for ln in lines:
        m = re.fullmatch(r'APPEND_TO_REGISTER q(\d+) r(\d+)', ln)
        if m:
            regs.setdefault(int(m.group(2)), []).append(int(m.group(1)))
        m = re.fullmatch(r'REGISTER r(\d+) "(\w+)"', ln)
        if m:
            names[int(m.group(1))] = m.group(2)
    qname, word_qubits = {}, []
    for rid, qs in regs.items():
        nm = names[rid]
        for i, q in enumerate(qs):
            qname[q] = f'sel{i}' if nm == 'selection' else f'w{nm[5:]}.{i}'
            if nm != 'selection':
                word_qubits.append(q)
    nq = 0
    for ln in lines:
        for p in ln.split():
            if p.startswith('q'):
                nq = max(nq, int(p[1:]) + 1)

    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
    products, cache = [], []
    n_cx = n_ccx = 0
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g, qs = parts[0], [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            n_cx += 1
            f[qs[1]] ^= f[qs[0]]
        elif g == 'CCX':
            n_ccx += 1
            a, b, t = qs
            tt = f[a] & f[b]
            if qname.get(t, '').startswith('w'):
                products.append((qname[t], tt, ln))
            else:
                cache.append((t, tt))
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown {g}')
    outs = [f[q] for q in word_qubits]
    return dict(nq=nq, n_cx=n_cx, n_ccx=n_ccx, products=products, cache=cache,
                outs=outs, f=f, qname=qname, lines=lines)


def add_basis(piv: dict[int, int], v: int) -> bool:
    while v:
        p = v.bit_length() - 1
        if p in piv:
            v ^= piv[p]
        else:
            piv[p] = v
            return True
    return False


def mk_basis(vals):
    piv: dict[int, int] = {}
    for v in vals:
        add_basis(piv, v)
    return piv


def dim(piv) -> int:
    return len(piv)


def reduce_mod(v: int, piv: dict[int, int]) -> int:
    while v:
        p = v.bit_length() - 1
        if p in piv:
            v ^= piv[p]
        else:
            break
    return v


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else KMX
    d = replay(path)
    prods, cache, outs = d['products'], d['cache'], d['outs']
    print(f"{path.name}: qubits={d['nq']} CX={d['n_cx']} CCX={d['n_ccx']} "
          f"products={len(prods)} cache={len(cache)} wordbits={len(outs)}")

    for mask, tag in ((ALL, '2048-addr (zero padded)'), (REAL, '1220 real addrs')):
        V = [v & mask for v in outs]
        G0 = [v & mask for v in [c[1] for c in cache] + [mask] + VAR]
        bV, bG, bVG = mk_basis(V), mk_basis(G0), mk_basis(V + G0)
        bI = mk_basis([x & y for x in V for y in []]) if False else None
        # V cap G0 : elements of V that reduce to 0 mod G0
        capr = [reduce_mod(v, bG) for v in V]
        cap_dim = sum(1 for v in V if True) and dim(mk_basis([v for v in V if reduce_mod(v, bG) == 0]))
        print(f'\n[{tag}]  dim V={dim(bV)}  dim G0={dim(bG)}  dim(V+G0)={dim(bVG)}'
              f'  dim(V cap G0)={dim(bV) + dim(bG) - dim(bVG)}'
              f'  (#V-basis elts with 0 image mod G0 = {cap_dim})')
        # quotiented V
        qV = mk_basis([reduce_mod(v, bG) for v in V])
        print(f'          dim pi(V) = {dim(qV)}')
        # how many products land in V+G0 ?
        inVG = sum(1 for (_, tt, _) in prods if reduce_mod(tt & mask, bVG) == 0)
        inVGp = sum(1 for (_, tt, _) in prods if reduce_mod(tt & mask, bG) == 0)
        print(f'          products with tt in V+G0: {inVG}/{len(prods)}'
              f'   (tt in G0 alone: {inVGp})')
        # greedy: cover pi(V) with products
        cur = mk_basis([])
        sel = []
        remaining = list(range(len(prods)))
        target = dim(qV)
        covered = 0
        while covered < target:
            best, best_gain, best_img = None, 0, None
            for j in remaining:
                img = reduce_mod(prods[j][1] & mask, bG)
                r = reduce_mod(img, cur)
                if not r:
                    continue
                # gain in dim of span(cur + r) cap pi(V)... use rank of (cur+pi(V) space)
                trial = dict(cur)
                before = dim(mk_basis([reduce_mod(x, cur) for x in list(qV.values())]))
                add_basis(trial, r)
                after = dim(mk_basis([reduce_mod(x, trial) for x in list(qV.values())]))
                gain = before - after
                if gain > best_gain:
                    best, best_gain, best_img = j, gain, r
            if best is None:
                break
            sel.append(best)
            add_basis(cur, best_img)
            remaining.remove(best)
            covered = dim(mk_basis([reduce_mod(x, cur) for x in list(qV.values())]))
            covered = target - covered
        print(f'          greedy products to span pi(V): {len(sel)} (of {len(prods)})')

    print('\n--- cache monomial structure (degree histogram) ---')
    from collections import Counter
    degs = Counter()
    for q, tt in cache:
        supp = [i for i in range(11) if (tt >> 0) & 1 and False]
        # find the unique monomial: weight = 2^(11-deg)
        w = bin(tt & REAL).count('1')
        degs[w] += 1
    print('cache weight histogram (over 1220 addrs):', dict(sorted(degs.items())))
    pw = Counter()
    for _, tt, _ in prods:
        pw[bin(tt & REAL).count('1')] += 1
    print('product weight histogram (over 1220 addrs):', dict(sorted(pw.items())))
    print('product distinct tt:', len({tt & REAL for (_, tt, _) in prods}), '/', len(prods))


if __name__ == '__main__':
    main()
