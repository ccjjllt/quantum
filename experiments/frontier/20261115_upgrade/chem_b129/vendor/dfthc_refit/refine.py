"""Refine the identity offsets W of a quantized DF-THC factorization to minimize lambda_eff.

The structure (two-body words, weights w) is fixed: it alone sets error_2. What remains is
lambda_eff = sqrt(E_gap (2 Lambda - E_gap)), which depends on the offsets W (R, C):

    h1'    = H1_base - sum_rb k_rb u_rb u_rb^T,  k_rb = sum_c W_rc w_rbc,
             H1_base = H1_THC - (eta/2) S + beta_1 I
    E_gap  = E_upper - ecore + eta beta_1 + (sum|l| - sum l) + 1/2 sum W^2   (l: eigenvalues of h1')
    Lambda = sum|l| + 1/4 sum_rc (sum_b |w_rbc| + |W_rc + sum_b w_rbc|)^2

With G = sign(h1') (from its eigenvectors), d sum|l| / dW_rc = -sum_b w_rbc u^T G u and
d sum l / dW_rc = -sum_b w_rbc, which gives exact gradients for L-BFGS.

Adapted from `chemistry_refine.py` (`sparsify_columns`, `optimize_effective_norm`) of the public
notebook ahmedberatozer/quantum-ai-df-thc-group-compression (Apache-2.0), which credits kozykappa's
sparse rotations and anazemcev's effective-norm method. Changes: restructured into `Problem`, a
second set of candidate rotation angles, full pair sweeps, and alternation with the offset solve.

Two moves alternate (the group-compression notebook's approach, reimplemented):
1. **Column rotations.** For each group, an orthogonal rotation of the copy columns of
   A = [w; w_B] keeps w w^T, w W^T and |W|^2, hence the two-body tensor, h1' and E_gap. It
   only changes the L1 term of Lambda, which pairwise rotations lower; for a pair, the optimum
   is checked among the angles where an entry crosses zero.
2. **Offsets.** L-BFGS on log lambda_eff with a quadratic penalty below E_gap floor + margin.

The one-body rows are then the eigenvectors of the final h1', encoded on the same tree.

    python notebooks/dfthc-refit/refine.py QUANTIZED.npz OUT.npz [--brot 10]

QUANTIZED.npz holds two-body `words` and weights `w` (quantize.py); with `--structure F`
instead, the continuous structure's vectors are just rounded (a preview at high brot).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import encode  # noqa: E402  (puts the verifiers on sys.path)
from paths import SHIFTS  # noqa: E402
from dfthcsos.scoreinfra.reference import UPPER_ENERGY, check_fcidump, load_reference  # noqa: E402
from dfthcsos.verify import evaluate_words, load_inputs, native_inputs  # noqa: E402

GAP_FLOOR = 3.914898
LAMBDA_FLOOR = 49.0


class Problem:
    """h1', E_gap and Lambda as functions of the offsets, for fixed vectors u and weights w."""

    def __init__(self, u: np.ndarray, w: np.ndarray, ref: dict, S: np.ndarray, beta: float):
        self.u, self.w = u, w
        n = u.shape[-1]
        eta = int(ref['electrons'])
        self.h1_base = ref['h1_thc'] - 0.5 * eta * S + beta * np.eye(n)
        self.energy = UPPER_ENERGY - ref['ecore'] + eta * beta
        self.sum_w = w.sum(axis=1)
        self.l1_w = np.abs(w).sum(axis=1)
        self.trace_x = self.sum_w  # tr X_rc = sum_b w_rbc for unit u

    def h1(self, W: np.ndarray) -> np.ndarray:
        k = np.einsum('rc,rbc->rb', W, self.w)
        return self.h1_base - np.einsum('rb,rbp,rbq->pq', k, self.u, self.u, optimize=True)

    def evaluate(self, W: np.ndarray):
        values, vectors = np.linalg.eigh(self.h1(W))
        sign_h1 = (vectors * np.sign(values)) @ vectors.T
        c = np.einsum('rbp,pq,rbq->rb', self.u, sign_h1, self.u, optimize=True)  # u^T G u
        gap = self.energy + np.abs(values).sum() - values.sum() + 0.5 * np.sum(W ** 2)
        w_B = W + self.sum_w
        lam = np.abs(values).sum() + 0.25 * np.sum((self.l1_w + np.abs(w_B)) ** 2)
        d_abs = -np.einsum('rb,rbc->rc', c, self.w)
        grad_gap = d_abs + self.trace_x + W
        grad_lam = d_abs + 0.5 * (self.l1_w + np.abs(w_B)) * np.sign(w_B)
        return float(gap), float(lam), grad_gap, grad_lam


