"""Cheap ANF proxy for a tree: sum over circuits of tensorqrom8.cost(per_output(C), L, H).

The proxy is not the loader (the real `shared` decomposition is 20% cheaper and tree-dependent), so
it is used only to rank trees before building real circuits.

    python proxy.py current path star heap greedy balanced random:1 random:2
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import numpy as np

import common as C
import encode
import trees
import tensorqrom8 as tq
from fourqrom import batch_deltas
from refine import Problem
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference


def edges_of(name, inputs):
    if name in trees.TREES:
        return trees.TREES[name]()
    if name == 'greedy':
        return trees.greedy_merge_tree(inputs.params['U'].reshape(-1, 76))
    if name == 'balanced':
        return trees.balanced_mass_tree(inputs.params['U'].reshape(-1, 76))
    if name.startswith('random'):
        return trees.random_tree(76, seed=int(name.split(':')[1]) if ':' in name else 0)
    raise SystemExit(name)


def proxy(words, j=5, lowbits=4):
    n_sel = max(1, (len(words) - 1).bit_length())
    total, per = 0, []
    for d in batch_deltas(words, j):
        C_ = tq.anf_tensor(d, 8, lowbits, full=True)
        c = tq.cost(tq.per_output(C_), C_.shape[0], C_.shape[1])
        per.append(int(c))
        total += int(c)
    return total, per


def main() -> None:
    params, words0, edges0, inputs = C.load_base()
    ref = load_reference(check_fcidump())
    rows = []
    for name in sys.argv[1:]:
        edges = edges_of(name, inputs)
        two = encode.to_words(encode.tree_angles(inputs.params['U'].reshape(-1, 76), edges), 8)
        u = encode.decode(two, edges, 8).reshape(*inputs.params['U'].shape)
        u /= np.linalg.norm(u, axis=2, keepdims=True)
        p = Problem(u, inputs.w, ref, inputs.S, inputs.beta_1)
        _, vecs = np.linalg.eigh(p.h1(inputs.W))
        one = encode.signed_words(vecs.T, edges, 8)
        words = np.vstack([one, two])
        tot, per = proxy(words)
        row = {'name': name, 'proxy_per_pass': tot, 'per': per}
        rows.append(row)
        print('ROW', json.dumps(row), flush=True)
    C.dump({'stage': 'proxy', 'rows': rows}, C.HERE / 'logs/proxy.jsonl')


if __name__ == '__main__':
    main()
