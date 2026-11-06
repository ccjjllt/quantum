"""Continue the Lera packed-pair L-BFGS fit on a saved (R,B,C) seed.

This is a training probe only: it optimizes U/W for error_2 with the starter
target, and saves the best U/W.  It does not quantize or build circuits.
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
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--chunk", type=int, default=200)
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
    params = {"U": jnp.asarray(z["U"]), "W": jnp.asarray(z["W"])}
    print("start", float(fastfit.error2(params["U"], params["W"], prob)) * 1e3, "mHa", flush=True)
    best = {"e2": float("inf"), "U": params["U"], "W": params["W"]}
    t0 = time.time()
    log = []

    def report(it, p):
        nonlocal best
        e = float(fastfit.error2(p["U"], p["W"], prob))
        log.append({"iter": it, "e2_mHa": e * 1e3, "seconds": round(time.time() - t0, 1)})
        if e < best["e2"]:
            best = {"e2": e, "U": p["U"], "W": p["W"]}
        print(json.dumps(log[-1]), flush=True)

    f = lambda p: fastfit.error2(p["U"], p["W"], prob)  # noqa: E731
    out = fastfit.lbfgs(f, params, iters=a.iters, chunk=a.chunk, report=report)
    e = float(fastfit.error2(out["U"], out["W"], prob))
    if e < best["e2"]:
        best = {"e2": e, "U": out["U"], "W": out["W"]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=np.asarray(best["U"]), W=np.asarray(best["W"]),
             H2_I=np.asarray(best["W"]).sum(axis=1),
             H1_I=np.float32(np.load(a.shifts)["H1_I"]),
             Hsym_lower=np.asarray(np.load(a.shifts)["Hsym_lower"], np.float32))
    print(json.dumps({"best_mHa": best["e2"] * 1e3, "seconds": round(time.time() - t0, 1),
                      "out": str(a.out), "log": log[-5:]}, indent=1))


if __name__ == "__main__":
    main()
