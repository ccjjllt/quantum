"""Compare loader-floor totals across free sign conventions (decoded U unchanged)."""
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode  # noqa: E402
from proxy import proxy  # noqa: E402
from signrules import encode_rule  # noqa: E402

z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
TREE = np.asarray(z['tree_edges'], np.int64)
SHIP = np.asarray(z['angle_words'], np.int64)
V = decode(SHIP, TREE, 8)
n = V.shape[1]


def floor_of(w):
    p = proxy(np.asarray(w, np.uint8))
    return p['sum_ceiling_products'], [r['ceiling_products'] for r in p['rows']]


def dec(w):
    return float(np.linalg.norm(decode(np.asarray(w, np.int64), TREE, 8) - V))


res = {}
for rule in ('pos', 'cos_pos'):
    w = encode_rule(V, TREE, 8, rule)
    # repair the global row sign: harmless (u u^T and |overlap| are invariant)
    d = decode(w, TREE, 8)
    dot = np.sum(d * V, axis=1)
    fl = np.sign(dot)
    print(rule, 'rows needing a global flip', int(np.sum(fl < 0)),
          'resid after repair', float(np.linalg.norm(d * fl[:, None] - V)))
    res[rule] = w
res['ship'] = SHIP.copy()

# single-column XOR by 128 on top of the best convention
base = 'pos'
best_w = res[base].copy()
best = floor_of(best_w)[0]
print('start', base, best)
for t in range(n - 1):
    w = res[base].copy()
    w[:, t] = (w[:, t] + 128) % 256
    f = floor_of(w)[0]
    if f < best:
        best, best_w = f, w
        print(f'  column {t} xor128 -> floor {f}', flush=True)
print('single-column best floor', best, floor_of(best_w)[1])

for name, w in list(res.items()):
    f, pk = floor_of(w)
    print(f'{name:9s} floor {f} per-k {pk} resid {dec(w):.2e}')
