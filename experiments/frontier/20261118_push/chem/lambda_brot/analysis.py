"""Measured brot / Lambda trade for the DFTHC-SOS chemistry leg.

Runs the UNMODIFIED official verifier code (``dfthcsos.verify.evaluate_words``,
``dfthcsos.verify.verify`` and ``dfthcsos.scoreinfra.dfthc_math``) on Kaggle CPU
and answers one question:

    if the 75 angle words are re-quantised to ``brot`` = 7 or 6 bits, how far can
    error_1 / error_2 be pulled back under 0.020 and how much must Lambda rise --
    so is brot 8->7 / 8->6 still a net win after paying that?

No circuit is simulated except by the official verifier at the end (a control
re-verification of the shipped 18-file package). Nothing is submitted.
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


def rec(**kw):
    tag = kw["kind"]
    OUT["rows"].append(dict(kw))
    say(tag, **{k: (round(v, 12) if isinstance(v, float) else v) for k, v in kw.items()})


# ---------------------------------------------------------------------------
# Competition data + official verifier modules
# ---------------------------------------------------------------------------
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
    QUBIT_CAP,
    evaluate_words,
    heuristic_costs,
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
# Embedded payload: the shipped submission.npz + the 15 shipped .kmb loaders
# ---------------------------------------------------------------------------
PAYLOAD = {"npz": PAYLOAD_NPZ_B64, "kmbs": PAYLOAD_KMB_B64, "lens": PAYLOAD_LENS}
DIR = WORK / "dfthcsos"
DIR.mkdir(parents=True, exist_ok=True)
_blob = lzma.decompress(base64.b64decode(PAYLOAD["kmbs"]))
_off, _shas = 0, []
for _k in range(15):
    _n = PAYLOAD["lens"][_k]
    _data = _blob[_off : _off + _n]
    _off += _n
    (DIR / f"angle_k_{_k}.kmb").write_bytes(_data)
    _shas.append(hashlib.sha256(_data).hexdigest())
say("loaders", kmb_shas=_shas)

with np.load(io.BytesIO(lzma.decompress(base64.b64decode(PAYLOAD["npz"]))), allow_pickle=False) as _z:
    ARR = {k: np.array(_z[k]) for k in _z.files}
TREE = np.asarray(ARR["tree_edges"], dtype=np.int64)
WORDS8 = np.asarray(ARR["angle_words"], dtype=np.int64)
NROWS, NANG = WORDS8.shape
NO = 76
RANK, BASES, COPIES = ARR["W"].shape
EDGES = [(int(a), int(b)) for a, b in TREE]


def decode(words, brot):
    return reconstruct_u_vectors(np.asarray(words) / (1 << (brot - 1)), TREE)


# ``U`` is not used by the verifier (only its shape is); the shipped array is
# exactly +-decode(angle_words) to 7e-16, so rebuild it from the decoded rows.
V8 = decode(WORDS8, 8)
U8 = V8[NO:]
FACT = {"U": U8.reshape(RANK, BASES, NO), "W": ARR["W"], "H2_I": ARR["H2_I"],
        "H1_I": ARR["H1_I"], "Hsym_lower": ARR["Hsym_lower"]}
np.savez(DIR / "submission.npz", **FACT, tree_edges=TREE,
         angle_words=WORDS8.astype(np.int64))
say("payload", npz_sha=hashlib.sha256((DIR / "submission.npz").read_bytes()).hexdigest(),
    npz_bytes=(DIR / "submission.npz").stat().st_size)

say("loading_integrals")
inputs = load_inputs(FACT)
w0 = np.asarray(inputs.w, np.float64)          # (R,B,C)  == npz["W"]
W0 = np.asarray(inputs.W, np.float64)          # (R,C)    == H2_I - sum_b w
S = np.asarray(inputs.S, np.float64)
BETA1 = float(inputs.beta_1)
REF = inputs.ref
TEI = np.asarray(REF["tei"], np.float64)
NO = int(REF["orbitals"])
NOCC = int(REF["electrons"])
h1_thc = np.asarray(REF["oei"], np.float64) - 0.5 * np.einsum("prrq->pq", TEI)
say("integrals_ready", shape=[RANK, BASES, COPIES], N=NO, nelec=NOCC, rows=NROWS, angles=NANG,
    seconds=round(time.time() - T0, 1))


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


_ov = np.abs(np.sum(V8[NO:] * U8, axis=1))
OUT["sanity"] = {
    "decode8_max_norm_dev": float(np.max(np.abs(np.linalg.norm(V8, axis=1) - 1.0))),
    "reencode8_mismatch_vs_words": int(np.sum(encode_rows(V8, 8) != WORDS8)),
    "npzU_vs_decoded_overlap_min": float(_ov.min()),
    "npzU_vs_decoded_overlap_max": float(_ov.max()),
    "quant_sq_brot7_vs_8bit": float(np.sum((decode(encode_rows(V8, 7), 7) - V8) ** 2)),
    "quant_sq_brot6_vs_8bit": float(np.sum((decode(encode_rows(V8, 6), 6) - V8) ** 2)),
}
say("encode_sanity", **OUT["sanity"])

# ---------------------------------------------------------------------------
# Official metric entry points
# ---------------------------------------------------------------------------
def u_all(words, brot, one_body=None):
    v = decode(words, brot)
    if one_body is not None:
        v = np.array(v, copy=True)
        v[:NO] = one_body
    return v


def official(words, brot, wts=None, Wmat=None, one_body=None):
    """dfthcsos.scoreinfra.dfthc_math.evaluate_dfthc_vectors, unmodified."""
    return M.evaluate_dfthc_vectors(
        u_all(words, brot, one_body),
        w0 if wts is None else wts,
        W0 if Wmat is None else Wmat,
        S, BETA1, REF, energy_upper=UPPER_ENERGY,
    )


def h1_prime_of(words, brot, wts):
    Xs = reconstruct_x(decode(words, brot)[NO:].reshape(RANK, BASES, NO), wts)
    Xs = np.tril(Xs) + np.swapaxes(np.tril(Xs, k=-1), -1, -2)
    return build_h1_prime(h1_thc, S, BETA1, NOCC, W0, Xs), Xs


def optimize_one_body(words1, brot, h1p, passes=4):
    """Best ``brot``-bit Givens encoding of the eigenvectors of h1_prime.

    Closed-form coordinate descent in the Givens sweep: after propagating the
    target eigenvector backwards, the overlap at rotation ``t`` is
    ``A cos(theta) + B sin(theta) + const`` on the 2**brot grid.
    """
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
    for _ in range(passes):
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
            A = z[:, p] * Uu[:, p] + z[:, c] * Uu[:, c]
            B = z[:, p] * Uu[:, c] - z[:, c] * Uu[:, p]
            pick = np.argmax(A[:, None] * cosg[None, :] + B[:, None] * sing[None, :], axis=1)
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


def quadratic_terms(words, brot, wts):
    """Gram of the 352 Kronecker factors and the linear term against T.

    With ``X_i -> s_i X_i`` the residual obeys
        error_2(s)^2 = (s^2)' G (s^2) - 2 b'(s^2) + ||T||^2,
    so the refit variable is ``u_i = s_i^2 >= 0``.
    """
    Xs = reconstruct_x(decode(words, brot)[NO:].reshape(RANK, BASES, NO), wts)
    Xs = np.tril(Xs) + np.swapaxes(np.tril(Xs, k=-1), -1, -2)
    Xf = Xs.reshape(RANK * COPIES, NO * NO)
    G = (Xf @ Xf.T) ** 2
    Tsym = np.array(TEI, np.float64, copy=True)
    diag = np.arange(NO)
    Tsym[:, :, diag, diag] += 0.5 * S[:, :, None]
    Tsym[diag, diag, :, :] += 0.5 * S[None, :, :]
    Mx = Tsym.reshape(NO * NO, NO * NO)
    b = np.einsum("ij,ij->i", Xf, (Mx @ Xf.T).T)
    T2 = float(np.dot(Tsym.ravel(), Tsym.ravel()))
    del Tsym, Mx
    return G, b, T2


def solve_nn_qp(G, b):
    """min_u u'Gu - 2b'u subject to u >= 0 (G PSD), active-set iteration."""
    n = len(b)
    free = np.ones(n, bool)
    ridge = 1e-12 * (np.trace(G) / n + 1e-300)
    u = np.zeros(n)
    for _ in range(60):
        idx = np.flatnonzero(free)
        if len(idx) == 0:
            break
        sub = G[np.ix_(idx, idx)] + ridge * np.eye(len(idx))
        sol = np.linalg.lstsq(sub, b[idx], rcond=None)[0]
        u = np.zeros(n)
        u[idx] = sol
        bad = free & (u <= 0.0)
        if not bad.any():
            break
        free &= ~bad
    return u


# ---------------------------------------------------------------------------
# Heuristic (T_h, Q) model at each brot
# ---------------------------------------------------------------------------
SEL = math.ceil(math.log2(NO + RANK * BASES))
HEUR = {}
for brot in (8, 7, 6, 5):
    h = heuristic_costs(NO, RANK, BASES, COPIES, brot)
    angles_temp_cap = QUBIT_CAP - SEL - 5 * brot
    Q = h["persistent_qubits"] + 5 * brot + max(h["temporary_qubits"], angles_temp_cap)
    HEUR[brot] = {"T_h": h["toffoli"], "Q": Q, "outer": h["outer_state_prep_toffoli"],
                  "inner": h["inner_state_prep_toffoli"], "givens": h["givens_rotations_toffoli"],
                  "heur_persistent": h["persistent_qubits"], "heur_temp": h["temporary_qubits"],
                  "angles_temp_cap": angles_temp_cap}
    rec(kind="heuristic", brot=brot, **HEUR[brot])
OUT["heuristic"] = {str(k): v for k, v in HEUR.items()}

# ---------------------------------------------------------------------------
# Control: the shipped 8-bit table, official
# ---------------------------------------------------------------------------
ctl = evaluate_words(inputs, WORDS8, TREE, 8)
OUT["control"] = {k: (v if isinstance(v, bool) else float(v)) for k, v in ctl.items()}
rec(kind="control_brot8", **{k: v for k, v in OUT["control"].items() if isinstance(v, float)})
SHIP_LAMBDA = float(ctl["lambda_eff"])
SHIP_T = 14706.0
SHIP_Q = 427
SHIP_COST = SHIP_LAMBDA * SHIP_T * SHIP_Q
OUT["shipped"] = {"T": SHIP_T, "Q": SHIP_Q, "lambda_eff": SHIP_LAMBDA, "cost": SHIP_COST,
                  "loader_sum_per_pass": 4022.0}
say("shipped", **OUT["shipped"])

# ---------------------------------------------------------------------------
# brot sweep
# ---------------------------------------------------------------------------
TABLES = {8: WORDS8}
QUANT_SQ = {8: 0.0}
for brot in (7, 6):
    TABLES[brot] = encode_rows(V8, brot)
    QUANT_SQ[brot] = float(np.sum((decode(TABLES[brot], brot) - V8) ** 2))

for brot in (8, 7, 6):
    tab = TABLES[brot]
    base = official(tab, brot)
    h1p, _ = h1_prime_of(tab, brot, w0)
    ob = optimize_one_body(tab[:NO], brot, h1p)
    opt = official(tab, brot, one_body=ob)
    rec(kind="reencode", brot=brot, quant_sq=QUANT_SQ[brot],
        error_1=base["error_1"], error_2=base["error_2"], Lambda=base["Lambda"],
        E_gap=base["E_gap"], lambda_eff=base["lambda_eff"], gap=bool(base["gap_in_domain"]))
    rec(kind="reencode_1body_opt", brot=brot, error_1=opt["error_1"], error_2=opt["error_2"],
        Lambda=opt["Lambda"], E_gap=opt["E_gap"], lambda_eff=opt["lambda_eff"],
        gap=bool(opt["gap_in_domain"]))
    del h1p, ob, opt

    # ---- per-(rho,c) refit of the 352 block scales ----------------------
    G, bq, T2 = quadratic_terms(tab, brot, w0)
    u_opt = solve_nn_qp(G, bq)
    one = np.ones_like(u_opt)
    A = float(u_opt @ G @ u_opt)
    Bq = float(bq @ u_opt)
    e2_min = math.sqrt(max(0.0, A - 2.0 * Bq + T2))
    e2_check = math.sqrt(max(0.0, float(one @ G @ one - 2.0 * bq @ one + T2)))
    s_opt = np.sqrt(np.maximum(u_opt, 0.0))
    rec(kind="refit352", brot=brot, error_2_min=e2_min, error_2_at_u1=e2_check,
        error_2_official_at_1=base["error_2"], n_active=int(np.sum(u_opt > 0)),
        s_min=float(s_opt.min()), s_max=float(s_opt.max()), s_med=float(np.median(s_opt)))

    # least-Lambda point on the ray s*sqrt(u_opt) where error_2 hits the gate
    gate2 = ERROR_2_THRESHOLD ** 2
    roots = []
    disc = 4.0 * Bq * Bq - 4.0 * A * (T2 - gate2)
    if A > 0 and disc >= 0:
        # A z^2 - 2 Bq z + (T2-gate2) = 0  ->  z = (2Bq +- sqrt(disc)) / (2A)
        z1 = (2.0 * Bq + math.sqrt(disc)) / (2.0 * A)
        z2 = (2.0 * Bq - math.sqrt(disc)) / (2.0 * A)
        for z in (z1, z2):
            if z > 0:
                roots.append(float(math.sqrt(z)))
    rec(kind="gate_ray", brot=brot, s_at_error_gate=sorted(roots),
        error_2_at_refit_min=e2_min,
        lower_lambda_than_shipped=bool(roots and min(roots) < 1.0))

    if roots and min(roots) < 0.999:
        s = min(roots)
        wt = (s * s_opt).reshape(RANK, COPIES)[:, None, :] * w0
        h1p, _ = h1_prime_of(tab, brot, wt)
        ob = optimize_one_body(tab[:NO], brot, h1p)
        m = official(tab, brot, wts=wt, one_body=ob)
        rec(kind="freewin", brot=brot, s=s, error_1=m["error_1"], error_2=m["error_2"],
            Lambda=m["Lambda"], E_gap=m["E_gap"], lambda_eff=m["lambda_eff"],
            gap=bool(m["gap_in_domain"]),
            cost_if_loaders_unchanged=m["lambda_eff"] * SHIP_T * SHIP_Q,
            ratio_vs_shipped=m["lambda_eff"] / SHIP_LAMBDA)
        del h1p, ob, m

    for s in (1.00, 1.03, 1.07, 1.12, 1.20, 1.35, 1.55, 1.85, 2.20):
        wt = (s * s_opt).reshape(RANK, COPIES)[:, None, :] * w0
        e2 = math.sqrt(max(0.0, A * s ** 4 - 2.0 * Bq * s ** 2 + T2))
        h1p, _ = h1_prime_of(tab, brot, wt)
        ob = optimize_one_body(tab[:NO], brot, h1p)
        m = official(tab, brot, wts=wt, one_body=ob)
        feasible = (m["error_1"] <= ERROR_1_THRESHOLD and e2 <= ERROR_2_THRESHOLD
                    and bool(m["gap_in_domain"]) and m["Lambda"] > LAMBDA_FLOOR
                    and m["E_gap"] > E_GAP_FLOOR)
        cost = m["lambda_eff"] * (2.0 * 4022.0 + HEUR[brot]["T_h"]) * HEUR[brot]["Q"] \
            if feasible else float("inf")
        rec(kind="trade", brot=brot, s=s, error_1=m["error_1"], error_2=e2,
            Lambda=m["Lambda"], E_gap=m["E_gap"], lambda_eff=m["lambda_eff"],
            gap=bool(m["gap_in_domain"]), feasible=bool(feasible),
            lambda_over_shipped=m["lambda_eff"] / SHIP_LAMBDA,
            cost_if_loaders_unchanged=cost, ratio_vs_shipped=cost / SHIP_COST if feasible else None)
        del h1p, ob, m
    del G, bq

# ---------------------------------------------------------------------------
# Break-even loader budget per brot (cost < SHIP_COST), using the best feasible
# trade row measured for that brot.
# ---------------------------------------------------------------------------
best = {}
for r in OUT["rows"]:
    if r.get("kind") == "trade" and r.get("feasible"):
        b = best.get(r["brot"])
        if b is None or r["cost_if_loaders_unchanged"] < b["cost_if_loaders_unchanged"]:
            best[r["brot"]] = r
OUT["best_feasible"] = best
for brot, r in best.items():
    lam = r["lambda_eff"]
    Th = HEUR[brot]["T_h"]
    Q = HEUR[brot]["Q"]
    Lmax = (SHIP_COST / (lam * Q) - Th) / 2.0
    OUT.setdefault("breakeven", {})[str(brot)] = {
        "loader_sum_per_pass_max": Lmax, "shipped_loader_sum": 4022.0,
        "headroom_per_pass": Lmax - 4022.0, "s": r["s"], "Lambda": r["Lambda"],
        "error_1": r["error_1"], "error_2": r["error_2"], "lambda_eff": lam,
        "cost_at_4022": r["cost_if_loaders_unchanged"],
    }
    say("breakeven", **OUT["breakeven"][str(brot)])

# ---------------------------------------------------------------------------
# End-to-end official verification of the rebuilt 18-file package
# ---------------------------------------------------------------------------
say("full_verify")
try:
    res = verify(str(DIR))
    fv = {k: res[k] for k in ("status", "score", "lambda_eff", "toffoli_count", "num_qubits",
                              "brot", "batch_size", "num_circuits", "submission_sha256")}
    for k in ("error_1", "error_2", "Lambda", "E_gap"):
        fv[k] = res["metrics"][k]
    for k in ("angles_qubits", "angles_toffoli", "heuristic_toffoli", "persistent_qubits",
              "temporary_qubits"):
        fv[k] = res["resources"][k]
    fv["recovered_words_equal_npz"] = bool(np.array_equal(np.asarray(res["angle_words"], np.int64), WORDS8))
    OUT["full_verify"] = fv
    say("full_verify_done", **{k: v for k, v in fv.items() if k != "submission_sha256"})
except Exception as ex:  # noqa: BLE001
    OUT["full_verify"] = {"status": "FAIL", "error": f"{type(ex).__name__}: {ex}"}
    say("full_verify_failed", error=OUT["full_verify"]["error"])

OUT["thresholds"] = {"error_1": ERROR_1_THRESHOLD, "error_2": ERROR_2_THRESHOLD,
                     "Lambda_floor": LAMBDA_FLOOR, "E_gap_floor": E_GAP_FLOOR, "qubit_cap": QUBIT_CAP}
OUT["seconds"] = round(time.time() - T0, 1)
(WORK / "brot_trade.json").write_text(json.dumps(OUT, indent=1, default=str) + "\n")
say("done", seconds=OUT["seconds"])
