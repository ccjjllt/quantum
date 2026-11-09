"""a_fail.py: default-salt failure analysis reusing baseline_2048shot.json (read-only).

Outputs artifacts/20261109_dqi_r_nonw17/a_fail.json.
No verifier run (baseline bytes untouched). No tests/CI.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import numpy as np

BASE = Path("artifacts/20261109_affine_cache/baseline_2048shot.json")
S1 = Path("artifacts/20261109_dqi_decoder_struct/s1_blocks.json")
OUT = Path("artifacts/20261109_dqi_r_nonw17/a_fail.json")

Q = 892
Q2 = Q * Q  # 795664


def clopper_pearson_upper(k: int, n: int, log2_delta: float = -128.0) -> float:
    log_delta = log2_delta * math.log(2.0)
    if k == 0:
        return -math.expm1(log_delta / n)
    j = np.arange(k + 1, dtype=np.float64)
    log_comb = np.r_[0.0, np.cumsum(np.log(n - j[1:] + 1.0) - np.log(j[1:]))]

    def log_tail(p: float) -> float:
        terms = log_comb + j * math.log(p) + (n - j) * math.log1p(-p)
        m = float(terms.max())
        return m + math.log(float(np.exp(terms - m).sum()))

    lo, hi = k / n if log_tail(k / n) >= log_delta else 0.0, 1.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        if log_tail(mid) > log_delta:
            lo = mid
        else:
            hi = mid
    return hi


def R(eps: float) -> float:
    return math.log(2.0) / -math.log(0.5 + 2.0 * math.sqrt(eps))


def main() -> None:
    base = json.loads(BASE.read_text())
    n = base["verified_shots"]
    k = base["value_errors"] + base["phase_errors"]
    eps0 = clopper_pearson_upper(0, 102400)
    eps1 = clopper_pearson_upper(1, 102400)
    r0, r1 = R(eps0), R(eps1)
    per_gate = r0 * Q2  # +1 static unconditional Toffoli ~= +1 mean T
    marginal_1fail = (r1 - r0) * Q2 * base["toffoli_count"]

    # DQI weight masses (verifier distribution, m=4095,n=70,deg=12,r=2016)
    m, nn, deg, rr = 4095, 70, 12, 2016
    lmax = nn // 2
    q = 1 << deg
    kk = np.arange(lmax + 1, dtype=float)
    off = np.sqrt(kk[1:] * (m - kk[1:] + 1))
    d = (q - 2 * rr) / math.sqrt(rr * (q - rr))
    M = np.diag(kk * d) + np.diag(off, 1) + np.diag(off, -1)
    _, vecs = np.linalg.eigh(M)
    w = np.abs(vecs[:, -1])
    w /= np.linalg.norm(w)
    p = w ** 2

    # candidate non-w17 locations (static facts from s1 census + line scans)
    s1 = json.loads(S1.read_text())
    summ = s1["block_summary"]
    cands = {
        "extract_inverse24_24bittests": {
            "n_blocks": summ["extract/inverse24"]["n"],
            "paid_mean": summ["extract/inverse24"]["paid_mean"],
            "lines": "e.g. block0 [2698637,2700622] 42 CCX; 69 blocks total ~3910 CCX",
            "hypothesis": "accidental zero in a 24-bit intermediate/test "
                          "(Syed V11 'for example an accidental zero in a 24-bit test'); "
                          "order estimate 69*2^-24~=4.1e-6/shot ~=0.42/102400, "
                          "same order as residual 21/7.37M=0.29/102400",
            "gate_cost_per_site": "mean ~57 CCX per block; guard proposal +2 CCX/site",
        },
        "unextract_push_ccz_zerotest": {
            "n_zones": 50,
            "example_9line_zones": [[52712857, 52712865], [53305389, 53305397]],
            "example_body": "PUSH if b; X a;X b;X t; CCZ a b t; X a;X b;X t; POP (=phase on a=b=t=0)",
            "static_per_zone": "1 CCZ (Toffoli-like) + 6 X, condition free",
            "hypothesis": "phase error if zero-test inputs hold accidental combination; "
                          "detection-only guard +2 CCX (AND cascade into fresh ancilla, data untouched)",
        },
        "extract_node3_pole": {
            "note": "Syed V11: node-3 runs retained without pole flag; pole fires only on "
                    "weight<=5 shots, class already given up/priced",
            "weight_le5_mass": float(p[:6].sum()),
            "expected_shots_per_7M": float(p[:6].sum() * 7.37e6),
            "verdict": "expected fixes ~0 (mass 4.2e-18); any flag retention (+~24 CCX by last-node precedent) net negative",
        },
        "w17_reference_excluded": {
            "weight17_mass": float(p[17]),
            "expected_w17_per_102400": float(p[17] * 102400),
            "note": "excluded from this experiment per task (see affine_cache §5: +175 vs (27-21)/72*1.722e9 net -2.2e7)",
        },
    }

    res = {
        "baseline_file": str(BASE),
        "baseline": {
            "value_errors": base["value_errors"],
            "phase_errors": base["phase_errors"],
            "verified_shots": n,
            "mean_T": base["toffoli_count"],
            "static": base["max_toffoli_count"],
            "R": base["repetition_factor"],
            "score": base["score"],
        },
        "finding": "0 failures in default-salt 2048-shot: NO failed-shot distribution exists to localize; "
                   "w17-excluded high-frequency mode cannot be read off this file. "
                   "Non-w17 candidates below come from Syed V11 taxonomy + weight masses + static scans (honest boundary).",
        "marginals_N102400": {
            "R0": r0, "R1": r1, "dR_1fail": r1 - r0,
            "per_static_gate": per_gate,
            "score_per_1fail": marginal_1fail,
            "rel_per_1fail": (r1 - r0) / r0,
        },
        "weight_masses": {
            "mean_weight": float(np.arange(lmax + 1) @ p),
            "p_le5": float(p[:6].sum()),
            "p17": float(p[17]),
            "exp_per_102400_le5": float(p[:6].sum() * 102400),
            "exp_per_102400_w17": float(p[17] * 102400),
        },
        "candidates_nonw17": cands,
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({
        "failures": k, "R0": r0, "dR": r1 - r0,
        "per_gate": per_gate, "per_fail": marginal_1fail,
        "p_le5": float(p[:6].sum()), "p17": float(p[17]),
    }, indent=1))


if __name__ == "__main__":
    main()
