"""Exhaustive symmetric-rank calibration on GF(2^2), GF(2^3), GF(2^4).

The question this answers: is the extension/Toom construction (the one DQI ships)
already rank-optimal at small n?  If yes for n=2,3,4, then "42 is the best in the
family" is much more meaningful for n=12 than a bare construction census.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[2] / 'artifacts' / '20261112_mulrank'
SRC = ART / 'source_copy'
sys.path[:0] = [str(HERE), str(SRC / 'playbook/kit/decoder'), str(SRC / 'playbook/kit/decoder/exp/arithmetic')]

import mulmath as mm
import rank_search as rs
import field as ar


def tower_terms(n):
    if n in (2, 3):
        return ar.tensor(n)
    if n == 4:
        t, why = mm.extension_tensor_generic(4, 2, 2, ar.tensor(2))
        return t
    raise SystemExit(n)


def main():
    print('== shipped/tower construction ==')
    for n in (2, 3, 4):
        t = tower_terms(n)
        ok, bad = mm.check_basis_pairs(mm.F(n).f, t, n)
        masks = [m for m, _ in t]
        ok2, outs = rs.solve(masks, mm.F(n).f, n)
        print(f'GF(2^{n}): {len(t)} terms, basis-pair proof {ok}, solver reproduces outs {ok2}')

    print('\n== exhaustive: no symmetric decomposition with fewer terms ==')
    t0 = time.time()
    for n, rmax in ((2, 4), (3, 6), (4, 8)):
        for r in range(2, rmax + 1):
            t = time.time()
            tested, sols = rs.exhaustive(n, r, limit=3)
            print(f'GF(2^{n}) r={r}: {tested} mask multisets, {len(sols)} solutions '
                  f'({time.time()-t:.1f}s)' + (f'  e.g. {sols[0]}' if sols else ''), flush=True)
    print(f'total {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
