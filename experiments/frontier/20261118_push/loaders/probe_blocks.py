"""Measure the block-rank / cut-space landscape for a loader target.

Pure GF(2) arithmetic; no circuit simulation.
"""
import json, sys, random
from pathlib import Path
import numpy as np
from common import (CODE2, load_words, gf2_basis, gf2_rank, proj_coord, NOUT, NDIM, M35)

from planner import complete_words, cross_tensor, BlockPlan
from lowbasis import inverse15, transform_target
from parity_recover import basis, nullspace, reduce

PARTS5 = [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]


def block_report(tt, parts=PARTS5, lo=1, hi=76):
    """Per-block rank of the (hi-lo) x (3*35) local matrix and its nullity."""
    out = []
    for part in parts:
        loc = []
        for x in tt[lo:hi]:
            v = 0
            for j, i in enumerate(part):
                v |= proj_coord(x, i) << (NOUT * j)
            loc.append(v)
        r = gf2_rank(loc)
        out.append({'part': list(part), 'rows': len(loc), 'rank': r, 'dim': len(part) * NOUT,
                    'nullity': len(part) * NOUT - r})
    return out


def main():
    W = load_words()
    Wc = complete_words(W)
    ks = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [9]
    for k in ks:
        t = cross_tensor(Wc, k)
        # identity basis
        rid = [1 << i for i in range(15)]
        tt_id = transform_target(t, inverse15(rid))
        rep = block_report(tt_id)
        print(f'k{k} identity-B block ranks', [b['rank'] for b in rep], 'sum', sum(b['rank'] for b in rep), flush=True)
        # plan basis if available
        f = CODE2 / f'basis_plan_k{k}.json'
        if f.exists():
            js = json.loads(f.read_text())
            if 'rows' not in js:
                print(f'k{k} plan file present but empty (stub) -> skipped', flush=True)
                rows = None
            else:
                rows = [int(x) for x in js['rows']]
        if f.exists() and rows is not None:
            tt = transform_target(t, inverse15(rows))
            rep = block_report(tt)
            print(f'k{k} plan-B     block ranks', [b['rank'] for b in rep], 'sum', sum(b['rank'] for b in rep), flush=True)
        # random invertible B
        rng = random.Random(1)
        for trial in range(3):
            B = random_invertible(rng)
            tt = transform_target(t, inverse15(B))
            rep = block_report(tt)
            print(f'k{k} random{trial}  block ranks', [b['rank'] for b in rep], 'sum', sum(b['rank'] for b in rep), flush=True)


def random_invertible(rng):
    while True:
        rows = [rng.getrandbits(15) for _ in range(15)]
        if gf2_rank(rows) == 15:
            return rows


if __name__ == '__main__':
    main()
