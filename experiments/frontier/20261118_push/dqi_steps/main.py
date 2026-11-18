"""qcc-dqi-steps: EEA step-count cost optimisation on REAL syndromes (classical only).

Kaggle CPU kernel. No circuits, no simulation, no official verifier.

What it measures
----------------
1. Real syndromes sampled exactly as `verify_submission_dqi.sample_shots` does
   (m=4095, n syndromes, degree=12, r=2016, DQI weights, P(k)=w_k^2, uniform
   positions, uniform nonzero values), for n=70 (t=35), n=10 (t=5), n=6 (t=3).
2. Textbook EEA on (x^n, S(x)) stopped at deg R < t: per-shot quotient-degree
   sequence delta_i and multiplicand word counts W_i = deg(B_i)+1.
3. The divstep family (one leading-term elimination + swap per step -- the family
   the shipped tape belongs to) and its exact MAC count sum_i (deg A_i + 1).
4. An s-step EEA that performs exactly one division per step, for every requested
   s: does it reproduce the reference sigma?  (deliverable: convergence vs s)
5. Cost model T(s) = 42*sum_i (delta_i+1)*W_i + s*k_div*378 with the balanced
   compile-time quota bracket from the real degree sequence, k_div in {1,2,4,s}.
6. Merge-loss bound: swallowing m classical divisions into one step requires a
   2x2 transfer matrix; the cheapest application is 2(m+1)W MACs against
   2mW - m^2 for the m divisions it replaces, i.e. +2W + m^2 -- never a saving.
7. GM for the best candidate: GM = 28.180659 * (367116/T_total)^(1/3),
   T_total = 2*T_pass + 46217.

Outputs /kaggle/working/steps.json.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np

DEG = 12
Q = 1 << DEG
ORDER = Q - 1
R_SUPPORT = 2016
M_POS = 4095
STEPS = [1, 2, 3, 5, 8, 10, 15, 20, 25, 35, 50, 69]

# Measured tape numbers (dqi_algo / dqi_normeea); quoted, not re-measured here.
TAPE = {
    "eea_fwd_T": 153180.1,
    "eea_rev_T": 169719.2,
    "rows_per_pass_normalised": 3647.0,   # 153174/42, a T/42 normalisation
    "mult_blocks_fwd": 2007,
    "mult_ccx_fwd": 80984,
    "control_ccx_fwd": 72201,             # 153185 - 80984
    "div_idiom_ccx": 107,
    "T_total": 367116.057,
    "gm": 28.180659,
    "other_T": 46217.0,
}


# --------------------------------------------------------------------------- #
# GF(2^12)
# --------------------------------------------------------------------------- #
def _mul_raw(a: int, b: int, poly: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a >> DEG:
            a ^= poly
    return r


def _pow_raw(a: int, e: int, poly: int) -> int:
    r = 1
    while e:
        if e & 1:
            r = _mul_raw(r, a, poly)
        a = _mul_raw(a, a, poly)
        e >>= 1
    return r


def find_primitive_poly() -> int:
    for low in range(1, 1 << DEG):
        poly = (1 << DEG) | low
        if _pow_raw(2, ORDER, poly) != 1:
            continue
        if all(_pow_raw(2, ORDER // p, poly) != 1 for p in (3, 5, 7, 13)):
            return poly
    raise RuntimeError("no primitive polynomial found")


POLY = find_primitive_poly()
LOG = [0] * Q
ALOG = [0] * ORDER
_v = 1
for _i in range(ORDER):
    ALOG[_i] = _v
    LOG[_v] = _i
    _v = _mul_raw(_v, 2, POLY)
LOG_NP = np.array(LOG, dtype=np.int64)
ALOG_NP = np.array(ALOG, dtype=np.int64)


def gmul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return ALOG[(LOG[a] + LOG[b]) % ORDER]


def ginv(a: int) -> int:
    return ALOG[(ORDER - LOG[a]) % ORDER]


# --------------------------------------------------------------------------- #
# polynomials over GF(2^12), little-endian
# --------------------------------------------------------------------------- #
def trim(p):
    n = len(p)
    while n and p[n - 1] == 0:
        n -= 1
    return p if n == len(p) else p[:n]


def pdeg(p) -> int:
    return len(p) - 1


def padd(a, b):
    if len(a) < len(b):
        a, b = b, a
    out = list(a)
    for i, v in enumerate(b):
        out[i] ^= v
    return trim(out)


def pmul(a, b):
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        la = LOG[ai]
        for j, bj in enumerate(b):
            if bj:
                out[i + j] ^= ALOG[(la + LOG[bj]) % ORDER]
    return trim(out)


def pdivmod(a, b):
    db = len(b) - 1
    if len(a) - 1 < db:
        return [], list(a)
    r = list(a)
    q = [0] * (len(a) - db)
    inv_lb = ginv(b[db])
    for dr in range(len(a) - 1, db - 1, -1):
        coef = r[dr]
        if coef == 0:
            continue
        c = gmul(coef, inv_lb)
        q[dr - db] = c
        lc = LOG[c]
        for i in range(db + 1):
            bi = b[i]
            if bi:
                r[dr - db + i] ^= ALOG[(lc + LOG[bi]) % ORDER]
    return trim(q), trim(r)


# --------------------------------------------------------------------------- #
# EEA variants
# --------------------------------------------------------------------------- #
def eea_divisions(S, n, t, want_cofactor=True):
    """Textbook EEA on (x^n, S) stopped at deg B < t."""
    A = [0] * (n + 1)
    A[n] = 1
    B = trim(list(S))
    T0, T1 = [], [1]
    deltas, windows = [], []
    while pdeg(B) >= t:
        da, db = pdeg(A), pdeg(B)
        if db < 0:
            break
        deltas.append(da - db)
        windows.append(db + 1)
        q, r = pdivmod(A, B)
        T2 = padd(T0, pmul(q, T1)) if want_cofactor else None
        A, B = B, r
        if want_cofactor:
            T0, T1 = T1, T2
    return {
        "deltas": deltas,
        "windows": windows,
        "n_div": len(deltas),
        "sigma": trim(T1) if want_cofactor else None,
        "omega": trim(B) if want_cofactor else None,
        "A_state": A,
    }


def eea_s_steps(S, s, n, t):
    """Exactly one division per step, s steps max.  Returns the cofactor reached."""
    A = [0] * (n + 1)
    A[n] = 1
    B = trim(list(S))
    T0, T1 = [], [1]
    used = 0
    while used < s and pdeg(B) >= t:
        q, r = pdivmod(A, B)
        T2 = padd(T0, pmul(q, T1))
        A, B = B, r
        T0, T1 = T1, T2
        used += 1
    return trim(T1), used, pdeg(B)


def divstep_windows(S, n, t):
    """Divstep family: one leading-term elimination + swap per step.

    Step cost = one full-window MAC of width deg(A)+1 (the tape's formulation).
    """
    A = [0] * (n + 1)
    A[n] = 1
    B = trim(list(S))
    windows = []
    while True:
        da, db = pdeg(A), pdeg(B)
        if db < t or db < 0:
            break
        windows.append(da + 1)
        if da >= db:
            c = gmul(A[da], ginv(B[db]))
            shift = da - db
            lc = LOG[c]
            for i in range(db + 1):
                bi = B[i]
                if bi:
                    A[shift + i] ^= ALOG[(lc + LOG[bi]) % ORDER]
            A = trim(A)
        A, B = B, A
    return windows


def band_gaps(deltas, s, top, t):
    """Group the division sequence into s degree bands; return each band's gap."""
    bounds = [top - round((top - t) * j / s) for j in range(s + 1)]
    gaps = [0] * s
    d = 0
    for dlt in deltas:
        start = top - d
        j = 0
        while j < s - 1 and start <= bounds[j + 1]:
            j += 1
        gaps[j] += dlt
        d += dlt
    return gaps, bounds


# --------------------------------------------------------------------------- #
# shot sampling (replica of the verifier distribution)
# --------------------------------------------------------------------------- #
def optimal_dqi_weights(m, max_errors, degree, r):
    q = 1 << degree
    k = np.arange(max_errors + 1, dtype=np.float64)
    off = np.sqrt(k[1:] * (m - k[1:] + 1))
    d = (q - 2 * r) / math.sqrt(r * (q - r))
    _, vecs = np.linalg.eigh(np.diag(k * d) + np.diag(off, 1) + np.diag(off, -1))
    w = np.abs(vecs[:, -1])
    return w / np.linalg.norm(w)


def sample_syndromes(n_synd, num_shots, seed):
    rng = np.random.default_rng(seed)
    l = n_synd // 2
    probs = optimal_dqi_weights(M_POS, l, DEG, R_SUPPORT) ** 2
    probs = probs / probs.sum()
    weights = rng.choice(len(probs), size=num_shots, p=probs)
    rows = np.arange(1, n_synd + 1, dtype=np.int64)[:, None]
    syn = np.zeros((num_shots, n_synd), dtype=np.int64)
    pos_all = np.full((num_shots, max(1, l)), -1, dtype=np.int64)
    for shot in range(num_shots):
        k = int(weights[shot])
        if k == 0:
            continue
        pos = rng.choice(M_POS, size=k, replace=False)
        vals = rng.integers(1, Q, size=k, dtype=np.int64)
        pos_all[shot, :k] = pos
        exps = (LOG_NP[vals][None, :] + rows * pos[None, :]) % ORDER
        syn[shot] = np.bitwise_xor.reduce(ALOG_NP[exps], axis=1)
    return syn, pos_all, weights


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #
def analyse(n_synd, num_shots, seed, cofactor_shots=150):
    t = n_synd // 2
    syn, pos_all, weights = sample_syndromes(n_synd, num_shots, seed)

    n_div_hist, delta_hist, deg_s_hist, drop_hist = {}, {}, {}, {}
    sum_delta, div_rows, step_macs, step_counts = [], [], [], []
    n_by_k: dict[int, list[int]] = {}
    worst_gap = {s: [0] * s for s in STEPS}
    gap_sum = {s: [0] * s for s in STEPS}
    conv = {s: [0, 0] for s in STEPS}
    roots_ok = [0, 0]
    first_gap_hist = {}
    sigma_deg_ok = [0, 0]

    t0 = time.time()
    for shot in range(num_shots):
        S = trim([int(x) for x in syn[shot]])
        deg_s_hist[pdeg(S)] = deg_s_hist.get(pdeg(S), 0) + 1
        r = eea_divisions(S, n_synd, t, want_cofactor=False)
        N = r["n_div"]
        first_gap_hist[r["deltas"][0] if r["deltas"] else 0] = (
            first_gap_hist.get(r["deltas"][0] if r["deltas"] else 0, 0) + 1)
        n_div_hist[N] = n_div_hist.get(N, 0) + 1
        for d in r["deltas"]:
            delta_hist[d] = delta_hist.get(d, 0) + 1
        kk = int(weights[shot])
        n_by_k.setdefault(kk, []).append(N)
        # pair-degree drop per division (what a 1-sweep-per-degree schedule needs)
        A = [0] * (n_synd + 1)
        A[n_synd] = 1
        B = S
        while pdeg(B) >= t:
            q, rr = pdivmod(A, B)
            A, B = B, rr
            dd = pdeg(A) - pdeg(B) if pdeg(B) >= 0 else 0
            drop_hist[dd] = drop_hist.get(dd, 0) + 1
        sum_delta.append(sum(r["deltas"]))
        div_rows.append(sum((d + 1) * w for d, w in zip(r["deltas"], r["windows"])))
        wnd = divstep_windows(S, n_synd, t)
        step_macs.append(sum(wnd))
        step_counts.append(len(wnd))
        for s in STEPS:
            g, _ = band_gaps(r["deltas"], s, n_synd, t)
            for j, v in enumerate(g):
                worst_gap[s][j] = max(worst_gap[s][j], v)
                gap_sum[s][j] += v

        if shot < cofactor_shots:
            ref = eea_divisions(S, n_synd, t, want_cofactor=True)
            sigma_ref = ref["sigma"]
            k_true = int((pos_all[shot] >= 0).sum())
            # root test at the true error locations
            good = True
            for j in pos_all[shot]:
                if j < 0:
                    continue
                x = ALOG[(ORDER - (j % ORDER)) % ORDER]
                acc = 0
                for c in reversed(sigma_ref):
                    acc = gmul(acc, x) ^ c
                if acc != 0:
                    good = False
                    break
            if k_true == 0:
                good = sigma_ref == [1]
            elif pdeg(sigma_ref) != k_true:
                good = False
            roots_ok[0] += int(good)
            roots_ok[1] += 1
            sigma_deg_ok[0] += int(pdeg(sigma_ref) == k_true)
            sigma_deg_ok[1] += 1
            # convergence of an s-step schedule (one division per step)
            for s in STEPS:
                sig, used, final_deg = eea_s_steps(S, s, n_synd, t)
                conv[s][0] += int(sig == list(sigma_ref))
                conv[s][1] += 1

    elapsed = time.time() - t0

    brackets = {}
    for s in STEPS:
        bounds = [n_synd - round((n_synd - t) * j / s) for j in range(s + 1)]
        gaps_nom = [bounds[j] - bounds[j + 1] for j in range(s)]
        W = [bounds[j] + 1 for j in range(s)]
        rows_nom = sum((g + 1) * w for g, w in zip(gaps_nom, W))
        rows_wc = sum((g + 1) * w for g, w in zip(worst_gap[s], W))
        # merges needed to collapse the required divisions into s bands: each of
        # the (N_req - s) merges adds >= 2W + m^2 (see merge-loss bound in docstring)
        n_req = max(n_div_hist)
        n_merges = max(0, n_req - s)
        m_avg = n_req / s
        w_avg = sum(W) / len(W)
        merge = n_merges * (2 * w_avg + m_avg ** 2)
        brackets[str(s)] = {
            "gaps_nominal": gaps_nom,
            "gaps_worst_observed": worst_gap[s],
            "gaps_mean_observed": [round(v / num_shots, 3) for v in gap_sum[s]],
            "windows": W,
            "rows_nominal": rows_nom,
            "rows_worst_case": rows_wc,
            "merge_loss_rows_floor": merge,
            "rows_honest_floor": None,   # filled below (divstep MACs are step-independent)
        }

    return {
        "n_syndromes": n_synd,
        "t": t,
        "num_shots": num_shots,
        "elapsed_s": round(elapsed, 1),
        "n_div_hist": {str(k): v for k, v in sorted(n_div_hist.items())},
        "n_div_stats": {
            "min": min(n_div_hist),
            "max": max(n_div_hist),
            "mean": round(float(sum(k * v for k, v in n_div_hist.items()) / num_shots), 3),
        },
        "delta_hist": {str(k): v for k, v in sorted(delta_hist.items())},
        "first_gap_hist": {str(k): v for k, v in sorted(first_gap_hist.items())},
        "sum_delta_stats": {
            "min": int(min(sum_delta)),
            "max": int(max(sum_delta)),
            "mean": round(float(np.mean(sum_delta)), 3),
        },
        "deg_syndrome_hist": {str(k): v for k, v in sorted(deg_s_hist.items())},
        "degree_drop_hist": {str(k): v for k, v in sorted(drop_hist.items())},
        "n_div_by_weight": {str(k): {"n": len(v), "mean": round(float(np.mean(v)), 2),
                                     "min": int(min(v)), "max": int(max(v))}
                            for k, v in sorted(n_by_k.items())},
        "div_model_rows_mean": round(float(np.mean(div_rows)), 2),
        "divstep": {
            "steps_mean": round(float(np.mean(step_counts)), 3),
            "steps_min": int(min(step_counts)),
            "steps_max": int(max(step_counts)),
            "macs_mean": round(float(np.mean(step_macs)), 2),
            "macs_min": int(min(step_macs)),
            "macs_max": int(max(step_macs)),
            "ideal_one_sweep_per_degree": sum(range(t + 2, n_synd + 2)),
            "closed_form_sum_h_plus_1": sum(range(t + 1, n_synd + 1)),
        },
        "convergence": {str(s): {"ok": v[0], "total": v[1]} for s, v in conv.items()},
        "sigma_roots_ok": {"ok": roots_ok[0], "total": roots_ok[1]},
        "sigma_degree_ok": {"ok": sigma_deg_ok[0], "total": sigma_deg_ok[1]},
        "step_brackets": brackets,
    }


def cost_table(analysis):
    out = {}
    rows_base = analysis["step_brackets"]["35"]["rows_nominal"]  # achievable schedule
    for s_key, br in analysis["step_brackets"].items():
        s = int(s_key)
        entry = {"s": s,
                 "rows_nominal": br["rows_nominal"],
                 "rows_worst_case": br["rows_worst_case"],
                 "merge_loss_rows_floor": br["merge_loss_rows_floor"]}
        # honest row count: the s=35 schedule plus the transfer-matrix merges
        # needed to collapse 35 divisions into s groups (>= 2W + m^2 per merge)
        rows_honest = rows_base + br["merge_loss_rows_floor"]
        entry["rows_honest"] = round(rows_honest, 1)
        # calibrated reading: the tape's rows already contain its control + division
        # cost (3,647 rows/pass = 153,174 T/42), so rows*42 alone is comparable.
        entry["T_rows_only"] = round(42.0 * br["rows_nominal"], 1)
        entry["GM_rows_only"] = round(
            TAPE["gm"] * (TAPE["T_total"] / (2 * 42.0 * br["rows_nominal"] + TAPE["other_T"])) ** (1 / 3), 4)
        entry["T_rows_only_honest"] = round(42.0 * rows_honest, 1)
        entry["GM_rows_only_honest"] = round(
            TAPE["gm"] * (TAPE["T_total"] / (2 * 42.0 * rows_honest + TAPE["other_T"])) ** (1 / 3), 4)
        # k_div = delta+1: one inversion per quotient term of the step
        for name, kd in (("k1", 1), ("k2", 2), ("k4", 4), ("kdelta", 0)):
            kd_eff = (analysis["n_syndromes"] / 2.0) / s + 1.0 if name == "kdelta" else kd
            for tag, rv in (("nom", br["rows_nominal"]), ("wc", br["rows_worst_case"])):
                T = 42.0 * rv + s * kd_eff * 378.0
                entry[f"T_{name}_{tag}"] = round(T, 1)
                entry[f"GM_{name}_{tag}"] = round(
                    TAPE["gm"] * (TAPE["T_total"] / (2 * T + TAPE["other_T"])) ** (1 / 3), 4)
                entry[f"dT_{name}_{tag}"] = round(T - TAPE["eea_fwd_T"], 1)
            Th = 42.0 * rows_honest + s * kd * 378.0
            entry[f"T_{name}_honest"] = round(Th, 1)
            entry[f"GM_{name}_honest"] = round(
                TAPE["gm"] * (TAPE["T_total"] / (2 * Th + TAPE["other_T"])) ** (1 / 3), 4)
        out[str(s)] = entry
    return out


def main():
    res = {"field": {"poly": hex(POLY), "order": ORDER},
           "tape_reference": TAPE, "runs": {}}
    for n_synd, shots, seed in ((70, 3000, 20261118), (10, 1500, 7), (6, 800, 11)):
        res["runs"][f"n{n_synd}"] = analyse(n_synd, shots, seed)
        print(f"done n={n_synd} in {res['runs'][f'n{n_synd}']['elapsed_s']} s", flush=True)

    a70 = res["runs"]["n70"]
    res["cost_table_n70"] = cost_table(a70)
    res["steps_required_fixed_schedule"] = a70["n_div_stats"]["max"]

    mult_floor = a70["divstep"]["closed_form_sum_h_plus_1"]
    best = 42.0 * mult_floor + TAPE["control_ccx_fwd"]
    res["calibrated"] = {
        "mult_floor_rows": mult_floor,
        "mult_model_ccx": 42.0 * mult_floor,
        "tape_mult_ccx": TAPE["mult_ccx_fwd"],
        "tape_mult_blocks": TAPE["mult_blocks_fwd"],
        "mult_slack_frac": round(1.0 - (42.0 * mult_floor) / TAPE["mult_ccx_fwd"], 4),
        "control_ccx": TAPE["control_ccx_fwd"],
        "control_per_step": round(TAPE["control_ccx_fwd"] / 34.0, 1),
        "T_best_pass": round(best, 1),
        "T_best_total": round(2 * best + TAPE["other_T"], 1),
        "GM_best": round(TAPE["gm"] * (TAPE["T_total"] / (2 * best + TAPE["other_T"])) ** (1 / 3), 4),
        "dT_vs_tape_fwd": round(best - TAPE["eea_fwd_T"], 1),
        "frac_of_tape": round(best / TAPE["eea_fwd_T"], 4),
    }
    with open("/kaggle/working/steps.json", "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res["calibrated"], indent=1))
    print("wrote /kaggle/working/steps.json")


if __name__ == "__main__":
    main()
