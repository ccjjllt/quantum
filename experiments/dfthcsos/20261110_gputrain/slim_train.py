"""Slim GPU/CPU training runner: precomputed prob + seed -> L-BFGS -> best U/W.

Same objective as fit_probe (fastfit.error2 on shifted packed target), but the
problem matrices are precomputed (prob.npz: T, M, i, j), so no fcidump,
no starter-kit checkout and no dfthc import are needed at train time.
Only numpy + jax + optax are required.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("prob", type=Path, help="prob.npz with T, M, i, j")
    ap.add_argument("seed", type=Path, help="seed .npz with U, W")
    ap.add_argument("out", type=Path, help="output .npz for best U, W")
    ap.add_argument("--iters", type=int, default=5000)
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--memory", type=int, default=30)
    a = ap.parse_args()

    import jax
    import jax.numpy as jnp
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import fastfit

    print(f"jax backend: {jax.devices()[0]}", flush=True)
    z = np.load(a.prob)
    prob = (jnp.asarray(z["T"]), jnp.asarray(z["M"]), jnp.asarray(z["i"]), jnp.asarray(z["j"]))
    s = np.load(a.seed)
    params = {"U": jnp.asarray(s["U"]), "W": jnp.asarray(s["W"])}
    print(f"start {float(fastfit.error2(params['U'], params['W'], prob)) * 1000:.2f} mHa", flush=True)

    best = {"e": float("inf"), "U": params["U"], "W": params["W"]}
    t0 = time.time()
    log = []

    def report(done, p):
        nonlocal best
        e = float(fastfit.error2(p["U"], p["W"], prob))
        log.append({"iter": done, "e2_mHa": e * 1000.0, "seconds": round(time.time() - t0, 1)})
        if e < best["e"]:
            best = {"e": e, "U": p["U"], "W": p["W"]}
        print(json.dumps(log[-1]), flush=True)

    f = lambda p: fastfit.error2(p["U"], p["W"], prob)  # noqa: E731
    out = fastfit.lbfgs(f, params, iters=a.iters, chunk=a.chunk, memory=a.memory, report=report)
    e = float(fastfit.error2(out["U"], out["W"], prob))
    if e < best["e"]:
        best = {"e": e, "U": out["U"], "W": out["W"]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=np.asarray(best["U"]), W=np.asarray(best["W"]))
    print(json.dumps({"best_mHa": best["e"] * 1000.0, "seconds": round(time.time() - t0, 1),
                      "out": str(a.out)}), flush=True)


if __name__ == "__main__":
    main()
