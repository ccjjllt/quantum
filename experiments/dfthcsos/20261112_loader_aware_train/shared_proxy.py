"""tensorqrom shared-decomposition proxy for the baseline and the paired table."""
from __future__ import annotations
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
ART = ROOT/'.worktree/dfthcsos/artifacts/20261112_loader_aware_train'


def one(args):
    k, d = args
    C = tq.anf_tensor(d, 8, 4)
    terms = tq.shared(C, list(tq.SIZES), trials=6, seed=k, groups=tq.low_groups(4))
    return k, len(terms)


def shared_proxy(words):
    prev = None; tasks = []
    for k in range(15):
        b = words[:, k*5:(k+1)*5]
        d = b if prev is None else b ^ prev; prev = b
        tasks.append((k, d))
    with ProcessPoolExecutor(8) as ex:
        out = dict(ex.map(one, tasks))
    n = sum(out.values())
    return n, dict(full_cache=15*80 + n, sparse_cache_model=15*40 + n, per_circuit=out)


def main():
    base = np.load(ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz')
    W0 = np.asarray(base['angle_words'], np.int64)
    res = {}
    n, d = shared_proxy(W0); res['base_words'] = dict(terms=n, **d)
    print('base_words: terms', n, 'full-cache proxy', d['full_cache'], 'sparse model', d['sparse_cache_model'], flush=True)
    z = np.load(ART/'train_lam0.001.npz')
    Wp = W0.copy(); Wp[76:] = np.mod(np.round(z['phi']).astype(np.int64), 256)
    n, d = shared_proxy(Wp); res['paired_bit0'] = dict(terms=n, **d)
    print('paired_bit0: terms', n, 'full-cache proxy', d['full_cache'], 'sparse model', d['sparse_cache_model'], flush=True)
    (ART/'shared_proxy.json').write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
