#!/usr/bin/env python
"""Stage A screen for the B=143 -> 129 chemistry idea (see ../chem_plan.md, sections 4-5).

Question
--------
The public chemistry block is 4,033 loader Toffolis/pass, T=14,728, Q=427, lambda_eff=46.9070,
cost 294,991,455.82, with (R,B,C)=(8,143,44), brot=8, J=5.  Because the verifier's own cost model
keeps `b2 = ceil(log2 B) + 11 = 19` and `ceil((B+1)/16) = 9` constant for every B in [129,143], the
inner PREPARE Toffolis and Q_total barely move in that band while the ANGLE address count
`R*B` (1,144 -> 1,032) falls: the loader gets cheaper for free.  The only thing that can block the
move is the 8-bit accuracy gate, and that is what this script measures.

What it does, per grid point
----------------------------
1. Truncate the shipped submitted table to (8, B, C): keep the `B` largest W columns per group,
   keep their angle words unchanged, cut `angle_words` to `76 + R*B` rows.  Increasing C splits the
   largest columns by 1/sqrt(2) in pairs, which leaves the two-body tensor, h1', E_gap and Lambda
   exactly invariant (a neutral warm start, not a new table).
2. Refit **only** `W (R,B,C)` and `H2_I (R,C)` at fixed words / U / tree with the public
   Apache-2.0 constrained refit of `vendor/dfthc_refit/`: minimise `log lambda_eff` under quadratic
   penalties for `error_2 > target` and `E_gap < floor`, exact numpy gradients from
   `refit_weights.WeightProblem`, L-BFGS-B with upstream's scaling and settings, then upstream's
   exact column-gauge moves and offset solve (`refine.rotate_columns`, `refine.optimize_offsets`).
3. Read `error_1, error_2, Lambda, E_gap, lambda_eff` back through the **unmodified official**
   `dfthcsos.verify.load_inputs` + `evaluate_words`, and `T_heur / Q` through the unmodified
   `dfthcsos.verify.heuristic_costs`.
4. Print one row per grid point, an L-BFGS trace, and a PASS/FAIL verdict against the gates.

What it does NOT do: no Givens-word rounding, no tree change, no `brot`/`J` change, no kickmix
simulation, no loader synthesis (the loader term is a calibrated model, see LOADER_MODEL), no
submission, no GPU.

Runtime (measured here; see README for the estimates and the guards)
    decode u ~4 s | error_terms 0.3 s here (~10-25 s on Kaggle CPU) | one L-BFGS iteration ~40 ms
    here (~60-120 ms on Kaggle CPU) | one-body polish per accepted state ~10-30 s

Usage (Kaggle script kernel or local; CPU only)
    python stage_a.py --submission-path /kaggle/input/qcc-chemistry-4033-toffoli-loaders/submission.npz
    python stage_a.py --submission-url  "$CHEM4033_URL"
    python stage_a.py --dry-run                 # inputs + cost model only, no refit, ~25 s
    python stage_a.py --b-list 143,129 --c-list 44 --maxiter 6000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor" / "dfthc_refit"

# ---------------------------------------------------------------------------------------------
# Pins
# ---------------------------------------------------------------------------------------------
SOURCE_SHA256 = "3f864a7aeaa4d78984c8822761782b63be2d553b229f487e79640a73be147c44"
SOURCE_REF = "maoxin123/qcc-chemistry-4033-toffoli-loaders v1 (CC0, 2026-11-14T13:02:23Z)"
SOURCE_URL_ENV = "CHEM4033_URL"

# Baseline for the relative geometric-mean delta (the shipped 4,033 file).
BASE_COST = 46.90701390190118 * 14728 * 427  # 294,991,455.81905466

# Competition gates (dfthcsos/verify.py, unchanged).
ERROR_1_GATE = 0.020        # Ha
ERROR_2_GATE = 0.020        # Ha
E_GAP_FLOOR = 3.914898      # Ha, strict
LAMBDA_FLOOR = 49.0         # strict
QUBIT_CAP = 128

# Fixed geometry for this experiment.
R = 8
N_ORB = 76
BROT = 8
J = 5
N_WORDS = N_ORB - 1         # 75 tree edges
K_CIRCUITS = math.ceil(N_WORDS / J)

# Loader model, calibrated on public data (chem_plan.md section 5.1):
#   one ANGLE circuit = 80 relation/cache ANDs + 189 products at R*B = 1,144,
#   i.e. L(pass) = K_CIRCUITS * (80 + d * R*B) with d = 189/1144 = 0.1650.
#   Independent check on Lera's (9,143,40) family (1,287 rows, 297-299 Toffoli/loader) -> d = 0.1686.
#   d = 0.1650 reproduces the shipped 4,033 (model 4,031); 0.1686 is the pessimistic bound.
LOADER_D_PRIMARY = 0.16509      # (4033/15 - 80)/1144, anchored on the measured 4,033/pass at R*B=1,144
LOADER_D_PESSIMISTIC = 0.1686   # (297 - 80)/1287, from Lera's (9,143,40) family
LOADER_FIXED_ANDS = 80.0


# ---------------------------------------------------------------------------------------------
# Vendored public refit (Apache-2.0, see vendor/dfthc_refit/SOURCES.md)
# ---------------------------------------------------------------------------------------------
def _bootstrap_vendor() -> None:
    """Put the vendored dfthc_refit modules and the competition verifiers on sys.path."""
    if not VENDOR.is_dir():
        sys.exit(f"missing {VENDOR} (see vendor/dfthc_refit/SOURCES.md)")
    os.environ.setdefault("DFTHC_DATA", str(HERE.parents[3] / "data" / "competition"))
    sys.path.insert(0, str(VENDOR))


_bootstrap_vendor()

import encode  # noqa: E402  (vendored)
import onebody  # noqa: E402  (vendored)
import paths  # noqa: E402  (vendored; inserts the verifiers on sys.path)
import refine  # noqa: E402  (vendored)
import refit_weights  # noqa: E402  (vendored)
from scipy.optimize import linear_sum_assignment, minimize  # noqa: E402
from dfthcsos.scoreinfra.reference import UPPER_ENERGY, check_fcidump, load_reference  # noqa: E402
from dfthcsos.verify import heuristic_costs, native_inputs  # noqa: E402  (official, unmodified)


# ---------------------------------------------------------------------------------------------
# One-body assembly without JAX
# ---------------------------------------------------------------------------------------------
def _align_rows(words, vecs, edges, brot):
    """Permute word rows so that row j is the row the verifier will pair with eigenvalue j.

    The verifier pairs each submitted one-body row with an exact eigenvector of h1' by a one-to-one
    assignment on |overlap| (`reconstruct_h1_thc`), so row order is free for it.  `onebody.polish`
    and `onebody.error` do not match: they assume row j is the j-th ascending eigenvector.  A table
    built by `encode.signed_words(eigvecs.T, ...)` is already in that order; a foreign table (like
    the shipped 4,033 one) need not be, and polishing it unaligned silently optimises the wrong
    pairing (~25 mHa instead of ~20 mHa on the shipped rows).
    """
    mod = 1 << brot
    v = encode.decode(np.asarray(words, np.int64) % mod, edges, brot)
    sub, ideal = linear_sum_assignment(-np.abs(v @ vecs))
    out = np.array(words, np.int64).copy()
    out[ideal] = np.asarray(words, np.int64)[sub]
    return out


def assemble_numpy(words2, w, W, p, edges, brot, one_start=None):
    """`refine.assemble` with its one-body step reduced to the numpy candidates of `onebody.refresh`.

    Upstream `refine.assemble` calls `onebody.refresh`, which additionally imports the JAX module
    `onebody_quant` (progressive one-body rounding) and runs `kicks` random restarts.  This keeps
    upstream's other two candidates -- the rounded eigenvectors of h1' and the caller's `one_start`
    -- polished with `onebody.polish`, and drops the JAX candidate and the kicks, after aligning
    `one_start` to the eigenbasis (see `_align_rows`).  `error_2`, `Lambda`, `E_gap` and
    `lambda_eff` do not depend on the one-body rows at all; only `error_1` does, and it is reported
    per row.  `--final` uses the full upstream path (needs jax).
    """
    h1p = p.h1(W)
    _, vecs = np.linalg.eigh(h1p)
    wide = (-4, -2, -1, 1, 2, 4)
    cands = [encode.signed_words(vecs.T, edges, brot)]
    if one_start is not None:
        cands.append(_align_rows(one_start, vecs, edges, brot))
    cands = [onebody.polish(c, h1p, edges, brot, steps=wide) for c in cands]
    one = min(cands, key=lambda c: onebody.error(c, h1p, edges, brot))
    with np.load(paths.SHIFTS) as z:
        shifts = {k: np.array(z[k]) for k in ("H1_I", "Hsym_lower")}
    return {
        "U": p.u,
        "W": w,
        "H2_I": W + w.sum(axis=1),
        **shifts,
        "tree_edges": edges,
        "angle_words": np.vstack([one, words2]),
        "brot": brot,
    }


# ---------------------------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_submission(args) -> Path:
    if args.submission_path:
        path = Path(args.submission_path)
        if not path.is_file():
            sys.exit(f"--submission-path not found: {path}")
    else:
        url = args.submission_url or os.environ.get(SOURCE_URL_ENV, "")
        if not url:
            sys.exit(
                "no input: pass --submission-path, or --submission-url, or set "
                f"{SOURCE_URL_ENV}.  Source must be {SOURCE_REF}."
            )
        path = HERE / "submission.npz"
        print(f"downloading signed URL -> {path}")
        urllib.request.urlretrieve(url, path)  # noqa: S310 (explicit signed URL, user supplied)
    digest = sha256_file(path)
    if digest != SOURCE_SHA256:
        sys.exit(f"SHA-256 mismatch: {digest} != {SOURCE_SHA256}\nThis screen is pinned to {SOURCE_REF}.")
    print(f"input {path} sha256 {digest} OK ({path.stat().st_size} bytes)")
    return path


def load_source(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        data = {k: np.array(z[k]) for k in z.files}
    if data["W"].shape != (R, 143, 44):
        sys.exit(f"unexpected W shape {data['W'].shape}, expected (8, 143, 44)")
    if int(data["angle_words"].max()) > (1 << BROT) - 1:
        sys.exit("angle words wider than brot=8")
    return data


# ---------------------------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------------------------
def _b_scores(W: np.ndarray, metric: str) -> np.ndarray:
    """Per-b magnitude of one group's weight matrix W_r (B, C)."""
    if metric == "l2":
        return np.linalg.norm(W, axis=1)
    if metric == "l1":
        return np.abs(W).sum(axis=1)
    if metric == "max":
        return np.abs(W).max(axis=1)
    raise SystemExit(f"unknown --drop-metric {metric}")


