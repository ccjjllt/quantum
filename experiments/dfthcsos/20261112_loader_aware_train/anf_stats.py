"""ANF support / rank statistics of the current table at lowbits 3 and 4."""
from __future__ import annotations
import sys, math
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq

NPZ = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT, J = 8, 5


def deltas(words):
    K = 15; out = []; prev = None
    for k in range(K):
        b = words[:, k*J:(k+1)*J]
        out.append(b if prev is None else b ^ prev); prev = b
    return out


def anf_full(d, lowbits, n_sel):
    L = 1 << lowbits
    H = -(-len(d)//L)
    hb = max(1, (H-1).bit_length())
    O = d.shape[1]*BROT
    pad = np.zeros((1 << n_sel, O), np.uint8)
    for j in range(d.shape[1]):
        for i in range(BROT):
            pad[:len(d), j*BROT+i] = (d[:, j] >> i) & 1
    # low transform: shape (L, n_sel-L, O) after first mobius over low axis
    x = tq.mobius(pad.reshape(1 << (n_sel-lowbits), L, O), 1)      # low monomials per block
    C = tq.mobius(x, 0)[:H]                                        # (H, L, O)
    return C.transpose(1, 0, 2)


def main():
    with np.load(NPZ) as z:
        words = np.asarray(z['angle_words'], np.int64)
    for lb in (3, 4, 5):
        n_sel = max(1, (len(words)-1).bit_length())
        sup_mixed = []; sup_pure = []; ranks = []; caches = []
        for d in deltas(words):
            C = anf_full(d, lb, n_sel)
            L, H, O = C.shape
            mixed = C[1:, 1:]
            pure = C[0, 1:]
            s = int(np.any(mixed.any(axis=0), axis=1).sum())
            sp = int(pure.any(axis=1).sum())
            sup_mixed.append(s); sup_pure.append(sp)
            rr = []
            for o in range(O):
                rows = [int(sum(int(v) << i for i, v in enumerate(mixed[m, :, o]))) for m in range(L-1)]
                rr.append(len(tq.rank_factor(rows)[0]))
            ranks.append(rr)
            caches.append(tq.cost([], L, H) - (H-1-(H-1).bit_length()))  # low cache only
        print(f'lowbits={lb}: L={2**lb} H={math.ceil(len(words)/(2**lb))} '
              f'mixed-support {np.mean(sup_mixed):.1f} pure-support {np.mean(sup_pure):.1f} '
              f'union {np.mean([max(a,b) for a,b in zip(sup_mixed,sup_pure)]):.1f} '
              f'rank mean {np.mean(ranks):.2f} max {np.max(ranks)} '
              f'lowcache {np.mean(caches):.1f} products/circuit {sum((r+1)//2 for r in ranks[0]):.0f}')


if __name__ == '__main__':
    main()
