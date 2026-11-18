"""Chem brot, stage 2: a FULL weight refit at brot 7 (and the shipped end-to-end receipt).

Stage 1 (`qcc-chem-brot-trade`) showed that a re-quantisation of the shipped
8-bit angle table to 7 bits gives error_2 = 4.26e-1 and that a per-(rho,c)
block-scale refit only reaches 3.66e-1, against a 2.0e-2 gate. This kernel
removes the last doubt: it refits ALL 8*143*44 = 50,336 inner weights with
L-BFGS on the exact official residual, and reports the best error_2 that the
7-bit word table can reach at all.

It also re-verifies the shipped package (submission.npz + 15 loaders) end to end with the unmodified
official ``dfthcsos.verify.verify``.  Nothing is submitted.
"""
import base64
import hashlib
import io
import json
import lzma
import math
import sys
import time
from pathlib import Path

import numpy as np

WORK = Path("/kaggle/working")
T0 = time.time()
OUT = {"rows": []}


def say(tag, **kw):
    print(json.dumps({"tag": tag, **kw}, default=str), flush=True)
    OUT.setdefault("log", []).append({"tag": tag, "t": round(time.time() - T0, 1), **kw})


COMP = None
for _p in Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for _up in (_p.parents[1], _p.parents[2], _p.parents[3]):
        if (_up / "kickmix").is_dir():
            COMP = _up
            break
    if COMP:
        break
if COMP is None:
    raise SystemExit("competition data not mounted")
sys.path.insert(0, str(COMP / "verifiers"))
sys.path.insert(0, str(COMP / "kickmix"))
say("comp", comp=str(COMP))

from dfthcsos.verify import (  # noqa: E402
    E_GAP_FLOOR,
    ERROR_1_THRESHOLD,
    ERROR_2_THRESHOLD,
    LAMBDA_FLOOR,
    evaluate_words,
    load_inputs,
    verify,
)
from dfthcsos.scoreinfra import dfthc_math as M  # noqa: E402
from dfthcsos.scoreinfra.dfthc_math import (  # noqa: E402
    build_h1_prime,
    reconstruct_u_vectors,
    reconstruct_x,
)
from dfthcsos.scoreinfra.reference import UPPER_ENERGY  # noqa: E402

# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------
DIR = WORK / "dfthcsos"
DIR.mkdir(parents=True, exist_ok=True)
_blob = lzma.decompress(base64.b64decode(PAYLOAD_KMB_B64))
_off, _shas = 0, []
for _k in range(15):
    _n = PAYLOAD_LENS[_k]
    _data = _blob[_off : _off + _n]
    _off += _n
    (DIR / f"angle_k_{_k}.kmb").write_bytes(_data)
    _shas.append(hashlib.sha256(_data).hexdigest())
say("loaders", kmb_shas=_shas[:3] + ["..."] + _shas[-1:])

with np.load(io.BytesIO(lzma.decompress(base64.b64decode(PAYLOAD_NPZ_B64))),
             allow_pickle=False) as _z:
    ARR = {k: np.array(_z[k]) for k in _z.files}
TREE = np.asarray(ARR["tree_edges"], np.int64)
WORDS8 = np.asarray(ARR["angle_words"], np.int64)
NROWS, NANG = WORDS8.shape
NO = 76
RANK, BASES, COPIES = ARR["W"].shape
EDGES = [(int(a), int(b)) for a, b in TREE]


def decode(words, brot):
    return reconstruct_u_vectors(np.asarray(words) / (1 << (brot - 1)), TREE)


def encode_rows(vectors, brot):
    u = np.array(vectors, np.float64, copy=True)
    words = np.zeros((u.shape[0], NANG), np.int64)
    scale = 1 << (brot - 1)
    for t in range(NANG - 1, -1, -1):
        p, c = EDGES[t]
        th = np.arctan2(u[:, c], u[:, p])
        th = np.where(th < 0.0, th + 2.0 * np.pi, th)
        th = np.where(np.hypot(u[:, p], u[:, c]) < 1e-12, 0.0, th)
        words[:, t] = np.round(th / np.pi * scale).astype(np.int64) % (2 * scale)
        u[:, p] = np.hypot(u[:, p], u[:, c])
        u[:, c] = 0.0
    return words


V8 = decode(WORDS8, 8)
FACT = {"U": V8[NO:].reshape(RANK, BASES, NO), "W": ARR["W"], "H2_I": ARR["H2_I"],
        "H1_I": ARR["H1_I"], "Hsym_lower": ARR["Hsym_lower"]}
np.savez(DIR / "submission.npz", **FACT, tree_edges=TREE, angle_words=WORDS8.astype(np.int64))

