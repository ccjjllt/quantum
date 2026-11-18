"""chem Lambda: is Lambda a free axis, and what is its floor?

Structure used (all read off the unmodified official verifier):

    Lambda        = Lambda_H1 + Lambda_H2
    Lambda_H1     = sum_j |lambda_j|,  lambda_j = eig(h1_prime)
    Lambda_H2     = 0.25 * sum_(rho c) ( ||w_rho c||_1 + |H2_I_rho c| )^2
    h1_prime      = A - G,   G = sum_(rho c) W_rho c X_rho c,  W = H2_I - sum_b w
    E_SOS         = ecore - n*beta1 - (Lambda_H1 - Tr h1_prime) - 0.5*||W||^2
    E_gap         = UPPER - E_SOS = C + 2*sum_(lambda<0)|lambda| + 0.5*||W||^2
    C             = UPPER - ecore + n*beta1              (a FIXED constant)

Two facts that decide the axis:

  (1) Lambda_H2 >= 0.25*||W||^2, with equality iff every w_rho c is single-signed over b
      and sign(H2_I) = -sign(sum_b w).  (|s| + |h| >= |s - h|)
  (2) hence 2*Lambda - E_gap >= 2P - C  with P = sum_(lambda>0) lambda >= 0, so

          lambda_eff >= sqrt( E_gap * (2P - C) ) >= sqrt( floor * |C| )

      which is submission independent.  The shipped point sits at P = Lambda_H1 = 13.03.

So the only chem-Lambda lever left is P: make h1_prime's spectrum non-positive while
E_gap stays on its floor.  w (and therefore X and error_2) is held EXACTLY fixed; only
the 352 classical offsets H2_I and the 76 one-body word rows move.

Nothing is submitted.  All metrics come from dfthcsos.verify / dfthc_math.
"""
import base64
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
)
from dfthcsos.scoreinfra import dfthc_math as M  # noqa: E402
from dfthcsos.scoreinfra.reference import UPPER_ENERGY  # noqa: E402

# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------
with np.load(io.BytesIO(lzma.decompress(base64.b64decode(PAYLOAD_NPZ_B64))),
             allow_pickle=False) as _z:
    ARR = {k: np.array(_z[k]) for k in _z.files}
TREE = np.asarray(ARR["tree_edges"], np.int64)
WORDS = np.asarray(ARR["angle_words"], np.int64)
W_NPZ = np.asarray(ARR["W"], np.float64)
H2I = np.asarray(ARR["H2_I"], np.float64)
NROWS, NANG = WORDS.shape
NO = 76
RANK, BASES, COPIES = W_NPZ.shape
EDGES = [(int(a), int(b)) for a, b in TREE]
BROT = 8

V8 = M.reconstruct_u_vectors(WORDS / (1 << (BROT - 1)), TREE)
FACT = {"U": V8[NO:].reshape(RANK, BASES, NO), "W": W_NPZ, "H2_I": H2I,
        "H1_I": ARR["H1_I"], "Hsym_lower": ARR["Hsym_lower"]}
inputs = load_inputs(FACT)

w = np.asarray(inputs.w, np.float64)          # (8,143,44)
Woff = np.asarray(inputs.W, np.float64)       # H2_I - sum_b w
S = np.asarray(inputs.S, np.float64)
BETA1 = float(inputs.beta_1)
REF = inputs.ref
NOCC = int(REF["electrons"])
ECORE = float(REF["ecore"])
TEI = np.asarray(REF["tei"], np.float64)
OEI = np.asarray(REF["oei"], np.float64)
H1_THC = OEI - 0.5 * np.einsum("prrq->pq", TEI)
I76 = np.eye(NO)
A = H1_THC - 0.5 * NOCC * S + BETA1 * I76
C_CONST = UPPER_ENERGY - ECORE + NOCC * BETA1
T_SHIP, Q_SHIP = 14706.0, 427.0
say("ready", seconds=round(time.time() - T0, 1), C=C_CONST, ecore=ECORE, beta1=BETA1,
    UPPER=UPPER_ENERGY, floor=E_GAP_FLOOR)

