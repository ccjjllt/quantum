"""Shared phase model for the 41 fine rotations of the Syed V9 baseline.

Units: 1 unit = 2^-64 turns (the verifier fixed point).  A rotation with angle
theta half-turns on control mask f contributes theta*2^63 units on every x
where f(x)=1.  `T_units.npy` is the ideal fine phase after removing the exact
Clifford/T part; the verifier error is `phase - T` (mod 2^64) and must stay
inside `tol_units.npy`.

Reproduced baseline (this module): min(tol-|err|) = 58,597,850 units at
x=52,229; worst |err|/tol = 0.9993237694056958 at x=161, identical to the
official run.
"""
from __future__ import annotations

import base64
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
BASE_KMB = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
ART = ROOT / "artifacts/20261107_mask_refit"

MAXX = 3_133_452
NB = (MAXX + 7) // 8
MASK64 = (1 << 64) - 1
SHIFT = 24          # LP works in units 2^-40 turns
ONE_TURN_LP = 1 << 40

OFFICIAL = {
    "score": 97700.776777236,
    "C": 1575.818980278,
    "toffoli": 1280.7281563891038,
    "t_base": 1.0,
    "n_rot": 41,
    "eps": 2.434041480874084e-13,
    "baseline_margin": 58597850,
    "worst_ratio": 0.9993237694056958,
    "worst_x": 161,
}
T_PER_TOFFOLI = 4.0


# ---------------------------------------------------------------- loading


def int_from_b64(s: str) -> int:
    return int.from_bytes(base64.b64decode(s), "little")


def unpack_int(v: int) -> np.ndarray:
    return np.unpackbits(
        np.frombuffer(v.to_bytes(NB, "little"), dtype=np.uint8), bitorder="little"
    )[:MAXX].astype(bool)


def load_model() -> dict:
    data = json.loads((ROT33 / "masks_full.json").read_text())
    thetas = np.array(
        [int(round(Fraction(t) * (1 << 63))) for t in data["angles_half_turns"]],
        dtype=np.int64,
    )
    masks = [unpack_int(int_from_b64(m["mask_b64"])) for m in data["masks"]]
    return {
        "data": data,
        "ops": list(data["ops"]),
        "targets": list(data["targets"]),
        "thetas": thetas,
        "masks": masks,
        "T": np.load(ROT33 / "T_units.npy").view(np.int64),
        "tol": np.load(ROT33 / "tol_units.npy").view(np.int64),
    }


# ---------------------------------------------------------------- phase


def phase_of(masks, thetas) -> np.ndarray:
    """Sum theta_i * mask_i over all legal x, uint64 mod 2^64."""
    phase = np.zeros(MAXX, dtype=np.uint64)
    for m, t in zip(masks, thetas):
        if t:
            phase += np.uint64(t) * m.astype(np.uint64)
    return phase


def err_of(phase, T) -> np.ndarray:
    return (phase - T.view(np.uint64)).view(np.int64)


def margins(phase, T, tol):
    err = err_of(phase, T)
    used = np.abs(err)
    margin = tol - used
    i = int(np.argmin(margin))
    ratio = np.divide(used.astype(np.float64), tol.astype(np.float64))
    j = int(np.argmax(ratio))
    return {
        "margin_units": int(margin[i]),
        "margin_x": i + 1,
        "margin_turns": float(margin[i]) / 2**64,
        "worst_ratio": float(ratio[j]),
        "worst_x": j + 1,
    }


def rotation_t_count(eps: float) -> float:
    return 0.56 * math.log2(1 / eps) + 5.3


def cost(margin_units: int, extra_C: float = 0.0, n_rot: int = 41) -> dict:
    """Verifier C/score from a full-domain min margin in units 2^-64."""
    eps = math.pi * margin_units / 2**64 / n_rot
    rot_t = n_rot * rotation_t_count(eps)
    C = OFFICIAL["toffoli"] + extra_C + (OFFICIAL["t_base"] + rot_t) / T_PER_TOFFOLI
    return {
        "eps": eps,
        "rotation_C": rot_t / T_PER_TOFFOLI,
        "C": C,
        "score": 62 * C,
        "saving": OFFICIAL["C"] - C,
    }


