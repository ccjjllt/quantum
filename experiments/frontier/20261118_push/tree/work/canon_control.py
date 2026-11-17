"""Control experiment: which loader count does the local planner find for the
canonical ('pos') re-encoding of the same decoded U at a fixed budget, against
the shipped table's measured 263 Toffoli (188 products) at k=4?

floor(pos, k=4) = 183  vs  floor(shipped, k=4) = 152.
If the achieved count tracks the floor, the floor proxy is usable for ranking.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode  # noqa: E402
from proxy import proxy  # noqa: E402
from signrules import encode_rule  # noqa: E402
from plan1 import plan_k  # noqa: E402

z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
TREE = np.asarray(z['tree_edges'], np.int64)
SHIP = np.asarray(z['angle_words'], np.int64)
V = decode(SHIP, TREE, 8)
canon = encode_rule(V, TREE, 8, 'pos')
print('canon floor total', proxy(canon.astype(np.uint8))['sum_ceiling_products'], flush=True)

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 420.0
ks = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '4').split(',')]
out = {}
for k in ks:
    t0 = time.time()
    b = plan_k(canon, k, seconds=secs)
    out[k] = None if b is None else {kk: b[kk] for kk in ('sum_cuts', 'd', 'products', 'seconds')}
    print(f'CANON k{k} {out[k]} wall {time.time() - t0:.0f}s', flush=True)
json.dump(out, open(WORK / 'canon_plan.json', 'w'), indent=1)