def _cand(U, w, wB, words, edges) -> dict:
    return {
        "U": np.ascontiguousarray(U, np.float64),
        "W": np.ascontiguousarray(w, np.float64),
        "H2_I": np.ascontiguousarray(wB, np.float64),
        # Both are ignored by the verifier (load_inputs replaces them with the fixed shifts file)
        # and by refit_weights.refit (it reads paths.SHIFTS).  Values here are placeholders.
        "H1_I": np.float32(0.0),
        "Hsym_lower": np.zeros(2926, np.float32),
        "tree_edges": edges,
        "angle_words": np.ascontiguousarray(words, np.int64),
        "brot": BROT,
    }


def truncate(data: dict, B: int, C: int, metric: str = "l2") -> dict:
    """The submitted table cut to (R, B, C): same words, same U rows, fewer or wider groups."""
    W0 = np.asarray(data["W"], np.float64)         # lowercase w (R, 143, C0)
    wB0 = np.asarray(data["H2_I"], np.float64)     # w_B = W + sum_b w  (R, C0)
    words = np.asarray(data["angle_words"], np.int64)
    edges = np.asarray(data["tree_edges"], np.int64)
    U0 = np.asarray(data["U"], np.float64)
    R0, B0, C0 = W0.shape
    assert words.shape == (N_ORB + R0 * B0, N_WORDS), words.shape

    keep = [np.sort(np.argsort(-_b_scores(W0[r], metric), kind="stable")[:B]) for r in range(R0)]
    Ws = np.stack([W0[r][keep[r]] for r in range(R0)])           # (R, B, C0)
    Us = np.stack([U0[r][keep[r]] for r in range(R0)])
    words_s = np.vstack([words[:N_ORB]] + [words[N_ORB + r * B0 + keep[r]] for r in range(R0)])

    if C == C0:
        return _cand(Us, Ws, wB0, words_s, edges)

    if C < C0:
        idx = [np.sort(np.argsort(-np.linalg.norm(Ws[r], axis=0), kind="stable")[:C]) for r in range(R0)]
        return _cand(Us,
                     np.stack([Ws[r][:, idx[r]] for r in range(R0)]),
                     np.stack([wB0[r][idx[r]] for r in range(R0)]),
                     words_s, edges)

    # C > C0: split the largest columns in pairs by 1/sqrt(2).  k_rb = sum_c W_rc w_rbc, the
    # two-body tensor and the Lambda term (|w|_1 + |w_B|)^2 are all invariant, so this is a neutral
    # warm start with more freedom for the refit.
    extra = C - C0
    Wl = [Ws[r].copy() for r in range(R0)]
    wBl = [wB0[r].copy() for r in range(R0)]
    for r in range(R0):
        for c in np.argsort(-np.linalg.norm(Wl[r], axis=0), kind="stable")[:extra]:
            Wl[r][:, c] /= math.sqrt(2)
            wBl[r][c] /= math.sqrt(2)
            Wl[r] = np.concatenate([Wl[r], Wl[r][:, c : c + 1]], axis=1)
            wBl[r] = np.concatenate([wBl[r], wBl[r][c : c + 1]])
    return _cand(Us, np.stack(Wl), np.stack(wBl), words_s, edges)


