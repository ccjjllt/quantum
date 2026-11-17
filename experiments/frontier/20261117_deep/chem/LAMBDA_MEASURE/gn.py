"""Gauss-Newton coordinate sweeps on the weights w (exact full-space Gram objective).

For one column y = P w the exact GN normal equations are

    (||y||^2 P^T P + (P^T y)(P^T y)^T) dw = -2 P^T (Y Y^T - H) y

(B x B, one `H @ y` per column), followed by a backtracking line search on the
true quartic objective. This is the standard factor-analysis GN and is far faster
than L-BFGS on this landscape (the residual is a ~2600x cancellation).
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

N = F.N


def unpack(x, R, B, C):
    nw = R * B * C
    w = x[:nw].reshape(R, B, C).copy()
    U = x[nw:].reshape(R, B, N).copy()
    U = U / np.linalg.norm(U, axis=2, keepdims=True)
    return w, U


def pack(w, U):
    return np.concatenate([w.ravel(), U.ravel()])


def fval(pb, Y, ):
    return float(np.sum((Y.T @ Y) ** 2)) - 2.0 * float(np.sum(Y * (pb.H @ Y))) + pb.Hfro2


def gn_w(pb, x, R, B, C, sweeps=2, damp=1e-8, verbose=True, wall=None):
    w, U = unpack(x, R, B, C)
    Ps = [pb.proj(U[r]) for r in range(R)]
    G = [Ps[r].T @ Ps[r] for r in range(R)]
    Y = np.zeros((pb.NS, R * C))
    for r in range(R):
        Y[:, r * C:(r + 1) * C] = Ps[r] @ w[r]
    t0 = time.time()
    for sw in range(sweeps):
        n_acc = 0
        for r in range(R):
            P, Gg = Ps[r], G[r]
            for c in range(C):
                i = r * C + c
                y = Y[:, i]
                yy = float(y @ y)
                Pt_y = P.T @ y
                Ry = Y @ (Y.T @ y) - pb.H @ y
                A = yy * Gg + np.outer(Pt_y, Pt_y) + damp * np.eye(B)
                b = -2.0 * (P.T @ Ry)
                try:
                    dw = np.linalg.solve(A, b)
                except np.linalg.LinAlgError:
                    continue
                f0 = fval(pb, Y)
                t = 1.0
                ok = False
                for _ in range(12):
                    wn = w[r, :, c] + t * dw
                    yn = P @ wn
                    Y[:, i] = yn
                    f1 = fval(pb, Y)
                    if f1 < f0:
                        w[r, :, c] = wn
                        ok = True
                        break
                    t *= 0.5
                if not ok:
                    Y[:, i] = y
                else:
                    n_acc += 1
        e = 1e3 * np.sqrt(max(fval(pb, Y), 0.0))
        if verbose:
            F.log(f'    gn_w sweep {sw}: {e:.3f} mHa  ({n_acc}/{R*C} steps accepted, '
                  f'{time.time()-t0:.0f}s)')
        if wall and time.time() - t0 > wall:
            break
    return pack(w, U)


if __name__ == '__main__':
    name = sys.argv[1]
    sweeps = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    z = np.load(I.CACHE / f'{name}.npz')
    R, B, C = int(z['R']), int(z['B']), int(z['C'])
    x = z['x']
    pb = F.Problem()
    F.log(f'{name} ({R},{B},{C}) start {pb.e2_reduced(x, R, B, C):.3f} mHa '
          f'(floor {pb.floor(R*C):.3f})')
    x = gn_w(pb, x, R, B, C, sweeps=sweeps)
    F.log(f'{name}: FINAL {pb.e2_reduced(x, R, B, C):.3f} mHa')
    np.savez_compressed(I.CACHE / f'{name}_gn.npz', x=x, R=R, B=B, C=C)
