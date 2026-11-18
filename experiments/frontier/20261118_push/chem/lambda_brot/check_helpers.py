"""Local pure-arithmetic check of the helpers in analysis.py (no integrals, no simulation).

Only numpy on the shipped (1220, 75) word table and its decoded vectors (76x76
Givens tree), plus a fabricated small Gram tensor. Nothing is verified here.
"""
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "data/competition/verifiers"))
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors  # noqa: E402

d = np.load(REPO / "experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz")
WORDS8 = np.asarray(d["angle_words"], np.int64)
U8 = np.asarray(d["U"], np.float64)
TREE = np.asarray(d["tree_edges"], np.int64)
NO = 76
NANG = 75
EDGES = [(int(a), int(b)) for a, b in TREE]


def decode(words, brot):
    return reconstruct_u_vectors(np.asarray(words) / (1 << (brot - 1)), TREE)


def encode_rows(vectors, brot):
    u = np.array(vectors, np.float64, copy=True)
    words = np.zeros((u.shape[0], NANG), np.int64)
    scale = 1 << (brot - 1)
    for t in range(NANG - 1, -1, -1):
        p, c = EDGES[t]
        th = np.arctan2(u[:, c], u[:, p])
        th = np.where(th < 0.0, th + 2.0 * np.pi, th)
        th = np.where(np.hypot(u[:, p], u[:, c]) < 1e-12, 0.0, th)
        words[:, t] = np.round(th / np.pi * scale).astype(np.int64) % (2 * scale)
        u[:, p] = np.hypot(u[:, p], u[:, c])
        u[:, c] = 0.0
    return words


V8 = decode(WORDS8, 8)
print("decode8 norm max dev", float(np.max(np.abs(np.linalg.norm(V8, axis=1) - 1))))
print("encode(V8,8) vs WORDS8 mismatch", int(np.sum(encode_rows(V8, 8) != WORDS8)))
print("encode(U,8) vs WORDS8[76:] mismatch", int(np.sum(encode_rows(U8.reshape(-1, NO), 8) != WORDS8[NO:])))
print("encode(U,8) vs encode(V8,8)[76:] mismatch", int(np.sum(encode_rows(U8.reshape(-1, NO), 8) != encode_rows(V8, 8)[NO:])))

for brot in (7, 6, 5):
    W = encode_rows(V8, brot)
    Vq = decode(W, brot)
    dq = float(np.sum((Vq - V8) ** 2))
    print(f"brot {brot}: quant_sq {dq:.6f} rms {np.sqrt(dq / V8.size):.6f} "
          f"max row err {np.max(np.linalg.norm(Vq - V8, axis=1)):.6f} "
          f"max word {W.max()}")

# --- optimize_one_body on a fabricated 76x76 symmetric h1p ------------------
rng = np.random.default_rng(0)
Qm, _ = np.linalg.qr(rng.standard_normal((NO, NO)))
lam = np.linspace(-1.0, 1.0, NO)
h1p = (Qm * lam) @ Qm.T


def optimize_one_body(rows_words, brot, h1p, passes=4):
    from scipy.optimize import linear_sum_assignment

    lam, vec = np.linalg.eigh(h1p)
    start = decode(rows_words, brot)
    ri, ci = linear_sum_assignment(-np.abs(start @ vec))
    target = np.zeros_like(start)
    target[ri] = vec[:, ci].T
    weight = np.zeros(len(ri))
    weight[ri] = lam[ci]
    scale = 1 << (brot - 1)
    grid = np.arange(2 * scale)
    cosg = np.cos(np.pi * grid / scale)
    sing = np.sin(np.pi * grid / scale)
    best_vec = start.copy()
    best = float(np.sum(weight ** 2 * np.sum(start * target, axis=1) ** 2))
    for _ in range(passes):
        cur = encode_rows(best_vec, brot)
        z = np.zeros((len(cur), NO))
        z[:, 0] = 1.0
        U = target.copy()
        back = [None] * NANG
        for t in range(NANG - 1, -1, -1):
            back[t] = U.copy()
            p, c = EDGES[t]
            th = np.pi * cur[:, t] / scale
            cs, sn = np.cos(th), np.sin(th)
            up, uc = U[:, p].copy(), U[:, c].copy()
            U[:, p] = cs * up + sn * uc
            U[:, c] = -sn * up + cs * uc
        for t in range(NANG):
            p, c = EDGES[t]
            Uu = back[t]
            A_ = z[:, p] * Uu[:, p] + z[:, c] * Uu[:, c]
            B_ = z[:, p] * Uu[:, c] - z[:, c] * Uu[:, p]
            pick = np.argmax(A_[:, None] * cosg[None, :] + B_[:, None] * sing[None, :], axis=1)
            cur[:, t] = pick
            th = np.pi * pick / scale
            cs, sn = np.cos(th), np.sin(th)
            zp, zc = z[:, p].copy(), z[:, c].copy()
            z[:, p] = cs * zp - sn * zc
            z[:, c] = sn * zp + cs * zc
        cand = decode(cur, brot)
        score = float(np.sum(weight ** 2 * np.sum(cand * target, axis=1) ** 2))
        if score <= best:
            break
        best, best_vec = score, cand
    return best_vec, best, float(np.sum(weight ** 2 * np.sum(start * target, axis=1) ** 2))


