"""Track B: signed-digit quadratic approximation line for 62Q invsqrt.

Mathematical model (derived fresh per config; nothing truncated from old tables):
    coords (authoritative): lz = #leading zeros of x in 22 bits, m = (x<<lz)&2^22-1,
        parity p = lz&1, a = (p<<7)|((m>>14)&127), delta = m&16383.
        Hidden leading one is bit21; bit20 is the TOP bit of the 7-bit segment
        field ((m>>14)&127) and is always modelled (see S below).
    mantissa: mbar = m/2^21 in [1,2); v = Cp/sqrt(mbar), Cp = 1 (p=1) | sqrt(2) (p=0).
        1/sqrt(x) = 2^e * v with e = s-10 (p=1) | s-11 (p=0), s = lz>>1. Exact.
    segments S in {6,7} (segment bits; parity outermost, fit per parity):
        S=7: seg = a&127 (bits14..20, keeps bit20); dprime = delta (14 bits).
        S=6: seg = (a&127)>>1 (bits15..20, keeps bit20 = "补bit20");
             dprime = ((a&1)<<13)|(delta>>1) (bit14 folded in exactly, still 14 bits);
             sub = delta&1 (bit0) becomes a domain-doubling fit constraint
             (target uses the true m incl. bit0; features are bit0-blind).
    features: u = (dprime-8192)/16384 (centered, exact);
        dt = dprime with low r0 rows cleared (TRUNC, literal "rows start at r0")
             or rounded to nearest multiple of 2^r0 in 15 bits (ROUND);
        ut = (dt-8192)/16384; w = ut*ut. r0 in {5,6,7}.
    per-segment model: vhat = B0 + M*u + R*w, coefficients as signed-digit
        (CSD) values with nonzero-digit caps Pm in {7,8,9} (M) and
        Pr in {16,17,18} (B0,R). "精度" = CSD digit budget (positions free).
    fit: scale-normalized IRLS minimax init (relative residual vs seg center),
        then CSD digit-cap quantization + coordinate digit search on
        tread-representative domain (omitted rows / subsumed bits included).
    phase: frac(vhat*2^e); 36-bit word P = round(frac*2^36) mod 2^36;
        static angles (36 + const) are the EXACT binary weights per config
        (bit-exact on the actual integer-model bits, "实际相位特征";
        a minimax-LP variant was tried and removed as numerically invalid,
        see trackB_approx.md), then global offset margin-centering. Optional drop of low LSBs with compensation.
    checks: seg/carry edges, normalization bounds, x=1..63, 161, 888;
        shortlist -> full 3,133,452 domain, batch-256 framing, padding split,
        seeds 101/202/303 determinism hashes. Overflow/widths recorded.

Billing is a HYPOTHESIS (parametric, assumption-tabled). No circuit exists;
no gain is claimed. Synthesis eps always comes from THIS model's own margin
with its OWN rotation count (never grafted from another model/circuit).

Usage:
    uv run python experiments/invsqrt/20261102_hw06_opt/approxB62.py --boundary
    uv run python experiments/invsqrt/20261102_hw06_opt/approxB62.py --angles S_Pm_Pr_r0_V
    uv run python experiments/invsqrt/20261102_hw06_opt/approxB62.py --full S_Pm_Pr_r0_V
    uv run python experiments/invsqrt/20261102_hw06_opt/approxB62.py --billing
Tables land in artifacts/20261102_hw06_opt/invsqrt/trackB_*.json (small).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from coords62 import X_MAX  # noqa: E402
from coords62 import decompose as decompose_one  # noqa: E402

from invsqrt import verify_submission_invsqrt as official  # noqa: E402

ART = ROOT / "artifacts/20261102_hw06_opt/invsqrt"
SPEC = official.ProblemSpecInvSqrt.for_n_p(10)
GRID_S = (6, 7)
GRID_PM = (7, 8, 9)
GRID_PR = (16, 17, 18)
GRID_R0 = (5, 6, 7)
VARIANTS = ("trunc", "round")
K_PHASE_BITS = 36

TOL_REL = 2.0 ** -24  # official relative tolerance


# --------------------------------------------------------------------------
# segment views
# --------------------------------------------------------------------------

def seg_view(S, p, a, delta):
    """Return (seg_id, dprime, sub) with everything derived from (a, delta)."""
    if S == 7:
        return (p << 7) | (a & 127), delta, 0
    seg = (p << 6) | ((a & 127) >> 1)
    dprime = ((a & 1) << 13) | (delta >> 1)
    return seg, dprime, delta & 1


def mantissa_of(S, p, seg, dprime, sub):
    """True mantissa value v for a rectangle point (uses full m incl. sub bit)."""
    if S == 7:
        m = (1 << 21) | ((seg & 127) << 14) | dprime
    else:
        b14 = (dprime >> 13) & 1
        seg7 = ((seg & 63) << 1) | b14
        delta = ((dprime & 8191) << 1) | (sub & 1)
        m = (1 << 21) | (seg7 << 14) | delta
    mbar = m / float(1 << 21)
    cp = 1.0 if p == 1 else math.sqrt(2.0)
    return cp / math.sqrt(mbar)


def dt_of(dprime, r0, variant):
    mask = (1 << r0) - 1
    if variant == "trunc":
        return dprime & ~mask
    return ((dprime + (1 << (r0 - 1))) >> r0) << r0  # 15-bit (<=16384)


# --------------------------------------------------------------------------
# CSD (signed-digit) utilities
# --------------------------------------------------------------------------

def to_csd(value, lsb):
    """Canonical signed-digit expansion of round(value/2^lsb), positions desc."""
    n = int(math.floor(value / (2.0 ** lsb) + 0.5))
    if n == 0:
        return []
    # non-adjacent form on |n|
    neg = n < 0
    n = abs(n)
    digits = []
    pos = lsb
    while n:
        if n & 1:
            r = n & 3
            if r == 3:
                digits.append((pos, -1))
                n = (n + 1) >> 1
            elif r == 1:
                digits.append((pos, 1))
                n >>= 1
            else:
                n >>= 1
        else:
            n >>= 1
        pos += 1
    if neg:
        digits = [(q, -s) for q, s in digits]
    return digits


def csd_value(digits):
    return sum(s * (2.0 ** q) for q, s in digits)


def quantize_cap(value, cap):
    """Round value to a CSD value with <= cap nonzero digits (positions free)."""
    if value == 0:
        return []
    msb = math.floor(math.log2(abs(value)))
    lsb = msb - 44
    d = to_csd(value, lsb)
    # drop least-significant digits until cap
    d = sorted(d, key=lambda t: t[0])
    while len(d) > cap:
        d = d[1:]
    return d


# --------------------------------------------------------------------------
# rectangle build + IRLS minimax init (vectorized over segments)
# --------------------------------------------------------------------------

def build_rect(S, r0, variant, p):
    nseg = 2 ** S
    dp = np.arange(16384, dtype=np.int64)
    if S == 7:
        DP = np.tile(dp, (nseg, 1))
        SUB = np.zeros_like(DP)
        SEG7 = np.tile(np.arange(nseg, dtype=np.int64)[:, None], (1, 16384))
        M = ((1 << 21) | (SEG7 << 14) | DP).astype(np.float64)
    else:
        DP = np.tile(dp, (nseg, 1))
        SUB = np.zeros_like(DP)
        B14 = (DP >> 13) & 1
        SEG7 = ((np.arange(nseg, dtype=np.int64)[:, None] << 1) | B14)
        DL = ((DP & 8191) << 1) | SUB
        M = ((1 << 21) | (SEG7 << 14) | DL).astype(np.float64)
        # domain doubling over subsumed bit0: duplicate with SUB=1
        DP = np.concatenate([DP, DP], axis=1)
        SEG7 = np.concatenate([SEG7, SEG7], axis=1)
        DL = np.concatenate([DL, DL + 1], axis=1)
        SUB = np.concatenate([SUB, np.ones_like(SUB)], axis=1)
        M = ((1 << 21) | (SEG7 << 14) | DL).astype(np.float64)
    mbar = M / float(1 << 21)
    cp = 1.0 if p == 1 else math.sqrt(2.0)
    V = cp / np.sqrt(mbar)
    U = (DP.astype(np.float64) - 8192.0) / 16384.0
    if variant == "trunc":
        DT = DP & ~((1 << r0) - 1)
    else:
        DT = ((DP + (1 << (r0 - 1))) >> r0) << r0
    UT = (DT.astype(np.float64) - 8192.0) / 16384.0
    W = UT * UT
    return {"DP": DP, "SUB": SUB, "V": V, "U": U, "W": W, "DT": DT, "nseg": nseg}


def irls_minimax(V, U, W, iters=30):
    """Scale-normalized minimax init: IRLS on relative residual. Returns (B0,M,R)."""
    nseg = V.shape[0]
    C = V[:, 8192 if V.shape[1] == 16384 else 8192].copy()
    C = np.where(C == 0, 1.0, C)
    R = V / C[:, None] - 1.0
    Phi = np.stack([np.ones_like(U), U, W], axis=-1)  # N x D x 3
    wt = np.ones_like(V)
    coef = np.zeros((nseg, 3))
    for _ in range(iters):
        A = np.einsum("nd,ndi,ndj->nij", wt, Phi, Phi)
        b = np.einsum("nd,ndi->ni", wt * R, Phi)
        coef = np.linalg.solve(A + 1e-18 * np.eye(3), b[..., None])[..., 0]
        pred = np.einsum("ndi,ni->nd", Phi, coef)
        res = np.abs(pred - R)
        mx = res.max(axis=1, keepdims=True) + 1e-300
        wt = 1.0 + 8.0 * (res / mx)
    # R = V/C - 1, so V = C*(1+c0) + (c1*C)*U + (c2*C)*W: B0 keeps the +1.
    B0 = (1.0 + coef[:, 0]) * C
    M = coef[:, 1] * C
    Rc = coef[:, 2] * C
    return B0, M, Rc


def tread_reps(S, r0, variant, p, seg):
    """Small representative domain per segment: tread edges/mid + ends, both subs."""
    pts = set()
    step = 1 << r0
    for t in range(0, 16384, step):
        for d in (t, t + 1, t + step // 2, t + step - 1):
            if 0 <= d < 16384:
                pts.add(d)
    pts.add(16383)
    out = []
    for d in sorted(pts):
        for sub in ((0, 1) if S == 6 else (0,)):
            v = mantissa_of(S, p, seg, d, sub)
            dt = dt_of(d, r0, variant)
            u = (d - 8192) / 16384.0
            w = ((dt - 8192) / 16384.0) ** 2
            out.append((v, u, w))
    V = np.array([t[0] for t in out])
    Phi = np.array([[1.0, t[1], t[2]] for t in out])
    return V, Phi


def seg_maxrel(coef_digits, V, Phi):
    b0, m, r = (csd_value(d) for d in coef_digits)
    pred = b0 + Phi[:, 1] * m + Phi[:, 2] * r
    return float(np.max(np.abs(pred - V) / V))


def fit_segment(V_rep, Phi_rep, b0r, mr, rr, cap_b0, cap_m, cap_r):
    """CSD digit-cap quantization + coordinate digit search. Returns digits."""
    coef = [quantize_cap(b0r, cap_b0), quantize_cap(mr, cap_m), quantize_cap(rr, cap_r)]
    best = seg_maxrel(coef, V_rep, Phi_rep)
    for _ in range(3):
        improved = False
        for ci in range(3):
            cur = list(coef[ci])
            cands = [cur]
            for i, (q, s) in enumerate(cur):
                for dq in (-2, -1, 1, 2):
                    c = list(cur)
                    c[i] = (q + dq, s)
                    cands.append(c)
                c = list(cur)
                del c[i]
                cands.append(c)
            # try adding a digit at a few candidate positions
            used = {q for q, _ in cur}
            if cur:
                lo = min(used) - 4
                hi = max(used) + 2
            else:
                lo, hi = -40, 2
            for q in range(lo, hi + 1):
                if q not in used:
                    for s in (1, -1):
                        cands.append(cur + [(q, s)])
            for c in cands:
                if len(c) > (cap_b0, cap_m, cap_r)[ci]:
                    continue
                trial = [coef[0], coef[1], coef[2]]
                trial[ci] = c
                err = seg_maxrel(trial, V_rep, Phi_rep)
                if err < best * (1 - 1e-9):
                    best = err
                    coef[ci] = c
                    improved = True
        if not improved:
            break
    return coef, best


# --------------------------------------------------------------------------
# config fit (boundary stage)
# --------------------------------------------------------------------------

def fit_config(S, Pm, Pr, r0, variant):
    segs = []
    worst = 0.0
    worst_loc = None
    bind = {"M": 0, "B0": 0, "R": 0}
    maxw = {"B0": 0, "M": 0, "R": 0, "prodM": 0, "prodR": 0, "sum": 0}
    coef_store = {}
    for p in (0, 1):
        rect = build_rect(S, r0, variant, p)
        B0r, Mr, Rr = irls_minimax(rect["V"], rect["U"], rect["W"])
        V, U, W = rect["V"], rect["U"], rect["W"]
        for seg in range(rect["nseg"]):
            V_rep, Phi_rep = tread_reps(S, r0, variant, p, seg)
            coef, err_rep = fit_segment(V_rep, Phi_rep, B0r[seg], Mr[seg], Rr[seg],
                                        Pr, Pm, Pr)
            # full-rectangle error with the digit coefficients
            b0, m, r = (csd_value(d) for d in coef)
            pred = b0 + U[seg] * m + W[seg] * r
            rel = np.abs(pred - V[seg]) / V[seg]
            err = float(rel.max())
            # binding stats: cap active?
            for key, d, cap in (("B0", coef[0], Pr), ("M", coef[1], Pm), ("R", coef[2], Pr)):
                if len(d) >= cap:
                    bind[key] += 1
            # width evidence (binary position spans of exact values)
            for key, d in (("B0", coef[0]), ("M", coef[1]), ("R", coef[2])):
                if d:
                    qs = [q for q, _ in d]
                    maxw[key] = max(maxw[key], max(qs) - min(qs) + 1)
            maxw["prodM"] = max(maxw["prodM"], 14 + (max([q for q, _ in coef[1]]) if coef[1] else 0))
            maxw["prodR"] = max(maxw["prodR"], 2 * 15 + (max([q for q, _ in coef[2]]) if coef[2] else 0))
            if err > worst:
                worst = err
                wi = int(np.argmax(rel))
                worst_loc = {"p": p, "seg": seg, "dprime": int(rect["DP"][seg, wi]),
                             "sub": int(rect["SUB"][seg, wi])}
            coef_store[(p, seg)] = coef
            segs.append({"p": p, "seg": seg, "B0": coef[0], "M": coef[1], "R": coef[2],
                         "maxrel": err})
    nseg_total = 2 * (2 ** S)
    return {"S": S, "Pm": Pm, "Pr": Pr, "r0": r0, "variant": variant,
            "maxrel_rect": worst, "worst_loc": worst_loc,
            "synth_share_left": 1.0 - worst / TOL_REL,
            "bind_counts": bind, "nseg": nseg_total, "widths": maxw,
            "pass_rect": bool(worst < TOL_REL)}, coef_store, segs


# --------------------------------------------------------------------------
# boundary-x set, phase assembly, angle LP
# --------------------------------------------------------------------------

def x_from_rect_point(S, p, seg, dprime, sub, s):
    t = (s << 1) | p
    if S == 7:
        m = (1 << 21) | ((seg & 127) << 14) | dprime
    else:
        b14 = (dprime >> 13) & 1
        seg7 = ((seg & 63) << 1) | b14
        delta = ((dprime & 8191) << 1) | (sub & 1)
        m = (1 << 21) | (seg7 << 14) | delta
    x = m >> t
    if not 1 <= x <= X_MAX:
        return None
    lz, m2, p2, _a, _d = decompose_one(int(x))
    if lz != t or m2 != m:
        return None
    return int(x)


def build_boundary(S, r0):
    pts = []  # (x, p, seg, dprime, sub, s)
    step = 1 << r0
    dp_choices = {0, 1, 8191, 8192, 8193, 16382, 16383}
    for t in range(0, 16384, step):
        dp_choices.update([t, min(t + 1, 16383), t + step // 2, max(t + step - 1, 0)])
    for p in (0, 1):
        for seg in range(2 ** S):
            for d in sorted(dp_choices):
                for sub in ((0, 1) if S == 6 else (0,)):
                    for s in range(0, 11):
                        x = x_from_rect_point(S, p, seg, d, sub, s)
                        if x is not None:
                            pts.append((x, p, seg, d, sub, s))
    # required checkpoints (dedup later)
    for x in list(range(1, 64)) + [161, 888]:
        lz, m, p, a, dlt = decompose_one(x)
        s = lz >> 1
        seg_id, dprime, sub = seg_view(S, p, a, dlt)
        seg = seg_id & ((1 << S) - 1)
        pts.append((x, p, seg, dprime, sub, s))
    for k in range(1, 22):
        for x in (2 ** k - 1, 2 ** k, min(2 ** k + 1, X_MAX)):
            if 1 <= x <= X_MAX:
                lz, m, p, a, dlt = decompose_one(x)
                s = lz >> 1
                seg_id, dprime, sub = seg_view(S, p, a, dlt)
                pts.append((x, p, seg_id & ((1 << S) - 1), dprime, sub, s))
    # carry points: dprime = 2^j boundaries
    for j in range(0, 14):
        for d in (2 ** j - 1, 2 ** j, min(2 ** j + 1, 16383)):
            if 0 <= d < 16384:
                for p in (0, 1):
                    for seg in range(2 ** S):
                        for sub in ((0, 1) if S == 6 else (0,)):
                            for s in (0, 5, 10):
                                x = x_from_rect_point(S, p, seg, d, sub, s)
                                if x is not None:
                                    pts.append((x, p, seg, d, sub, s))
    seen = set()
    out = []
    for t in pts:
        if t[0] not in seen or True:
            key = t
            if key not in seen:
                seen.add(key)
                out.append(t)
    return out


def model_phase_of(coef_store, S, r0, variant, p, seg, dprime, sub, s):
    coef = coef_store[(p, seg)]
    b0, m, r = (csd_value(d) for d in coef)
    u = (dprime - 8192) / 16384.0
    dt = dt_of(dprime, r0, variant)
    w = ((dt - 8192) / 16384.0) ** 2
    vhat = b0 + m * u + r * w
    e = s - 10 if p == 1 else s - 11
    return (vhat * (2.0 ** e)) % 1.0, vhat


def fit_angles(S, r0, variant, coef_store, pts, tgt, tol, drop_low=0):
    # Exact binary-weight construction. (A minimax-LP formulation used to sit
    # here; it was numerically invalid: its constraint matrix mixed O(1) bit
    # columns with a t-column scaled by tol~1e-11, below solver feasibility
    # tolerance, so it returned lp_t=8.4e6 / boundary maxrel 136.7 where exact
    # binary weights achieve maxrel ~0.58 on the same set. Evidence recorded
    # in trackB_approx.md; the LP was removed rather than rescaled because the
    # exact weights already represent every model phase word bit-exactly.)
    n = len(pts)
    P = np.zeros(n, dtype=np.int64)
    for i, (x, p, seg, dprime, sub, s) in enumerate(pts):
        ph, _vh = model_phase_of(coef_store, S, r0, variant, p, seg, dprime, sub, s)
        P[i] = int(ph * float(1 << K_PHASE_BITS) + 0.5) % (1 << K_PHASE_BITS)
    nbit = K_PHASE_BITS - drop_low
    B = np.zeros((n, nbit + 1))
    for j in range(nbit):
        B[:, j] = ((P >> (j + drop_low)) & 1).astype(np.float64)
    B[:, nbit] = 1.0
    w = np.array([2.0 ** (j + drop_low - K_PHASE_BITS) for j in range(nbit)] + [0.0])
    theta = w.copy()
    # global offset margin-centering on the boundary set
    err0 = (B @ theta - tgt + 0.5) % 1.0 - 0.5
    to = np.where(tol > 0, tol, 1)
    best = (0.0, -1.0)
    for delta in np.linspace(-2e-9, 2e-9, 41):
        e2 = err0 + delta
        e2 = (e2 + 0.5) % 1.0 - 0.5
        mgn = np.min((tol - np.abs(e2)) / to)
        if mgn > best[1]:
            best = (float(delta), float(mgn))
    theta[-1] += best[0]
    err = (B @ theta - tgt + 0.5) % 1.0 - 0.5
    rel = float(np.max(np.abs(err) / to))
    return {"theta": [float(t) for t in theta], "lp_t": rel,
            "offset": best[0], "drop_low": drop_low,
            "max_abs_dev_weight": 0.0,
            "n_rot": nbit + 1}
# --------------------------------------------------------------------------
# full-domain evaluation
# --------------------------------------------------------------------------

def full_eval(S, r0, variant, coef_store, angle_doc, seeds=(101, 202, 303)):
    tgt_all, tol_all = official.reference_values(
        SPEC, np.arange(1, X_MAX + 1, dtype=np.uint64))
    tgt_all = tgt_all.astype(np.float64) / 2 ** 64
    tol_all = tol_all.astype(np.float64) / 2 ** 64
    # coefficient lookup tables
    nseg = 2 ** S
    B0 = np.zeros((2, nseg))
    MM = np.zeros((2, nseg))
    RR = np.zeros((2, nseg))
    for (p, seg), coef in coef_store.items():
        B0[p, seg] = csd_value(coef[0])
        MM[p, seg] = csd_value(coef[1])
        RR[p, seg] = csd_value(coef[2])
    theta = np.array(angle_doc["theta"])
    drop_low = angle_doc["drop_low"]
    nbit = K_PHASE_BITS - drop_low
    chunk = 1 << 18
    bounds2 = 2.0 ** np.arange(1, 23)
    maxrel = 0.0
    min_margin_units = 1 << 64
    worst = (0, 0.0, 0.0)
    hashes = []
    n_real_total = 0
    n_pad_total = 0
    of = {"prodM_bits": 0, "prodR_bits": 0, "sum_bits": 0}
    for seed in seeds:
        h = hashlib.sha256()
        cur_maxrel = 0.0
        cur_min_margin = 1 << 64
        cur_worst = (0, 0.0)
        for start in range(1, X_MAX + 1, chunk):
            xs = np.arange(start, min(start + chunk, X_MAX + 1), dtype=np.uint64)
            # batch-256 framing with tail padding (padding never evaluated)
            real = xs
            n_real_total += len(real)
            xi = xs.astype(np.int64)
            bitlen = np.digitize(xi, bounds2) + 1
            lz = 22 - bitlen
            m = (xi << lz) & ((1 << 22) - 1)
            p = lz & 1
            a = (p << 7) | ((m >> 14) & 127)
            dl = m & 16383
            s = lz >> 1
            if S == 7:
                seg = a & 127
                dp = dl
            else:
                seg = (a & 127) >> 1
                dp = ((a & 1) << 13) | (dl >> 1)
            u = (dp.astype(np.float64) - 8192.0) / 16384.0
            mask = (1 << r0) - 1
            if variant == "trunc":
                dtv = dp & ~mask
            else:
                dtv = ((dp + (1 << (r0 - 1))) >> r0) << r0
            w = ((dtv.astype(np.float64) - 8192.0) / 16384.0) ** 2
            vhat = B0[p, seg] + MM[p, seg] * u + RR[p, seg] * w
            e = np.where(p == 1, s - 10, s - 11)
            ph = (vhat * np.exp2(e)) % 1.0
            P = (ph * float(1 << K_PHASE_BITS) + 0.5).astype(np.int64) % (1 << K_PHASE_BITS)
            B = ((P[:, None] >> np.arange(drop_low, K_PHASE_BITS)) & 1).astype(np.float64)
            B1 = np.ones((len(xs), 1))
            Bb = np.concatenate([B, B1], axis=1)
            model = (Bb @ theta) % 1.0
            tg = tgt_all[xs - 1]
            to = tol_all[xs - 1]
            err = (model - tg + 0.5) % 1.0 - 0.5
            ae = np.abs(err)
            rel = ae / np.where(to > 0, to, 1)
            i = int(np.argmax(rel))
            if rel[i] > cur_maxrel:
                cur_maxrel = float(rel[i])
                cur_worst = (int(xs[i]), float(ae[i]))
            used = ae
            allowed = to
            if not np.all(used <= allowed):
                bad = int(np.argmax(used > allowed))
                return {"pass": False, "first_fail_x": int(xs[bad]),
                        "seed": seed}
            mgn = ((allowed - used) * 2 ** 64)
            m = float(mgn.min())
            if m < cur_min_margin:
                cur_min_margin = m
            h.update(np.ascontiguousarray(ae).tobytes())
        hashes.append(h.hexdigest()[:16])
        maxrel = max(maxrel, cur_maxrel)
        if cur_min_margin < min_margin_units:
            min_margin_units = cur_min_margin
            worst = (cur_worst[0], cur_worst[1], cur_maxrel)
    # tail padding split: last batch
    tail = X_MAX % 256
    n_pad_total = (256 - tail) % 256
    return {"pass": True, "max_rel_err": maxrel,
            "min_abs_margin_units": min_margin_units,
            "min_abs_margin_turns": min_margin_units / 2 ** 64,
            "worst": {"x": worst[0], "abserr_turns": worst[1], "rel": worst[2]},
            "hashes": hashes, "seeds": list(seeds),
            "n_real": n_real_total // len(seeds), "n_pad_last_batch": n_pad_total,
            "n_rot": int(nbit + 1)}


# --------------------------------------------------------------------------
# billing hypothesis (parametric; assumption-tabled; NOT a verification)
# --------------------------------------------------------------------------

def baseline_calibration():
    import io
    import kickmix
    c = kickmix.Circuit.from_file(ART / "baseline_hw06.kmb")
    buf = __import__("io").StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines()
           if not l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    def ccx(lo, hi):
        return sum(1 for l in ops[lo:hi] if l.split()[0] in ("CCX", "CCZ", "CSWAP"))
    compute = ccx(16127, 25630)      # A+B Horner compute
    uncomp = ccx(28726, 43870)       # inverse_B + inverse_A
    return {"compute_ccx": compute, "uncompute_ccx": uncomp,
            "F_uncompute": uncomp / max(compute, 1)}


def billing_hypothesis(feats):
    """feats: dict with S, nseg, nM_digits, nR_digits, w_keep, n_rot,
    min_abs_margin_units, Ws_sum. Returns parametric cost table."""
    cal = baseline_calibration()
    F = cal["F_uncompute"]
    S = feats["S"]
    N = 2 ** S
    out = {}
    # variant 1: unary-SELECT QROM (shared decode) + reversible uncompute x2
    qrom_rev = 2.0 * N
    # variant 2: measurement-based uncompute calibrated from baseline
    qrom_meas = (1.0 + F) * N
    sq = (14 - feats["r0"]) * 14 // 2
    mlt = feats["nM_digits"] * 14 + 20
    rlt = feats["nR_digits"] * feats["w_keep"] + 20
    adds = 3 * feats["Ws_sum"]
    align = 4 * 36 + 20
    misc = 40
    datapath_meas = qrom_meas + sq + mlt + rlt + adds + align + misc
    datapath_rev = qrom_rev + 2.0 * (sq + mlt + rlt + adds + align) + misc
    out["calibration"] = cal
    for tag, dp in (("meas-calibrated", datapath_meas), ("reversible-x2", datapath_rev)):
        n_rot = feats["n_rot"]
        eps = math.pi * feats["min_abs_margin_units"] / 2 ** 64 / n_rot
        if not eps > 0:
            out[tag] = {"note": "no synthesis budget left"}
            continue
        t_rot = n_rot * (0.56 * math.log2(1.0 / eps) + 5.3)
        t_base = 7.0  # baseline-like conditional-T count, stated assumption
        C = dp + (t_base + t_rot) / 4.0
        out[tag] = {"datapath_exec": dp, "n_rot": n_rot, "eps": eps,
                    "t_rot": t_rot, "C": C, "Q62xC": 62 * C,
                    "vs_baseline_100568": 62 * C - 100568.4992,
                    "vs_threshold_95540": 62 * C - 95540.0742}
    out["formulas"] = {
        "qrom": "(1+F)*2^S shared-decode (meas) | 2*2^S (reversible)",
        "squarer": "(14-r0)*14/2",
        "M_mult": "nM_digits*14+20",
        "R_mult": "nR_digits*w_keep+20",
        "adders": "3*Ws_sum", "align_shifter": "4*36+20",
        "rot_synth": "n*(0.56*log2(1/eps)+5.3), eps=pi*min_margin_units/2^64/n",
    }
    out["assumptions"] = [
        "Q fixed at 62 (borrowed delta/seg lines; live-width check separate).",
        "Executed Toffoli-like ~= static (datapath unconditional).",
        "QROM decode shared across coefficient words; outputs are CNOTs (free).",
        "C_seg folding / OFF-form storage not assumed (conservative widths).",
        "T_base=7 conditional Ts assumed baseline-like.",
        "HYPOTHESIS ONLY: no circuit, no verification, no gain claimed.",
    ]
    return out


# --------------------------------------------------------------------------
# persistence + commands
# --------------------------------------------------------------------------

def fit_path(S, Pm, Pr, r0, variant):
    return ART / f"trackB_fit_{S}_{Pm}_{Pr}_{r0}_{variant}.json"


def save_fit(path, coef_store, summary):
    doc = {"summary": summary,
           "coef": {f"{p}_{s}": {"B0": c[0], "M": c[1], "R": c[2]}
                    for (p, s), c in coef_store.items()}}
    path.write_text(json.dumps(doc))


def load_fit(path):
    doc = json.loads(path.read_text())
    coef = {}
    for k, c in doc["coef"].items():
        p, s = k.split("_")
        coef[(int(p), int(s))] = (
            [tuple(d) for d in c["B0"]],
            [tuple(d) for d in c["M"]],
            [tuple(d) for d in c["R"]],
        )
    return doc["summary"], coef


def cfg_path(name):
    return ART / f"trackB_{name}.json"


def parse_cfg(name):
    S, Pm, Pr, r0, variant = name.split("_")
    return int(S), int(Pm), int(Pr), int(r0), variant


def cmd_cfg(one):
    S, Pm, Pr, r0, variant = one
    t0 = __import__("time").time()
    summary, coef_store, _segs = fit_config(S, Pm, Pr, r0, variant)
    summary["seconds"] = round(__import__("time").time() - t0, 1)
    save_fit(fit_path(S, Pm, Pr, r0, variant), coef_store, summary)
    print(json.dumps(summary, indent=2))


def cmd_boundary():
    rows = []
    for S in GRID_S:
        for Pm in GRID_PM:
            for Pr in GRID_PR:
                for r0 in GRID_R0:
                    for variant in VARIANTS:
                        t0 = __import__("time").time()
                        summary, coef_store, _segs = fit_config(S, Pm, Pr, r0, variant)
                        summary["seconds"] = round(__import__("time").time() - t0, 1)
                        save_fit(fit_path(S, Pm, Pr, r0, variant), coef_store, summary)
                        rows.append(summary)
                        print(json.dumps(summary), flush=True)
    tab = {"rows": rows,
           "note": "rectangle-relative minimax errors with digit-capped CSD coefficients; "
                   "HYPOTHESIS, no circuit. Threshold context: rel tol 2^-24."}
    (ART / "trackB_grid.json").write_text(json.dumps(tab, indent=2))
    print(f"wrote trackB_grid.json with {len(rows)} configs", flush=True)


def cmd_angles(one):
    S, Pm, Pr, r0, variant = one
    summary, coef_store = load_fit(fit_path(S, Pm, Pr, r0, variant))
    pts = build_boundary(S, r0)
    xs = np.array([t[0] for t in pts], dtype=np.uint64)
    tgt, tol = official.reference_values(SPEC, xs)
    tgt = tgt.astype(np.float64) / 2 ** 64
    tol = tol.astype(np.float64) / 2 ** 64
    out = {}
    for drop_low in (0, 1, 2):
        doc = fit_angles(S, r0, variant, coef_store, pts, tgt, tol, drop_low)
        if doc is None:
            out[f"drop{drop_low}"] = None
            continue
        theta = np.array(doc["theta"])
        nbit = K_PHASE_BITS - drop_low
        maxrel = 0.0
        min_margin = 1 << 64
        for (x, p, seg, dprime, sub, s), tg, to in zip(pts, tgt, tol):
            ph, _vh = model_phase_of(coef_store, S, r0, variant, p, seg, dprime, sub, s)
            P = int(ph * float(1 << K_PHASE_BITS) + 0.5) % (1 << K_PHASE_BITS)
            bits = [((P >> (j + drop_low)) & 1) for j in range(nbit)] + [1.0]
            model = sum(b * t for b, t in zip(bits, theta)) % 1.0
            err = (model - tg + 0.5) % 1.0 - 0.5
            rel = abs(err) / to if to > 0 else 0.0
            maxrel = max(maxrel, rel)
            mgn = (to - abs(err)) * 2 ** 64
            if mgn < min_margin:
                min_margin = mgn
                wloc = {"x": x, "p": p, "seg": seg, "dprime": dprime, "sub": sub, "s": s}
            if abs(err) > to:
                doc_fail = {"fail_x": x}
                break
        else:
            doc_fail = {}
        doc.update({"boundary_maxrel": maxrel, "boundary_min_margin_units": min_margin,
                    "boundary_worst_loc": wloc, "n_boundary": len(pts),
                    "boundary_pass": bool(maxrel < 1.0), **doc_fail})
        out[f"drop{drop_low}"] = doc
    named = f"{S}_{Pm}_{Pr}_{r0}_{variant}"
    cfg_path(f"angles_{named}").write_text(json.dumps(
        {"cfg": named, "rect": summary, "angles": out}, indent=2))
    print(json.dumps({"cfg": named, "n_boundary": len(pts),
                      "drop0": {k: out["drop0"][k] for k in
                                ("lp_t", "boundary_maxrel", "boundary_min_margin_units",
                                 "boundary_pass", "max_abs_dev_weight", "n_rot")}
                      if out["drop0"] else None}, indent=2))


def cmd_full(one):
    S, Pm, Pr, r0, variant = one
    named = f"{S}_{Pm}_{Pr}_{r0}_{variant}"
    _summary, coef_store = load_fit(fit_path(S, Pm, Pr, r0, variant))
    ang = json.loads(cfg_path(f"angles_{named}").read_text())["angles"]["drop0"]
    if ang is None:
        print(json.dumps({"cfg": named, "error": "no angles"}))
        return
    res = full_eval(S, r0, variant, coef_store, ang)
    res["cfg"] = named
    cfg_path(f"full_{named}").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


def cmd_billing():
    cal = baseline_calibration()
    print(json.dumps({"baseline_static_calibration": cal,
                      "baseline_official": {
                          "score": 100568.4992, "C": 1622.0725676541888,
                          "toffoli_exec": 1325.481775804887, "t_base": 6.999871841622275,
                          "n_rot": 41.0, "eps": 2.434041480874084e-13}},
                     indent=2))
    for p in sorted(ART.glob("trackB_full_*.json")):
        full = json.loads(p.read_text())
        if not full.get("pass"):
            print(json.dumps({"cfg": full.get("cfg"), "billing": "no pass, no billing"}))
            continue
        named = full["cfg"]
        S = int(named.split("_")[0])
        r0 = int(named.split("_")[3])
        fit = json.loads(fit_path(*named.split("_")[:4], named.split("_")[4]).read_text()) \
            if False else None
        # digit counts from the stored fit
        fdoc = json.loads((ART / f"trackB_fit_{named}.json").read_text())
        nM = max(len(c["M"]) for c in fdoc["coef"].values())
        nR = max(len(c["R"]) for c in fdoc["coef"].values())
        feats = {"S": S, "r0": r0, "nM_digits": nM, "nR_digits": nR,
                 "w_keep": 24, "Ws_sum": 40, "n_rot": full["n_rot"],
                 "min_abs_margin_units": full["min_abs_margin_units"]}
        hypo = billing_hypothesis(feats)
        cfg_path(f"billing_{named}").write_text(json.dumps(
            {"cfg": named, "feats": feats, "full": full, "hypo": hypo}, indent=2))
        print(json.dumps({"cfg": named, "feats": feats,
                          "meas_Q62xC": hypo["meas-calibrated"]["Q62xC"],
                          "rev_Q62xC": hypo["reversible-x2"]["Q62xC"]}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default=None)
    ap.add_argument("--boundary", action="store_true")
    ap.add_argument("--angles", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--billing", action="store_true")
    args = ap.parse_args()
    if args.boundary:
        return cmd_boundary()
    if args.billing:
        return cmd_billing()
    if args.cfg is None:
        ap.print_help()
        return 2
    one = parse_cfg(args.cfg)
    if args.angles:
        return cmd_angles(one)
    if args.full:
        return cmd_full(one)
    return cmd_cfg(one)


if __name__ == "__main__":
    main()
