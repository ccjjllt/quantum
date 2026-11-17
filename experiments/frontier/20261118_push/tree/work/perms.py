"""FREE column permutation of the shipped table: exact same U, different 5-word batches.

A permutation of `tree_edges` is legal, and `reconstruct_u_vectors` re-reads the
rotations in that order.  If the permutation keeps every node's child order and
only interleaves independent subtrees, the rotations see the same amplitudes, so
`decode(words[:, perm], tree[perm])` reproduces the shipped U bit-for-bit and the
accuracy metrics cannot move.  What DOES move is which 5 columns land in each
loader batch, and the loader product count is a function of that batch.
"""
import json
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode, check_tree  # noqa: E402
from proxy import proxy  # noqa: E402

z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
TREE = np.asarray(z['tree_edges'], np.int64)
SHIP = np.asarray(z['angle_words'], np.int64)
V = decode(SHIP, TREE, 8)
N = V.shape[1]


def child_lists(edges):
    ch = {}
    for i, (p, c) in enumerate(edges):
        ch.setdefault(int(p), []).append(i)
    return ch


def value_preserving_extension(edges, rng):
    """Random interleaving of independent subtrees; every node's child order kept."""
    ch = child_lists(edges)
    ptr = {v: 0 for v in ch}
    ready = [0] if ch.get(0) else []
    order = []
    while ready:
        j = int(rng.integers(0, len(ready)))
        v = ready[j]
        i = ch[v][ptr[v]]
        ptr[v] += 1
        if ptr[v] == len(ch[v]):
            ready.pop(j)
        order.append(i)
        c = int(edges[i][1])
        if ch.get(c):
            ready.append(c)
    assert len(order) == len(edges), (len(order), len(edges))
    return np.array(order, np.int64)


def score(edges, words):
    p = proxy(np.asarray(words, np.uint8))
    return p['sum_ceiling_products'], [r['ceiling_products'] for r in p['rows']]


if __name__ == '__main__':
    rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 21)
    nsamp = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    o = value_preserving_extension(TREE, rng)
    e1, w1 = TREE[o], SHIP[:, o]
    check_tree(e1, N)
    r = float(np.linalg.norm(decode(w1, e1, 8) - V))
    print('value-preserving perm: ||decode - shipped U|| =', r, flush=True)
    print('shipped grouping floor', score(TREE, SHIP), flush=True)
    print('permuted grouping floor', score(e1, w1), flush=True)

    best = None
    recs = []
    for it in range(nsamp):
        o = value_preserving_extension(TREE, rng)
        e1, w1 = TREE[o], SHIP[:, o]
        s, pk = score(e1, w1)
        recs.append({'floor': s, 'per_k': pk})
        if best is None or s < best[0]:
            best = (s, pk, o)
    recs.sort(key=lambda d: d['floor'])
    f = np.array([d['floor'] for d in recs])
    print('n', len(recs), 'best', recs[0], 'median', float(np.median(f)), 'worst', recs[-1]['floor'])
    print('shipped floor 2366 -> best permutation delta', recs[0]['floor'] - 2366)
    json.dump({'shipped': 2366, 'n': len(recs), 'floors': recs},
              open(WORK / 'perm_search.json', 'w'), indent=1)
