"""Screen Givens trees on a subset of the real loader circuits (same encoder for every tree).

    python screen.py current path star heap greedy balanced random:1 --ksel 0,5,10

Per tree: encode the two-body rows from the exact U on that tree (unsigned nearest rounding) and
refresh the one-body rows; then build only the circuits in ``--ksel`` and report their Toffoli sum.
The control is ``current`` under the same encoder, not the public table's 4,089.
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
import trees
from refine import Problem
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference


def edges_of(name: str, inputs) -> np.ndarray:
    if name in trees.TREES:
        return trees.TREES[name]()
    if name == 'greedy':
        return trees.greedy_merge_tree(inputs.params['U'].reshape(-1, 76))
    if name == 'balanced':
        return trees.balanced_mass_tree(inputs.params['U'].reshape(-1, 76))
    if name.startswith('random'):
        return trees.random_tree(76, seed=int(name.split(':')[1]) if ':' in name else 0)
    raise SystemExit(f'unknown tree {name}')


def encode_table(inputs, edges, start_one=None):
    two = encode.to_words(encode.tree_angles(inputs.params['U'].reshape(-1, 76), edges), 8)
    u = encode.decode(two, edges, 8).reshape(*inputs.params['U'].shape)
    u /= np.linalg.norm(u, axis=2, keepdims=True)
    ref = load_reference(check_fcidump())
    p = Problem(u, inputs.w, ref, inputs.S, inputs.beta_1)
    one = C.onebody_words(p.h1(inputs.W), edges, 8, start=start_one, kicks=0)
    return np.vstack([one, two]), two


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='+')
    ap.add_argument('--ksel', default='0,5,10')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--save', action='store_true', help='keep each table under work/')
    a = ap.parse_args()
    ksel = [int(k) for k in a.ksel.split(',')]

    params, words0, edges0, inputs = C.load_base()
    for name in a.names:
        t0 = time.time()
        edges = edges_of(name, inputs)
        try:
            words, two = encode_table(inputs, edges)
        except Exception as exc:  # noqa: BLE001
            print('ENCODE FAIL', name, repr(exc), flush=True)
            continue
        m = C.metrics(inputs, words, edges, 8)
        enc_s = round(time.time() - t0, 1)
        t1 = time.time()
        try:
            res = C.build_selected(words, ksel, jobs=min(a.jobs, len(ksel)), full=True)
            per = [int(c.operation_statistics().num_toffoli_like) for c in res]
            q = [int(c.num_qubits) for c in res]
        except Exception as exc:  # noqa: BLE001
            print('BUILD FAIL', name, repr(exc), flush=True)
            per, q = None, None
        row = {'name': name, 'ksel': ksel, 'per': per, 'sum': (sum(per) if per else None), 'qmax': (max(q) if q else None),
               'enc_sec': enc_s, 'build_sec': round(time.time() - t1, 1),
               **{k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}}
        print('ROW', json.dumps(row), flush=True)
        C.dump(row, C.HERE / 'logs/screen.jsonl')
        if a.save:
            np.savez(C.HERE / f'work/scr_{name.replace(":", "_")}.npz', angle_words=words, tree_edges=edges, **params)


if __name__ == '__main__':
    main()
