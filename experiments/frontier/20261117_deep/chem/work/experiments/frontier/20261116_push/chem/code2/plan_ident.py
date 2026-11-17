"""Best block-cut plan for one loader in the identity low basis (no MinRank
basis needed, so it also works for the uncoded batches 0/1).

Sweeps partitions of the 15 low monomials into 5 triples; for each, the full
annihilator (30 cuts/block) is screened, then the shipped top-down descent and
the swap local search are run.  The best perfect-pairing state is written as a
literal plan (identity low basis).
"""
import sys, json, random, time, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from parity_recover import NOUT, basis, alternating_field, gf_rank  # noqa: E402
from planner import (BlockPlan, complete_words, cross_tensor, NDIM, top_down, local_search,  # noqa: E402
                     descend_smart, physical_cuts, solve_padding, candidates)
sys.path.insert(0, str(HERE))
from plan_screen import valid_rels, partitions  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
IDENT = [1 << i for i in range(15)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('--parts', type=int, default=10)
    ap.add_argument('--seconds', type=float, default=40)
    ap.add_argument('--seed', type=int, default=5)
    ap.add_argument('--style', default='mix')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    k = a.k
    z = np.load(BUILD / 'submission.npz', allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    Wc = complete_words(W)
    target = cross_tensor(Wc, k)
    rels = valid_rels(target)
    print(f'k{k}: rels {len(rels)}', flush=True)
    rng = random.Random(a.seed)
    t0 = time.time()
    best = None
    for pi, parts in enumerate(partitions(rng, a.parts, a.style)):
        bp = BlockPlan(target, parts, rels, per_coord=True, hmax=76)
        c0 = top_down(bp, seed=a.seed + pi, trials=24, verbose=False, time_limit=a.seconds)
        if c0 is None:
            print(f'   parts{pi}: no top-down state ({time.time() - t0:.0f}s)', flush=True)
            continue
        bp.best = c0
        c1 = local_search(bp, c0, seconds=a.seconds, seed=a.seed + 7 + pi, verbose=False)
        sc = sum(map(len, c1))
        print(f'   parts{pi}: {sum(map(len, c0))} -> LS {sc} cuts ({(NDIM - sc) // 2} products, '
              f'{time.time() - t0:.0f}s)', flush=True)
        if best is None or sc > best[0]:
            best = (sc, c1, parts)
    out = {'k': k}
    if best:
        sc, cuts, parts = best
        phys = physical_cuts(parts, cuts)
        F = solve_padding(phys, target[76])
        out.update({'sum_cuts': sc, 'products': (NDIM - sc) // 2, 'parts': parts,
                    'rows': IDENT, 'cuts': [[int(c) for c in blk] for blk in cuts],
                    'F': int(F) if F is not None else None,
                    'padding_ok': F is not None})
        print(f'k{k}: BEST {sc} cuts {((NDIM - sc) // 2)} products padding '
              f'{"ok" if F is not None else "UNSOLVABLE"} ({time.time() - t0:.0f}s)', flush=True)
    else:
        out.update({'sum_cuts': None, 'products': None})
    (HERE / (a.out or f'ident_plan_k{k}.json')).write_text(json.dumps(out, indent=1))
    print('RESULT', json.dumps({kk: vv for kk, vv in out.items() if kk != 'cuts'}), flush=True)


if __name__ == '__main__':
    main()
