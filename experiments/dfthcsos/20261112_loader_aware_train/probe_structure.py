"""How the tensorqrom proxy responds to row repetition / clustering of the stored words."""
from __future__ import annotations
import sys, math
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq

P = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT, J, LB = 8, 5, 4


def deltas(words, J=J):
    K = math.ceil(words.shape[1]/J); out = []; prev = None
    for k in range(K):
        b = words[:, k*J:(k+1)*J]
        if b.shape[1] < J: b = np.pad(b, ((0,0),(0,J-b.shape[1])))
        out.append(b if prev is None else b ^ prev); prev = b
    return out


def proxy(words):
    tot = 0
    for d in deltas(words):
        C = tq.anf_tensor(d, BROT, LB)
        tot += tq.cost(tq.per_output(C), 1 << LB, C.shape[1])
    return tot


def blockify(words, start, stop, k):
    """Replace each k consecutive rows in [start, stop) by the first of them."""
    out = words.copy()
    for i in range(start, stop, k):
        out[i:min(i+k, stop)] = out[i]
    return out


def main():
    with np.load(P, allow_pickle=False) as z:
        w = np.asarray(z['angle_words'], np.int64)
    base = proxy(w)
    print('base', base)
    # isolate one-body (rows 0..75) and two-body (76..)
    print('one-body constant', proxy(blockify(w, 0, 76, 76)))
    print('two-body constant (all 1144)', proxy(blockify(w, 76, 1220, 1144)))
    for k in (2, 3, 4, 6, 8, 11, 13, 16):
        print(f'two-body blockify k={k:2d}', proxy(blockify(w, 76, 1220, k)))
    # one-body aligned order: sort one-body rows so similar words are adjacent (greedy on 75-bit word)
    print('one-body + two-body k=2', proxy(blockify(blockify(w, 0, 76, 76), 76, 1220, 2)))
    # Hamming-greedy order of rows within each group then blockify
    def greedy_order(rows, start):
        idx = list(range(len(rows)))
        out = [idx.pop(0)]
        while idx:
            last = rows[out[-1]]
            d = ((rows[idx] ^ last) != 0).sum(axis=1)
            j = int(np.argmin(d))
            out.append(idx.pop(j))
        return np.array(out)
    wo = w.copy()
    for r in range(9):
        s = 0 if r == 0 else 76 + (r-1)*143; e = 76 + r*143
        o = greedy_order(w[s:e], s)
        wo[s:e] = w[s:e][o]
    print('greedy row order proxy', proxy(wo))
    for k in (2, 4, 8, 16):
        print(f'greedy order + blockify k={k:2d}', proxy(blockify(wo, 76, 1220, k)))


if __name__ == '__main__':
    main()
