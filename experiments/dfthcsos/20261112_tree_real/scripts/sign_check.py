"""Signed-gauge re-encoding of one table: does 7-bit loading (bit 7 = bit 6) hold and what is T?

The signed gauge (theta/pi in [-1/2, 1/2)) makes every word's top bit a copy of the bit below, so
`tensorqrom8` may drop it (35 outputs instead of 40) and borrow it as scratch. The metric must be
unchanged: the decoded rows only change by a global sign, and error_1/error_2 are sign-blind.

    python sign_check.py --tree current --tag ctl_signed
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import time

import numpy as np

import common as C
import encode
import onebody
import trees
from refine import Problem
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default='current')
    ap.add_argument('--tag', required=True)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--start', type=str, default=None, help='npz with one-body words to warm start from')
    a = ap.parse_args()

    params, words0, edges0, inputs = C.load_base()
    edges = trees.TREES[a.tree]() if a.tree in trees.TREES else trees.greedy_merge_tree(inputs.params['U'].reshape(-1, 76))
    two = onebody.signed_gauge(encode.to_words(encode.tree_angles(inputs.params['U'].reshape(-1, 76), edges), 8), edges, 8)
    u = encode.decode(two, edges, 8).reshape(*inputs.params['U'].shape)
    u /= np.linalg.norm(u, axis=2, keepdims=True)
    ref = load_reference(check_fcidump())
    p = Problem(u, inputs.w, ref, inputs.S, inputs.beta_1)
    h1p = p.h1(inputs.W)
    start = None
    if a.start:
        with np.load(a.start) as z:
            start = np.asarray(z['angle_words'])[:76]
    one = C.onebody_words(h1p, edges, 8, start=start, kicks=0)
    words = np.vstack([one, two])
    assert np.array_equal(((words >> 7) ^ (words >> 6)) & 1, np.zeros_like(words)), 'not the signed gauge'
    m = C.metrics(inputs, words, edges, 8)
    print('metrics', json.dumps({k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}),
          flush=True)
    np.savez(C.HERE / f'work/{a.tag}.npz', angle_words=words, tree_edges=edges, **params)
    t1 = time.time()
    fam = C.build_family(words, jobs=a.jobs, full=False)
    cost = C.full_cost(inputs, fam, m, 8)
    print('cost', json.dumps({k: cost[k] for k in ('angles_T_pass', 'T_total', 'Q_total', 'lambda_eff', 'cost',
                                                   'angles_qubits', 'circuit_qmax')}), flush=True)
    out = C.HERE / f'work/{a.tag}'
    C.save_candidate(out, params, words, edges, fam)
    C.dump({'tag': a.tag, 'tree': a.tree, 'stage': 'signed_built', 'build_sec': round(time.time() - t1, 1),
            **{k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}, **cost},
           C.HERE / 'logs/rows.jsonl')


if __name__ == '__main__':
    main()
