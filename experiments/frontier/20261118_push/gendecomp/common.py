"""Shared pure-arithmetic helpers for the general GF(2) product-decomposition line.

Imports the shipped chem compiler (read-only) from
experiments/frontier/20261117_deep/chem/work/ds/code2 and adds GF(2) linear
algebra over Python ints.

Nothing here simulates a circuit.  Only GF(2) rank arithmetic on the 1220x75
angle table and on the 77x15x35 ANF cell tensor.
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
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


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


def reduce_to(x, d):
    for p in sorted(d, reverse=True):
        if x & (1 << p):
            x ^= d[p]
    return x


def cells(target):
    """target[h] (h=0..76) -> dict[(h,l)] = 35-bit ANF coefficient, l in 1..15.

    target[h] packs the 15 low-monomial coordinates as 35-bit chunks, chunk k
    (0-based) = low monomial k+1.  Axial cells (h=0, or the implicit l=0) are
    NOT represented here: the emitter fixes those for free with CX fanouts.
    """
    out = {}
    for h in range(len(target)):
        x = int(target[h])
        if not x:
            continue
        for k in range(15):
            v = (x >> (NOUT * k)) & M35
            if v:
                out[(h, k + 1)] = v
    return out


def build(k, words=None):
    """Complete the table, build the loader-k ANF tensor (77 slices) and its cells."""
    from planner import complete_words, cross_tensor
    W = load_words() if words is None else np.asarray(words, np.uint8)
    Wc = complete_words(W)
    target = cross_tensor(Wc, k)
    return W, Wc, target, cells(target)