# ---------------------------------------------------------------------------------------------
# Constrained refit: upstream objective + optimizer, reporting the whole trace
# ---------------------------------------------------------------------------------------------
class _Reached(Exception):
    """Raised from the L-BFGS callback once error_2 has reached the target."""


def refit_w_W(cand: dict, target_mha: float, margin: float, maxiter: int, log_every: int,
              rounds: int = 1, gauge_hops: int = 10, log=print):
    """Refit (w, W) at fixed words.  This is `vendor/dfthc_refit/refit_weights.py:refit()` with its
    acceptance wrapper opened up.

    Identical to upstream: `error_terms`, `WeightProblem.evaluate` (exact gradients), the objective
    `f = 0.5 log(E_gap (2 Lambda - E_gap))` plus the two quadratic penalties, the per-block rescaling
    of (w, W), L-BFGS-B with `maxcor=30, ftol=1e-15, gtol=1e-10, maxls=50`.  Changes: (a) a
    callback records the trace and stops as soon as `error_2 <= target`, (b) the result is returned
    even when it misses the gates, because the point of this screen is to measure how close the
    shape gets.  Upstream's wrapper otherwise discards the refit and returns the input.

    Returns (data, metrics, trace) where metrics come from `refine.official` (official
    `evaluate_words`) and trace is a list of dicts.
    """
    brot = BROT
    edges = np.asarray(cand["tree_edges"], np.int64)
    w0 = np.asarray(cand["W"], np.float64)
    W0 = np.asarray(cand["H2_I"], np.float64) - w0.sum(axis=1)
    R_, B_, C_ = w0.shape
    N = edges.shape[0] + 1
    words2 = np.asarray(cand["angle_words"], np.int64)[N:]
    u = encode.decode(words2, edges, brot).reshape(R_, B_, N)
    u /= np.linalg.norm(u, axis=2, keepdims=True)

    ref = load_reference(check_fcidump())
    with np.load(paths.SHIFTS) as z:
        _, _, S, beta = native_inputs({"U": u, "W": w0, "H2_I": cand["H2_I"],
                                    "H1_I": z["H1_I"], "Hsym_lower": z["Hsym_lower"]})
    eta = int(ref["electrons"])
    K, Q, T2 = refit_weights.error_terms(u, np.asarray(ref["tei"], np.float64), S)
    wp = refit_weights.WeightProblem(u, K, Q, T2, ref["h1_thc"] - 0.5 * eta * S + beta * np.eye(N),
                                     float(UPPER_ENERGY - ref["ecore"] + eta * beta))
    target, floor = 1e-3 * target_mha, refine.GAP_FLOOR + margin
    log(f"start: error_2 {1e3 * wp.error_2(w0)[0]:.4f} mHa (target {target_mha}), "
        f"W offsets std {np.std(W0):.4g}")

    def objective(x):
        w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
        (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
        rad = gap * (2 * Lam - gap)
        if rad <= 0:  # outside the verifier's domain: reject the line-search step
            return 1e12, np.zeros_like(x)
        f = 0.5 * np.log(rad)
        gw, gW = [((Lam - gap) * g + gap * l) / rad for g, l in zip(dgap, dLam)]
        if e2 > target:
            f += 1e6 * (e2 - target) ** 2
            gw = gw + 2e6 * (e2 - target) * de2
        if gap < floor:
            f += 1e5 * (floor - gap) ** 2
            gw, gW = gw - 2e5 * (floor - gap) * dgap[0], gW - 2e5 * (floor - gap) * dgap[1]
        return f, np.concatenate([gw.ravel(), gW.ravel()])

    scale = np.concatenate([np.full(w0.size, np.std(w0)), np.full(W0.size, np.std(W0))])

    def scaled(y):
        f, g = objective(y * scale)
        return f, g * scale

    trace, state = [], {}

    def callback(xk):
        x = xk * scale
        (e2, gap, Lam), _ = wp.evaluate(x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape))
        state["x"] = x
        lam = math.sqrt(max(gap * (2 * Lam - gap), 0.0))
        trace.append({"iter": len(trace), "e2_mHa": 1e3 * e2, "E_gap": gap,
                      "Lambda": Lam, "lambda_eff": lam})
        if log_every and len(trace) % log_every == 0:
            log(f"  it {len(trace):5d}  e2 {1e3 * e2:8.3f} mHa  gap {gap:.6f}  "
                f"Lambda {Lam:7.3f}  lambda_eff {lam:.4f}")
        if e2 <= target:
            raise _Reached

    x0 = np.concatenate([w0.ravel(), W0.ravel()]) / scale
    res_msg = "maxiter"
    try:
        res = minimize(scaled, x0, jac=True, method="L-BFGS-B",
                       callback=callback,
                       options={"maxiter": maxiter, "maxcor": 30, "ftol": 1e-15, "gtol": 1e-10,
                                "maxls": 50})
        res_msg = str(res.message)
        state["x"] = res.x * scale
    except _Reached:
        res_msg = f"target {target_mha} mHa reached"

    x = state.get("x", x0 * scale)
    w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
    (e2, gap, Lam), _ = wp.evaluate(w, W)
    log(f"L-BFGS: {res_msg} after {len(trace)} iterations: e2 {1e3 * e2:.4f} mHa, "
        f"E_gap {gap:.9f}, Lambda {Lam:.4f}, lambda_eff {math.sqrt(max(gap * (2 * Lam - gap), 0)):.4f}")

    # Upstream's round body, verbatim in order: exact column gauge (it leaves w w^T, w W^T and
    # |W|^2 alone, so error_2 and h1' are unchanged and only the L1 term of Lambda moves), then the
    # offset solve, then the official read-back; keep the best lambda_eff that keeps error_2.
    one_start = np.asarray(cand["angle_words"])[:N]
    best = None
    for r in range(rounds):
        w, W = refine.rotate_columns(w, W, sweeps=2, seed=r, hops=gauge_hops)
        p = refine.Problem(u, w, ref, S, beta)
        W = refine.optimize_offsets(p, W, margin)
        table = (refine.assemble(words2, w, W, p, edges, brot, one_start=one_start)
                 if _USE_UPSTREAM_ONE_BODY else
                 assemble_numpy(words2, w, W, p, edges, brot, one_start=one_start))
        metrics = refine.official(table, brot)
        log(f"round {r}: e1 {1e3 * metrics['error_1']:.4f}  e2 {1e3 * metrics['error_2']:.4f} mHa  "
            f"Lambda {metrics['Lambda']:.4f}  E_gap {metrics['E_gap']:.9f}  "
            f"lambda_eff {metrics['lambda_eff']:.6f}")
        ok = (metrics["error_2"] <= ERROR_2_GATE and metrics["E_gap"] > E_GAP_FLOOR
              and metrics["Lambda"] > LAMBDA_FLOOR)
        if ok and (best is None or metrics["lambda_eff"] < best[1]["lambda_eff"]):
            best = (table, metrics)
    if best is None:
        best = (table, metrics)
    return best[0], best[1], trace