# ---------------------------------------------------------------------------
# 1. control
# ---------------------------------------------------------------------------
ctl = evaluate_words(inputs, WORDS, TREE, BROT)
LAM_CTL = float(ctl["lambda_eff"])
COST_CTL = LAM_CTL * T_SHIP * Q_SHIP
OUT["control"] = {k: (v if isinstance(v, bool) else float(v)) for k, v in ctl.items()}
OUT["control"]["cost"] = COST_CTL
say("control", err1=float(ctl["error_1"]), err2=float(ctl["error_2"]), Lam=float(ctl["Lambda"]),
    E_gap=float(ctl["E_gap"]), lam_eff=LAM_CTL, cost=COST_CTL)

# ---------------------------------------------------------------------------
# 2. the exact algebra: Lambda_H1 / Lambda_H2 split, C, P
# ---------------------------------------------------------------------------
u2 = V8[NO:].reshape(RANK, BASES, NO)
X = M.reconstruct_x(u2, w)
X = np.tril(X) + np.swapaxes(np.tril(X, -1), -1, -2)          # exactly the verifier's X
H1P = A - np.einsum("rc,rcpq->pq", Woff, X, optimize=True)
H1P_OFF = M.build_h1_prime(H1_THC, S, BETA1, NOCC, Woff, X)
say("h1p_match", max_abs_diff=float(np.abs(H1P - H1P_OFF).max()))

ev = np.linalg.eigvalsh(H1P)
LAM_H1 = float(np.sum(np.abs(ev)))
TR_HP = float(np.sum(ev))
POS = float(np.sum(ev[ev > 0.0]))
NEG = float(-np.sum(ev[ev < 0.0]))
D_OFF = float(np.sum(Woff ** 2))
L1 = np.abs(w).sum(axis=1)
SB = w.sum(axis=1)
PSI = 0.25 * float(np.sum((L1 + np.abs(H2I)) ** 2))
LAM_H2 = float(M.lambda_h2(w, Woff))
E_GAP_ID = C_CONST + 2.0 * NEG + 0.5 * D_OFF
say("split", Lam_H1=LAM_H1, Lam_H2=LAM_H2, Lam_sum=LAM_H1 + LAM_H2, Tr=TR_HP,
    P=POS, Neg=NEG, D=D_OFF, quarter_D=0.25 * D_OFF, psi=PSI,
    lam_h2_over_quarter_D=LAM_H2 / (0.25 * D_OFF),
    min_eig=float(ev.min()), max_eig=float(ev.max()),
    E_gap_identity=E_GAP_ID, E_gap_official=float(ctl["E_gap"]),
    bound_2PmC=2.0 * POS - C_CONST, bound_abs_C=-C_CONST,
    lam_eff_from_bound=math.sqrt(float(ctl["E_gap"]) * (2.0 * POS - C_CONST)),
    lam_eff_hard_floor=math.sqrt(E_GAP_FLOOR * (-C_CONST)))
OUT["split"] = dict(Lam_H1=LAM_H1, Lam_H2=LAM_H2, P=POS, Neg=NEG, D=D_OFF,
                    psi=PSI, C=C_CONST, E_gap_identity=E_GAP_ID,
                    hard_floor=math.sqrt(E_GAP_FLOOR * (-C_CONST)),
                    bound_at_P=math.sqrt(float(ctl["E_gap"]) * (2.0 * POS - C_CONST)),
                    min_eig=float(ev.min()), max_eig=float(ev.max()))


