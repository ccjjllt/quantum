"""Recover Maoxin v22's loader cost model from its circuits and test it on the table."""
from __future__ import annotations
import sys, math, collections
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq

SUB = ROOT/'artifacts/20261111_maoxin4097/dfthcsos'
NPZ = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT, J = 8, 5


def circuit_counts():
    out = []
    for k in range(15):
        import kickmix as km
        c = km.Circuit.from_file(str(SUB/f'angle_k_{k}.kmx'.replace('.kmx', '.kmb')), format='kmb')
        c.to_file(f'/tmp/ak{k}.kmx', format='kmx')
        lines = [l for l in open(f'/tmp/ak{k}.kmx').read().splitlines() if l.startswith('CCX')]
        deg = collections.Counter(len(l.split())-2 for l in lines)
        out.append(dict(ccx=len(lines), deg=dict(sorted(deg.items())),
                        cache=sum(1 for l in lines if int(l.split()[-1][1:]) >= 11+5*8)))
    return out


def table_model(words):
    A = len(words)
    n_sel = max(1, (A-1).bit_length())
    rows = []
    prev = None
    for k in range(15):
        b = words[:, k*J:(k+1)*J]
        if b.shape[1] < J: b = np.pad(b, ((0,0),(0,J-b.shape[1])))
        d = b if prev is None else b ^ prev; prev = b
        # ANF over the full selection register (2**n_sel addresses), 8 bits per word
        pad = np.zeros((1 << n_sel, J*BROT), np.uint8)
        for j in range(J):
            for i in range(BROT):
                pad[:A, j*BROT+i] = (d[:, j] >> i) & 1
        C = tq.mobius(tq.mobius(pad.reshape(16, -1, J*BROT), 0), 1)  # (16, 128, O)
        C = C.transpose(1, 0, 2)
        mixed = C[1:, 1:]                                # (15, 127, O)
        sup = np.any(mixed.any(axis=0), axis=1)          # (127,) monomial in any output
        cache = int(sup.sum())
        prods = 0
        ranks = []
        for o in range(mixed.shape[2]):
            bitrows = [int(sum(int(v) << i for i, v in enumerate(mixed[m, :, o]))) for m in range(15)]
            r = len(tq.rank_factor(bitrows)[0])
            ranks.append(r)
            prods += (r + 1)//2
        rows.append(dict(k=k, cache=cache, products=prods, cost=cache+prods,
                         cache_cost=tq.cost([], 16, 128), ranks=ranks))
    return rows


def main():
    cc = circuit_counts()
    with np.load(NPZ) as z:
        words = np.asarray(z['angle_words'], np.int64)
    mm = table_model(words)
    for a, b in zip(cc, mm):
        print(f"k={a['ccx'] and b['k']:2d} real ccx {a['ccx']:3d} (cache {a['cache']:2d}) | "
              f"model cache {b['cache']:2d} + products {b['products']:3d} = {b['cost']:3d} "
              f"rank mean {np.mean(b['ranks']):.2f}")
    print('real total', sum(a['ccx'] for a in cc), 'model total', sum(b['cost'] for b in mm))


if __name__ == '__main__':
    main()
