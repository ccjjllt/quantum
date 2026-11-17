"""The author's own best loader pipeline (compile_basis.plan_one) on the shipped
(marculera) table: rank-74 low-basis search (MinRank kernel attack), 75-slice
annihilators, rank-guided top-down cut descent, v18 matching, GF(2) padding
solve.  Writes one JSON per loader; no circuit is built here.
"""
import sys, json, time, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
import compile_basis as cb  # noqa: E402
import os
cb.STOP_AT = int(os.environ.get('STOP_AT', '149'))
cb.LS_SECONDS = int(os.environ.get('LS_SECONDS', '120'))
from planner import complete_words, cross_tensor, NDIM, local_search  # noqa: E402
from parity_recover import NOUT, basis, reduce  # noqa: E402
from planner import physical_cuts, solve_padding  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('--seeds', default='7')
    ap.add_argument('--limit', type=float, default=900)
    args = ap.parse_args()
    k = args.k
    z = np.load(BUILD / 'submission.npz', allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    Wc = complete_words(W)
    target = cross_tensor(Wc, k)
    t0 = time.time()
    best = cb.plan_one(target, seeds=tuple(int(x) for x in args.seeds.split(',')), trials=40,
                       verbose=True, time_limit=args.limit)
    out = {'k': k, 'shipped_T': SHIPPED[k]}
    if best is None:
        out['result'] = None
    else:
        sc = int(best['sum_c'])
        out.update({'sum_cuts': sc, 'products': (NDIM - sc) // 2, 'parts': cb.PARTS5,
                    'rows': [int(x) for x in best['rows']],
                    'cuts': [[int(c) for c in block] for block in best['cuts']],
                    'F': int(best['F'])})
    out['seconds'] = round(time.time() - t0, 1)
    print('RESULT', json.dumps({kk: vv for kk, vv in out.items() if kk not in ('cuts',)}), flush=True)
    (HERE / f'basis_plan_k{k}.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
