"""Screen many low-monomial partitions cheaply, then spend the budget on the
best few (top-down descent + swap local search).  Writes a literal plan in the
identity low basis.
"""
import sys, json, random, time, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from parity_recover import NOUT, basis  # noqa: E402
from planner import (BlockPlan, complete_words, cross_tensor, NDIM, top_down, local_search,  # noqa: E402
                     physical_cuts, solve_padding, candidates)
from plan_screen import valid_rels  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
IDENT = [1 << i for i in range(15)]
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


def all_parts(rng, n):
    LIN = [0, 1, 3, 7]
    NL = [m for m in range(15) if m not in LIN]
    out = [[[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]]
    for _ in range(n):
        nl = NL[:]; rng.shuffle(nl)
        if rng.random() < 0.5:
            out.append([[LIN[i], nl[2 * i], nl[2 * i + 1]] for i in range(4)] + [nl[8:11]])
        else:
            pool = LIN + NL; rng.shuffle(pool)
            out.append([pool[3 * i:3 * i + 3] for i in range(5)])
    # de-duplicate
    seen, uniq = set(), []
    for p in out:
        key = tuple(sorted(tuple(sorted(t)) for t in p))
        if key not in seen:
            seen.add(key); uniq.append(p)
    return uniq


def screen(bp):
    full = [list(basis(f).values()) for f in bp.full]
    pairs, _ = candidates({'parts': bp.parts, 'cuts': full}, full)
    sp = len(basis([x for p in pairs for x in p[:2]]))
    return sp - (NDIM - sum(map(len, full)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('--screen', type=int, default=60)
    ap.add_argument('--keep', type=int, default=4)
    ap.add_argument('--seconds', type=float, default=90)
    ap.add_argument('--seed', type=int, default=5)
    a = ap.parse_args()
    k = a.k
    z = np.load(BUILD / 'submission.npz', allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    Wc = complete_words(W)
    target = cross_tensor(Wc, k)
    rels = valid_rels(target)
    rng = random.Random(a.seed)
    t0 = time.time()
    scored = []
    for parts in all_parts(rng, a.screen):
        bp = BlockPlan(target, parts, rels, per_coord=True, hmax=76)
        scored.append((screen(bp), parts, bp))
    scored.sort(key=lambda x: -x[0])
    print(f'k{k}: screen top gaps {[s[0] for s in scored[:6]]} of {len(scored)} '
          f'({time.time() - t0:.0f}s)', flush=True)
    best = None
    for g, parts, bp in scored[:a.keep]:
        c0 = top_down(bp, seed=a.seed, trials=24, verbose=False, time_limit=a.seconds)
        if c0 is None:
            print(f'   gap {g}: no top-down state ({time.time() - t0:.0f}s)', flush=True)
            continue
        bp.best = c0
        c1 = local_search(bp, c0, seconds=a.seconds, seed=a.seed + 3, verbose=False)
        sc = sum(map(len, c1))
        print(f'   gap {g}: {sum(map(len, c0))} -> LS {sc} cuts ({(NDIM - sc) // 2} products, '
              f'{time.time() - t0:.0f}s)', flush=True)
        if best is None or sc > best[0]:
            best = (sc, c1, parts)
    out = {'k': k, 'products': None}
    if best:
        sc, cuts, parts = best
        F = solve_padding(physical_cuts(parts, cuts), target[76])
        out = {'k': k, 'sum_cuts': sc, 'products': (NDIM - sc) // 2, 'parts': parts, 'rows': IDENT,
               'cuts': [[int(c) for c in blk] for blk in cuts], 'F': int(F) if F is not None else None,
               'padding_ok': F is not None}
        print(f'k{k}: BEST {sc} cuts {((NDIM - sc) // 2)} products -> T {(NDIM - sc) // 2 + 75} '
              f'(shipped {SHIPPED[k]}) padding {"ok" if F is not None else "UNSOLVABLE"}', flush=True)
    (HERE / f'screen_plan_k{k}_{a.seed}.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
