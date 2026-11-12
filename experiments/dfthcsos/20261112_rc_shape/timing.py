"""Timing + accuracy of the public/current tables, and of exact/compressed merges."""
from __future__ import annotations

import time

import numpy as np

import common as C
import jax.numpy as jnp
from structure import merge

prob, ref = C.get_target()
cur = C.load(C.CURRENT)
U, w = np.asarray(cur['U'], np.float64), np.asarray(cur['W'], np.float64)
print('current float e2 %.4f mHa' % (1e3 * C.e2(U, w, prob)))

# timing of one jitted error2 and grad at (6,143,64)
import jax
import optax


def make(U, w):
    U, w = jnp.asarray(U), jnp.asarray(w)
    f = lambda p: fast_err(p)  # noqa: E731
    return U, w


import fastfit


def timeit(U, w, n=20):
    Uj, wj = jnp.asarray(U), jnp.asarray(w)
    f = jax.jit(lambda U, w: fastfit.error2(U, w, prob))
    g = jax.jit(jax.grad(lambda U, w: fastfit.error2(U, w, prob), argnums=(0, 1)))
    f(Uj, wj).block_until_ready()
    t0 = time.time()
    for _ in range(n):
        f(Uj, wj).block_until_ready()
    t1 = time.time()
    for _ in range(n):
        g(Uj, wj)
    t2 = time.time()
    print('  error2 %.1f ms, grad %.1f ms' % (1e3 * (t1 - t0) / n, 1e3 * (t2 - t1) / n))


print('current:')
timeit(U, w)
rng = np.random.default_rng(0)
print('(6,143,64) random:')
timeit(rng.normal(size=(6, 143, 76)), 1e-4 * rng.normal(size=(6, 143, 64)))

# exact merge in pairs: (4,286,88)
pm = merge({'U': U, 'W': w, 'H2_I': np.asarray(cur['H2_I'])}, 2, 88)
print('exact merge (4,286,88): float e2 %.9f mHa' % (1e3 * C.e2(pm['U'], pm['W'], prob)))
