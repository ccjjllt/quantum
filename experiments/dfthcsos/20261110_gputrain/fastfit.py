"""error_2 in packed pair space and an L-BFGS loop that stays on the device (for GPUs).

The starter kit's objective builds every group copy's full N x N matrix, gathers its lower
triangle and contracts; with SciPy's L-BFGS on the host, an A100 runs it at 9 iterations per
second in float32 and float64 alike, so the arithmetic is not the limit. Here

    A[(r, c), p] = sum_b w[r, b, c] u[r, b, i_p] u[r, b, j_p]      (p = (i_p, j_p), i_p >= j_p)
    error_2      = || sqrt(m m^T) * (A^T A - T) ||_F

with m = 1 on diagonal pairs and 2 elsewhere (Compute_H2_norm's multiplicities) and T the
symmetry-shifted target, so that A^T A - T is exactly Compute_H2_residual_after_symmetry_shift.
`lbfgs` runs optax's L-BFGS (zoom line search) in jitted chunks, with no host round trips.
"""
from __future__ import annotations

import numpy as np

import jax
import jax.numpy as jnp
import optax


def problem(ref, frozen, dtype):
    """(T, M, i, j): the shifted packed target, the norm weights and the pair indices."""
    from dfthc import df_thc_sga
    N = int(ref['orbitals'])
    zero = jnp.zeros((1, 1, N, N), dtype)
    T = -df_thc_sga.Compute_H2_residual_after_symmetry_shift(frozen, ref, zero)
    i, j = (np.asarray(t) for t in ref['tril'])
    m = np.where(i == j, 1.0, 2.0)
    return jnp.asarray(T, dtype), jnp.asarray(np.outer(m, m), dtype), jnp.asarray(i), jnp.asarray(j)


def error2(U, w, prob):
    T, M, i, j = prob
    u = U / jnp.linalg.norm(U, axis=2, keepdims=True)
    pairs = u[:, :, i] * u[:, :, j]                                        # (R, B, P)
    A = jnp.einsum('rbc,rbp->rcp', w, pairs).reshape(-1, T.shape[0])       # (R C, P)
    H = A.T @ A - T
    return jnp.sqrt(jnp.sum(M * H * H))


def lbfgs(f, params, iters: int, chunk: int = 200, memory: int = 30, report=None):
    """Minimize f(params) (a scalar, jit-traceable) with optax L-BFGS; params is any pytree."""
    opt = optax.lbfgs(memory_size=memory)
    vg = optax.value_and_grad_from_state(f)

    @jax.jit
    def run(params, state):
        def body(_, carry):
            p, s = carry
            value, grad = vg(p, state=s)
            upd, s = opt.update(grad, s, p, value=value, grad=grad, value_fn=f)
            return optax.apply_updates(p, upd), s
        return jax.lax.fori_loop(0, chunk, body, (params, state))

    state = opt.init(params)
    done = 0
    while done < iters:
        params, state = run(params, state)
        done += chunk
        if report:
            report(done, params)
    return params
