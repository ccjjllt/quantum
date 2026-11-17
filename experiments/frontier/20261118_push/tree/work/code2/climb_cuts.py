"""Climb the cut count at a perfect pairing: swap local search from a saved
perfect state, in the stored (rank-74) low basis.

products = (525 - sum_cuts)/2 and the emitter price is products + 69 + 6, so
each +2 cuts is one fewer Toffoli.
"""
import sys, json, time, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from planner import (BlockPlan, complete_words, cross_tensor, NDIM, local_search,  # noqa: E402
                     physical_cuts, solve_padding)
from lowbasis import inverse15, transform_target  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('--state', default=None)
    ap.add_argument('--seconds', type=float, default=600)
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    k = a.k
    st = json.loads(Path(a.state or HERE / f'basis_plan_k{k}.json').read_text())
    z = np.load(BUILD / 'submission.npz', allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    Wc = complete_words(W)
    target = cross_tensor(Wc, k)
    B = inverse15(st['rows'])
    tt = transform_target(target, B)
    bp = BlockPlan(tt, st['parts'], [], per_coord=True, hmax=76)
    cuts = [list(map(int, blk)) for blk in st['cuts']]
    c0 = sum(map(len, cuts))
    bp.best = cuts
    t0 = time.time()
    c1 = local_search(bp, cuts, seconds=a.seconds, seed=a.seed, verbose=True, p_down=0.15,
                      restart_every=200)
    c1 = local_search(bp, c1, seconds=a.seconds / 2, seed=a.seed + 5, verbose=False, p_down=0.15,
                      restart_every=200)
    c2 = sum(map(len, c1))
    F = solve_padding(physical_cuts(st['parts'], c1, Binv=st['rows']), target[76])
    out = dict(st, sum_cuts=c2, products=(NDIM - c2) // 2,
               cuts=[[int(c) for c in blk] for blk in c1],
               F=int(F) if F is not None else None, padding_ok=F is not None,
               climbed_from=c0, seconds=round(time.time() - t0, 1))
    (HERE / (a.out or f'climb_k{k}.json')).write_text(json.dumps(out, indent=1))
    print('RESULT', json.dumps({kk: vv for kk, vv in out.items() if kk != 'cuts'}), flush=True)


if __name__ == '__main__':
    main()
