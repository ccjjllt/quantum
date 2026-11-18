"""Shared read-only helpers for the loader-cut experiment.

Imports the shipped chem compiler (read-only) from
experiments/frontier/20261117_deep/chem/work/ds/code2 and adds fast GF(2)
linear algebra over Python ints.

Nothing here simulates a circuit; only GF(2) rank arithmetic on the table.
"""
import sys
from pathlib import Path
import numpy as np

REPO = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
CODE2 = REPO / 'experiments/frontier/20261117_deep/chem/work/ds/code2'
for p in (str(CODE2 / 'compiler'), str(CODE2)):
    if p not in sys.path:
        sys.path.insert(0, p)

NOUT = 35
NDIM = 15 * NOUT
M35 = (1 << NOUT) - 1

TABLE = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/submission.npz')


def load_words(path=TABLE):
    z = np.load(path, allow_pickle=False)
    return np.asarray(z['angle_words'], np.uint8)


def gf2_basis(xs):
    d = {}
    for x in xs:
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p]
            else:
                d[p] = x
                break
    return d


def gf2_rank(xs):
    return len(gf2_basis(xs))


def proj_coord(x, m):
    return (x >> (NOUT * m)) & M35


def target_slices(target, lo=1, hi=76):
    return [int(x) for x in target[lo:hi]]


def stats(target, lo=1, hi=76, label=''):
    """Rank of the slice matrix and the per-coordinate projection ranks."""
    S = target_slices(target, lo, hi)
    r = gf2_rank(S)
    dims = [gf2_rank([proj_coord(x, m) for x in S]) for m in range(15)]
    out = {'label': label, 'n_slices': len(S), 'rank_full': r, 'coord_dims': dims,
           'sum_coord_dims': int(sum(dims))}
    return out
