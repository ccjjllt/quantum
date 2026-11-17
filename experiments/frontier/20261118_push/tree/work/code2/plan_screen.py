"""How far is the shipped table from a perfect 149-cut plan, per loader?

Screens partitions by the saturation gap (span - dim) of the full annihilator,
which the shipped planner uses as its feasibility signal, then reports the
best perfect-pairing cut count reached by the shipped search on the best
partitions.
"""
import sys, json, random, time, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from parity_recover import NOUT, basis  # noqa: E402
from planner import (BlockPlan, complete_words, cross_tensor, NDIM, descend_smart,  # noqa: E402
                     top_down, local_search, physical_cuts, solve_padding, candidates)
from parity_recover import alternating_field, gf_rank  # noqa: E402

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
    """The code relations that annihilate this loader on h=1..75 at every
    nonlinear low monomial (the set the shipped planner uses; the cubic-only
    xor_b2 relation is left to the cut search, since forced() applies one rel
    set to every nonlinear monomial of a block)."""
    def holds(rel, masks):
        return all(bin((((x >> (NOUT * (m - 1))) & M35) & rel)).count('1') % 2 == 0
                   for m in masks for x in target[1:76])
    out = []
    for name in ('lsb0', 'lsb1', 'lsb2', 'lsb3', 'lsb4', 'xor_b1'):
        if holds(RELS[name], NLM):
            out.append(RELS[name])
    return out


def partitions(rng, n, style):
    LIN = [0, 1, 3, 7]
    NL = [m for m in range(15) if m not in LIN]
    out = [[[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]]
    for _ in range(n):
        nl = NL[:]; rng.shuffle(nl)
        if style == 'mix':
            out.append([[LIN[i], nl[2 * i], nl[2 * i + 1]] for i in range(4)] + [nl[8:11]])
        elif style == 'pure':
            out.append([nl[3 * i:3 * i + 3] for i in range(4)] + [[LIN[0], LIN[1], LIN[2]]])
        else:
            rng.shuffle(nl)
            allv = LIN + nl
            out.append([allv[3 * i:3 * i + 3] for i in range(5)])
    return out


def screen(bp, rng):
    """Saturation gap: span of the pair columns at the full annihilator."""
    full = [list(basis(f).values()) for f in bp.full]
    pairs, _ = candidates({'parts': bp.parts, 'cuts': full}, full)
    sp = len(basis([x for p in pairs for x in p[:2]]))
    d = NDIM - sum(map(len, full))
    return sp - d


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('ks')
    ap.add_argument('--parts', type=int, default=8)
    ap.add_argument('--seconds', type=float, default=180)
    ap.add_argument('--style', default='mix')
    ap.add_argument('--out', default='plan_screen.json')
    a = ap.parse_args()
    words, Wc = load()
    rng = random.Random(5)
    res = {}
    for k in [int(x) for x in a.ks.split(',')]:
        t0 = time.time()
        target = cross_tensor(Wc, k)
        rels = valid_rels(target)
        print(f'k{k}: rels {len(rels)} shipped {SHIPPED[k]} = {SHIPPED[k] - 75} products '
              f'({525 - 2 * (SHIPPED[k] - 75)} cuts of 149)', flush=True)
        plist = partitions(rng, a.parts, a.style)
        scored = []
        for pi, parts in enumerate(plist):
            bp = BlockPlan(target, parts, rels, per_coord=True, hmax=76)
            g = screen(bp, rng)
            scored.append((g, pi, parts, bp))
            print(f'   parts{pi}: F {[len(f) for f in bp.F]} full {[len(f) for f in bp.full]} '
                  f'gap {g} ({time.time() - t0:.0f}s)', flush=True)
        scored.sort(key=lambda x: -x[0])
        best = None
        for g, pi, parts, bp in scored[:2]:
            for mode in ('top_down', 'descend'):
                if mode == 'top_down':
                    c0 = top_down(bp, seed=7, trials=30, verbose=False, time_limit=a.seconds / 4)
                else:
                    path = descend_smart(bp, seed=7, per_block=8, extra_random=4,
                                         time_limit=a.seconds / 4, verbose=False)
                    c0 = None
                    for c, (R, d, r) in sorted(path.items(), reverse=True):
                        if d % 2 == 0 and r >= d:
                            c0 = [list(bp.F[i]) + list(R[i]) for i in range(5)]
                            break
                if c0 is None:
                    print(f'   parts{pi} {mode}: no perfect state', flush=True)
                    continue
                bp.best = c0
                c1 = local_search(bp, c0, seconds=a.seconds / 4, seed=11, verbose=False)
                sc = sum(map(len, c1))
                print(f'   parts{pi} {mode}: {sum(map(len, c0))} -> LS {sc} cuts '
                      f'({(NDIM - sc) // 2} products) ({time.time() - t0:.0f}s)', flush=True)
                if best is None or sc > best[0]:
                    best = (sc, c1, parts)
        if best:
            sc, cuts, parts = best
            phys = physical_cuts(parts, cuts)
            F = solve_padding(phys, target[76])
            print(f'k{k}: BEST {sc} cuts {((NDIM - sc) // 2)} products, padding '
                  f'{"ok" if F is not None else "UNSOLVABLE"} ({time.time() - t0:.0f}s)', flush=True)
            res[k] = {'sum_cuts': sc, 'products': (NDIM - sc) // 2, 'parts': parts,
                      'cuts': cuts, 'F': int(F) if F is not None else None}
        else:
            res[k] = None
        (HERE / a.out).write_text(json.dumps(res, indent=1))
