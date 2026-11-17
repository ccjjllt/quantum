"""Local search over the two FREE re-encodings of the same decoded U:

  (a) per-edge sign representative (angle + pi, exact grid point),
  (b) column order / grouping into the 15 blocks of five (linear extension that
      keeps every node's child order, so the angle *values* do not move),

both of which leave `decode(words)` at 1e-14 from the shipped V, hence leave
error_1 / error_2 / Lambda / lambda_eff untouched.  Objective: the cheap loader
floor `sum_k ceil_products_k` from proxy.py.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode, check_tree  # noqa: E402
from proxy import proxy  # noqa: E402
from signsweep import encode_signed  # noqa: E402

NPZ = str(WORK / 'build' / 'submission.npz')


def load():
    z = np.load(NPZ, allow_pickle=False)
    tree = np.asarray(z['tree_edges'], np.int64)
    words = np.asarray(z['angle_words'], np.int64)
    return tree, words, decode(words, tree, 8)


def child_order(edges):
    ch = {}
    for i, (p, c) in enumerate(edges):
        ch.setdefault(int(p), []).append(i)
    return ch


def sibling_preserving_extension(edges, n, rng):
    """Random linear extension keeping each node's child order (values unchanged)."""
    ch = child_order(edges)
    ready = list(ch.get(0, []))
    order = []
    while ready:
        i = ready.pop(int(rng.integers(0, len(ready))))
        order.append(i)
        ready.extend(ch.get(int(edges[i][1]), []))
    assert len(order) == n - 1
    return np.array(order, np.int64)


def score(words):
    p = proxy(words.astype(np.uint8))
    return p['sum_ceiling_products'], p['sum_c_max'], [r['ceiling_products'] for r in p['rows']]


if __name__ == '__main__':
    tree, ship_words, V = load()
    n = V.shape[1]
    rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    t0 = time.time()

    # control
    c0 = score(ship_words)
    print('control  ceil', c0[0], 'sum_c_max', c0[1], c0[2], flush=True)

    # does a sibling-preserving re-order keep the values exactly?
    order = sibling_preserving_extension(tree, n, rng)
    e2 = tree[order]
    w2 = encode_signed(V, e2, np.ones(n - 1))
    print('sibling-preserving reorder: ||decode-V||', float(np.linalg.norm(decode(w2, e2, 8) - V)),
          flush=True)

    # random signs, shipped grouping
    best = None
    for it in range(60):
        sg = rng.integers(0, 2, n - 1) * 2 - 1
        w = encode_signed(V, tree, sg)
        s = score(w)
        if best is None or s[0] < best[1][0]:
            best = (sg, s)
    print('best random sign pattern (shipped grouping) ceil', best[1][0], best[1][2], flush=True)

    # random regroupings, shipped signs
    bestg = None
    for it in range(60):
        order = sibling_preserving_extension(tree, n, rng)
        e2 = tree[order]
        w = encode_signed(V, e2, np.ones(n - 1))
        s = score(w)
        if bestg is None or s[0] < bestg[1][0]:
            bestg = (order, s)
    print('best regrouping (shipped signs) ceil', bestg[1][0], bestg[1][2], flush=True)

    # hill climb over signs (coordinate blocks) on the best grouping
    order = bestg[0]
    e2 = tree[order]
    sg = np.ones(n - 1, np.int64)
    cur = score(encode_signed(V, e2, sg))
    print('climb start ceil', cur[0], cur[2], flush=True)
    for sweep in range(8):
        improved = False
        for t in range(n - 1):
            trial = sg.copy()
            trial[t] *= -1
            s = score(encode_signed(V, e2, trial))
            if s[0] < cur[0]:
                sg, cur = trial, s
                improved = True
        print(f'  sweep {sweep}: ceil {cur[0]} {cur[2]} ({time.time() - t0:.0f}s)', flush=True)
        if not improved:
            break
    w = encode_signed(V, e2, sg)
    print('hill-climb final: ceil', cur[0], 'sum_c_max', cur[1], cur[2],
          '||decode-V||', float(np.linalg.norm(decode(w, e2, 8) - V)), flush=True)
    json.dump({'edges': e2.tolist(), 'signs': sg.tolist(), 'words': w.tolist(),
               'ceil_total': int(cur[0]), 'ceil_per_k': cur[2]},
              open(WORK / 'climb_signs.json', 'w'))
