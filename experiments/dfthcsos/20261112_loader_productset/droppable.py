"""Per-circuit: how many of the product CCX are *already in span(G0)*, i.e. reproducible
with free CX fan-out from cached monomials / address bits / the constant 1.

G0 = span(cache monomials, 1, 11 address bits).  If p in G0 then instead of
`CCX pivotA pivotB target` (1 T) one can XOR p into every consumer with CX gates (0 T),
provided the target word bit is not used as a *control* by any later gate
(otherwise the whole downstream function changes).

Prints, for all 15 circuits: #products, #products in G0, #of those with a free target,
the resulting CCX count, and the greedy minimum product count over the remaining pool.

Usage: python droppable.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import KMXDIR, REAL, Basis, g0_basis, replay  # noqa: E402


def analyse(path: Path, verbose=False):
    d = replay(path)
    cache, prods = d['cache'], d['prods']
    mask = REAL
    G0 = g0_basis(cache, mask)
    inG0 = [j for j, (_, tt, _) in enumerate(prods) if G0.contains(tt & mask)]
    # which qubits are used as a control by any gate, and after which index?
    # we need: is the target word bit of product j read as a control by a later gate?
    gate_index = {id(gd): i for i, gd in enumerate(d['gates'])}
    ctrl_use: dict[int, list[int]] = {}
    for i, gd in enumerate(d['gates']):
        if gd['op'] not in ('CX', 'CCX'):      # CZ/Z/NEG are diagonal: no basis read
            continue
        for c in gd['c']:
            ctrl_use.setdefault(c, []).append(i)
    tainted = []
    for j, (t, tt, gd) in enumerate(prods):
        i = gate_index[id(gd)]
        later = [x for x in ctrl_use.get(t, []) if x > i]
        if later:
            tainted.append(j)
    nz = [j for j in range(len(prods)) if not G0.contains(prods[j][1] & mask)]
    safe = [j for j in inG0 if j not in set(tainted)]
    return dict(d=d, G0=G0, inG0=inG0, tainted=tainted, nz=nz, safe=safe)


def greedy_cover(A: list[int], r: list[int], Alen: int) -> int:
    S = Basis()
    chosen = 0
    covered = 0
    rem = [j for j in range(len(r)) if r[j]]
    while covered < Alen:
        best, bg, bt = None, covered, None
        for j in rem:
            t = Basis(S.values())
            t.add(r[j])
            g = len(t) + Alen - len(Basis(t.values() + A))
            if g > bg:
                best, bg, bt = j, g, t
        if best is None:
            break
        chosen += 1
        rem.remove(best)
        S, covered = bt, bg
    return chosen


def main() -> None:
    tot_prod = tot_inG0 = tot_tainted = tot_safe = 0
    rows = []
    for k in range(15):
        path = KMXDIR / f'angle_k_{k}.kmx'
        a = analyse(path)
        d, G0 = a['d'], a['G0']
        nP = len(d['prods'])
        n_in = len(a['inG0'])
        n_t = len(a['tainted'])
        n_s = len(a['safe'])
        tot_prod += nP
        tot_inG0 += n_in
        tot_tainted += n_t
        tot_safe += n_s
        rows.append((k, nP, n_in, n_t, n_s, d['n_ccx'], d['n_ccx'] - n_s))
        print(f'k={k:2d}  T={d["n_ccx"]:4d}  products={nP:4d}  in G0={n_in:3d}'
              f'  wordbit-tainted={n_t:3d}  safely droppable={n_s:3d}'
              f'  -> T-{n_s} = {d["n_ccx"] - n_s}')
    print(f'\nTOTAL products={tot_prod}  in G0={tot_inG0}  tainted={tot_tainted}'
          f'  safe={tot_safe}  T 4089 -> {4089 - tot_safe}')
    print(f'\n(CCX after dropping = {sum(r[6] for r in rows)})')


if __name__ == '__main__':
    main()