def margin_saving_C(m0: int, m1: int) -> float:
    """Rotation synthesis C saved by raising the min margin m0 -> m1."""
    return 41 * 0.56 / T_PER_TOFFOLI * math.log2(m1 / m0)


# ---------------------------------------------------------------- LP


def constraint_matrix(masks, idx) -> np.ndarray:
    return np.stack([m[idx].astype(np.float64) for m in masks], axis=1)


def solve_lp(A: np.ndarray, E: np.ndarray, Ts: np.ndarray, bounds):
    """max m  s.t.  |E - A d| <= Ts - m.  Returns (d, m)."""
    from scipy.optimize import linprog

    n = len(E)
    # |E - A d| <= Ts - m  <=>  A d + m <= Ts + E  and  -A d + m <= Ts - E
    AA = np.vstack([np.c_[A, np.ones(n)], np.c_[-A, np.ones(n)]])
    bb = np.r_[Ts + E, Ts - E]
    c = np.r_[np.zeros(A.shape[1]), -1.0]
    sol = linprog(c, A_ub=AA, b_ub=bb, bounds=list(bounds) + [(None, None)],
                  method="highs")
    if not sol.success:
        raise RuntimeError(f"LP failed: {sol.message}")
    return sol.x[:-1], float(sol.x[-1])


def refit(masks, theta0, T, tol, idx0, *, max_iter=10, add=3000, verbose=False):
    """Active-set max-margin refit of all 41 angles.

    Returns theta (int64 units 2^-64), margin history and best theta.
    """
    theta = np.array(theta0, dtype=np.int64, copy=True)
    idx = np.unique(np.asarray(idx0, dtype=np.int64))
    hist, best = [], None
    for it in range(max_iter):
        A = constraint_matrix(masks, idx)
        ph = phase_of(masks, theta)
        E = (T - ph.view(np.int64)).astype(np.float64) / 2**SHIFT
        Ts = tol.astype(np.float64) / 2**SHIFT
        bnds = [(-2_000_000.0, 2_000_000.0)] * len(masks)
        d, m = solve_lp(A, E[idx], Ts[idx], bnds)
        new = theta + np.round(d * 2**SHIFT).astype(np.int64)
        ph = phase_of(masks, new)
        st = margins(ph, T, tol)
        row = {"iter": it, "ncon": int(len(idx)),
               "lp_margin_units": m * 2**SHIFT,
               "full_margin_units": st["margin_units"],
               "full_margin_x": st["margin_x"],
               "worst_ratio": st["worst_ratio"], "worst_x": st["worst_x"]}
        hist.append(row)
        if verbose:
            print(json.dumps(row), flush=True)
        if best is None or st["margin_units"] > best[0]:
            best = (st["margin_units"], new.copy())
        if m * 2**SHIFT - st["margin_units"] < 8:
            break
        err = err_of(ph, T)
        margin = tol - np.abs(err)
        take = np.argpartition(margin, min(add, MAXX - 1))[: min(add, MAXX - 1)]
        idx = np.unique(np.r_[idx, take])
    return {"theta": best[1], "margin": best[0], "history": hist}


def replace_lp(masks, theta0, T, tol, idx, i, g, *, dbound=2_000_000.0,
               ibound=float(1 << 39)):
    """One LP solve with mask i replaced by g (arrays over all x).

    Returns (new_theta, lp_margin_units) where lp margin is in 2^-64 units.
    d_j are angle changes; the replacement column is g, and the base residual
    is corrected by moving the old contribution theta_i*(f_i -> g).
    """
    A = constraint_matrix([g if j == i else masks[j] for j in range(len(masks))], idx)
    ph = phase_of(masks, theta0)
    R = (T - ph.view(np.int64)).astype(np.float64) / 2**SHIFT
    old = masks[i][idx].astype(np.float64) * (theta0[i] / 2**SHIFT)
    new = g[idx].astype(np.float64) * (theta0[i] / 2**SHIFT)
    E = R[idx] + old - new
    Ts = tol.astype(np.float64) / 2**SHIFT
    bnds = [(-dbound, dbound)] * len(masks)
    bnds[i] = (-ibound, ibound)
    d, m = solve_lp(A, E, Ts[idx], bnds)
    new_theta = theta0 + np.round(d * 2**SHIFT).astype(np.int64)
    return new_theta, m * 2**SHIFT, d
