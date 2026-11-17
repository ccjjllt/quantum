"""Sign-representative and column-grouping search: words change, decoded U does not.

`reconstruct_u_vectors` is not injective: at every edge the pre-rotation amplitude
may be taken positive or negative, which shifts that edge's angle by pi and negates
the parent's accumulated amplitude.  Both representatives are exact grid points of
the 8-bit table, so `decode(words)` is identical to 1e-15 -> error_1/error_2/
Lambda/lambda_eff are unchanged while the loader targets (which see the words)
change.
"""
import json
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode, check_tree  # noqa: E402
from proxy import proxy  # noqa: E402

NPZ = str(WORK / 'build' / 'submission.npz')


def encode_signed(vectors, edges, signs, brot=8):
    u = np.array(vectors, np.float64, copy=True)
    edges = np.asarray(edges, np.int64)
    signs = np.asarray(signs, np.int64)
    n = len(edges)
    scale = 1 << (brot - 1)
    words = np.zeros((u.shape[0], n), np.int64)
    for t in range(n - 1, -1, -1):
        p, c = int(edges[t][0]), int(edges[t][1])
        s = 1 if signs[t] >= 0 else -1
        th = np.arctan2(s * u[:, c], s * u[:, p])
        th = np.where(th < 0.0, th + 2.0 * np.pi, th)
        th = np.where(np.hypot(u[:, p], u[:, c]) < 1e-12, 0.0, th)
        words[:, t] = np.round(th / np.pi * scale).astype(np.int64) % (2 * scale)
        u[:, p] = s * np.hypot(u[:, p], u[:, c])
        u[:, c] = 0.0
    return words


def linear_extensions(edges, n, rng, sibling_free=True):
    """Random linear extension; with sibling_free=False every node's children keep
    their order in `edges` (so the angle *values* are unchanged)."""
    children = {}
    for i, (p, c) in enumerate(edges):
        children.setdefault(int(p), []).append(i)
    if sibling_free:
        for v in children:
            rng.shuffle(children[v])
    ready = list(children.get(0, []))
    order = []
    while ready:
        i = ready.pop(int(rng.integers(0, len(ready))))
        order.append(i)
        c = int(edges[i][1])
        ready.extend(children.get(c, []))
    assert len(order) == n - 1
    return np.array(order, np.int64)


if __name__ == '__main__':
    z = np.load(NPZ, allow_pickle=False)
    TREE = np.asarray(z['tree_edges'], np.int64)
    WORDS = np.asarray(z['angle_words'], np.int64)
    V = decode(WORDS, TREE, 8)
    n = V.shape[1]
    rng = np.random.default_rng(7)

    # (a) does the sign trick really preserve the decoded vectors?
    signs = rng.integers(0, 2, n - 1) * 2 - 1
    w = encode_signed(V, TREE, signs)
    rec = decode(w, TREE, 8)
    print('signed variant: ||decode - V||_F', float(np.linalg.norm(rec - V)),
          ' words changed', int(np.sum(w != WORDS)))
    p = proxy(w.astype(np.uint8))
    print('signed proxy sum_c_max', p['sum_c_max'], 'ceil_total', p['sum_ceiling_products'],
          'per-k', [r['ceiling_products'] for r in p['rows']])
    p0 = proxy(WORDS.astype(np.uint8))
    print('shipped  sum_c_max', p0['sum_c_max'], 'ceil_total', p0['sum_ceiling_products'],
          'per-k', [r['ceiling_products'] for r in p0['rows']])
