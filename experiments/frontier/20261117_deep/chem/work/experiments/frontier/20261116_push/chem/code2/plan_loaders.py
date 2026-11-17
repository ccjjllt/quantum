"""Run the shipped block-cut planner on the shipped (marculera) word table.

For loader k the plan is a set of block-local annihilators of the 75 determined
high slices of delta = w_k XOR w_{k-1}; with a perfect matroid-parity pairing
the loader needs (525 - sum_cuts)/2 products, and the emitter price is
    T_k = #products with a nonzero high support + 69 (high cache) + 6 (low cache).
188 products (= 149 cuts) is the floor of this family.

Everything here is classical GF(2) algebra on the table; no circuit is built.
"""
import sys, json, random, time, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from parity_recover import NOUT, basis, reduce  # noqa: E402
from planner import (BlockPlan, complete_words, cross_tensor, NDIM, descend_smart,  # noqa: E402
                     top_down, local_search, rank_climb, physical_cuts, solve_padding, candidates)
from transport_cuts import coordinate_basis, coordinates  # noqa: E402

M35 = (1 << NOUT) - 1
BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
RELS = {'lsb0': 1 << 0, 'lsb1': 1 << 7, 'lsb2': 1 << 14, 'lsb3': 1 << 21, 'lsb4': 1 << 28,
        'xor_b1': sum(1 << (7 * z + 1) for z in range(5)),
        'xor_b2': sum(1 << (7 * z + 2) for z in range(5))}
NLM = [3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15]
CUB = [7, 11, 13, 14, 15]
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


def load():
    z = np.load(BUILD / 'submission.npz', allow_pickle=False)
    return np.asarray(z['angle_words'], np.int64), complete_words(np.asarray(z['angle_words'], np.uint8))


def valid_rels(target):
    """Rels that really annihilate this loader's target on h=1..75."""
    out = []
    for name, rel in RELS.items():
        ok = all(bin((((x >> (NOUT * (m - 1))) & M35) & rel)).count('1') % 2 == 0
                 for m in range(1, 16) for x in target[1:76])
        if ok:
            out.append(rel)
    return out


def partitions(rng, n_random=0, base=None):
    """Coordinate partition plus random 3+3+3+3+3 splits that keep the linear forms apart."""
    out = [base or [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]]
    LIN = [0, 1, 3, 7]
    NL = [m for m in range(15) if m not in LIN]
    for _ in range(n_random):
        nl = NL[:]; rng.shuffle(nl)
        out.append([[LIN[i], nl[2 * i], nl[2 * i + 1]] for i in range(4)] + [nl[8:11]])
        nl = NL[:]; rng.shuffle(nl)
        out.append([nl[3 * i:3 * i + 3] for i in range(4)] + [[LIN[0], LIN[1], LIN[2]]])
    return out


def try_plan(target, parts, rels, seed, time_limit, verbose=False):
    bp = BlockPlan(target, parts, rels, per_coord=True, hmax=76)
    t0 = time.time()
    path = descend_smart(bp, seed=seed, per_block=8, extra_random=4, time_limit=time_limit, verbose=False)
    best = None
    for c, (R, d, r) in sorted(path.items(), reverse=True):
        if d % 2 or r < d:
            continue
        cuts = [list(bp.F[i]) + list(R[i]) for i in range(5)]
        phys = physical_cuts(parts, cuts)
        F = solve_padding(phys, target[76])
        if F is None:
            continue
        best = {'sum_cuts': c, 'd': d, 'products': d // 2, 'parts': parts, 'cuts': cuts,
                'F': int(F) if F is not None else None, 'seconds': round(time.time() - t0, 1)}
        break
    return best, path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ks')
    ap.add_argument('--seconds', type=float, default=120)
    ap.add_argument('--seeds', default='7')
    ap.add_argument('--random-parts', type=int, default=0)
    ap.add_argument('--out', default='plan_search.json')
    args = ap.parse_args()
    words, Wc = load()
    rng = random.Random(5)
    res = {}
    for k in [int(x) for x in args.ks.split(',')]:
        target = cross_tensor(Wc, k)
        rels = valid_rels(target)
        print(f'k{k}: valid rels {len(rels)} shipped {SHIPPED[k]} ({SHIPPED[k] - 75} products, '
              f'{525 - 2 * (SHIPPED[k] - 75)} cuts)', flush=True)
        best = None
        for pi, parts in enumerate(partitions(rng, args.random_parts)):
            for seed in [int(x) for x in args.seeds.split(',')]:
                t0 = time.time()
                got, path = try_plan(target, parts, rels, seed, args.seconds)
                top = max((c for c, (R, d, r) in path.items() if r >= d and d % 2 == 0), default=None)
                print(f'   parts{pi} seed{seed}: path max cuts {max(path)} '
                      f'perfect-best {top} -> {None if got is None else got["products"]} products '
                      f'({time.time() - t0:.0f}s)', flush=True)
                if got and (best is None or got['sum_cuts'] > best['sum_cuts']):
                    best = got
        res[k] = best
        if best:
            print(f'k{k}: BEST cuts {best["sum_cuts"]} products {best["products"]} '
                  f'(shipped {SHIPPED[k] - 75})', flush=True)
        (HERE / args.out).write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
