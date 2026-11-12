"""Break down the tensorqrom per_output proxy of the current table and probe structure."""
from __future__ import annotations
import sys, math, json
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
from dfthcsos.verify import load_inputs, evaluate_words

P = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT, J, LB = 8, 5, 4


def deltas(words, J=J):
    K = math.ceil(words.shape[1]/J); out = []; prev = None
    for k in range(K):
        b = words[:, k*J:(k+1)*J]
        if b.shape[1] < J: b = np.pad(b, ((0,0),(0,J-b.shape[1])))
        out.append(b if prev is None else b ^ prev); prev = b
    return out


def detail(words):
    rows = []
    for k, d in enumerate(deltas(words)):
        C = tq.anf_tensor(d, BROT, LB)
        L, H, O = C.shape
        terms = tq.per_output(C)
        rows.append(dict(k=k, L=L, H=H, O=O, cache=tq.cost([], L, H), products=len(terms), cost=tq.cost(terms, L, H)))
    return rows


def proxy(words):
    return sum(r['cost'] for r in detail(words))


def main():
    with np.load(P, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64); tree = np.asarray(z['tree_edges'], np.int64)
    rows = detail(words)
    print('per-circuit:', json.dumps(rows))
    print('proxy total', proxy(words), 'products', sum(r['products'] for r in rows))
    inp = load_inputs(P)
    m = evaluate_words(inp, words, tree, BROT)
    print('metrics', {k: float(m[k]) for k in ('error_1','error_2','Lambda','E_gap','lambda_eff')})
    # word structure
    print('rows', words.shape, 'unique 5-word vectors per circuit:',
          [len(np.unique(words[:, k*J:(k+1)*J], axis=0)) for k in range(15)])
    print('distinct words per column', [len(np.unique(words[:, c])) for c in range(75)])
    # blockiness: how many 16-row blocks are constant in each circuit's delta
    for name, w in (('orig', words), ('block-const', np.repeat(words[::16], 16, axis=0)[:len(words)])):
        print(name, 'proxy', proxy(w))
    # duplication probe: copy row 0's words into its 15 block neighbours
    w2 = words.copy(); w2[1:16] = w2[0]
    print('dup first block proxy', proxy(w2))
    # all rows of a group -> same vector (worst case)
    w3 = words.copy()
    for r in range(8):
        sl = slice(76+r*143, 76+(r+1)*143)
        w3[sl] = w3[76+r*143]
    print('one vector per group proxy', proxy(w3))


if __name__ == '__main__':
    main()
