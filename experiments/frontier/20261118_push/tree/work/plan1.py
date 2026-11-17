"""Local planner oracle: products per loader for a given words table.

Pure GF(2) algebra on the 1232x75 table (no circuit is built or simulated).
Uses the shipped `plan_loaders.try_plan` (BlockPlan + descend_smart + padding solve).
"""
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
for p in (str(HERE), str(HERE / 'code2'), str(HERE / 'code2' / 'compiler')):
    if p not in sys.path:
        sys.path.insert(0, p)

from planner import complete_words, cross_tensor  # noqa: E402
from plan_loaders import partitions, try_plan, valid_rels  # noqa: E402


def plan_k(words, k, seconds=120.0, seeds=(7,), random_parts=0, parts_index=None, verbose=True):
    Wc = complete_words(np.asarray(words, np.uint8))
    target = cross_tensor(Wc, k)
    rels = valid_rels(target)
    rng = random.Random(5)
    parts_list = partitions(rng, random_parts)
    if parts_index is not None:
        parts_list = [parts_list[parts_index]]
    best = None
    for pi, parts in enumerate(parts_list):
        for seed in seeds:
            t0 = time.time()
            got, path = try_plan(target, parts, rels, seed, seconds)
            if verbose:
                print(f'  k{k} parts{pi} seed{seed}: max cuts {max(path)} '
                      f'-> {None if got is None else got["products"]} products '
                      f'({time.time() - t0:.0f}s)', flush=True)
            if got and (best is None or got['sum_cuts'] > best['sum_cuts']):
                best = got
    return best


if __name__ == '__main__':
    ks = [int(x) for x in sys.argv[1].split(',')]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    z = np.load(HERE / 'build' / 'submission.npz', allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    out = {}
    for k in ks:
        b = plan_k(W, k, seconds=seconds)
        out[k] = None if b is None else {kk: b[kk] for kk in ('sum_cuts', 'd', 'products', 'seconds')}
        print('SHIPPED-TABLE', k, out[k], flush=True)
    json.dump(out, open(HERE / 'plan_oracle_test.json', 'w'), indent=1)
