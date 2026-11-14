"""Refit the weights w and offsets W at fixed words: spend the error budget on lambda_eff.

The circuits fix only the Givens words. The weights w (R, B, C) and the offsets W (R, C) are read
from submission.npz, so they can be refit after rounding: lower lambda_eff while keeping error_2
under a target just below the 20 mHa gate (idea: phucthaiv02, "QCC | Verified Portfolio + DF-THC
Retraining Study", Apache-2.0; this is our own implementation). Unlike a refit that keeps the
circuits byte-identical, the one-body rows are regenerated from the final h1' (as `refine.py`
does), so error_1 follows the new weights.

With the projectors P_b = u_b u_b^T fixed, error_2 is exact and cheap in w:

    error_2^2 = ||sum_rc X_rc (x) X_rc - T||^2 = sum_rr' ||w_r^T K_rr' w_r'||^2 - 2 sum_r tr(w_r^T Q_rr w_r) + ||T||^2

with K_bb' = (u_b . u_b')^2, Q_bb' = <P_b, T P_b'> and T = tei + (S (x) I + I (x) S) / 2, the
verifier's target. lambda_eff(w, W) is the verifier's formula (eigenvalues of h1'). The objective
is log lambda_eff plus quadratic penalties below the error target and the E_gap floor, minimized
with L-BFGS on exact gradients (numpy, float64), then polished with `refine.py`'s exact moves.

    python notebooks/dfthc-refit/refit_weights.py REFINED.npz OUT.npz [--target 19.92]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import encode  # noqa: E402  (puts the verifiers on sys.path)
from paths import SHIFTS, UPPER_ENERGY  # noqa: E402
from refine import GAP_FLOOR, Problem, assemble, official, optimize_offsets, rotate_columns  # noqa: E402
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference  # noqa: E402
from dfthcsos.verify import native_inputs  # noqa: E402



def error_terms(u: np.ndarray, tei: np.ndarray, S: np.ndarray):
    """K (R, B, R, B), Q (R, B, B) and ||T||^2 for fixed unit vectors u (R, B, N)."""
    R, B, N = u.shape
    flat = u.reshape(R * B, N)
    K = ((flat @ flat.T) ** 2).reshape(R, B, R, B)
    T = tei.reshape(N * N, N * N).copy()
    eye = np.eye(N).ravel()
    T += 0.5 * (np.outer(S.ravel(), eye) + np.outer(eye, S.ravel()))
    P = np.einsum('mp,mq->mpq', flat, flat).reshape(R * B, N * N)
    TP = T @ P.T                                         # (N^2, R B)
    Q = np.stack([P[r * B:(r + 1) * B] @ TP[:, r * B:(r + 1) * B] for r in range(R)])
    Q = 0.5 * (Q + Q.swapaxes(1, 2))  # same tr(w^T Q w); the gradient 2 Q w needs Q symmetric
    return K, Q, float(np.sum(T ** 2))


class WeightProblem:
    """error_2, E_gap and Lambda of (w, W) at fixed unit vectors u, with exact gradients (numpy).

    error_2^2 = F - 2 L + ||T||^2, F = sum_rs ||A_rs||^2 with A_rs = w_r^T K_rs w_s and
    L = sum_r tr(w_r^T Q_r w_r): dF/dw_r = 4 sum_s K_rs w_s A_rs^T, dL/dw_r = 2 Q_r w_r.
    With G = sign(h1') and c_rb = u_rb^T G u_rb, h1' depends on w and W through k_rb = sum_c W_rc w_rbc:
    d sum|l| / dk_rb = -c_rb and d sum l / dk_rb = -1.
    """

    def __init__(self, u, K, Q, T2, h1_base, energy):
        self.u, self.K, self.Q, self.T2, self.h1_base, self.energy = u, K, Q, T2, h1_base, energy

    def error_2(self, w):
        A = np.einsum('rbc,rbsd,sdk->rcsk', w, self.K, w, optimize=True)
        E = np.sum(A ** 2) - 2 * np.einsum('rbc,rbd,rdc->', w, self.Q, w, optimize=True) + self.T2
        return float(np.sqrt(max(E, 0.0))), A

    def evaluate(self, w, W):
        """(error_2, E_gap, Lambda) and their gradients in (w, W)."""
        e2, A = self.error_2(w)
        dF = 4 * np.einsum('rbsd,sdk,rcsk->rbc', self.K, w, A, optimize=True)
        de2 = (dF - 4 * np.einsum('rbd,rdc->rbc', self.Q, w)) / (2 * e2)
        k = np.einsum('rc,rbc->rb', W, w)
        lam_j, vec = np.linalg.eigh(self.h1_base - np.einsum('rb,rbp,rbq->pq', k, self.u, self.u, optimize=True))
        c = np.einsum('rbp,pq,rbq->rb', self.u, (vec * np.sign(lam_j)) @ vec.T, self.u, optimize=True)
        gap = self.energy + np.abs(lam_j).sum() - lam_j.sum() + 0.5 * np.sum(W ** 2)
        s, l1 = w.sum(axis=1), np.abs(w).sum(axis=1)
        m = l1 + np.abs(W + s)
        Lam = np.abs(lam_j).sum() + 0.25 * np.sum(m ** 2)
        sg = np.sign(W + s)
        dgap = ((1 - c)[:, :, None] * W[:, None, :], np.einsum('rb,rbc->rc', 1 - c, w) + W)
        dLam = (-c[:, :, None] * W[:, None, :] + 0.5 * m[:, None, :] * (np.sign(w) + sg[:, None, :]),
                -np.einsum('rb,rbc->rc', c, w) + 0.5 * m * sg)
        return (e2, float(gap), float(Lam)), (de2, dgap, dLam)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('refined', type=Path, help='refine.py output (angle_words, tree_edges, U, W, H2_I, ...)')
    ap.add_argument('out', type=Path)
    ap.add_argument('--target', type=float, default=19.92, help='error_2 kept below this (mHa)')
    ap.add_argument('--margin', type=float, default=0.002, help='E_gap kept this far above the floor (Ha)')
    ap.add_argument('--maxiter', type=int, default=3000)
    ap.add_argument('--rounds', type=int, default=3, help='rounds of refine.py moves after the refit')
    a = ap.parse_args()
    with np.load(a.refined) as z:
        data = {k: np.array(z[k]) for k in z.files}
    best, best_m = refit(data, a.target, a.margin, a.maxiter, a.rounds, log=lambda *x: print(*x, flush=True))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, **best, brot=int(data.get('brot', 10)))
    print('RESULT', json.dumps(best_m))
    print('saved', a.out)


def refit(data: dict, target_mha: float = 19.92, margin: float = 0.002, maxiter: int = 3000, rounds: int = 3,
          log=print) -> tuple[dict, dict]:
    """Refit w and W of a refined factorization (refine.py output) at fixed words.

    Returns the best factorization (one-body rows regenerated) and its official metrics; the input
    itself when nothing better fits under the error target.
    """
    brot = int(data.get('brot', 10))
    edges = np.asarray(data['tree_edges'], np.int64)
    w0 = np.asarray(data['W'], np.float64)
    W0 = np.asarray(data['H2_I'], np.float64) - w0.sum(axis=1)
    R, B, C = w0.shape
    N = edges.shape[0] + 1
    words2 = np.asarray(data['angle_words'], np.int64)[N:]
    coded = [int(c) for c in data['coded']] if 'coded' in data else []   # coded word columns (quantize.py --coded)
    coded2 = [int(c) for c in data['coded2']] if 'coded2' in data else []
    u = encode.decode(words2, edges, brot).reshape(R, B, N)
    u /= np.linalg.norm(u, axis=2, keepdims=True)

    ref = load_reference(check_fcidump())
    with np.load(SHIFTS) as z:
        _, _, S, beta = native_inputs({'U': u, 'W': w0, 'H2_I': data['H2_I'], 'H1_I': z['H1_I'],
                                       'Hsym_lower': z['Hsym_lower']})
    K, Q, T2 = error_terms(u, np.asarray(ref['tei'], np.float64), S)
    start = official(data, brot)

    eta = int(ref['electrons'])
    wp = WeightProblem(u, K, Q, T2, ref['h1_thc'] - 0.5 * eta * S + beta * np.eye(N),
                       float(UPPER_ENERGY - ref['ecore'] + eta * beta))
    target, floor = 1e-3 * target_mha, GAP_FLOOR + margin
    e2_start = wp.error_2(w0)[0]
    log(f"start: official error_2 {1e3 * start['error_2']:.4f} mHa, this formula {1e3 * e2_start:.4f}; "
        f"lambda_eff {start['lambda_eff']:.4f}")
    assert abs(e2_start - start['error_2']) < 1e-7, 'the error_2 formula does not match the verifier'

    def objective(x):
        """log lambda_eff plus quadratic penalties above the error target and below the gap floor."""
        w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
        (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
        rad = gap * (2 * Lam - gap)
        if rad <= 0:  # outside the verifier's domain: reject the line-search step
            return 1e12, np.zeros_like(x)
        f = 0.5 * np.log(rad)
        gw, gW = [((Lam - gap) * g + gap * l) / rad for g, l in zip(dgap, dLam)]
        if e2 > target:
            f += 1e6 * (e2 - target) ** 2
            gw = gw + 2e6 * (e2 - target) * de2
        if gap < floor:
            f += 1e5 * (floor - gap) ** 2
            gw, gW = gw - 2e5 * (floor - gap) * dgap[0], gW - 2e5 * (floor - gap) * dgap[1]
        return f, np.concatenate([gw.ravel(), gW.ravel()])

    # w is ~1e-4 and W ~1: optimize in units of each one's spread, or L-BFGS stalls.
    scale = np.concatenate([np.full(w0.size, np.std(w0)), np.full(W0.size, np.std(W0))])

    def scaled(y):
        f, g = objective(y * scale)
        return f, g * scale

    x0 = np.concatenate([w0.ravel(), W0.ravel()]) / scale
    res = minimize(scaled, x0, jac=True, method='L-BFGS-B',
                   options={'maxiter': maxiter, 'maxcor': 30, 'ftol': 1e-15, 'gtol': 1e-10, 'maxls': 50})
    x = res.x * scale
    w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
    (e2, gap, Lam), _ = wp.evaluate(w, W)
    # It usually stops on the gap floor: the penalty there is a kink, where the line search ends
    # (scipy reports ABNORMAL). Say which constraint binds rather than the line-search status.
    why = ('E_gap on its floor' if gap < floor + 1e-3 else
           'error_2 on its target' if e2 > target - 1e-5 else res.message)
    log(f"L-BFGS stopped after {res.nit} iterations ({why}): error_2 {1e3 * e2:.4f} mHa, E_gap {gap:.4f}, "
        f"lambda_eff {np.sqrt(gap * (2 * Lam - gap)):.4f}")

    best, best_m = None, None
    for k in range(rounds):  # the exact moves of refine.py; they keep error_2 (w w^T is unchanged)
        w, W = rotate_columns(w, W, sweeps=2, seed=k)
        p = Problem(u, w, ref, S, beta)
        W = optimize_offsets(p, W, margin)
        cand = assemble(words2, w, W, p, edges, brot, one_start=np.asarray(data['angle_words'])[:N], coded=coded, coded2=coded2)
        m = official(cand, brot)
        log(f'moves {k}', json.dumps(m))
        ok = m['error_2'] <= target and m['error_1'] <= 0.0199 and m['E_gap'] > GAP_FLOOR
        if ok and (best_m is None or m['lambda_eff'] < best_m['lambda_eff']):
            best, best_m = cand, m
    if best_m is None or best_m['lambda_eff'] >= start['lambda_eff']:
        log('no improvement within the error target: the input is passed through unchanged')
        best, best_m = {k: v for k, v in data.items() if k != 'brot'}, start
    return best, best_m


if __name__ == '__main__':
    main()
