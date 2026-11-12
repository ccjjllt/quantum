"""Is the rank-15 obstruction real, and what does it imply for 2,850 / 2,045 / 1,300?

(a) Extension freedom: the table is only defined on 1,220 of the 2,048 addresses.
    Refit the ANF with random values on the 828 unused addresses and see whether the
    interior rank moves.  (If it stays 15 for every extension, zero padding is not the cause.)
(b) Dimension count: the affine family of admissible ANF cubes has dimension 828; the
    variety of 16x128 matrices of rank <= k has dimension k(16+128-k).  Intersection is
    generically empty when 828 + k(144-k) < 2048  ->  k >= 9 needed before rank<=k is
    even dimensionally possible.  So the don't-care freedom cannot buy rank<=2.
(c) Information bound: the 40 delta bits over 1,220 addresses are 48,800 bits, essentially
    random.  One Toffoli-like gate is one CCX = one product A*B of two workspace
    polynomials, i.e. a pair of subsets of a span of dimension D <= 128 -> <= 2D bits.
    With the span growing from 12 (1 + 11 address bits) by one per CCX, the number of
    distinguishable behaviours with n CCX is <= 2**sum_t 2*min(12+t,128).
(d) Per-circuit T for the full-support model, all 15 circuits, and the cost projection.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / '.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_re'))
sys.path.insert(0, str(Path(__file__).parent))
import tensorqrom8 as tq  # noqa: E402
import fullsupport_solve as F  # noqa: E402

W = np.load(ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz')['angle_words']
J, N = 5, 1220
LAMBDA = 46.9027
HEUR_T = 6662
Q_TOT = 427


def cost(t_pass: float) -> float:
    return LAMBDA * (2 * t_pass + HEUR_T) * Q_TOT


def anf_cube_ext(k: int, rng: np.random.Generator | None) -> np.ndarray:
    d = F.delta_of(k)
    bits = np.zeros((2048, 40), np.uint8)
    for j in range(5):
        for kk in range(8):
            bits[:N, j * 8 + kk] = (d[:, j] >> kk) & 1
    if rng is not None:
        bits[N:] = rng.integers(0, 2, size=(2048 - N, 40), dtype=np.uint8)
    return tq.mobius(bits, axis=0)


def interior_ranks(cube: np.ndarray) -> list[int]:
    return [F.gf2_rank(F.to_matrix(cube[:, o])[1:, 1:]) for o in range(40)]


def main() -> None:
    print('=== (a) extension freedom: interior rank with random don\'t-care fill ===')
    rng = np.random.default_rng(0)
    for k in (4, 0):
        base = interior_ranks(anf_cube_ext(k, None))
        trials = [interior_ranks(anf_cube_ext(k, rng)) for _ in range(5)]
        same = all(t == base for t in trials)
        print(f'  k={k}: zero-filled distinct ranks {sorted(set(base))}'
              f' (hist {[base.count(v) for v in sorted(set(base))]})')
        print(f'       random fills distinct ranks {sorted({v for t in trials for v in t})}'
              f' ; identical to zero-fill: {same}')

    print()
    print('=== (b) dimension count ===')
    for kk in (1, 2, 3, 4, 6, 8, 9, 10, 15):
        d = kk * (16 + 128 - kk)
        print(f'  rank<={kk:2d}: variety dim {d:4d}  +828 free coords - 2048 = {828 + d - 2048:+d}'
              f'  {"possible" if 828 + d - 2048 >= 0 else "generically empty"}')

    print()
    print('=== (c) information bound on CCX/circuit ===')
    need = 40 * N
    n = 0
    acc = 0
    while acc < need:
        n += 1
        acc += 2 * min(12 + n, 128)
    print(f'  target bits = 40 x {N} = {need}')
    steady = -(-need // 256)
    print(f'  floor with a full 128-dim workspace from the start: {steady} CCX/circuit')
    print(f'  floor with span growing 12 -> 128 (one per CCX):    {n} CCX/circuit')
    for lab, v in (('steady', steady), ('cold-start', n)):
        print(f'    {lab}: {v*15} T/pass -> T_total {2*v*15+HEUR_T} -> cost {cost(v*15)/1e6:.1f}M')

    print()
    print('=== (d) full-support model, all 15 circuits ===')
    tot_prod = tot_prods = 0
    rows = []
    for k in range(15):
        cube = anf_cube_ext(k, None)
        prods = 0
        lb = 0
        for o in range(40):
            M = F.to_matrix(cube[:, o])
            r = F.gf2_rank(M[1:, 1:])
            lb += (r + 1) // 2
            p, ok = F.decompose(M)
            assert ok, (k, o)
            prods += len(p)
        cache = 80 if k == 0 else 70
        rows.append((k, lb, prods, cache + 11 + prods))
        tot_prod += prods
        tot_prods += cache + 11 + prods
    for k, lb, pr, tt in rows:
        print(f'  k={k:2d}: lb {lb:3d} products, built {pr:3d}, T/circuit (incl. r-cache) {tt:3d}')
    print(f'  TOTAL T/pass = {tot_prods}  (Maoxin 4,089)')
    print(f'  T_total {2*tot_prods+HEUR_T}  cost {cost(tot_prods)/1e6:.1f}M')

    print()
    print('=== (e) the 2,850 / 2,045 / 1,300 targets ===')
    for t in (4089, 3645, 3450, 2865, 2850, 2045, 1300, 1815):
        print(f'  loader T/pass {t:5d}: T_total {2*t+HEUR_T:6d}  cost {cost(t)/1e6:7.1f}M')

    print()
    print('=== (f) bit weights of the delta table (why 8 LSBs of k=4 have low rank) ===')
    for k in (4, 0):
        d = F.delta_of(k)
        bits = np.zeros((N, 40), np.uint8)
        for j in range(5):
            for kk in range(8):
                bits[:, j * 8 + kk] = (d[:, j] >> kk) & 1
        wt = bits.sum(0).tolist()
        print(f'  k={k}: weight/1220 {wt}')
        print(f'         LSBs (bit0 of each word): {[wt[8*j] for j in range(5)]}'
              f'   bit7: {[wt[8*j+7] for j in range(5)]}')

    print()
    print('=== (g) can full-support beat 4,089 at all?  (don\'t-care freedom, best case) ===')
    # rank >= 10 for every bit (dimension count) -> 5 products/bit, cache 70 q + 11 r
    for rank, cache, lab in ((10, 81, 'rank>=10 (dimension bound)'), (15, 81, 'observed rank 15')):
        prod = 40 * ((rank + 1) // 2)
        t = cache + prod
        print(f'  {lab:28s}: {prod:3d} products + {cache} cache = {t:3d} T/circuit'
              f' = {15*t:5d} T/pass -> cost {cost(15*t)/1e6:.1f}M')
    print(f'  current Maoxin                : 272.6 T/circuit = 4,089 T/pass -> cost {cost(4089)/1e6:.1f}M')
    print('  break-even needs rank <= 9 per bit, dimension count forbids it')


if __name__ == '__main__':
    main()