_USE_UPSTREAM_ONE_BODY = False


# ---------------------------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------------------------
def cost_row(B: int, C: int, lambda_eff: float, d: float) -> dict:
    hc = heuristic_costs(N_ORB, R, B, C, BROT)          # official, unmodified
    selection = math.ceil(math.log2(N_ORB + R * B))
    words = J * BROT
    # resource_costs(): Q = persistent + J*brot + max(heuristic_temp, angles_temp); the shipped k0
    # loader fills the 128-qubit cap, so angles_temp = 128 - selection - words is the exact value.
    q = hc["persistent_qubits"] + words + max(hc["temporary_qubits"], QUBIT_CAP - selection - words)
    loader_per_pass = K_CIRCUITS * (LOADER_FIXED_ANDS + d * R * B)
    t_total = 2.0 * loader_per_pass + hc["toffoli"]
    return {
        "selection": selection, "T_heur": hc["toffoli"], "outer": hc["outer_state_prep_toffoli"],
        "inner": hc["inner_state_prep_toffoli"], "givens": hc["givens_rotations_toffoli"],
        "loader_per_pass": loader_per_pass, "T": t_total, "Q": q,
        "cost": lambda_eff * t_total * q,
    }


def gates(m: dict) -> tuple[bool, list[str]]:
    bad = []
    if not m["error_1"] <= ERROR_1_GATE:
        bad.append("e1")
    if not m["error_2"] <= ERROR_2_GATE:
        bad.append("e2")
    if not m["E_gap"] > E_GAP_FLOOR:
        bad.append("E_gap")
    if not m["Lambda"] > LAMBDA_FLOOR:
        bad.append("Lambda")
    return (not bad), bad


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def main() -> None:
    global _USE_UPSTREAM_ONE_BODY
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--submission-path", type=Path, help="local submission.npz of the 4,033 dataset")
    ap.add_argument("--submission-url", help="signed URL for the same file (or set CHEM4033_URL)")
    ap.add_argument("--b-list", default="143,139,135,131,129")
    ap.add_argument("--c-list", default="44,46,48")
    ap.add_argument("--drop-metric", default="l2", choices=("l2", "l1", "max"))
    ap.add_argument("--target", type=float, default=19.99,
                    help="error_2 target in mHa.  The gate is 20.0 and lambda_eff is smallest at the "
                         "largest allowed error, so the public refits sit at 19.9999 mHa; upstream's "
                         "own 19.92 default only helps tables whose frozen-word floor is well below it.")
    ap.add_argument("--margin", type=float, default=1e-5,
                    help="E_gap kept this far above the floor (Ha).  The verifier floor is strict; the "
                         "shipped file sits 4e-9 above it, but L-BFGS lands ~3e-7 Ha low on the offset "
                         "solve, so 1e-5 Ha (1.3e-6 of lambda_eff) is the smallest safe cushion.")
    ap.add_argument("--maxiter", type=int, default=6000, help="L-BFGS iterations per grid point")
    ap.add_argument("--log-every", type=int, default=250, help="print the trace every N iterations")
    ap.add_argument("--rounds", type=int, default=1,
                    help="refine.py gauge+offset rounds per point (upstream default 3; 1 is enough to screen)")
    ap.add_argument("--gauge-hops", type=int, default=10,
                    help="basin-hopping rounds inside refine.rotate_columns (upstream 10; 0 is faster)")
    ap.add_argument("--final", action="store_true",
                    help="use the unmodified upstream one-body step (needs jax) -- for finalists only")
    ap.add_argument("--dry-run", action="store_true", help="inputs + cost model only, no refit")
    ap.add_argument("--no-early-stop", action="store_true",
                    help="keep descending B after an e2 > 20.5 mHa flag")
    ap.add_argument("--max-minutes", type=float, default=0.0, help="stop after this wall time (0 = off)")
    ap.add_argument("--json-out", type=Path, default=HERE / "stage_a_results.json")
    args = ap.parse_args()

    _USE_UPSTREAM_ONE_BODY = bool(args.final)
    if args.final:
        try:
            import onebody_quant  # noqa: F401  (JAX; only imported to fail early and clearly)
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"--final needs jax (and the upstream onebody_quant module): {exc}")

    data = load_source(fetch_submission(args))
    edges = np.asarray(data["tree_edges"], np.int64)
    print(f"source: {SOURCE_REF}")
    print(f"shipped table: (R,B,C)=({R},{data['W'].shape[1]},{data['W'].shape[2]}) "
          f"brot={BROT} J={J} rows={data['angle_words'].shape[0]} edges={edges.shape[0]}")
    print("official cost model of the shipped shape: T_heur=6662 (317 outer + 4095 inner + 2250 givens); "
          "Q=84 persistent + 40 words + 303 inner temp = 427")

    b_list = [int(x) for x in args.b_list.split(",") if x.strip()]
    c_list = [int(x) for x in args.c_list.split(",") if x.strip()]

    rows = []
    t_start = time.time()
    for C in c_list:
        for B in b_list:
            if args.max_minutes and (time.time() - t_start) / 60.0 > args.max_minutes:
                print(f"\n[budget] exceeded --max-minutes {args.max_minutes}: stopping")
                break
            t0 = time.time()
            cand = truncate(data, B, C, args.drop_metric)
            base = cost_row(B, C, 1.0, LOADER_D_PRIMARY)
            print(f"\n=== B={B} C={C}  P={R * B * C}  rows={N_ORB + R * B}  sel={base['selection']}  "
                  f"T_heur={base['T_heur']} (inner {base['inner']})  Q={base['Q']}  "
                  f"L~{base['loader_per_pass']:.0f}/pass ===", flush=True)
            if args.dry_run:
                m = refine.official(cand, BROT)     # official evaluate_words, no refit
                trace, note = [], "dry-run (no refit)"
            else:
                _, m, trace = refit_w_W(cand, args.target, args.margin, args.maxiter, args.log_every,
                                    rounds=args.rounds, gauge_hops=args.gauge_hops)
                note = ""
            ok, bad = gates(m)
            decisive = [g for g in bad if g != "e1"]
            c1 = cost_row(B, C, m["lambda_eff"], LOADER_D_PRIMARY)
            c2 = cost_row(B, C, m["lambda_eff"], LOADER_D_PESSIMISTIC)
            row = {
                "B": B, "C": C, "P": R * B * C, "rows": N_ORB + R * B,
                "error_1_mHa": 1e3 * m["error_1"], "error_2_mHa": 1e3 * m["error_2"],
                "Lambda": m["Lambda"], "E_gap": m["E_gap"], "lambda_eff": m["lambda_eff"],
                "T_heur": c1["T_heur"], "inner": c1["inner"],
                "loader_per_pass": c1["loader_per_pass"], "T": c1["T"], "Q": c1["Q"],
                "cost": c1["cost"], "cost_pessimistic": c2["cost"],
                "dGM_pct": ((BASE_COST / c1["cost"]) ** (1 / 3) - 1) * 100,
                "pass": ok, "failed_gates": bad, "pass_decisive": not decisive,
                "note": note,
                "lbfgs_iters": len(trace),
                "seconds": round(time.time() - t0, 1),
                "trace_every": args.log_every,
                "trace": trace[:: max(1, args.log_every)][:80],
            }
            rows.append(row)
            print(f"    e1={row['error_1_mHa']:.4f} mHa  e2={row['error_2_mHa']:.4f} mHa  "
                  f"Lambda={row['Lambda']:.4f}  E_gap={row['E_gap']:.9f}  "
                  f"lambda_eff={row['lambda_eff']:.6f}")
            print(f"    T={row['T']:.0f}  Q={row['Q']}  cost={row['cost'] / 1e6:.2f}M  "
                  f"cost_pess={row['cost_pessimistic'] / 1e6:.2f}M  dGM={row['dGM_pct']:+.3f}%  "
                  f"{'PASS' if ok else 'FAIL ' + ','.join(bad)}  "
                  f"[{row['seconds']}s, {len(trace)} iters]", flush=True)
            if args.dry_run:
                continue
            if not ok and row["error_2_mHa"] > 20.5:
                print(f"    FLAG: e2 = {row['error_2_mHa']:.2f} mHa > 20.5 mHa; smaller B can only be "
                      f"worse at this C", flush=True)
                if not args.no_early_stop:
                    break
            if row["error_1_mHa"] > 20.0 and row["error_2_mHa"] <= 20.0:
                print("    NOTE: e2 clears the gate but the numpy one-body step did not; rerun this "
                      "point with --final (upstream JAX one-body) before judging it.", flush=True)

    # ---------------------------------------------------------------- report
    print("\n" + "=" * 130)
    print(f"Stage A grid -- fixed words/U/tree, only W and H2_I refitted "
          f"(target {args.target} mHa, E_gap floor +{args.margin:g} Ha, maxiter {args.maxiter})")
    print("=" * 130)
    head = (f"{'B':>4}{'C':>4}{'P':>7}{'e1(mHa)':>9}{'e2(mHa)':>9}{'Lambda':>9}{'E_gap':>13}"
            f"{'lam_eff':>10}{'T_heur':>8}{'L/pass':>8}{'T_tot':>8}{'Q':>5}{'cost(M)':>10}{'dGM%':>8}"
            f"{'iters':>7}{'gate':>9}")
    print(head)
    print("-" * len(head))
    for r in rows:
        print(f"{r['B']:>4}{r['C']:>4}{r['P']:>7}{r['error_1_mHa']:>9.3f}{r['error_2_mHa']:>9.3f}"
              f"{r['Lambda']:>9.3f}{r['E_gap']:>13.9f}{r['lambda_eff']:>10.4f}{r['T_heur']:>8}"
              f"{r['loader_per_pass']:>8.0f}{r['T']:>8.0f}{r['Q']:>5}{r['cost'] / 1e6:>10.2f}"
              f"{r['dGM_pct']:>+8.3f}{r['lbfgs_iters']:>7}"
              f"{('PASS' if r['pass'] else 'FAIL:' + ','.join(r['failed_gates'])):>9}")
    if not rows:
        print("(no rows)")
    else:
        print("\ncost with the pessimistic loader model d =", LOADER_D_PESSIMISTIC)
        for r in rows:
            print(f"  B={r['B']:>3} C={r['C']:>2}  cost={r['cost_pessimistic'] / 1e6:9.2f}M  "
                  f"dGM={((BASE_COST / r['cost_pessimistic']) ** (1 / 3) - 1) * 100:+7.3f}%  "
                  f"{'PASS' if r['pass'] else 'FAIL'}")

    best = min((r for r in rows if r["pass"]), key=lambda r: r["cost"], default=None)
    best_dec = min((r for r in rows if r["pass_decisive"]), key=lambda r: r["cost"], default=None)
    best_e2 = min(rows, key=lambda r: r["error_2_mHa"], default=None)
    print("\n" + "-" * 130)
    if args.dry_run:
        print("DRY RUN: the e2 column is the un-refitted truncation, which is expected to be far above "
              "20 mHa.  Rerun without --dry-run to refit.")
    elif best is not None and best["cost"] > BASE_COST * 0.995:
        print(f"VERDICT: NO GAIN -- the only passing point is (B,C)=({best['B']},{best['C']}) at "
              f"{best['cost'] / 1e6:.2f}M, which is the unmodified control (|dGM| "
              f"{abs(best['dGM_pct']):.3f}%).  Nothing in the grid beats the shipped point, so the "
              f"truncate-plus-weight-refit form of B<143 is closed; record the e2 column and stop.")
    elif best is not None:
        print(f"VERDICT: PASS at (B,C)=({best['B']},{best['C']}): cost {best['cost'] / 1e6:.2f}M "
              f"({best['cost'] / BASE_COST * 100 - 100:+.2f}%), dGM {best['dGM_pct']:+.3f}%. "
              f"Next: Stage B (15 loaders, <=128 qubits, <=3894 Toffolis/pass), then the full official "
              f"78,080-shot verifier at two salts.")
    elif best_dec is not None:
        print(f"VERDICT: PARTIAL -- (B,C)=({best_dec['B']},{best_dec['C']}) clears the decisive gates "
              f"(e2, E_gap, Lambda) but error_1 did not, because the numpy one-body step cannot absorb "
              f"the refitted h1'.  Rerun that point with --final (upstream JAX one-body) before judging "
              f"it; e1 does not depend on the shape, so this is a tooling gap, not a result.")
    else:
        print(f"VERDICT: FAIL -- no (B,C) in the grid clears the decisive gates.  Best e2 = "
              f"{best_e2['error_2_mHa']:.3f} mHa at (B,C)=({best_e2['B']},{best_e2['C']}) after "
              f"{best_e2['lbfgs_iters']} L-BFGS iterations.  If that floor is still >20.5 mHa, then "
              f"truncate-plus-weight-refit cannot open B<143: the dropped basis rows are not "
              f"recoverable by re-weighting the kept ones, and opening it needs a full refit of U and "
              f"a new word table (new loaders).  Record the column and stop.")
    print(f"total wall time {(time.time() - t_start) / 60:.1f} min, {len(rows)} grid points")

    payload = {
        "source_ref": SOURCE_REF, "source_sha256": SOURCE_SHA256,
        "upstream": "marculera/dfthc-compact-pipeline v7 dfthc_refit "
                    "(VERSION 704091bf1e1325b090202343e4d8130ff1c80b64, Apache-2.0)",
        "brot": BROT, "J": J, "R": R, "target_mHa": args.target, "margin_Ha": args.margin,
        "maxiter": args.maxiter, "drop_metric": args.drop_metric,
        "onebody": "upstream-jax" if args.final else "numpy",
        "loader_model": {"fixed_ands": LOADER_FIXED_ANDS, "d": LOADER_D_PRIMARY,
                         "d_pessimistic": LOADER_D_PESSIMISTIC, "circuits": K_CIRCUITS},
        "base_cost": BASE_COST, "rows": rows,
    }
    args.json_out.write_text(json.dumps(payload, indent=2, default=float))
    print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