def optimize_offsets(p: Problem, W: np.ndarray, margin: float, maxiter: int = 400) -> np.ndarray:
    floor = GAP_FLOOR + margin
    shape = W.shape

    def objective(x):
        gap, lam, g_gap, g_lam = p.evaluate(x.reshape(shape))
        radicand = gap * (2.0 * lam - gap)
        if radicand <= 0:
            return 1e12, np.zeros_like(x)
        f = 0.5 * math.log(radicand)
        g = ((lam - gap) * g_gap + gap * g_lam) / radicand
        if gap < floor:  # quadratic penalty: tight enough that the optimum sits at the floor
            f += 1e5 * (floor - gap) ** 2
            g = g - 2e5 * (floor - gap) * g_gap
        if lam < LAMBDA_FLOOR + 0.01:
            f += 1e5 * (LAMBDA_FLOOR + 0.01 - lam) ** 2
            g = g - 2e5 * (LAMBDA_FLOOR + 0.01 - lam) * g_lam
        return f, g.ravel()

    res = minimize(objective, W.ravel(), jac=True, method='L-BFGS-B',
                   options={'maxiter': maxiter, 'maxcor': 20, 'ftol': 1e-14, 'gtol': 1e-9, 'maxls': 50})
    return res.x.reshape(shape)


def _l1sq(Y: np.ndarray) -> float:
    return float(np.sum(np.abs(Y).sum(axis=0) ** 2))


def _gauge_descent(A: np.ndarray, Q: np.ndarray, delta: float, iters: int = 400) -> np.ndarray:
    """Riemannian gradient descent on O(C) for sum_c ||(A Q)_c||_1^2, with |x| smoothed as
    sqrt(x^2 + delta^2): a Cayley retraction along the skew gradient, with backtracking."""
    eye = np.eye(Q.shape[0])

    def f(Q):
        Y = A @ Q
        s = np.sqrt(Y ** 2 + delta ** 2)
        n = s.sum(axis=0)
        return float(np.sum(n ** 2)), Y, s, n

    fv, Y, s, n = f(Q)
    tau = 1e-2
    for _ in range(iters):
        G = A.T @ (2 * n[None, :] * Y / s)
        Om = G @ Q.T - Q @ G.T
        gn = np.linalg.norm(Om)
        if gn < 1e-12:
            break
        while tau > 1e-12:
            Qn = np.linalg.solve(eye + 0.5 * tau * Om, eye - 0.5 * tau * Om) @ Q
            fn, Yn, sn, nn = f(Qn)
            if fn < fv - 1e-4 * tau * gn ** 2:
                Q, fv, Y, s, n = Qn, fn, Yn, sn, nn
                tau *= 2
                break
            tau *= 0.5
        else:
            break
    return Q