# ---------------------------------------------------------------------------
# 3. Lambda's free degrees: fast metric (identical algebra, no error_2 rebuild)
# ---------------------------------------------------------------------------
def metrics_fast(g, with_lam=True):
    """lambda_eff for an arbitrary offset vector g = W (= H2_I - sum_b w), w fixed."""
    G = np.einsum("rc,rcpq->pq", g, X, optimize=True)
    lam = np.linalg.eigvalsh(A - G)
    lh1 = float(np.sum(np.abs(lam)))
    neg = float(-np.sum(lam[lam < 0.0]))
    pos = float(np.sum(lam[lam > 0.0]))
    D = float(np.sum(g ** 2))
    h = SB + g
    psi = 0.25 * float(np.sum((L1 + np.abs(h)) ** 2))
    Lam = lh1 + psi
    Eg = C_CONST + 2.0 * neg + 0.5 * D
    le = math.sqrt(Eg * (2.0 * Lam - Eg)) if 0.0 < Eg <= 2.0 * Lam else float("nan")
    return dict(lam_eff=le, Lambda=Lam, E_gap=Eg, Lam_H1=lh1, P=pos, Neg=neg, D=D, psi=psi)


def decode(words):
    return M.reconstruct_u_vectors(np.asarray(words) / (1 << (BROT - 1)), TREE)


_chk = metrics_fast(Woff)
say("fast_vs_official", lam_eff_fast=_chk["lam_eff"], lam_eff_official=LAM_CTL,
    Lam_fast=_chk["Lambda"], Lam_official=float(ctl["Lambda"]),
    gap_fast=_chk["E_gap"], gap_official=float(ctl["E_gap"]))

# 3a. the 76 one-body rows cannot touch Lambda at all
zz = WORDS.copy()
zz[:NO] = 0
m_zz = M.evaluate_dfthc_vectors(decode(zz), w, Woff, S, BETA1, REF, energy_upper=UPPER_ENERGY)
say("probe_onebodyzero", Lambda=float(m_zz["Lambda"]), E_gap=float(m_zz["E_gap"]),
    lam_eff=float(m_zz["lambda_eff"]), err1=float(m_zz["error_1"]), err2=float(m_zz["error_2"]))
OUT["probe_onebodyzero"] = {k: float(m_zz[k]) for k in ("Lambda", "E_gap", "error_1", "error_2")}

# 3b. two-body words do move Lambda (through Lambda_H1 only)
for tag, delta in (("tbw_plus1", 1), ("tbw_minus1", -1), ("tbw_rand", 17)):
    zw = WORDS.copy()
    rng = np.random.default_rng(11)
    if tag == "tbw_rand":
        zw[NO:] = (zw[NO:] + rng.integers(-1, 2, size=zw[NO:].shape)) % (1 << BROT)
    else:
        zw[NO:, ::7] = (zw[NO:, ::7] + delta) % (1 << BROT)
    vv = decode(zw)
    mm = M.evaluate_dfthc_vectors(vv, w, Woff, S, BETA1, REF, energy_upper=UPPER_ENERGY)
    say("probe_" + tag, Lambda=float(mm["Lambda"]), dLam=float(mm["Lambda"]) - float(ctl["Lambda"]),
        E_gap=float(mm["E_gap"]), lam_eff=float(mm["lambda_eff"]),
        err2=float(mm["error_2"]))
    OUT.setdefault("probe_words", {})[tag] = dict(
        Lambda=float(mm["Lambda"]), E_gap=float(mm["E_gap"]), lerr_eff=float(mm["lambda_eff"]),
        err2=float(mm["error_2"]))

# ---------------------------------------------------------------------------
# 4. fit the 352 classical offsets to minimise lambda_eff at E_gap = floor
# ---------------------------------------------------------------------------
VEC = NO * NO
BMAT = np.asarray(X, np.float64).reshape(RANK * COPIES, VEC)     # (352, 5776)
GRAM = BMAT @ BMAT.T
say("span", gram_cond=float(np.linalg.cond(GRAM)),
    rank=int(np.linalg.matrix_rank(GRAM, tol=1e-9 * np.linalg.norm(GRAM))))

vecI = I76.ravel()
# how much of the identity is reachable
alpha = np.linalg.solve(GRAM, BMAT @ vecI)
Iproj = (BMAT.T @ alpha).reshape(NO, NO)
RI = I76 - Iproj
say("identity_span", proj_norm=float(np.linalg.norm(Iproj)), resid_norm=float(np.linalg.norm(RI)),
    resid_eig_min=float(np.linalg.eigvalsh(RI).min()), resid_eig_max=float(np.linalg.eigvalsh(RI).max()))

