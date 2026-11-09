"""Staged training paradigm probe: U-first then joint U/W (total 500 L-BFGS iters).

Stage 1 (iters_u): freeze W, optimize only U on fastfit.error2.
Stage 2 (iters_w or joint): optimize U+W jointly (default) or W-only-then-joint
per --stage2 {joint,w}. Fresh optax L-BFGS state per stage. Reports every
--chunk iters with continuous error_2 (mHa) and saves best-U/W (by error2).

This differs from fit_probe.py (joint U/W for all iters): it tests whether the
~180mHa stall is a joint-curvature/basin artifact that a U-first curriculum
escapes. Loss is pure error_2 (same metric as baseline); no quantization.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--iters-u", type=int, default=250)
    ap.add_argument("--iters-joint", type=int, default=250)
    ap.add_argument("--stage2", choices=("joint", "w"), default="joint")
    ap.add_argument("--chunk", type=int, default=50)
    ap.add_argument("--fcidump", default=str(ROOT / "data/competition/verifiers/dfthcsos/FeMoCo76o113e.fcidump"))
    ap.add_argument("--shifts", default=str(ROOT / "data/competition/verifiers/dfthcsos/FeMoCo76o113e.fixed_shifts.npz"))
    a = ap.parse_args()
    ref = Initialize(a.fcidump, -22140.27335)
    ref = {k: (jnp.asarray(v, jnp.float64) if hasattr(v, "dtype") and jnp.issubdtype(v.dtype, jnp.floating) else v)
           for k, v in ref.items()}
    with np.load(a.shifts) as z:
        frozen = {k: jnp.asarray(z[k], jnp.float64) for k in ("Hsym_lower", "H1_I")}
    prob = fastfit.problem(ref, frozen, jnp.float64)
    z = np.load(a.seed, allow_pickle=False)
    U0 = jnp.asarray(z["U"])
    W0 = jnp.asarray(z["W"])
    print(f"start {float(fastfit.error2(U0, W0, prob))*1e3:.2f} mHa", flush=True)
    best = {"e2": float("inf"), "U": U0, "W": W0}
    t0 = time.time()
    log = []

    def report(it, p, tag):
        nonlocal best
        e = float(fastfit.error2(p["U"], p["W"], prob))
        log.append({"iter": it, "tag": tag, "e2_mHa": e * 1e3, "seconds": round(time.time() - t0, 1)})
        if e < best["e2"]:
            best = {"e2": e, "U": p["U"], "W": p["W"]}
        print(json.dumps(log[-1]), flush=True)

    # Stage 1: U-only (W frozen)
    Wf = W0
    fU = lambda p: fastfit.error2(p["U"], Wf, prob)  # noqa: E731
    pU: dict = {"U": U0}
    done = 0
    while done < a.iters_u:
        n = min(a.chunk, a.iters_u - done)
        pU = fastfit.lbfgs(fU, pU, iters=n, chunk=n,
                           report=lambda it, p, _done=done: report(_done + it, {"U": p["U"], "W": Wf}, "U-only"))
        done += n
    U1 = pU["U"]

    # Stage 2: joint (or W-only)
    if a.stage2 == "joint":
        fJ = lambda p: fastfit.error2(p["U"], p["W"], prob)  # noqa: E731
        pJ: dict = {"U": U1, "W": Wf}
        done2 = 0
        while done2 < a.iters_joint:
            n = min(a.chunk, a.iters_joint - done2)
            base = a.iters_u + done2
            pJ = fastfit.lbfgs(fJ, pJ, iters=n, chunk=n,
                               report=lambda it, p, _b=base: report(_b + it, p, "joint"))
            done2 += n
        out = pJ
    else:
        Uf = U1
        fW = lambda p: fastfit.error2(Uf, p["W"], prob)  # noqa: E731
        pW: dict = {"W": Wf}
        done2 = 0
        while done2 < a.iters_joint:
            n = min(a.chunk, a.iters_joint - done2)
            base = a.iters_u + done2
            pW = fastfit.lbfgs(fW, pW, iters=n, chunk=n,
                               report=lambda it, p, _b=base: report(_b + it, {"U": Uf, "W": p["W"]}, "W-only"))
            done2 += n
        out = {"U": Uf, "W": pW["W"]}

    e = float(fastfit.error2(out["U"], out["W"], prob))
    if e < best["e2"]:
        best = {"e2": e, "U": out["U"], "W": out["W"]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=np.asarray(best["U"]), W=np.asarray(best["W"]),
             H2_I=np.asarray(best["W"]).sum(axis=1),
             H1_I=np.float32(np.load(a.shifts)["H1_I"]),
             Hsym_lower=np.asarray(np.load(a.shifts)["Hsym_lower"], np.float32))
    print(json.dumps({"best_mHa": best["e2"] * 1e3, "seconds": round(time.time() - t0, 1),
                      "out": str(a.out), "log": log}, indent=1))


if __name__ == "__main__":
    main()
