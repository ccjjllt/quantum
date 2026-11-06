"""Reproduce the baseline margin and refit the 41 angles with the max-margin LP.

Writes artifacts/20261107_mask_refit/repro.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

import model as M

OUT = M.ART


def main() -> None:
    t0 = time.time()
    m = M.load_model()
    masks, thetas, T, tol = m["masks"], m["thetas"], m["T"], m["tol"]

    ph = M.phase_of(masks, thetas)
    base = M.margins(ph, T, tol)
    print("baseline", json.dumps(base), flush=True)
    assert base["margin_units"] == M.OFFICIAL["baseline_margin"], base
    assert abs(base["worst_ratio"] - M.OFFICIAL["worst_ratio"]) < 1e-15

    cost0 = M.cost(base["margin_units"])
    print("baseline cost", json.dumps(cost0), flush=True)
    print("official C", M.OFFICIAL["C"], "score", M.OFFICIAL["score"])

    # Initial constraint set: small x, random x, and current tightest margins.
    rng = np.random.default_rng(20261107)
    err = M.err_of(ph, T)
    tight = np.argsort(tol - np.abs(err))[:2000]
    idx = np.unique(np.concatenate([np.arange(8192), rng.integers(0, M.MAXX, 12000), tight]))
    print("initial constraints", len(idx), flush=True)

    t1 = time.time()
    out = M.refit(masks, thetas, T, tol, idx, max_iter=12, verbose=True)
    dt = time.time() - t1
    print(f"refit done in {dt:.1f}s margin={out['margin']} "
          f"saving_vs_baseline={M.margin_saving_C(base['margin_units'], out['margin']):.4f}C")

    rec = {
        "baseline": base,
        "baseline_cost": cost0,
        "refit": {
            "margin_units": out["margin"],
            "history": out["history"],
            "theta_units": out["theta"].tolist(),
            "theta_half_turns": [float(v) / 2**63 for v in out["theta"]],
            "refit_cost": M.cost(out["margin"]),
            "saving_C_vs_baseline": M.margin_saving_C(base["margin_units"], out["margin"]),
            "seconds": dt,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "repro.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(f"total {time.time() - t0:.1f}s; wrote {OUT / 'repro.json'}")


if __name__ == "__main__":
    main()
