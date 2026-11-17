"""Structural accuracy limit: K-term rank-1-projector (THC) decomposition of H.

Every DF-THC column is  y_k = sum_b w_b p(u_b)  with  p(u) = vech(u u^T).
The B/C -> 1 limit is one projector per column:  y_k = s_k p(u_k), which is a
classical THC/rank-1 factorization of H. This script computes it constructively
(greedy matched filter, then coordinate-descent sweeps over all K terms), so the
number is *converged* and does not depend on any warm start:

    e2_thc(K) = || H - sum_{k<K} s_k^2 p_k p_k^T ||_F.

That is an upper bound for the best (R,B,C) fit with B/C >= 1, and it is the
honest "can this many columns reach the gate" question.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

T0 = time.time()


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


ps = I.cached_pair_space()
H, PA, sqw, NS = ps['H'], ps['PA'], ps['sqw'], ps['NS']
N = 76
P0, P1 = PA[:, 0], PA[:, 1]


def vech(X):
    return X[P0, P1] * sqw


def unvech(v):
    M = np.zeros((N, N))
    M[P0, P1] = v / sqw
    return np.triu(M) + np.triu(M, 1).T


def quartic(R, u):
    """g = p(u)^T R p(u) and its Euclidean gradient (4 R_sym u)."""
    pp = vech(np.outer(u, u))
    Rp = R @ pp
    g = float(pp @ Rp)
    G = unvech(Rp)
    return g, 4.0 * (G @ u), pp


def best_u(R, starts, iters=200):
    """Maximise p(u)^T R p(u) on the unit sphere (projected-gradient ascent)."""
    best = (-np.inf, None, None)
    for u0 in starts:
        u = u0 / np.linalg.norm(u0)
        g, grad, pp = quartic(R, u)
        step = 0.05
        for _ in range(iters):
            t = grad - (grad @ u) * u
            tn = np.linalg.norm(t)
            if tn < 1e-10:
                break
            u = u + step * t / tn
            u /= np.linalg.norm(u)
            g2, grad, pp = quartic(R, u)
            if g2 > g:
                g, step = g2, min(step * 1.3, 2.0)
            else:
                step *= 0.5
                if step < 1e-8:
                    break
        if g > best[0]:
            best = (g, u.copy(), pp.copy())
    return best


def run(K, sweeps=4, log_every=40):
    ev, evec = np.linalg.eigh(H)
    order = np.argsort(ev)[::-1]
    lam, vec = ev[order], evec[:, order]
    R = H.copy()
    us, gs, pps = [], [], []
    for k in range(K):
        starts = [unvech(vec[:, j])[:, 0] for j in range(k, min(k + 2, 6))]
        # unvech(...) gives a matrix whose first column is not an orbital; use top eigenvector
        starts = []
        for j in range(k, min(k + 3, 12)):
            M = unvech(vec[:, j])
            w_, v_ = np.linalg.eigh(M)
            starts.append(v_[:, -1])
        if us:
            starts.append(us[-1])
        g, u, pp = best_u(R, starts, iters=120)
        if not np.isfinite(g) or g <= 0:
            log(f'  k={k}: g={g} -> stop')
            break
        us.append(u)
        gs.append(g)
        pps.append(pp)
        R -= g * np.outer(pp, pp)
        if (k + 1) % log_every == 0:
            log(f'  greedy k={k+1}: e2 {1e3*np.linalg.norm(R):.3f} mHa '
                f'(floor {I.floor_mha(lam, k+1, float(np.sum(np.minimum(lam,0)**2))):.3f})')
    e2 = 1e3 * float(np.linalg.norm(R))
    log(f'greedy K={K}: e2 {e2:.3f} mHa')
    # coordinate-descent sweeps: re-optimise each (u_k, s_k) against the others
    for sw in range(sweeps):
        t = time.time()
        for k in range(len(us)):
            R = R + gs[k] * np.outer(pps[k], pps[k])
            starts = [us[k]]
            g, u, pp = best_u(R, starts, iters=80)
            if g <= 0:
                g, u, pp = 0.0, us[k], pps[k]
            us[k], gs[k], pps[k] = u, g, pp
            R -= g * np.outer(pp, pp)
        e2 = 1e3 * float(np.linalg.norm(R))
        log(f'  sweep {sw}: e2 {e2:.3f} mHa [{time.time()-t:.0f}s]')
    e2 = 1e3 * float(np.linalg.norm(R))
    log(f'FINAL K={K}: e2 {e2:.4f} mHa = {e2/I.floor_mha(lam, K, float(np.sum(np.minimum(lam,0)**2))):.2f}x floor')
    return dict(K=K, e2=e2, u=np.array(us), s=np.sqrt(np.array(gs)),
                floor=I.floor_mha(lam, K, float(np.sum(np.minimum(lam, 0) ** 2))))


if __name__ == '__main__':
    import json
    out = {}
    for K in [int(x) for x in (sys.argv[1:] or ['352', '480'])]:
        r = run(K)
        out[K] = dict(e2=r['e2'], floor=r['floor'], rho=r['e2'] / r['floor'])
        np.savez_compressed(I.CACHE / f'thc_{K}.npz', u=r['u'], s=r['s'], K=K)
    (I.CACHE / 'thc.json').write_text(json.dumps(out, indent=1))
    log(json.dumps(out))
