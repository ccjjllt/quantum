"""Quantization-aware fine-tune of an (8,B,44) factorization.

Alternates 500 L-BFGS steps on (U,W) with a hard projection of U to the 8-bit
signed Givens words, then a 200-step W-only refit at the projected U.  The
reported e2 after each projection is the e2 of an exactly 8-bit-representable
two-body table, i.e. the quantity the official ``evaluate_words`` will see.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "data/competition/verifiers"))
sys.path.insert(0, str(WT / "experiments/dfthcsos/20261111_r3_probe"))
sys.path.insert(0, str(WT / "experiments/dfthcsos/20261110_gputrain"))

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

jax.config.update("jax_enable_x64", True)
jax.config.update("jax_default_matmul_precision", "highest")
import fastfit  # noqa: E402
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors  # noqa: E402


def signed_angles(vectors, edges):
    a = np.array(vectors, dtype=np.float64)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    theta = np.zeros((len(a), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        s = np.where(a[:, p] > 0, 1.0, np.where(a[:, p] < 0, -1.0,
                    np.where(a[:, q] > 0, -1.0, 1.0)))
        theta[:, t] = np.arctan2(s * a[:, q], s * a[:, p])
        a[:, p] = s * np.hypot(a[:, p], a[:, q])
        a[:, q] = 0.0
    return theta / np.pi


def signed_words(vectors, edges, brot):
    s = 1 << (brot - 1)
    k = np.clip(np.round(signed_angles(vectors, edges) * s), -s // 2, s // 2 - 1)
    return k.astype(np.int64) % (1 << brot)

BASE = WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos/submission.npz"
PROB = WT / "artifacts/20261110_gputrain/prob_r5.npz"


def main() -> None:
    seed = Path(sys.argv[1])
    out = Path(sys.argv[2])
    chunks = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    tree = np.asarray(np.load(BASE)["tree_edges"], np.int64)
    z = np.load(PROB)
    prob = (jnp.asarray(z["T"]), jnp.asarray(z["M"]),
            jnp.asarray(z["i"]), jnp.asarray(z["j"]))
    s = np.load(seed)
    U = jnp.asarray(s["U"], jnp.float64)
    W = jnp.asarray(s["W"], jnp.float64)

    def e2(Uv, Wv):
        return float(fastfit.error2(Uv, Wv, prob)) * 1e3

    def project(Uv):
        u = np.asarray(Uv, np.float64)
        words = signed_words(u.reshape(-1, 76), tree, 8)
        v = reconstruct_u_vectors(words / 128.0, tree)
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        return jnp.asarray(v.reshape(u.shape), jnp.float64), words

    log = []
    # report the seed's continuous and quantized e2
    Uq, words = project(U)
    log.append({"chunk": 0, "continuous_e2_mHa": e2(U, W),
                "quant_e2_mHa": e2(Uq, W)})
    print(json.dumps(log[0]), flush=True)
    best = {"e": log[0]["quant_e2_mHa"], "U": Uq, "W": W}
    t0 = time.time()
    for c in range(1, chunks + 1):
        p = {"U": U, "W": W}
        f = lambda q: fastfit.error2(q["U"], q["W"], prob)  # noqa: E731
        p = fastfit.lbfgs(f, p, iters=500, chunk=500, report=None)
        Uq, _ = project(p["U"])
        pw = {"W": p["W"]}
        fw = lambda q: fastfit.error2(Uq, q["W"], prob)  # noqa: E731
        pw = fastfit.lbfgs(fw, pw, iters=200, chunk=200, report=None)
        W = pw["W"]
        U = Uq
        row = {"chunk": c, "continuous_e2_mHa": e2(p["U"], p["W"]),
               "quant_e2_mHa": e2(U, W), "seconds": round(time.time() - t0, 1)}
        print(json.dumps(row), flush=True)
        if row["quant_e2_mHa"] < best["e"]:
            best = {"e": row["quant_e2_mHa"], "U": U, "W": W}
    np.savez(out, U=np.asarray(best["U"]), W=np.asarray(best["W"]))
    print(json.dumps({"best_quant_e2_mHa": best["e"], "out": str(out)}), flush=True)


if __name__ == "__main__":
    main()
