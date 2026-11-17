#!/usr/bin/env python3
"""DQI width exchange rate: what a qubit is worth vs what a qubit costs.

Official formula (data/competition/verifiers/dqi/verify_submission_dqi.py:16,420):
    score = R(eps_plus) * Q^2 * T
so d(score)/score = 2 dQ/Q + dT/T and the T allowance for shedding k qubits is
exactly the cost gain, (Q/(Q-k))^2 - 1.

Mechanism costs are the MEASURED ones from dqi/RESULT.md §3 and dqi/RESULT2.md §2.
No simulation, no verifier runs.
"""

Q = 890
T = 367120.0042382812          # mean Toffoli-like per shot, shipped 61c8348d
GM = 28.15083                  # current public best (ref 58454232)
GOLD = 28.68633

MECH = {
    "optimistic  q864 re-home, 1 CCX/episode": 925,
    "realistic   q864 re-home, 1 CCX/product": 7195,
    "measured    888 build (2 qubits/15,864 T)": 15864 / 2,
}

need = (GM / GOLD) ** 3


def gm_at(k, t_per_qubit=0.0):
    f = ((Q - k) / Q) ** 2 * (1 + t_per_qubit * k / T)
    return GM / f ** (1 / 3)


def main():
    print(f"score ~ Q^2*T ; Q={Q} T={T:.1f} ; current GM {GM} ; gold {GOLD}")
    print(f"gold needs the cost factor {need:.6f} (product shrink {1/need:.6f}x)\n")

    print("k   Q    cost gain  break-even T total  per qubit   free-T GM   gold T budget")
    for k in (1, 5, 10, 20, 25, 26, 50):
        q = Q - k
        f = (q / Q) ** 2
        gain = 1 - f
        be = (1 / f - 1) * T
        gold_budget = (need / f - 1) * T
        gold_pct = (need / f - 1) * 100
        print(f"{k:2d} {q:3d}   {gain*100:8.3f}%   {be:12,.0f} T   {be/k:7.1f}   "
              f"{GM/f**(1/3):9.5f}   {gold_pct:+8.3f}% ({gold_budget:,.0f} T)")

    print("\nmechanism cost vs the two thresholds:")
    for name, tq in MECH.items():
        print(f"  {name:44} {tq:8.0f} T/qubit")
    print(f"  {'break-even at Q865':44} {861:8.1f} T/qubit")
    print(f"  {'gold at Q865 (T budget 166 T / 25 qubits)':44} {166/25:8.1f} T/qubit")

    print("\nGM obtained by shedding k qubits at each measured mechanism:")
    print("  k    " + "".join(f"{n.split()[0]:>12}" for n in MECH))
    for k in (1, 5, 25, 50):
        row = "".join(f"{gm_at(k, tq):12.5f}" for tq in MECH.values())
        print(f"  {k:2d}   {row}")
    print(f"\n  (current {GM}; gold {GOLD}) — every measured mechanism lands BELOW current,")
    print("  and Q865 must be T-flat to clear gold at all.")


if __name__ == "__main__":
    main()