inputs = load_inputs(FACT)
w0 = np.asarray(inputs.w, np.float64)
W0 = np.asarray(inputs.W, np.float64)
S = np.asarray(inputs.S, np.float64)
BETA1 = float(inputs.beta_1)
REF = inputs.ref
TEI = np.asarray(REF["tei"], np.float64)
NOCC = int(REF["electrons"])
h1_thc = np.asarray(REF["oei"], np.float64) - 0.5 * np.einsum("prrq->pq", TEI)
NN = NO * NO
i_diag = np.arange(NO)
TSYM = np.array(TEI, np.float64, copy=True)
TSYM[:, :, i_diag, i_diag] += 0.5 * S[:, :, None]
TSYM[i_diag, i_diag, :, :] += 0.5 * S[None, :, :]
say("ready", shape=[RANK, BASES, COPIES], seconds=round(time.time() - T0, 1))

# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------
ctl = evaluate_words(inputs, WORDS8, TREE, 8)
SHIP_LAMBDA = float(ctl["lambda_eff"])
SHIP_T, SHIP_Q = 14706.0, 427
SHIP_COST = SHIP_LAMBDA * SHIP_T * SHIP_Q
OUT["control"] = {k: (v if isinstance(v, bool) else float(v)) for k, v in ctl.items()}
say("control", **{k: v for k, v in OUT["control"].items() if isinstance(v, float)})
OUT["shipped"] = {"T": SHIP_T, "Q": SHIP_Q, "lambda_eff": SHIP_LAMBDA, "cost": SHIP_COST}
say("shipped", **OUT["shipped"])


def official(words, brot, wts, one_body=None):
    v = decode(words, brot)
    if one_body is not None:
        v = np.array(v, copy=True)
        v[:NO] = one_body
    return M.evaluate_dfthc_vectors(v, wts, W0, S, BETA1, REF, energy_upper=UPPER_ENERGY)


def h1p_of(words, brot, wts):
    Xs = reconstruct_x(decode(words, brot)[NO:].reshape(RANK, BASES, NO), wts)
    return build_h1_prime(h1_thc, S, BETA1, NOCC, W0, Xs)


def best_one_body(words1, brot, h1p, passes=6, restarts=3):
    """Lowest error_1 achievable for the 76 one-body rows at ``brot`` bits."""
    from scipy.optimize import linear_sum_assignment

    lam, vec = np.linalg.eigh(h1p)
    start = decode(words1, brot)
    ri, ci = linear_sum_assignment(-np.abs(start @ vec))
    target = np.zeros_like(start)
    target[ri] = vec[:, ci].T
    weight = np.zeros(len(ri))
    weight[ri] = lam[ci]
    scale = 1 << (brot - 1)
    grid = np.arange(2 * scale)
    cosg = np.cos(np.pi * grid / scale)
    sing = np.sin(np.pi * grid / scale)
    best_vec = start.copy()
    best = float(np.sum(weight ** 2 * np.sum(start * target, axis=1) ** 2))
    for _ in range(restarts):
        cur = encode_rows(best_vec, brot)
        z = np.zeros((len(cur), NO))
        z[:, 0] = 1.0
        U = target.copy()
        back = [None] * NANG
        for t in range(NANG - 1, -1, -1):
            back[t] = U.copy()
            p, c = EDGES[t]
            th = np.pi * cur[:, t] / scale
            cs, sn = np.cos(th), np.sin(th)
            up, uc = U[:, p].copy(), U[:, c].copy()
            U[:, p] = cs * up + sn * uc
            U[:, c] = -sn * up + cs * uc
        for t in range(NANG):
            p, c = EDGES[t]
            Uu = back[t]
            Aq = z[:, p] * Uu[:, p] + z[:, c] * Uu[:, c]
            Bq = z[:, p] * Uu[:, c] - z[:, c] * Uu[:, p]
            pick = np.argmax(Aq[:, None] * cosg[None, :] + Bq[:, None] * sing[None, :], axis=1)
            cur[:, t] = pick
            th = np.pi * pick / scale
            cs, sn = np.cos(th), np.sin(th)
            zp, zc = z[:, p].copy(), z[:, c].copy()
            z[:, p] = cs * zp - sn * zc
            z[:, c] = sn * zp + cs * zc
        cand = decode(cur, brot)
        score = float(np.sum(weight ** 2 * np.sum(cand * target, axis=1) ** 2))
        if score <= best:
            break
        best, best_vec = score, cand
    return best_vec


