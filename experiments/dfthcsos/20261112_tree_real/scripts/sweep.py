"""Full real-loader sweep over Givens trees: encode, evaluate, build all 15 circuits, price exactly.

    python sweep.py current path star heap greedy twostar balanced random:1 random:2

One table per tree, same encoder for all (two-body = nearest 8-bit rounding of the exact U on that
tree; one-body = polished signed-gauge rows), J=5, lowbits=4, all 8 bits loaded.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time

import numpy as np

import common as C
import encode
import trees
from refine import Problem
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference


def edges_of(name, inputs):
    if name in trees.TREES:
        return trees.TREES[name]()
    if name == 'greedy':
        return trees.greedy_merge_tree(inputs.params['U'].reshape(-1, 76))
    if name == 'balanced':
        return trees.balanced_mass_tree(inputs.params['U'].reshape(-1, 76))
    if name == 'twostar':
        return trees.two_star_tree()
    if name.startswith('random'):
        return trees.random_tree(76, seed=int(name.split(':')[1]) if ':' in name else 0)
    raise SystemExit(name)


def encode_table(inputs, edges):
    two = encode.to_words(encode.tree_angles(inputs.params['U'].reshape(-1, 76), edges), 8)
    u = encode.decode(two, edges, 8).reshape(*inputs.params['U'].shape)
    u /= np.linalg.norm(u, axis=2, keepdims=True)
    ref = load_reference(check_fcidump())
    p = Problem(u, inputs.w, ref, inputs.S, inputs.beta_1)
    one = C.onebody_words(p.h1(inputs.W), edges, 8, kicks=0)
    return np.vstack([one, two])


def main() -> None:
    params, words0, edges0, inputs = C.load_base()
    for name in sys.argv[1:]:
        t0 = time.time()
        edges = edges_of(name, inputs)
        words = encode_table(inputs, edges)
        m = C.metrics(inputs, words, edges, 8)
        enc = time.time() - t0
        t1 = time.time()
        try:
            fam = C.build_family(words, jobs=6)
            cost = C.full_cost(inputs, fam, m, 8)
            tag = name.replace(':', '_')
            C.save_candidate(C.HERE / f'work/tree_{tag}', params, words, edges, fam)
            row = {'name': name, 'stage': 'built', 'enc_sec': round(enc, 1),
                   'build_sec': round(time.time() - t1, 1), 'n_edges': len(edges),
                   **{k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}, **cost}
        except Exception as exc:  # noqa: BLE001
            row = {'name': name, 'stage': 'build_fail', 'error': repr(exc), 'enc_sec': round(enc, 1),
                   **{k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}}
        print('ROW', json.dumps(row), flush=True)
        C.dump(row, C.HERE / 'logs/sweep.jsonl')


if __name__ == '__main__':
    main()
