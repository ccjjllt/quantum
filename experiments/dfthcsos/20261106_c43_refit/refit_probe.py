"""Constrained-refit probe for a C-reduced factorization at fixed Syed V9 words.

This is a numerical feasibility probe: it changes only W/H2_I (never the
loaders or words) and reports the official metrics of every intermediate
point. It does not build a submission or run the official verifier.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "artifacts/20261106_high_yield/public/dfthc_refit_1.7.0"
sys.path.insert(0, str(SOURCE))
import dfthc_refit as dr  # noqa: E402


def official(P, y):
    m = P.official(y)
    return {
        "error_1_mHa": 1e3 * m["error_1"],
        "error_2_mHa": 1e3 * m["error_2"],
        "Lambda": m["Lambda"],
        "E_gap": m["E_gap"],
        "lambda_eff": m["lambda_eff"],
        "passes": P.passes(m),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("start_npz", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--words", type=Path, default=ROOT / "artifacts/20261106_syed_v9/dfthcsos/recovered_words.npy")
    ap.add_argument("--verifier-dir", type=Path, default=ROOT / "data/competition/verifiers")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--max-evals", type=int, default=1200)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    import torch

    torch.set_num_threads(args.threads)
    words = np.load(args.words)
    z = dict(np.load(args.start_npz, allow_pickle=False))
    P = dr.femoco_problem(args.start_npz, words, 8, str(args.verifier_dir))
    y = P.y0()
    o0 = P.official(y)
    q0 = P.evaluate(y)
    targets, notes = dr.default_targets(
        o0, q0, e1t=19.999, e2t=19.999, gap_margin=1e-5, gap_floor=P.gap_floor,
        e1t_explicit=True, e2t_explicit=True,
    )
    log = {
        "scope": "fixed-word constrained weight refit; no loader emission, no official verifier run",
        "start": str(args.start_npz),
        "targets": {"e1_mHa": targets[0], "e2_mHa": targets[1], "gap_Ha": targets[2], "notes": notes},
        "rounds": [],
    }
    best = {"lambda_eff": float("inf"), "y": None, "metrics": None}
    start = time.time()
    cur = y
    for k in range(1, args.rounds + 1):
        rec = {"round": k}
        w, wB = P.split(cur)
        t0 = time.time()
        gw, gwB, _, gi = dr.gauge(w, wB, seed=args.seed + k, kappas=(0.01, 0.05), procs=max(1, args.threads - 1),
                                  kicks_on=k <= 1, log=lambda **kw: None)
        yg = P.from_weights(gw, gwB)
        rec["gauge"] = official(P, yg)
        rec["gauge"]["seconds"] = round(time.time() - t0, 1)
        cands = [(yg, rec["gauge"], "gauge")]
        t0 = time.time()
        rf = dr.refit(P, yg, targets, max_evals=args.max_evals, log=lambda **kw: None)
        rec["refit"] = {"stop": rf["stop"], "evals": rf["evals"], "iterations": rf["iterations"],
                        "seconds": round(time.time() - t0, 1)}
        if rf["y"] is not None:
            yr = rf["y"]
            rec["refit"].update(official(P, yr))
            cands.append((yr, rec["refit"], "refit"))
        # continue from the numerically lowest official lambda_eff even when it does not pass yet
        yb, db, how = min(cands, key=lambda c: c[1]["lambda_eff"])
        rec["kept"] = how
        cur = yb
        if db["lambda_eff"] < best["lambda_eff"]:
            best = {"lambda_eff": db["lambda_eff"], "y": yb.copy(), "metrics": db, "round": k, "how": how}
        log["rounds"].append(rec)
        print(json.dumps(rec), flush=True)
        if db["passes"]:
            # one more round is still useful: gauge may lower lambda at the same errors
            pass
    log["best"] = {"round": best["round"], "how": best["how"], "metrics": best["metrics"]}
    log["seconds"] = round(time.time() - start, 1)
    (args.out_dir / "refit_probe.json").write_text(json.dumps(log, indent=1) + "\n")
    if best["y"] is not None:
        w, wB = P.split(best["y"])
        out = dict(z)
        out["W"] = w
        out["H2_I"] = wB
        np.savez(args.out_dir / "submission_best.npz", **out)
    print(json.dumps({"best": log["best"], "seconds": log["seconds"]}, indent=1))


if __name__ == "__main__":
    main()
