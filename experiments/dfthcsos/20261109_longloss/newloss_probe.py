"""New-loss training probe on R5/B135/C70: Huberized e2 and e2+alpha*eL1 joint.

Continuous probe only (no quantization). Optimizes U/W with optax L-BFGS
(same kernel as fit_probe.py) but on a surrogate loss; reports TRUE error_2
(fastfit.error2, same metric as baseline 182.00 mHa) every --chunk iters and
saves best-U/W by TRUE e2 (gate metric), not by surrogate.

Losses:
  l2    : pure fastfit.error2 (reference; should reproduce 182.00 at 500)
  huber : sqrt(sum M * rho(H))), rho=x^2 if |x|<=d else 2d|x|-d^2.
          At d->inf equals e2; finite d downweights large outliers C1.
  joint : e2 + alpha * eL1, eL1 = Compute_H2_norm_1(H) (full-index L1 of the
          same packed residual). NOTE scale: at R5 seed eL1=636 Ha vs
          e2=0.79 Ha (ratio 801), so literal alpha=0.1 would be 80x e2 and
          purely L1-dominated. Default alpha=1.25e-4 makes alpha*eL1 = 0.1*e2
          at seed (10% weight in e2 units). --alpha sets raw multiplier.

Usage matches fit_probe.py (seed/out/itres/chunk) plus --loss/--delta/--alpha.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "artifacts/20261106_high_yield/lera_data/dfthc_refit"))
sys.path.insert(0, str(ROOT / "artifacts/20261106_high_yield/starter_kit/starter_kit"))
import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

jax.config.update("jax_enable_x64", True)
jax.config.update("jax_default_matmul_precision", "highest")
import fastfit  # noqa: E402
from dfthc.train_df_thc_sga import Initialize  # noqa: E402
from dfthc import df_thc_sga  # noqa: E402


def build_losses(prob, tril_diag, loss: str, delta: float, alpha: float):
    T, M, i, j = prob
    td = jnp.asarray(tril_diag)

    def unpack(U, W):
        u = U / jnp.linalg.norm(U, axis=2, keepdims=True)
        pairs = u[:, :, i] * u[:, :, j]
        A = jnp.einsum("rbc,rbp->rcp", W, pairs).reshape(-1, T.shape[0])
        H = A.T @ A - T
        return H

    def e2_fn(U, W):
        return fastfit.error2(U, W, prob)

    def huber_fn(U, W):
        H = unpack(U, W)
        a = jnp.abs(H)
        rho = jnp.where(a <= delta, H * H, 2.0 * delta * a - delta * delta)
        return jnp.sqrt(jnp.sum(M * rho))

    def l1_fn(U, W):
        H = unpack(U, W)
        return df_thc_sga.Compute_H2_norm_1(H, td)

    if loss == "l2":
        return (lambda p: e2_fn(p["U"], p["W"])), e2_fn, l1_fn, huber_fn
    if loss == "huber":
        return (lambda p: huber_fn(p["U"], p["W"])), e2_fn, l1_fn, huber_fn
    if loss == "joint":
        return (lambda p: e2_fn(p["U"], p["W"]) + alpha * l1_fn(p["U"], p["W"])), e2_fn, l1_fn, huber_fn
    raise ValueError(loss)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--loss", choices=("l2", "huber", "joint"), default="huber")
    ap.add_argument("--delta", type=float, default=2e-4)
    ap.add_argument("--alpha", type=float, default=1.25e-4)
    ap.add_argument("--iters", type=int, default=500)
    ap.add_argument("--chunk", type=int, default=100)
    ap.add_argument("--fcidump", default=str(ROOT / "data/competition/verifiers/dfthcsos/FeMoCo76o113e.fcidump"))
    ap.add_argument("--shifts", default=str(ROOT / "data/competition/verifiers/dfthcsos/FeMoCo76o113e.fixed_shifts.npz"))
    a = ap.parse_args()
    ref = Initialize(a.fcidump, -22140.27335)
    tril_diag = np.asarray(ref["tril_diag"])
    ref = {k: (jnp.asarray(v, jnp.float64) if hasattr(v, "dtype") and jnp.issubdtype(v.dtype, jnp.floating) else v)
           for k, v in ref.items()}
    with np.load(a.shifts) as z:
        frozen = {k: jnp.asarray(z[k], jnp.float64) for k in ("Hsym_lower", "H1_I")}
    prob = fastfit.problem(ref, frozen, jnp.float64)
    f, e2_fn, l1_fn, huber_fn = build_losses(prob, tril_diag, a.loss, a.delta, a.alpha)
    z = np.load(a.seed, allow_pickle=False)
    params = {"U": jnp.asarray(z["U"]), "W": jnp.asarray(z["W"])}
    e0 = float(e2_fn(params["U"], params["W"]))
    l0 = float(f(params))
    print(f"start e2 {e0*1e3:.2f} mHa surrogate {l0:.6f} loss={a.loss} delta={a.delta} alpha={a.alpha}", flush=True)
    best = {"e2": float("inf"), "U": params["U"], "W": params["W"]}
    t0 = time.time()
    log = []

    def report(it, p):
        nonlocal best
        e = float(e2_fn(p["U"], p["W"]))
        s = float(f(p))
        log.append({"iter": it, "e2_mHa": e * 1e3, "surrogate": s,
                    "seconds": round(time.time() - t0, 1)})
        if e < best["e2"]:
            best = {"e2": e, "U": p["U"], "W": p["W"]}
        print(json.dumps(log[-1]), flush=True)

    out = fastfit.lbfgs(f, params, iters=a.iters, chunk=a.chunk, report=report)
    e = float(e2_fn(out["U"], out["W"]))
    if e < best["e2"]:
        best = {"e2": e, "U": out["U"], "W": out["W"]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=np.asarray(best["U"]), W=np.asarray(best["W"]),
             H2_I=np.asarray(best["W"]).sum(axis=1),
             H1_I=np.float32(np.load(a.shifts)["H1_I"]),
             Hsym_lower=np.asarray(np.load(a.shifts)["Hsym_lower"], np.float32))
    print(json.dumps({"best_mHa": best["e2"] * 1e3, "seconds": round(time.time() - t0, 1),
                      "out": str(a.out), "loss": a.loss, "log": log[-6:]}, indent=1))


if __name__ == "__main__":
    main()
