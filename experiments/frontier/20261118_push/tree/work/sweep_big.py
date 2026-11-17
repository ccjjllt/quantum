"""Broad tree sweep: the loader-floor total for ~300 trees.

The floor is `sum_k (525 - sum_c_max_k)/2` from proxy.py: the loader product count
that a perfect pairing of every available annihilator would reach.  The shipped
table's measured achieved counts are 212,212,194,194,188 x5,189,190 x4,191
(Toffoli 292,287,269,269,263 x5,264,265 x4,266 = 4022, kickmix operation
statistics of the shipped .kmb), against floors 187,187,160,160,152 x11.
"""
import json
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode, check_tree  # noqa: E402
from proxy import proxy  # noqa: E402
from signrules import encode_rule  # noqa: E402
from sweep import (chain_tree, heap_tree, random_tree, star_tree,  # noqa: E402
                   _heap_perm, _chain_perm)

z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
SHIP_TREE = np.asarray(z['tree_edges'], np.int64)
SHIP = np.asarray(z['angle_words'], np.int64)
V = decode(SHIP, SHIP_TREE, 8)
N = V.shape[1]


def evaluate(name, edges):
    try:
        check_tree(edges, N)
    except AssertionError as ex:
        return {'name': name, 'error': str(ex)}
    w = encode_rule(V, edges, 8, 'pos')
    p = proxy(w.astype(np.uint8))
    resid = float(np.linalg.norm(decode(w, edges, 8) - V))
    return {'name': name, 'floor_total': p['sum_ceiling_products'],
            'floor_per_k': [r['ceiling_products'] for r in p['rows']],
            'sum_c_max': p['sum_c_max'], 'resid': resid}


if __name__ == '__main__':
    rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
    out = [evaluate('ship_control', SHIP_TREE)]
    print(json.dumps({k: v for k, v in out[0].items() if k != 'floor_per_k'}), flush=True)
    out.append(evaluate('chain_id', chain_tree()))
    out.append(evaluate('star_id', star_tree()))
    for kind in ('attach', 'prufer', 'deep', 'bushy'):
        for i in range(50):
            out.append(evaluate(f'{kind}{i}', random_tree(N, rng, kind)))
    for i in range(40):
        out.append(evaluate(f'heap_perm{i}', _heap_perm(N, rng)))
    for i in range(20):
        out.append(evaluate(f'chain_perm{i}', _chain_perm(N, rng)))
    ok = [r for r in out if 'floor_total' in r]
    ok.sort(key=lambda r: r['floor_total'])
    print('n', len(ok), 'best', [(r['name'], r['floor_total']) for r in ok[:8]])
    print('worst', [(r['name'], r['floor_total']) for r in ok[-5:]])
    vals = np.array([r['floor_total'] for r in ok])
    print('median', float(np.median(vals)), 'mean', float(vals.mean()), 'std', float(vals.std()))
    json.dump(out, open(WORK / 'sweep_big.json', 'w'), indent=1)
