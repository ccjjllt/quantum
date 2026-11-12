"""Step 2: is the group *partition* the binding structure?  Free regrouping, same words, same T/Q.

The 1144 rows are distinct, so the group assignment is a partition of them into 8 groups of 143.
Regrouping permutes rows only: same directions, same 8-bit words (row order), same T/Q.  For each
candidate partition: block-optimal rank-44 init inside each group's span, then the exact
augmented-Lagrangian refit of (w, W).  Also prints the partition's residual decomposition
(off-block mass and block rank-C tails), which bounds the best error that partition can reach.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_lib as g  # noqa: E402

ART = g.ART


def contiguous(R, B):
    return [np.arange(r * B, (r + 1) * B) for r in range(R)]


def cooc_partition(sp, R, B, seed=0):
    """Balanced partition maximising the within-block mass of max(Q0, 0)."""
    Wgt = np.maximum(sp.Q0, 0.0)
    np.fill_diagonal(Wgt, 0.0)
    d = Wgt.sum(axis=1)
    L = np.diag(d) - Wgt
    ev, V = np.linalg.eigh(L)
    F = V[:, :R - 1]
    rng = np.random.default_rng(seed)
    cent = F[rng.choice(len(F), R, replace=False)]
    for _ in range(40):
        lab = np.argmin(((F[:, None, :] - cent[None, :, :]) ** 2).sum(-1), axis=1)
        for r in range(R):
            if np.any(lab == r):
                cent[r] = F[lab == r].mean(axis=0)
    blocks = [list(np.where(lab == r)[0]) for r in range(R)]
    while True:
        big = max(range(R), key=lambda r: len(blocks[r]))
        if len(blocks[big]) <= B:
            break
        small = min(range(R), key=lambda r: len(blocks[r]))
        v = min(blocks[big], key=lambda b: Wgt[b, blocks[big]].sum())
        blocks[big].remove(v)
        blocks[small].append(v)
    # pairwise-swap local search: the gain of swapping a in r with b in s separates as u[a]+v[b]
    for _ in range(20):
        moved = 0
        for r in range(R):
            for s in range(r + 1, R):
                br, bs = np.asarray(blocks[r]), np.asarray(blocks[s])
                rr, rs = Wgt[np.ix_(br, br)].sum(1), Wgt[np.ix_(br, bs)].sum(1)
                sr, ss = Wgt[np.ix_(bs, br)].sum(1), Wgt[np.ix_(bs, bs)].sum(1)
                u = rs - rr                         # gain for the r-member
                v = sr - ss                         # gain for the s-member
                if u.max() + v.max() > 1e-12:
                    a = br[int(np.argmax(u))]
                    b = bs[int(np.argmax(v))]
                    blocks[r].remove(int(a))
                    blocks[s].remove(int(b))
                    blocks[r].append(int(b))
                    blocks[s].append(int(a))
                    moved += 1
        if not moved:
            break
    return np.concatenate([np.asarray(b) for b in blocks])


def decompose(sp, blocks, C):
    """(off-block mass^2, sum of block rank-C tails^2) in the p-coordinate Q0 metric."""
    off = sp.Q0.copy()
    tail = 0.0
    for b in blocks:
        sub = sp.Q0[np.ix_(b, b)]
        off[np.ix_(b, b)] = 0.0
        ev = np.linalg.eigvalsh(sub)[::-1]
        tail += float(np.sum(ev[C:] ** 2))
    return float(np.linalg.norm(off) ** 2), tail


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    sp = g.Space(data['U'], inp)
    R, B, C = sp.R, sp.B, sp.C
    w0 = data['W']
    base = g.rw.official(data, 8)
    print('baseline lambda_eff %.4f at error_2 %.4f mHa (continuous floor %.3f)'
          % (base['lambda_eff'], 1e3 * base['error_2'], 1e3 * sp.error2(w0)), flush=True)
    print('outside span %.3f mHa ; |Q0| %.3f' % (1e3 * np.sqrt(sp.outside2), np.linalg.norm(sp.Q0)), flush=True)

    rng = np.random.default_rng(7)
    cands = {'current': np.arange(R * B)}
    for k in range(3):
        cands[f'random{k}'] = rng.permutation(R * B)
    t = time.time()
    cands['cooc'] = cooc_partition(sp, R, B)
    print('cooc partition built in %.0f s' % (time.time() - t), flush=True)

    rows = {}
    w_ref, W_ref = data['W'], data['H2_I'] - data['W'].sum(axis=1)
    for name, perm in cands.items():
        w = sp.block_init(perm, contiguous(R, B))
        e2_init = sp.error2(w, perm)
        W = sp.init_W(w, perm, w_ref, W_ref)
        res = sp.refit(w, W, perm=perm, target_mha=19.999, outer=8, inner=150,
                       log=lambda *a: None)
        ww, WW, e2, gap, Lam, lam = res
        rows[name] = dict(e2_init=1e3 * e2_init, e2=1e3 * e2, gap=gap, Lam=Lam, lam_eff=lam)
        print('   block-init e2 %.3f -> refit e2 %.3f mHa  E_gap %.5f  Lambda %.3f  lambda_eff %.4f'
              % (1e3 * e2_init, 1e3 * e2, gap, Lam, lam), flush=True)
        np.savez(ART / f'part_{name}.npz', perm=perm, W=ww, H2_I=WW + ww.sum(axis=1))
        with open(ART / 'step2.json', 'w') as f:
            json.dump(rows, f, indent=1)


if __name__ == '__main__':
    main()
