"""Progressive rounding of the one-body rows with coded low bits.

The one-body words are the signed-gauge angles of h1's eigenvectors. Rounding them with bit 0 of the
coded columns pinned to an affine pattern per 16-address block, by projection and greedy polish,
costs about as much as 7-bit words (error_1 11 -> 29 mHa on the (4,239,128) table). Rounding them
progressively instead, as quantize.py does for the two-body rows (freeze the angles whose rounding
hurts most, refit the free ones, choose and lock the block patterns as angles freeze), lets the
still-free angles compensate. error_1 = ||V^T diag(lam) V - h1'||_F with lam the eigenvalues.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

import encode
import onebody

FREE = (0.9995, 0.999, 0.9975, 0.995, 0.99, 0.98, 0.965, 0.95, 0.925, 0.9, 0.86, 0.82, 0.77, 0.72, 0.66, 0.6, 0.54,
        0.48, 0.42, 0.36, 0.3, 0.25, 0.2, 0.16, 0.12, 0.09, 0.065, 0.045, 0.03, 0.02, 0.012, 0.006, 0.0)


def quantize_coded(h1p: np.ndarray, edges: np.ndarray, brot: int, coded, following: np.ndarray,
                   free=FREE, iters: int = 300, probes: int = 8, seed: int = 0, log=None, coded2=()) -> np.ndarray:
    """One-body words (N, N-1) in [0, 2**brot) with bit 0 of the `coded` columns (and bit 1 of the `coded2`
    columns) affine on every block of 16 addresses; `following` holds the two-body rows that complete the
    last block (their bits fix its pattern). With `coded2` the angles stay in the signed gauge (bounds)."""
    import jax
    import jax.numpy as jnp
    from quantize import decode
    jax.config.update('jax_enable_x64', True)
    N = h1p.shape[0]
    lam, vecs = np.linalg.eigh(h1p)
    scale, mod = float(1 << (brot - 1)), 1 << brot
    theta = encode.signed_angles(vecs.T, edges)
    H, L = jnp.asarray(h1p), jnp.asarray(lam)

    def resid(th):
        V = decode(th, edges, N)
        return ((V.T * L) @ V - H).ravel()

    vg = jax.jit(jax.value_and_grad(lambda th: jnp.sum(resid(th) ** 2)))

    @jax.jit
    def curvature(th, key):
        _, vjp = jax.vjp(resid, th)
        one = lambda k: vjp(jax.random.normal(k, (N * N,), th.dtype))[0] ** 2  # noqa: E731
        return jnp.mean(jax.vmap(one)(jax.random.split(key, probes)), axis=0)

    coded = [int(c) for c in coded]
    coded2 = [int(c) for c in coded2]
    assert set(coded2) <= set(coded), 'coded2 columns must be coded'
    two = np.array([c in coded2 for c in coded], bool)
    ccol = {c: i for i, c in enumerate(coded)}
    AFFI = onebody.AFFINE.astype(np.int64)
    RES = AFFI[:, None, :] + 2 * AFFI[None, :, :]
    g_lo, g_hi = -0.5, 0.5 - 1.0 / scale
    rows = np.arange(N)
    blk, pos = rows // 16, rows % 16
    nblk = int(blk.max()) + 1
    AFF = onebody.AFFINE
    allowed, allowed2 = {}, {}
    for i, col in enumerate(coded):
        for b in range(nblk):
            fixed = [(a - 16 * b, int(following[a - N, col]) & 1)
                     for a in range(max(N, 16 * b), min(16 * b + 16, N + len(following)))]
            cands = [p for p in range(32) if all(AFF[p, j] == v for j, v in fixed)]
            allowed[b, i] = cands or list(range(32))
            fixed2 = [(a - 16 * b, (int(following[a - N, col]) >> 1) & 1)
                      for a in range(max(N, 16 * b), min(16 * b + 16, N + len(following)))]
            cands2 = [p for p in range(32) if all(AFF[p, j] == v for j, v in fixed2)]
            allowed2[b, i] = cands2 or list(range(32))
    pattern2 = np.zeros((nblk, len(coded)), np.int64)
    pattern = np.zeros((nblk, len(coded)), np.int64)
    locked = np.zeros((nblk, len(coded)), bool)
    frozen = np.zeros(theta.shape, bool)
    qvals = np.zeros_like(theta)

    def parity_round(t, par):
        lo = np.floor(t)
        lo = np.where((lo % 2) != par, lo - 1, lo)
        return np.where(t - lo <= lo + 2 - t, lo, lo + 2)

    def residue_round(t, r):
        lo = np.floor(t)
        lo = lo - np.mod(lo - r, 4)
        return np.where(t - lo <= lo + 4 - t, lo, lo + 4)

    def into_gauge(v, m):
        if not coded2:
            return v
        v = np.where(v > scale / 2 - 1, v - m, v)
        return np.where(v < -scale / 2, v + m, v)

    def choose(th, c):
        q = np.round(th * scale) / scale
        if coded:
            t, cc = th[:, coded] * scale, c[:, coded]
            d = [parity_round(t, p) - t for p in (0, 1)]
            for i in range(len(coded)):
                for b in range(nblk):
                    if locked[b, i]:
                        continue
                    r = rows[blk == b]
                    costs = [np.sum(cc[r, i] * np.where(AFF[p, pos[r]] == 1, d[1][r, i], d[0][r, i]) ** 2)
                             for p in allowed[b, i]]
                    pattern[b, i] = allowed[b, i][int(np.argmin(costs))]
            q[:, coded] = into_gauge(parity_round(t, AFF[pattern[blk, :], pos[:, None]]), 2) / scale
            for i in np.flatnonzero(two):   # two-bit columns: bits 0 and 1 chosen together (residue mod 4)
                for b in range(nblk):
                    if locked[b, i]:
                        continue
                    r = rows[blk == b]
                    best, best_cost = None, np.inf
                    for p0 in allowed[b, i]:
                        for p1 in allowed2[b, i]:
                            cost = np.sum(cc[r, i] * (residue_round(t[r, i], RES[p0, p1, pos[r]]) - t[r, i]) ** 2)
                            if cost < best_cost:
                                best, best_cost = (p0, p1), cost
                    pattern[b, i], pattern2[b, i] = best
                res = AFFI[pattern[blk, i], pos] + 2 * AFFI[pattern2[blk, i], pos]
                q[:, coded[i]] = into_gauge(residue_round(t[:, i], res), 4) / scale
        return q, c * (q - th) ** 2

    def refit(th):
        mask = frozen.astype(np.float64)

        def fun(x):
            v, g = vg(jnp.asarray(mask * qvals + (1.0 - mask) * x.reshape(th.shape)))
            return float(v), (np.asarray(g, np.float64) * (1.0 - mask)).ravel()

        bounds = [(g_lo, g_hi)] * th.size if coded2 else None
        res = minimize(fun, np.clip(th, g_lo, g_hi).ravel() if coded2 else th.ravel(), jac=True, method='L-BFGS-B',
                       bounds=bounds, options={'maxiter': iters, 'maxcor': 30})
        return np.where(frozen, qvals, res.x.reshape(th.shape))

    key = jax.random.key(seed)
    current = theta
    for stage, fr in enumerate(list(free)):
        need = int(round((1.0 - fr) * theta.size)) - int(frozen.sum())
        if need > 0:
            key, sub = jax.random.split(key)
            now = np.where(frozen, qvals, current)
            c = np.asarray(curvature(jnp.asarray(now), sub))
            q, impact = choose(now, c)
            impact[frozen] = -np.inf
            pick = np.argsort(-impact, axis=None)[:need]
            frozen.flat[pick] = True
            qvals.flat[pick] = q.flat[pick]
            for r, col in zip(*np.unravel_index(pick, theta.shape)):
                if col in ccol:
                    locked[blk[r], ccol[col]] = True
        current = refit(current) if not frozen.all() else qvals
        if log:
            e = float(np.sqrt(vg(jnp.asarray(current))[0]))
            log(f'one-body stage {stage:2d}: frozen {frozen.mean():.4f}  error_1 {1e3 * e:7.3f} mHa')
    words = np.round(current * scale).astype(np.int64) % mod
    if coded:
        bits = words[:, coded] & 1
        for i in range(len(coded)):
            assert np.array_equal(bits[:, i], AFF[pattern[blk, i], pos]), 'coded bit not affine'
        bits1 = (words[:, coded] >> 1) & 1
        for i in np.flatnonzero(two):
            assert np.array_equal(bits1[:, i], AFFI[pattern2[blk, i], pos]), 'second coded bit not affine'
    return words
