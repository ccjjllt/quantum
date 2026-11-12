"""Accuracy cost of block-clustering within-group two-body vectors (unsigned gauge)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import encode
from dfthcsos.verify import load_inputs, evaluate_words
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

P = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT = 8


def main():
    inp = load_inputs(P)
    with np.load(P, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64); tree = np.asarray(z['tree_edges'], np.int64)
    U = np.asarray(inp.params['U'], np.float64)
    u_dec = reconstruct_u_vectors(words[76:] / 128.0, tree).reshape(U.shape)
    u_dec /= np.linalg.norm(u_dec, axis=2, keepdims=True)
    print('decode vs U: max |1-|cos||', np.abs(np.abs((u_dec*U).sum(-1))-1).max())
    two0 = encode.to_words(encode.tree_angles(u_dec.reshape(-1, 76), tree), BROT)
    print('unsigned re-encode reproduces npz two-body words:', np.array_equal(two0, words[76:]),
          'diff', np.count_nonzero(two0 != words[76:]))
    for k in (1, 2, 3, 4, 8):
        Uc = U.copy()
        if k > 1:
            for r in range(8):
                for b in range(0, 143, k):
                    blk = U[r, b:b+k]
                    m = blk.mean(0); m /= np.linalg.norm(m)
                    Uc[r, b:b+k] = m
        two = encode.to_words(encode.tree_angles(Uc.reshape(-1, 76), tree), BROT)
        w2 = words.copy(); w2[76:] = two
        m = evaluate_words(inp, w2, tree, BROT)
        print(f'k={k}: e1 {1e3*m["error_1"]:.3f} e2 {1e3*m["error_2"]:.3f} mHa '
              f'Lambda {m["Lambda"]:.3f} E_gap {m["E_gap"]:.4f} lambda_eff {m["lambda_eff"]:.3f}',
              flush=True)


if __name__ == '__main__':
    main()
