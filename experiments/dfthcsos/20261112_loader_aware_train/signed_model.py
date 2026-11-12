"""Cost model on the signed-gauge table vs Maoxin v22's real 4,097."""
from __future__ import annotations
import sys, math
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
from dfthcsos.verify import load_inputs
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors
import encode

NPZ = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
REAL = [294, 289, 289, 289, 268, 268, 268, 268, 268, 265, 266, 266, 266, 266, 267]
BROT, J, LB = 8, 5, 4


def model(words, lowbits=LB, O_bits=7, n_sel=None):
    n_sel = n_sel or max(1, (len(words)-1).bit_length())
    rows = []; prev = None
    for k in range(15):
        b = words[:, k*J:(k+1)*J]
        d = b if prev is None else b ^ prev; prev = b
        L = 1 << lowbits; H = -(-len(d)//L); O = d.shape[1]*O_bits
        pad = np.zeros((1 << n_sel, O), np.uint8)
        for j in range(d.shape[1]):
            for i in range(O_bits):
                pad[:len(d), j*O_bits+i] = (d[:, j] >> i) & 1
        x = tq.mobius(pad.reshape(1 << (n_sel-lowbits), L, O), 1)
        C = tq.mobius(x, 0)[:H].transpose(1, 0, 2)
        mixed = C[1:, 1:]
        sup = int(np.any(mixed.any(axis=0), axis=1).sum())
        prods = 0
        for o in range(O):
            rr = [int(sum(int(v) << i for i, v in enumerate(mixed[m, :, o]))) for m in range(L-1)]
            prods += (len(tq.rank_factor(rr)[0]) + 1)//2
        rows.append(dict(k=k, cache=sup, products=prods, cost=sup+prods))
    return rows


def main():
    inp = load_inputs(NPZ)
    with np.load(NPZ) as z:
        words = np.asarray(z['angle_words'], np.int64); tree = np.asarray(z['tree_edges'], np.int64)
    u = reconstruct_u_vectors(words[76:] / 128.0, tree)
    sw = words.copy()
    sw[76:] = encode.signed_words(u, tree, BROT)
    for name, w in (('unsigned', words), ('signed', sw)):
        mm = model(w)
        print(f'{name}: total model {sum(r["cost"] for r in mm)} cache {sum(r["cache"] for r in mm)} '
              f'products {sum(r["products"] for r in mm)}')
        print('   per circuit', [r['cost'] for r in mm])
    print('real          ', REAL, 'total', sum(REAL))


if __name__ == '__main__':
    main()