def gauge(A: np.ndarray, hops: int, rng) -> np.ndarray:
    """A better orthogonal gauge of one group's copy columns: smoothed descent from the current gauge,
    then small random rotations (basin hopping) kept only when they lower sum_c ||a_c||_1^2.
    (A per-block orthogonal C-gauge lowering Lambda_2 is haideptry's idea, as used by phucthaiv02.)"""
    from scipy.linalg import expm
    C = A.shape[1]
    scale = np.abs(A).mean()

    def descend(Q):
        for d in (1e-2, 1e-3, 1e-4):
            Q = _gauge_descent(A, Q, d * scale)
        return Q

    best_Q = descend(np.eye(C))
    best = _l1sq(A @ best_Q)
    for _ in range(hops):
        S = rng.normal(size=(C, C)) * 0.3 / np.sqrt(C)
        Q = descend(expm(S - S.T) @ best_Q)
        if _l1sq(A @ Q) < best:
            best_Q, best = Q, _l1sq(A @ Q)
    return A @ best_Q if best < _l1sq(A) else A


def rotate_columns(w: np.ndarray, W: np.ndarray, sweeps: int, seed: int, hops: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """Orthogonal rotations of each group's copy columns A_r = [w_r; w_B,r] lowering sum_c ||A_rc||_1^2
    (the L1 term of Lambda) while keeping A A^T: exact pair sweeps, then a smoothed descent on the
    orthogonal group with `hops` rounds of basin hopping (0 skips it)."""
    A = np.concatenate([w, (W + w.sum(axis=1))[:, None, :]], axis=1)  # (R, B+1, C)
    R, _, C = A.shape
    gram = A @ A.swapaxes(1, 2)
    rng = np.random.default_rng(seed)
    for _ in range(sweeps):
        for i, j in rng.permutation([(i, j) for i in range(C) for j in range(i + 1, C)]):
            x, y = A[:, :, i], A[:, :, j]
            # Zero crossings of cos x + sin y and of cos y - sin x, folded into [0, pi/2).
            cand = np.concatenate([np.arctan2(-x, y), np.arctan2(y, x)], axis=1) % (np.pi / 2)
            cand = np.concatenate([np.zeros((R, 1)), cand], axis=1)
            co, si = np.cos(cand)[:, :, None], np.sin(cand)[:, :, None]
            f = (np.abs(co * x[:, None] + si * y[:, None]).sum(axis=2) ** 2
                 + np.abs(co * y[:, None] - si * x[:, None]).sum(axis=2) ** 2)
            best = cand[np.arange(R), np.argmin(f, axis=1)]
            co, si = np.cos(best)[:, None], np.sin(best)[:, None]
            A[:, :, i], A[:, :, j] = co * x + si * y, co * y - si * x
    if hops:
        A = np.stack([gauge(A[r], hops, rng) for r in range(R)])
    drift = np.max(np.abs(A @ A.swapaxes(1, 2) - gram))
    assert drift < 1e-9, f'column rotations changed A A^T by {drift}'
    w_new = A[:, :-1]
    return w_new, A[:, -1] - w_new.sum(axis=1)


def assemble(words2, w, W, p: Problem, edges, brot, one_start=None, coded=(), coded2=()) -> dict:
    """Factorization arrays plus the full word table (one-body rows from the final h1'). With `coded`
    word columns (quantize.py --coded), the one-body rows keep their bit 0 affine per address block."""
    if brot <= 9 or len(coded):  # rounded eigenvectors miss the 20 mHa error_1 gate at 8 bits: polish the words
        import onebody
        one = onebody.refresh(p.h1(W), edges, brot, start=one_start, kicks=10, coded=coded, coded2=coded2,
                              following=words2[:16] if len(coded) else None)
    else:
        _, vecs = np.linalg.eigh(p.h1(W))
        one = encode.signed_words(vecs.T, edges, brot)  # signed gauge, like the two-body rows
    R, B, N = p.u.shape
    with np.load(SHIFTS) as z:
        shifts = {k: np.array(z[k]) for k in ('H1_I', 'Hsym_lower')}
    return {'U': p.u, 'W': w, 'H2_I': W + w.sum(axis=1), **shifts, 'tree_edges': edges,
            'angle_words': np.vstack([one, words2]), 'coded': np.asarray(coded, np.int64),
            'coded2': np.asarray(coded2, np.int64)}


def official(data: dict, brot: int) -> dict:
    inputs = load_inputs({k: data[k] for k in ('U', 'W', 'H2_I', 'H1_I', 'Hsym_lower')})
    m = evaluate_words(inputs, data['angle_words'], data['tree_edges'], brot)
    return {k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}


def refine(words2: np.ndarray, w: np.ndarray, brot: int = 10, rounds: int = 3, margin: float = 0.002,
           maxiter: int = 3000, log=print, coded=(), coded2=()) -> tuple[dict, dict]:
    """Offsets for fixed two-body words and weights: alternate column rotations and L-BFGS on lambda_eff.

    Returns the best factorization (with the full word table, one-body rows from the final h1') and
    its official metrics.
    """
    edges = encode.log_depth_tree()
    R, B, C = w.shape
    N = edges.shape[0] + 1
    u = encode.decode(words2, edges, brot).reshape(R, B, N)
    ref = load_reference(check_fcidump())
    with np.load(SHIFTS) as z:
        _, _, S, beta = native_inputs({'U': u, 'W': w, 'H2_I': w.sum(axis=1), 'H1_I': z['H1_I'],
                                       'Hsym_lower': z['Hsym_lower']})
    p = Problem(u, w, ref, S, beta)
    W = -p.sum_w  # zero offsets on the identity-shifted squares; it converges lower than a bisected start
    best = assemble(words2, w, W, p, edges, brot, coded=coded, coded2=coded2)
    best_m = official(best, brot)
    log('initial', json.dumps(best_m))
    for k in range(rounds):
        w, W = rotate_columns(w, W, sweeps=2, seed=k)
        p = Problem(u, w, ref, S, beta)
        W = optimize_offsets(p, W, margin, maxiter)
        cand = assemble(words2, w, W, p, edges, brot, coded=coded, coded2=coded2)
        m = official(cand, brot)
        log(f'round {k}', json.dumps(m))
        if m['E_gap'] > GAP_FLOOR and m['Lambda'] > LAMBDA_FLOOR and m['lambda_eff'] < best_m['lambda_eff']:
            best, best_m = cand, m
    return best, best_m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('quantized', type=Path, nargs='?', help='npz with two-body `words` and `w`')
    ap.add_argument('out', type=Path)
    ap.add_argument('--structure', type=Path, help='continuous U, W instead of quantized words (preview)')
    ap.add_argument('--brot', type=int, default=10)
    ap.add_argument('--margin', type=float, default=0.002, help='E_gap kept this far above the floor (Ha)')
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--maxiter', type=int, default=3000, help='L-BFGS iterations per round')
    a = ap.parse_args()
    if a.structure:
        with np.load(a.structure) as z:
            U, w = np.asarray(z['U'], np.float64), np.asarray(z['W'], np.float64)
        words2 = encode.to_words(encode.tree_angles(U.reshape(-1, U.shape[2]), encode.log_depth_tree()), a.brot)
        coded, coded2 = [], []
    else:
        with np.load(a.quantized) as z:
            words2, w = np.asarray(z['words'], np.int64), np.asarray(z['w'], np.float64)
            coded = [int(c) for c in z['coded']] if 'coded' in z.files else []
            coded2 = [int(c) for c in z['coded2']] if 'coded2' in z.files else []
    if coded:
        print(f'coded bit 0 in {len(coded)} word columns: kept affine per address block in the one-body rows too')
    best, best_m = refine(words2, w, a.brot, a.rounds, a.margin, a.maxiter, log=lambda *x: print(*x, flush=True),
                          coded=coded, coded2=coded2)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, **best, brot=a.brot)
    print('RESULT', json.dumps(best_m))
    print('saved', a.out)


if __name__ == '__main__':
    main()