Avec = A.ravel()
cands = [("shipped", Woff)]
for theta in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
    g = np.linalg.solve(GRAM, BMAT @ (Avec + theta * vecI))
    cands.append((f"ls_theta{theta:g}", g))
for tag, g in cands:
    m = metrics_fast(g)
    say("cand", cand=tag, lam_eff=m["lam_eff"], Lambda=m["Lambda"], E_gap=m["E_gap"],
        Lam_H1=m["Lam_H1"], P=m["P"], D=m["D"])
    OUT["rows"].append(dict(tag=tag, **m))


def objective(g, kappa=80.0, margin=1e-6):
    m = metrics_fast(g)
    le = m["lam_eff"]
    if not np.isfinite(le):
        le = 1e3
    short = max(0.0, (E_GAP_FLOOR + margin) - m["E_gap"])
    return le + kappa * short + 40.0 * max(0.0, m["E_gap"] - (E_GAP_FLOOR + 2e-3))


best_tag, best_g, best_v = None, None, np.inf
for tag, g0 in cands:
    m0 = metrics_fast(g0)
    if np.isfinite(m0["lam_eff"]) and m0["lam_eff"] < best_v:
        best_tag, best_g, best_v = tag, g0.copy(), m0["lam_eff"]
say("best_before_opt", tag=best_tag, lam_eff=best_v)

try:
    from scipy.optimize import minimize

    def fun(v):
        return objective(v)

    for seed, tag in ((0, "ls"), (1, "ls_reduced")):
        if best_g is None:
            continue
        x0 = best_g.copy()
        if seed == 1:
            x0 = x0 * 0.5
        t1 = time.time()
        res = minimize(fun, x0, method="L-BFGS-B",
                       options=dict(maxiter=300, maxfun=25000, eps=1e-7, ftol=1e-13, gtol=1e-11))
        m = metrics_fast(res.x)
        say("opt_round", round_tag=tag, fun=float(res.fun), seconds=round(time.time() - t1, 1),
            lam_eff=m["lam_eff"], Lambda=m["Lambda"], E_gap=m["E_gap"], P=m["P"], D=m["D"])
        OUT["rows"].append(dict(tag="opt_" + tag, **m, fun=float(res.fun)))
        if np.isfinite(m["lam_eff"]) and m["lam_eff"] < best_v and m["E_gap"] >= E_GAP_FLOOR:
            best_tag, best_g, best_v = "opt_" + tag, res.x.copy(), m["lam_eff"]
except Exception as exc:  # pragma: no cover
    say("opt_failed", err=repr(exc)[:400])

# targeted polish: pull E_gap onto the floor exactly by scaling, keep the direction
if best_g is not None:
    def gap_of(t):
        return metrics_fast(t * best_g)["E_gap"]

    lo, hi = 0.2, 3.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if gap_of(mid) < E_GAP_FLOOR + 1e-6:
            lo = mid
        else:
            hi = mid
    t_star = 0.5 * (lo + hi)
    g_fl = t_star * best_g
    m_fl = metrics_fast(g_fl)
    say("floor_scale", t=t_star, lam_eff=m_fl["lam_eff"], Lambda=m_fl["Lambda"],
        E_gap=m_fl["E_gap"], P=m_fl["P"])
    OUT["rows"].append(dict(tag="floor_scale", **m_fl))
    if np.isfinite(m_fl["lam_eff"]) and m_fl["lam_eff"] < best_v and m_fl["E_gap"] >= E_GAP_FLOOR:
        best_tag, best_g, best_v = "floor_scale", g_fl, m_fl["lam_eff"]

say("best_after_opt", tag=best_tag, lam_eff=best_v)
OUT["best_tag"] = best_tag
OUT["best_fast"] = metrics_fast(best_g) if best_g is not None else None