# ---------------------------------------------------------------------------
# FULL weight refit (all R*B*C inner weights) on the exact official residual
# ---------------------------------------------------------------------------
def full_refit(words, brot, w_start, maxfun=45, label="refit"):
    from scipy.optimize import minimize

    u_b = decode(words, brot)[NO:].reshape(RANK, BASES, NO)
    x0 = np.array(w_start, np.float64).ravel()
    hist = []

    def fg(x):
        wq = x.reshape(RANK, BASES, COPIES)
        X = np.einsum("tjp,tjq,tjl->tlpq", u_b, u_b, wq, optimize=True)
        D = np.einsum("rcpq,rcst->pqst", X, X, optimize=True)
        D -= TSYM
        f = float(np.dot(D.ravel(), D.ravel()))
        Dm = D.reshape(NN, NN)
        Xf = X.reshape(RANK * COPIES, NN)
        Mi = (Dm @ Xf.T).T.reshape(RANK, COPIES, NO, NO)
        Bm = np.einsum("tlpq,tjq->tlpj", Mi, u_b, optimize=True)
        g = 4.0 * np.einsum("tlpj,tjp->tlj", Bm, u_b, optimize=True)
        del D, Dm, Xf, Mi, Bm
        hist.append(f)
        if time.time() - T0 > 1500.0:
            raise TimeoutError("refit wall-clock guard")
        if len(hist) % 10 == 0:
            say("refit_progress", label=label, evals=len(hist), f=f, seconds=round(time.time() - T0, 1))
        return f, g.ravel()

    say("refit_start", label=label, n=len(x0), f0=float(fg(x0)[0]))
    res = minimize(fg, x0, jac=True, method="L-BFGS-B",
                   options={"maxfun": maxfun, "maxcor": 10, "ftol": 0.0, "gtol": 0.0,
                            "maxiter": maxfun + 10})
    w_new = res.x.reshape(RANK, BASES, COPIES)
    f_new = float(res.fun)
    say("refit_done", label=label, evals=len(hist), f_new=f_new,
        error_2_new=math.sqrt(max(0.0, f_new)), seconds=round(time.time() - T0, 1))
    return w_new, f_new, len(hist)


REFITS = {}
for brot, budget in ((8, 60), (7, 150)):
    tab = WORDS8 if brot == 8 else encode_rows(V8, brot)
    try:
        w_new, f_new, nev = full_refit(tab, brot, w0, maxfun=budget, label=f"full_{brot}")
    except Exception as ex:  # noqa: BLE001
        say("refit_aborted", brot=brot, error=f"{type(ex).__name__}: {ex}")
        continue
    REFITS[brot] = w_new
    m = official(tab, brot, w_new)
    h1p = h1p_of(tab, brot, w_new)
    ob = best_one_body(tab[:NO], brot, h1p)
    m2 = official(tab, brot, w_new, one_body=ob)
    row = {"kind": "full_refit", "brot": brot, "evals": nev, "error_2": float(m["error_2"]),
           "error_1": float(m["error_1"]), "Lambda": float(m["Lambda"]),
           "E_gap": float(m["E_gap"]), "lambda_eff": float(m["lambda_eff"]),
           "error_1_1body_best": float(m2["error_1"]),
           "lambda_eff_1body_best": float(m2["lambda_eff"]),
           "w_ratio_med": float(np.median(np.abs(w_new) / np.maximum(np.abs(w0), 1e-300))),
           "Lambda_over_shipped": float(m["Lambda"]) / float(ctl["Lambda"])}
    if brot == 7:
        row["cost_if_loaders_unchanged"] = float(m2["lambda_eff"]) * SHIP_T * SHIP_Q
        row["ratio_vs_shipped"] = row["cost_if_loaders_unchanged"] / SHIP_COST
    OUT["rows"].append(row)
    say("full_refit_metrics", **{k: (round(v, 10) if isinstance(v, float) else v)
                                for k, v in row.items()})
    del m, m2, h1p, ob

# ---------------------------------------------------------------------------
# End-to-end official verification of the shipped package
# ---------------------------------------------------------------------------
say("full_verify")
try:
    res = verify(str(DIR))
    fv = {k: res[k] for k in ("status", "score", "lambda_eff", "toffoli_count", "num_qubits",
                              "brot", "batch_size", "num_circuits", "submission_sha256")}
    for k in ("error_1", "error_2", "Lambda", "E_gap"):
        fv[k] = float(res["metrics"][k])
    for k in ("angles_qubits", "angles_toffoli", "heuristic_toffoli", "persistent_qubits",
              "temporary_qubits", "angles_toffoli_per_pass"):
        fv[k] = res["resources"][k]
    fv["delta_score_vs_shipped"] = float(res["score"]) - SHIP_COST
    OUT["full_verify"] = fv
    say("full_verify_done", **{k: v for k, v in fv.items() if k != "submission_sha256"})
except Exception as ex:  # noqa: BLE001
    OUT["full_verify"] = {"status": "FAIL", "error": f"{type(ex).__name__}: {ex}"}
    say("full_verify_failed", error=OUT["full_verify"]["error"])

OUT["thresholds"] = {"error": ERROR_1_THRESHOLD, "Lambda_floor": LAMBDA_FLOOR,
                     "E_gap_floor": E_GAP_FLOOR}
OUT["seconds"] = round(time.time() - T0, 1)
(WORK / "brot_stage2.json").write_text(json.dumps(OUT, indent=1, default=str) + "\n")
say("done", seconds=OUT["seconds"])
