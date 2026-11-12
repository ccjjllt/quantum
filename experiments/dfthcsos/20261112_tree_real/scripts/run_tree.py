"""Encode one Givens tree, evaluate the official metrics, build the real loader, price it.

    python run_tree.py --tree current --tag ctl
    python run_tree.py --tree path --tag path
    python run_tree.py --tree greedy --tag greedy

Writes ``work/<tag>.npz`` (words, edges, params) and appends a JSON row to ``logs/rows.jsonl``.
No refit here; ``refit.py`` takes a tag and spends the error budget.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import time
from pathlib import Path

import numpy as np

import common as C
import encode
import trees
from refine import Problem
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference

HERE = C.HERE


def tree_edges(name: str, inputs) -> np.ndarray:
    if name in trees.TREES:
        return trees.TREES[name]()
    if name == 'greedy':
        return trees.greedy_merge_tree(inputs.params['U'].reshape(-1, 76))
    if name == 'balanced':
        return trees.balanced_mass_tree(inputs.params['U'].reshape(-1, 76))
    if name.startswith('random'):
        seed = int(name.split(':')[1]) if ':' in name else 0
        return trees.random_tree(76, seed=seed)
    raise SystemExit(f'unknown tree {name}')


def encode_table(inputs, edges, one_start=None):
    """Two-body rows: nearest rounding of the exact U on this tree. One-body rows: polished."""
    two = encode.to_words(encode.tree_angles(inputs.params['U'].reshape(-1, 76), edges), 8)
    u = encode.decode(two, edges, 8).reshape(*inputs.params['U'].shape)
    u /= np.linalg.norm(u, axis=2, keepdims=True)
    ref = load_reference(check_fcidump())
    p = Problem(u, inputs.w, ref, inputs.S, inputs.beta_1)
    h1p = p.h1(inputs.W)
    one = C.onebody_words(h1p, edges, 8, start=one_start, kicks=0)
    return np.vstack([one, two]), two, u, h1p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--build', action='store_true')
    a = ap.parse_args()

    params, words0, edges0, inputs = C.load_base()
    t0 = time.time()
    edges = tree_edges(a.tree, inputs)
    print(f'tree {a.tree}: {len(edges)} edges in {time.time() - t0:.1f}s', flush=True)
    words, two, u, h1p = encode_table(inputs, edges)
    m = C.metrics(inputs, words, edges, 8)
    print('metrics', json.dumps({k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}),
          flush=True)
    np.savez(HERE / f'work/{a.tag}.npz', angle_words=words, tree_edges=edges, **params)
    row = {'tag': a.tag, 'tree': a.tree, 'stage': 'encoded', 'edges': edges.tolist(),
           **{k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}}
    if a.build:
        t1 = time.time()
        fam = C.build_family(words, jobs=a.jobs)
        t2 = time.time()
        cost = C.full_cost(inputs, fam, m, 8)
        row.update({'stage': 'built', 'build_sec': round(t2 - t1, 1), **cost})
        d = HERE / f'work/{a.tag}'
        C.save_candidate(d, params, words, edges, fam)
        print('cost', json.dumps({k: cost[k] for k in ('angles_T_pass', 'T_total', 'Q_total', 'lambda_eff', 'cost')}),
              flush=True)
    C.dump(row, HERE / 'logs/rows.jsonl')
    print('WROTE', HERE / 'logs/rows.jsonl', flush=True)


if __name__ == '__main__':
    main()
