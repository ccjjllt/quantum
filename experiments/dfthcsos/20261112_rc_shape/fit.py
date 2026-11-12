"""L-BFGS fit of (U, W) on the packed error_2 + kappa*D(w) objective (optax, jitted).

    python fit.py SEED.npz OUT.npz --iters 20000 [--kappa 5e-5] [--chunk 50]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import optax

import common as C
import fastfit
import jax
import jax.numpy as jnp

prob, ref = C.get_target()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('seed', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--iters', type=int, default=20000)
    ap.add_argument('--kappa', type=float, default=5e-5)
    ap.add_argument('--chunk', type=int, default=50)
    ap.add_argument('--report', type=int, default=500)
    ap.add_argument('--save-every', type=int, default=1000)
    ap.add_argument('--resume', type=Path)
    a = ap.parse_args()

    with np.load(a.seed) as z:
        U0 = jnp.asarray(np.asarray(z['U'], np.float64))
        w0 = jnp.asarray(np.asarray(z['W'], np.float64))
    if a.resume:
        with np.load(a.resume) as z:
            U0 = jnp.asarray(np.asarray(z['U'], np.float64))
            w0 = jnp.asarray(np.asarray(z['W'], np.float64))

    def aux_fn(p):
        eps = fastfit.error2(p[0], p[1], prob)
        D = 0.5 * jnp.sum(jnp.sum(jnp.abs(p[1]), axis=1) ** 2 - jnp.sum(p[1], axis=1) ** 2)
        return eps, D

    def loss(p):
        eps, D = aux_fn(p)
        return eps + a.kappa * D

    opt = optax.lbfgs(memory_size=30)
    vg = optax.value_and_grad_from_state(loss)
    aux_j = jax.jit(aux_fn)

    @jax.jit
    def run(p, s):
        def body(_, carry):
            pp, ss = carry
            value, g = vg(pp, state=ss)
            upd, ss = opt.update(g, ss, pp, value=value, grad=g, value_fn=loss)
            return optax.apply_updates(pp, upd), ss
        return jax.lax.fori_loop(0, a.chunk, body, (p, s))

    p = (U0, w0)
    state = opt.init(p)
    eps0, D = (float(x) for x in aux_j(p))
    print('start %s: error_2 %.3f mHa D %.2f' % (tuple(np.shape(w0)), 1e3 * eps0, D), flush=True)
    best, best_p = eps0, p
    t0, step = time.time(), 0
    hist = []
    while step < a.iters:
        p, state = run(p, state)
        step += a.chunk
        eps, D = (float(x) for x in aux_j(p))
        hist.append((step, 1e3 * eps))
        if eps < best:
            best, best_p = eps, p
        if step % a.report == 0:
            print('%7d: error_2 %8.3f mHa  D %7.2f  best %8.3f  (%.0f s, %.1f it/s)' % (
                step, 1e3 * eps, D, 1e3 * best, time.time() - t0, step / (time.time() - t0)), flush=True)
        if step % a.save_every == 0:
            U, w = (np.asarray(x) for x in p)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            np.savez(a.out, U=U, W=w, H2_I=w.sum(axis=1))
            a.out.with_suffix('.json').write_text(json.dumps({'step': step, 'e2_mHa': 1e3 * eps,
                                                              'best_mHa': 1e3 * best, 'hist': hist[-40:]}))
    U, w = (np.asarray(x) for x in best_p)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=U, W=w, H2_I=w.sum(axis=1))
    print('done: best %.3f mHa' % (1e3 * best), flush=True)


if __name__ == '__main__':
    main()
