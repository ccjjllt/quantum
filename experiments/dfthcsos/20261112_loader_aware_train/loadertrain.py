"""Loader-aware fine-tune of the dfthcsos table (numpy + scipy L-BFGS-B, analytic gradients).

Variables: the two-body Givens angles phi (R*B, N-1) in signed-gauge word units (w = round(phi))
and the weights w (R, B, C).  Loss = error_2^2 + lam * R, with

    R = mean over 16-address blocks and row pairs (a, a^8) of (s(phi_a) - s(phi_a'))^2 / 4,
    s(phi) = cos(pi * phi / 2**k)

which is zero exactly when bit k of the two quantized words agrees, i.e. when the mixed ANF
tensor loses every monomial containing the top low address bit and the product rank halves.
"""
from __future__ import annotations
import sys, json, time, argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import encode
import e2model
from dfthcsos.verify import load_inputs
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

NPZ = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT = 8


class Problem:
    def __init__(self, inp, lam: float, bit: int = 0, cols: int | None = None, verbose=True):
        self.inp = inp
        self.lam = lam
        self.bit = bit
        self.verbose = verbose
        self.T, self.M, self.i, self.j = e2model.target(inp)
        self.tree = np.asarray(inp.params['tree_edges'] if 'tree_edges' in inp.params else
                               np.load(NPZ)['tree_edges'], np.int64)
        self.R, self.B, self.N = np.asarray(inp.params['U']).shape
        self.C = np.asarray(inp.params['W']).shape[2]
        self.A = self.R * self.B
        w0 = np.asarray(inp.params['W'], np.float64)
        u0 = np.asarray(inp.params['U'], np.float64)
        u0 = u0 / np.linalg.norm(u0, axis=2, keepdims=True)
        self.phi0 = (encode.signed_angles(u0.reshape(-1, self.N), self.tree) * 128.0)
        self.w0 = w0
        self.cols = np.arange(self.N - 1) if cols is None else np.asarray(cols)
        # pair index list inside 16-blocks: a in [s, s+8), a2 = a+8
        # pair addresses a and a ^ 8 inside the loader's 16-address blocks; the two-body rows sit at
        # addresses N + r (N = 76 one-body rows), so the pairing is offset by N % 16.
        N = self.N
        pairs = []
        for s in range(0, N + self.A, 16):
            for lo in range(8):
                a, a2 = s + lo, s + lo + 8
                if a >= N and a2 < N + self.A:
                    pairs.append((a - N, a2 - N))
        self.pairs = np.array(pairs, np.int64)
        self.nR = 1.0
        # gather matrices for du
        P = len(self.i)
        self.M1 = np.zeros((P, self.N)); self.M2 = np.zeros((P, self.N))
        self.M1[np.arange(P), self.i] = 1.0
        self.M2[np.arange(P), self.j] = 1.0

    # ---- forward pieces
    def u_of(self, phi):
        return reconstruct_u_vectors(phi / 128.0, self.tree).reshape(self.R, self.B, self.N)

    def e2sq(self, U, w):
        u = U / np.linalg.norm(U, axis=2, keepdims=True)
        pairs = (u[:, :, self.i] * u[:, :, self.j]).reshape(self.R, self.B, -1)
        A = np.einsum('rbc,rbp->rcp', w, pairs).reshape(self.R * self.C, -1)
        H = A.T @ A - self.T
        return float(np.sum(self.M * H * H)), A, pairs, u

    def _lattice(self, phi):
        """Distance of every angle to the nearest word with bit k equal to parity p, p = 0/1."""
        q = 2 ** (self.bit + 1)
        out = []
        for p in (0, 1):
            base = np.floor((phi[:, self.cols] - p) / q + 0.5) * q + p
            out.append((phi[:, self.cols] - base, base))
        return out

    def reg(self, phi):
        a, b = self.pairs[:, 0], self.pairs[:, 1]
        (da, na), (db, nb) = self._lattice(phi)
        d0 = da[a] ** 2 + da[b] ** 2
        d1 = db[a] ** 2 + db[b] ** 2
        return float(np.sum(np.minimum(d0, d1)) / self.nR) if self.nR != 1.0 else float(np.sum(np.minimum(d0, d1)))

    def loss_grad(self, x):
        nphi = self.A * (self.N - 1)
        phi = x[:nphi].reshape(self.A, self.N - 1)
        w = x[nphi:].reshape(self.R, self.B, self.C)
        eq, A, pairs, u = self.e2sq(self.u_of(phi), w)
        H = A.T @ A - self.T
        dA = (4.0 * (A @ (self.M * H))).reshape(self.R, self.C, -1)
        dw = np.einsum('rcp,rbp->rbc', dA, pairs)
        dpairs = np.einsum('rcp,rbc->rbp', dA, w)
        # dpairs -> du
        uj = u[:, :, self.j]; ui = u[:, :, self.i]
        du = (dpairs * uj) @ self.M1 + (dpairs * ui) @ self.M2
        # du -> dU (normalisation)
        U = reconstruct_u_vectors(phi / 128.0, self.tree).reshape(self.R, self.B, self.N)
        nrm = np.linalg.norm(U, axis=2, keepdims=True)
        un = U / nrm
        dU = (du - un * np.sum(un * du, axis=2, keepdims=True)) / nrm
        # dU -> dphi through the Givens tree (backprop)
        dphi = self.backprop(dU.reshape(self.A, self.N), phi)
        # regulariser
        a, b = self.pairs[:, 0], self.pairs[:, 1]
        (da_, na), (db_, nb) = self._lattice(phi)
        d0 = da_[a] ** 2 + da_[b] ** 2
        d1 = db_[a] ** 2 + db_[b] ** 2
        R = float(np.sum(np.minimum(d0, d1)) / self.nR)
        gpa = np.where(d0 <= d1, da_[a], db_[a])
        gpb = np.where(d0 <= d1, da_[b], db_[b])
        dR = np.zeros_like(phi)
        for c_i, c in enumerate(self.cols):
            dR[a, c] += 2.0 * gpa[:, c_i] / self.nR
            dR[b, c] += 2.0 * gpb[:, c_i] / self.nR
        g = np.concatenate([(dphi + self.lam * dR).ravel(), dw.ravel()])
        return eq + self.lam * R, g, eq, R

    def backprop(self, dU, phi):
        """d/dphi of u = R_{T-1}...R_0 e_0, given dU = dloss/du."""
        T = len(self.tree)
        vecs = np.zeros((T + 1, self.A, self.N))
        vecs[0][:, 0] = 1.0
        for t, (p, q) in enumerate(self.tree):
            vp = vecs[t][:, p].copy(); vq = vecs[t][:, q].copy()
            th = np.pi * phi[:, t] / 128.0
            c, s = np.cos(th), np.sin(th)
            vecs[t + 1][:, p] = c * vp - s * vq
            vecs[t + 1][:, q] = s * vp + c * vq
        dphi = np.zeros((self.A, T))
        g = dU.copy()
        for t in range(T - 1, -1, -1):
            p, q = self.tree[t]
            th = np.pi * phi[:, t] / 128.0
            c, s = np.cos(th), np.sin(th)
            vp = vecs[t][:, p]; vq = vecs[t][:, q]
            new_p = vecs[t + 1][:, p]; new_q = vecs[t + 1][:, q]
            dphi[:, t] = (g[:, q] * new_p - g[:, p] * new_q) * (np.pi / 128.0)
            gp, gq = g[:, p].copy(), g[:, q].copy()
            g[:, p] = c * gp + s * gq
            g[:, q] = -s * gp + c * gq
        return dphi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lam', type=float, default=0.0)
    ap.add_argument('--bit', type=int, default=0)
    ap.add_argument('--iters', type=int, default=200)
    ap.add_argument('--cols', type=int, default=0, help='0 = all 75 rotations')
    ap.add_argument('--out', type=Path, default=None)
    a = ap.parse_args()
    inp = load_inputs(NPZ)
    cols = None if a.cols == 0 else range(a.cols)
    P = Problem(inp, a.lam, a.bit, cols)
    x0 = np.concatenate([P.phi0.ravel(), P.w0.ravel()])
    print(f'cols {len(P.cols)} pairs {len(P.pairs)} lam {a.lam} bit {a.bit}', flush=True)
    t0 = time.time()
    v, g, eq, R = P.loss_grad(x0)
    print(f'start e2 {1e3*np.sqrt(eq):.4f} mHa  R {R:.6f}  sec {time.time()-t0:.2f}', flush=True)
    hist = []

    def fun(x):
        v, g, eq, R = P.loss_grad(x)
        hist.append((1e3 * np.sqrt(eq), R))
        if len(hist) % 20 == 0:
            print(f'  it {len(hist)} e2 {1e3*np.sqrt(eq):.3f} mHa  R {R:.6f}  loss {v:.6g}  {time.time()-t0:.0f}s', flush=True)
        return v, g
    res = minimize(fun, x0, jac=True, method='L-BFGS-B',
                   options=dict(maxiter=a.iters, maxfun=2 * a.iters, maxcor=20, ftol=0, gtol=0))
    nphi = P.A * (P.N - 1)
    phi = res.x[:nphi].reshape(P.A, P.N - 1)
    w = res.x[nphi:].reshape(P.R, P.B, P.C)
    U = P.u_of(phi)
    eq = P.e2sq(U, w)[0]
    print(f'final e2 {1e3*np.sqrt(eq):.4f} mHa  R {P.reg(phi):.6f}  iters {res.nit}  {time.time()-t0:.0f}s', flush=True)
    out = a.out or (Path(__file__).resolve().parents[3] / 'artifacts/20261112_loader_aware_train' /
                    f'train_lam{a.lam:g}_bit{a.bit}_cols{a.cols}.npz')
    out.parent.mkdir(parents=True, exist_ok=True)
    words = np.mod(np.round(phi).astype(np.int64), 1 << BROT)
    np.savez(out, U=U, W=w, phi=phi, words=words, tree_edges=P.tree, lam=a.lam, bit=a.bit,
             cols=np.asarray(P.cols), hist=np.asarray(hist))
    print('WROTE', out, flush=True)


if __name__ == '__main__':
    main()
