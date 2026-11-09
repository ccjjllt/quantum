"""Fusion-candidate prize evaluation (static, verifier cost model).

Cost model (verifiers/invsqrt/verify_submission_invsqrt.py):
  t(n) = n * (0.56*log2(1/eps_n) + 5.3),  eps_n = pi*min_margin/2^64/n
  score = Q * (toffoli_count + t_count/4),  t_count = t_base + t(n)
A semantics-preserving merge n -> n' keeps min_margin and toffoli fixed, so
  dScore = Q * (t(n)-t(n'))/4.
eps_41 proxy = 2.434041480874084e-13 (full-verifier value measured on
maoxin_v2_nofallback, n_rot=41; see 20261106_cleanup/README). Frontier eps is
unmeasured (no full verify per constraints); sensitivity x0.1/x10 reported.

Candidates:
  A (mega): 11 zero-branch-duplicate rotations -> 1 (41 -> 31).
  B (pair): the two read-identical rotations on 8 probes -> 1 (41 -> 40).
  C (clifford): q3 1.0 @15966 + q3 1.0 @16302 -> 1 (free-gate merge, dScore=0).
Feasibility (from phase_census.json + branch_check.json): A dead (21/24 cells
differ across cuts, same branch); B open-to-arbitration (built + verifier-run);
C blocked (CSWAP nondiag touches on q3 between the two).
"""
from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path

EPS41 = 2.434041480874084e-13
Q = 62
ANGLES_11 = [
    "0.000000953674674433768222725493757252479554153978824615478515625",
    "0.00000190735156659180456195645803063598577864468097686767578125",
    "0.000003814699517350607187171629419708551722578704357147216796875",
    "0.000007629400187021966213418711078020351123996078968048095703125",
    "0.000015258793341380309967203476873010004055686295032501220703125",
    "0.000030517585763242577497067475889025445212610065937042236328125",
    "0.000061035207881432636256580082090295036323368549346923828125",
    "0.000122070493077072283853723444480010584811680018901824951171875",
    "0.000244140657685986838150438149597221126896329224109649658203125",
    "0.0004882823651352449952078860206938770716078579425811767578125",
    "0.00097655912376819610336287080798456372576765716075897216796875",
]


def t_of_n(n: int, eps41: float) -> float:
    eps = eps41 * 41 / n
    return n * (0.56 * math.log2(1 / eps) + 5.3)


def main() -> None:
    census = json.load(open("experiments/invsqrt/20261109_tphase_fusion/phase_census.json"))
    branch = json.load(open("experiments/invsqrt/20261109_tphase_fusion/branch_check.json"))
    assert census["counts"]["rotation"] == 41
    total11 = sum(Fraction(a) for a in ANGLES_11)
    out = {
        "model": "score=Q*(toffoli+t/4); t=n*(0.56*log2(1/eps)+5.3); eps_n=eps41*41/n",
        "eps41_proxy": EPS41,
        "eps41_source": "20261106_cleanup maoxin_v2 full-verify (n_rot=41); frontier unmeasured",
        "angle_sum_11_half_turns": str(total11),
        "angle_sum_11_turns": str(total11 / 2),
        "candidates": {},
    }
    for name, n_from, n_to, feas in [
        ("A_mega_11_to_1", 41, 31, "dead: 21/24 (x,seed) same-branch cells differ (branch_check.json)"),
        ("B_pair_41_to_40", 41, 40, "screen-pass on 8 probes; built as candidate kmb, verifier-arbitrated"),
        ("C_clifford_q3", 41, 41, "blocked: CSWAP nondiag touches on q3 between @15966/@16302; prize 0 anyway"),
    ]:
        row = {"n_from": n_from, "n_to": n_to, "feasibility": feas, "by_eps": {}}
        for tag, e in [("proxy", EPS41), ("x0.1", EPS41 * 0.1), ("x10", EPS41 * 10.0)]:
            dt = t_of_n(n_from, e) - t_of_n(n_to, e)
            row["by_eps"][tag] = {"dT": dt, "dC": dt / 4, "dScore_Q62": Q * dt / 4}
        out["candidates"][name] = row
    # single-rotation value at proxy (reference scale)
    dt1 = t_of_n(41, EPS41) - t_of_n(40, EPS41)
    out["one_rotation_value_proxy"] = {"dT": dt1, "dScore": Q * dt1 / 4}
    Path("experiments/invsqrt/20261109_tphase_fusion/fusion_eval.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
