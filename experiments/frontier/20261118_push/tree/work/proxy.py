"""Cheap loader proxy for a candidate angle-words table.

For loader k the compiler's target is `cross_tensor(complete_words(W), k)`, i.e.
the Mobius/ANF transform of the 5-word block (block k XOR block k-1) over the
(high 7 bits, low 4 bits) address split.  The plan searches annihilators ("cuts")
of the 75 determined high slices inside five 3-coordinate blocks
(PARTS5).  The cut count is bounded by

    per block:  |forced per-coordinate relations| + dim(nullspace of the 75 slices)
    products >= (525 - sum of those) / 2

so `ceiling_products = (525 - sum_c_max) / 2` is a hard floor for the loader's
product count, and `products = sum_c_max - achieved` measures the search gap.
This proxy needs no pairing search and no emitter: pure GF(2) on python ints.
"""
import sys
import numpy as np

HERE = '/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work/code2'
for p in (HERE, HERE + '/compiler'):
    if p not in sys.path:
        sys.path.insert(0, p)

from planner import complete_words, cross_tensor  # noqa: E402
from parity_recover import NOUT, nullspace, basis, reduce  # noqa: E402
from transport_cuts import local  # noqa: E402

PARTS5 = [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]
M35 = (1 << NOUT) - 1


def loader_dims(words, k):
    """(forced cuts, full-nullspace dims) per block for loader k, plus slice rank."""
    Wc = complete_words(np.asarray(words, np.uint8))
    t = cross_tensor(Wc, k)
    slices = t[1:len(t) - 1]              # h = 1 .. nh-2  (the 'determined' slices)
    out = []
    for part in PARTS5:
        loc = [local(x, part) for x in slices]
        full = len(nullspace(loc, len(part) * NOUT))
        forced = 0
        for m in part:
            col = [(x >> (NOUT * m)) & M35 for x in slices]
            forced += NOUT - len(basis(col))
        out.append((forced, full))
    return out, len(slices)


def proxy(words, verbose=False):
    """Per-loader (sum_c_max, ceiling products) and their totals."""
    rows = []
    for k in range(15):
        dims, ns = loader_dims(words, k)
        scm = sum(f + s for f, s in dims)
        ceil = (15 * NOUT - scm) // 2
        rows.append({'k': k, 'forced': [f for f, s in dims], 'full': [s for f, s in dims],
                     'sum_c_max': scm, 'ceiling_products': ceil})
        if verbose:
            print(k, rows[-1], flush=True)
    return {'nslices': ns, 'rows': rows,
            'sum_c_max': sum(r['sum_c_max'] for r in rows),
            'sum_ceiling_products': sum(r['ceiling_products'] for r in rows),
            'max_ceiling_products': max(r['ceiling_products'] for r in rows)}


if __name__ == '__main__':
    z = np.load('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work/build/submission.npz',
                allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    r = proxy(W, verbose=True)
    print('TOTAL sum_c_max', r['sum_c_max'], 'ceiling products total', r['sum_ceiling_products'],
          'max', r['max_ceiling_products'])
