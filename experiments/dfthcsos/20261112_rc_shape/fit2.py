"""L-BFGS-B (scipy, host loop over a jitted value_and_grad) on error_2 + kappa*D(w).

    python fit2.py SEED.npz OUT.npz --iters 5000 [--kappa 5e-5] [--every 250]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

import common as C
import fastfit
import jax
import jax.numpy as jnp

prob, ref = C.get_target()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('seed', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--iters', type=int, default=5000)
    ap.add_argument('--kappa', type=float, default=5e-5)
    ap.add_argument('--every', type=int, default=250)
    ap.add_argument('--resume', type=Path)
    ap.add_argument('--tag', default='')
    a = ap.parse_args()

    with np.load(a.resume or a.seed) as z:
        U0 = np.asarray(z['U'], np.float64)
        w0 = np.asarray(z['W'], np.float64)

    def aux(p):
        eps = fastfit.error2(p[0], p[1], prob)
        D = 0.5 * jnp.sum(jnp.sum(jnp.abs(p[1]), axis=1) ** 2 - jnp.sum(p[1], axis=1) ** 2)
        return eps, D

    def loss(p):
        eps, D = aux(p)
        return eps + a.kappa * D

    vg = jax.jit(jax.value_and_grad(loss))
    auxj = jax.jit(aux)

    def fun(x):
        U = jnp.asarray(x[:U0.size].reshape(U0.shape))
        w = jnp.asarray(x[U0.size:].reshape(w0.shape))
        v, g = vg((U, w))
        return float(v), np.concatenate([np.asarray(g[0], np.float64).ravel(), np.asarray(g[1], np.float64).ravel()])

    x0 = np.concatenate([U0.ravel(), w0.ravel()])
    eps0, D0 = (float(x) for x in auxj((jnp.asarray(U0), jnp.asarray(w0))))
    print(f'{a.tag} start {w0.shape}: error_2 {1e3*eps0:.3f} mHa D {D0:.2f}', flush=True)
    t0 = time.time()
    it = [0]

    def cb(xk):
        it[0] += 1
        if it[0] % a.every == 0:
            eps, D = (float(v) for v in auxj((jnp.asarray(xk[:U0.size].reshape(U0.shape)),
                                              jnp.asarray(xk[U0.size:].reshape(w0.shape)))))
            print(f'{a.tag} it {it[0]:5d}: error_2 {1e3*eps:8.3f} mHa D {D:7.2f} '
                  f'({time.time()-t0:.0f} s, {it[0]/(time.time()-t0):.1f} it/s)', flush=True)
            Uc = np.asarray(xk[:U0.size].reshape(U0.shape))
            wc = np.asarray(xk[U0.size:].reshape(w0.shape))
            np.savez(a.out, U=Uc, W=wc, H2_I=wc.sum(axis=1))

    res = minimize(fun, x0, jac=True, method='L-BFGS-B', callback=cb,
                   options={'maxiter': a.iters, 'maxfun': 4 * a.iters, 'maxcor': 30,
                            'ftol': 1e-16, 'gtol': 1e-14, 'maxls': 40})
    U = res.x[:U0.size].reshape(U0.shape)
    w = res.x[U0.size:].reshape(w0.shape)
    eps, D = (float(v) for v in auxj((jnp.asarray(U), jnp.asarray(w))))
    print(f'{a.tag} done {res.nit} its: error_2 {1e3*eps:.3f} mHa D {D:.2f} ({time.time()-t0:.0f} s)', flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=U, W=w, H2_I=w.sum(axis=1))
    a.out.with_suffix('.json').write_text(json.dumps({'shape': list(w.shape), 'nit': int(res.nit),
                                                      'e2_mHa': 1e3 * eps, 'D': D,
                                                      'seconds': time.time() - t0}))


if __name__ == '__main__':
    main()