# ---------------------------------------------------------------------------
# 5. re-encode the 76 one-body rows and run the official evaluator
# ---------------------------------------------------------------------------
G = np.einsum("rc,rcpq->pq", best_g, X, optimize=True)
H1P_NEW = A - G
ev2, VEC2 = np.linalg.eigh(H1P_NEW)
say("new_spectrum", min_eig=float(ev2.min()), max_eig=float(ev2.max()),
    sum_abs=float(np.sum(np.abs(ev2))), P=float(np.sum(ev2[ev2 > 0])))


def encode_rows(vectors, scale=1 << (BROT - 1)):
    u = np.array(vectors, np.float64, copy=True)
    words = np.zeros((u.shape[0], NANG), np.int64)
    for t in range(NANG - 1, -1, -1):
        p, c = EDGES[t]
        th = np.arctan2(u[:, c], u[:, p])
        th = np.where(th < 0.0, th + 2.0 * np.pi, th)
        th = np.where(np.hypot(u[:, p], u[:, c]) < 1e-12, 0.0, th)
        words[:, t] = np.round(th / np.pi * scale).astype(np.int64) % (2 * scale)
        u[:, p] = np.hypot(u[:, p], u[:, c])
        u[:, c] = 0.0
    return words


one_new = encode_rows(VEC2.T)
words_new = WORDS.copy()
words_new[:NO] = one_new
H2I_NEW = SB + best_g

fact_new = dict(FACT)
fact_new["H2_I"] = H2I_NEW
try:
    inputs_new = load_inputs(fact_new)
    new = evaluate_words(inputs_new, words_new, TREE, BROT)
except Exception as exc:
    say("evaluate_new_failed", err=repr(exc)[:600])
    new = None
if new is not None:
    LAM_NEW = float(new["lambda_eff"])
    COST_NEW = LAM_NEW * T_SHIP * Q_SHIP
    ok = (float(new["error_1"]) <= ERROR_1_THRESHOLD and float(new["error_2"]) <= ERROR_2_THRESHOLD
          and float(new["Lambda"]) > LAMBDA_FLOOR and float(new["E_gap"]) > E_GAP_FLOOR
          and bool(new["gap_in_domain"]))
    OUT["candidate"] = dict(ok=bool(ok), cost=COST_NEW, T=T_SHIP, Q=Q_SHIP,
                            dcost=COST_NEW - COST_CTL,
                            ratio=COST_NEW / COST_CTL,
                            **{k: float(new[k]) for k in ("error_1", "error_2", "Lambda", "E_gap",
                                                         "lambda_eff")})
    say("candidate", ok=bool(ok), err1=float(new["error_1"]), err2=float(new["error_2"]),
        Lam=float(new["Lambda"]), E_gap=float(new["E_gap"]), lam_eff=LAM_NEW, cost=COST_NEW,
        dcost=COST_NEW - COST_CTL, ratio=COST_NEW / COST_CTL)

    # exact-eigenvector control: how much of error_1 is quantisation only
    vv = decode(words_new).copy()
    vv[:NO] = VEC2.T
    ctlx = M.evaluate_dfthc_vectors(vv, w, H2I_NEW - np.sum(w, axis=1), S, BETA1, REF,
                                    energy_upper=UPPER_ENERGY)
    say("unquantised_control", err1=float(ctlx["error_1"]), Lam=float(ctlx["Lambda"]),
        lam_eff=float(ctlx["lambda_eff"]))
    OUT["unquantised"] = {k: float(ctlx[k]) for k in ("error_1", "error_2", "Lambda", "E_gap",
                                                      "lambda_eff")}

    # artifact for the loader rebuild (small: 76 x 75 words + 352 offsets)
    np.savez(WORK / "chem_lambda_candidate.npz",
             one_body_words=one_new.astype(np.uint8),
             H2_I=H2I_NEW,
             two_body_words=np.asarray(WORDS[NO:], np.uint8),
             tree_edges=TREE,
             w=w)
    say("saved", path=str(WORK / "chem_lambda_candidate.npz"))

(WORK / "chem_lambda_stage1.json").write_text(json.dumps(OUT, indent=1, default=float))
say("done", seconds=round(time.time() - T0, 1))
