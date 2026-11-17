#!/usr/bin/env python3
"""DQI width exchange rate at the SHIPPED point 575b043f (pure arithmetic).

    python3 budget2.py

cost = R(eps+) * Q^2 * meanT   (official verifier, verify_submission_dqi.py:420)
R is a constant tax (0 failures at N=102,400 => eps+ = 8.6606e-4 => R = 1.1912605),
so dcost/cost = 2 dQ/Q + dT/T and the T budget for shedding k qubits is
    ((Q/(Q-k))^2 - 1) * T          (tie)     |  ((Q/(Q-k))^2 * cost0/target - 1) * T  (gold)

No simulation, no verifier run: the two inputs are the official verifier output
(575b043f: Q 890, meanT 367,116.0572168, cost 346,409,762,292.7187) and self-checked
arithmetic.
"""
from __future__ import annotations

R = 1.1912605
Q = 890
T = 367116.0572168             # mean Toffoli-like per shot, shipped 575b043f
COST = 346409762292.7187       # official clean cost, shipped 575b043f
GOLD_GM = 28.71339
CUR_GM = 28.150932035980528
# single-leg DQI cost needed for gold with the other two legs held (scripts/gm.py)
GOLD_COST = 326448778537.0


def gm_at(k: int, t_per_qubit: float) -> float:
    """GM when k qubits are shed at `t_per_qubit` extra T each and nothing else moves."""
    cost = R * (Q - k) ** 2 * (T + k * t_per_qubit)
    # GM scales as the cube root of the leg's cost ratio
    return CUR_GM * (COST / cost) ** (1 / 3)


def main() -> None:
    print(f"model cost R*Q^2*T = {R * Q * Q * T:,.4f}   official {COST:,.4f} "
          f"(residual {100 * (R * Q * Q * T / COST - 1):+.6f} %)")
    print(f"gold needs this leg <= {GOLD_COST:,.0f} = factor {GOLD_COST / COST:.6f} "
          f"({100 * (GOLD_COST / COST - 1):+.3f} %)\n")

    print(" k    Q   gain(Q only)   T budget to TIE      per qubit   T budget for GOLD     per qubit")
    for k in (1, 3, 5, 10, 25, 26, 27, 50):
        q = Q - k
        f = (q / Q) ** 2
        tie = (1 / f - 1) * T
        gold = (GOLD_COST / COST / f - 1) * T
        print(f"{k:2d} {q:4d}   {100 * (1 - f):8.3f} %   {tie:16,.0f} T   {tie / k:9.1f}   "
              f"{gold:14,.0f} T   {gold / k:9.1f}")

    print("\nGM obtained by shedding k qubits, T flat (t_per_qubit = 0):")
    for k in (1, 3, 5, 10, 25, 26, 27, 50):
        print(f"  k={k:2d} Q={Q - k}: GM {gm_at(k, 0.0):.5f}  ({gm_at(k, 0.0) - CUR_GM:+.5f})")

    print("\nmeasured mechanisms, GM per k (cost = k * T/qubit):")
    mech = {"925 T/qubit (dqi RESULT.md best)": 925, "1831 T/qubit (q889 whole-wire)": 1831,
            "3822 T/qubit (50-wire average)": 3822}
    print("  k    " + "".join(f"{n.split()[0]:>12}" for n in mech))
    for k in (1, 3, 5, 10, 25, 50):
        print(f"  {k:2d}   " + "".join(f"{gm_at(k, tq):12.5f}" for tq in mech.values()))


if __name__ == "__main__":
    main()
