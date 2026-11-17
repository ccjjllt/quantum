"""Exact cost arithmetic for the invsqrt leg (no simulation).

Everything here is closed-form from the official verifier's cost model:
  C      = Toffoli + T/4
  T      = t_base + n_rot * (0.56*log2(1/eps) + 5.3)
  eps    = pi * margin_units / 2**64 / n_rot          (margin in units of 2^-64 turns)
  score  = Q * C
"""
import json
import math

TARGET = 74560.90687312803
Q0, TOF0, TBASE0, NROT0, EPS0 = 44, 1454.000786597537, 2.500049142088342, 33, 1.6406054738480745e-13


def rot_t(eps):
    return 0.56 * math.log2(1 / eps) + 5.3


def C(tof, n, margin_units, tbase=TBASE0):
    if n == 0:
        return tof + tbase / 4
    eps = math.pi * margin_units / 2.0**64 / n
    return tof + (tbase + n * rot_t(eps)) / 4


M0 = EPS0 * 2.0**64 * NROT0 / math.pi  # margin units implied by the shipped eps

out = {}
out["shipped"] = {
    "Q": Q0, "toffoli": TOF0, "t_base": TBASE0, "n_rot": NROT0, "eps": EPS0,
    "margin_units": M0, "C": C(TOF0, NROT0, M0), "score": Q0 * C(TOF0, NROT0, M0),
}

# 1. what C each Q must beat, at the shipped rotation block
out["budget_by_Q"] = {}
for Q in range(44, 21, -1):
    Cmax = TARGET / Q
    tof_max = Cmax - (TBASE0 + NROT0 * rot_t(EPS0)) / 4
    out["budget_by_Q"][Q] = {
        "C_max": Cmax,
        "toffoli_max_at_shipped_rotations": tof_max,
        "toffoli_delta_vs_shipped": tof_max - TOF0,
        "frac_C_delta": (Cmax / out["shipped"]["C"] - 1),
    }

# 2. rotation block cost vs n_rot at fixed margin, and at better margins
out["rot_block"] = {}
for mult in (1, 2, 4, 8, 16):
    key = f"margin_x{mult}"
    out["rot_block"][key] = {}
    for n in (33, 32, 30, 28, 25, 22, 20, 15, 10):
        eps = math.pi * (M0 * mult) / 2.0**64 / n
        per = rot_t(eps)
        out["rot_block"][key][n] = {"eps": eps, "t_per_rot": per, "t_total": n * per,
                                    "C_block": n * per / 4}

# 3. what an extra Toffoli must buy: sensitivity of the score to n_rot at fixed margin
out["sensitivity"] = {
    "dT_per_rotation_at_n33": rot_t(EPS0),
    "dC_per_rotation": rot_t(EPS0) / 4,
    "dScore_per_rotation": Q0 * rot_t(EPS0) / 4,
    "dScore_frac_per_rotation": (rot_t(EPS0) / 4) / out["shipped"]["C"],
    "one_qubit_equiv_C": out["shipped"]["C"] / Q0,
    "one_qubit_frac": 1 / Q0,
}

# 4. public / measured frontier points (Q, mean_toffoli, n_rot, eps, cost) for reference
frontier = [
    {"name": "563d0583 (ours now)", "Q": 44, "tof": 1454.0008, "n": 33, "eps": 1.6406055e-13},
    {"name": "0af21cb8 (prev ours)", "Q": 44, "tof": 1459.3749, "n": 33, "eps": 1.6406055e-13},
    {"name": "Syed46 (ahoirg K=6)", "Q": 46, "tof": 1480.8, "n": 33, "eps": 6.42e-13},
]
for f in frontier:
    f["C"] = C(f["tof"], f["n"], f["eps"] * 2.0**64 * f["n"] / math.pi)
    f["score"] = f["Q"] * f["C"]
    f["vs_target"] = f["score"] / TARGET - 1

out["frontier"] = frontier

# 5. the 42Q question: required Toffoli slope
b = out["budget_by_Q"]
out["slope_42"] = {
    "required_toffoli_at_Q42": b[42]["toffoli_max_at_shipped_rotations"],
    "delta_vs_44": b[42]["toffoli_max_at_shipped_rotations"] - TOF0,
    "per_wire": (b[42]["toffoli_max_at_shipped_rotations"] - TOF0) / 2,
    "observed_46_to_44_per_wire": (1480.8 - TOF0) / 2,
}

print(json.dumps(out, indent=1))
open("/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/invsqrt/trade.json", "w").write(
    json.dumps(out, indent=1))