for brot in (8, 7, 6):
    v, sc, sc0 = optimize_one_body(WORDS8[:NO], brot, h1p)
    print(f"brot {brot}: 1body objective {sc0:.6f} -> {sc:.6f} (x{sc / sc0:.4f}), "
          f"norms {np.max(np.abs(np.linalg.norm(v, axis=1) - 1)):.2e}")

# --- error_2 quadratic form vs direct evaluation on a small fabricated case --
NOx, Rx, Cx = 6, 2, 2
rng = np.random.default_rng(1)
Sx = rng.standard_normal((NOx, NOx))
Sx = Sx + Sx.T
tex = rng.standard_normal((NOx,) * 4)
wx = rng.standard_normal((Rx, 3, Cx))
ub = rng.standard_normal((Rx, 3, NOx))

Xx = np.einsum("tjp,tjq,tjl->tlpq", *(lambda u: (u, u, wx))(ub / np.linalg.norm(ub, axis=2)[:, :, None]), optimize=True)
Xx = np.tril(Xx) + np.swapaxes(np.tril(Xx, k=-1), -1, -2)
diag = np.arange(NOx)
T = np.array(tex, copy=True)
T[:, :, diag, diag] += 0.5 * Sx[:, :, None]
T[diag, diag, :, :] += 0.5 * Sx[None, :, :]
Xf = Xx.reshape(Rx * Cx, NOx * NOx)
G = (Xf @ Xf.T) ** 2
Mx = T.reshape(NOx * NOx, NOx * NOx)
b = np.einsum("ij,ij->i", Xf, (Mx @ Xf.T).T)
T2 = float(np.dot(T.ravel(), T.ravel()))
def solve_nn_qp(G, b):
    n = len(b)
    free = np.ones(n, bool)
    ridge = 1e-12 * (np.trace(G) / n + 1e-300)
    u = np.zeros(n)
    for _ in range(60):
        idx = np.flatnonzero(free)
        if len(idx) == 0:
            break
        sub = G[np.ix_(idx, idx)] + ridge * np.eye(len(idx))
        sol = np.linalg.lstsq(sub, b[idx], rcond=None)[0]
        u = np.zeros(n)
        u[idx] = sol
        bad = free & (u <= 0.0)
        if not bad.any():
            break
        free &= ~bad
    return u


def direct_err2(scale2d):
    """scale2d[r,c] multiplies X[r,c]; returns ||sum X' (x) X' - T||_F."""
    Xp = scale2d[:, :, None, None] * Xx
    D = np.einsum("rcpq,rcst->pqst", Xp, Xp, optimize=True)
    D -= T
    return float(np.linalg.norm(D.ravel()))


u_opt = solve_nn_qp(G, b)
A_ = float(u_opt @ G @ u_opt)
B_ = float(b @ u_opt)
print("QP: u active", int((u_opt > 0).sum()), "of", len(u_opt))
for s in (1.0, 0.8, 1.2, 1.6):
    sc = (s * np.sqrt(np.maximum(u_opt, 0.0))).reshape(Rx, Cx)
    e_dir = direct_err2(sc)
    e_q = math.sqrt(max(0.0, A_ * s ** 4 - 2.0 * B_ * s ** 2 + T2))
    print(f"  s={s:.2f} direct {e_dir:.12f} quadratic {e_q:.12f} rel {abs(e_dir - e_q) / e_dir:.2e}")
