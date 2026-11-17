"""Run the ported planner on the shipped vs re-coded table for one loader."""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CHEM = HERE.parent
sys.path.insert(0, str(CHEM / 'code2'))
sys.path.insert(0, str(CHEM / 'code2' / 'compiler'))

import os
os.environ.setdefault('STOP_AT', '175')
os.environ.setdefault('LS_SECONDS', '90')
import compile_basis as cb  # noqa: E402
from planner import complete_words, cross_tensor, NDIM  # noqa: E402
from recode import load_words, recode  # noqa: E402

def run(words, k, seeds=(7,), limit=420, tag=''):
    Wc = complete_words(np.asarray(words, np.uint8))
    target = cross_tensor(Wc, k)
    t0 = time.time()
    best = cb.plan_one(target, seeds=seeds, trials=40, verbose=True, time_limit=limit)
    if best is None:
        print(f'[{tag}] k{k}: NO PLAN ({time.time()-t0:.0f}s)', flush=True)
        return None
    sc = int(best['sum_c'])
    res = {'tag': tag, 'k': k, 'sum_cuts': sc, 'products': (NDIM - sc) // 2,
           'toffoli_69': (NDIM - sc) // 2 + 69 + 6, 'toffoli_68': (NDIM - sc) // 2 + 68 + 6,
           'seconds': round(time.time() - t0, 1)}
    print('RESULT', json.dumps(res), flush=True)
    return res


if __name__ == '__main__':
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    words = load_words()
    out = []
    if 'base' in sys.argv:
        out.append(run(words, k, tag='base'))
    if 'rec' in sys.argv:
        mod = recode(words, k)
        np.save(HERE / f'words_recode_k{k}.npy', mod)
        out.append(run(mod, k, tag='recoded'))
    print(json.dumps(out, indent=1))
