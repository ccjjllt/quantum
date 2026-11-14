"""EXCERPT of the upstream ``dfthc_refit/quantize.py`` -- ``levels`` and ``decode`` only.

Copied verbatim (Apache-2.0) from ``marculera/dfthc-compact-pipeline`` v7,
``dfthc_refit/quantize.py``, VERSION ``704091bf1e1325b090202343e4d8130ff1c80b64``.
See ../SOURCES.md and ../LICENSE.

Why an excerpt: the upstream module also carries the progressive-rounding stages, which import
``optax`` and the starter kit's ``dfthc`` package at module level. ``onebody_quant`` imports only
``decode`` from here, so the excerpt keeps the JAX one-body path working (``--final`` mode) on a
plain Kaggle image without the starter kit. Nothing else from upstream is changed.
"""
from __future__ import annotations

import numpy as np
import jax.numpy as jnp


def levels(edges: np.ndarray) -> list[np.ndarray]:
    """Split the ordered edges into runs that touch disjoint orbitals (7 for the log-depth tree)."""
    runs, current, used = [], [], set()
    for t, (p, q) in enumerate(edges):
        if p in used or q in used:
            runs.append(np.array(current))
            current, used = [], set()
        current.append(t)
        used.update((int(p), int(q)))
    return runs + [np.array(current)]


def decode(theta, edges: np.ndarray, n: int):
    """The verifier's Givens tree (reconstruct_u_vectors) in JAX: rows of theta/pi -> vectors.

    Edges within a level act on disjoint orbitals, so each level is one vectorized update.
    """
    c, s = jnp.cos(jnp.pi * theta), jnp.sin(jnp.pi * theta)
    u = jnp.zeros((theta.shape[0], n), theta.dtype).at[:, 0].set(1.0)
    for ts in levels(edges):
        p, q = edges[ts, 0], edges[ts, 1]
        up, uq = u[:, p], u[:, q]
        u = u.at[:, p].set(c[:, ts] * up - s[:, ts] * uq).at[:, q].set(s[:, ts] * up + c[:, ts] * uq)
    return u
