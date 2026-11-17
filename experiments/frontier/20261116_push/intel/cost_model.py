#!/usr/bin/env python3
"""Reproduce all three official task costs from their published formulas.

Sources (read-only, unmodified):
  invsqrt  data/competition/verifiers/invsqrt/verify_submission_invsqrt.py:31-41,327
  dqi      data/competition/verifiers/dqi/verify_submission_dqi.py:16,420
  chem     data/competition/verifiers/dfthcsos/verify.py:4,53-58,128-139,389-412

No simulation, no verifier runs: pure arithmetic on the numbers the verifiers
already printed into pipeline/RESULT_2815083.md.
"""

import math

R1, R2, R3 = 2076774.233715, 24439463583672.93, 3355599588.3155375


def gm(ci, cd, cc):
    return (R1 / ci * R2 / cd * R3 / cc) ** (1.0 / 3.0)


# ---------------------------------------------------------------- invsqrt
# score = Q * C, C = Toffolis + T/4 ; a non-Clifford rotation costs
# (0.56*log2(1/eps) + 5.3) T each, eps picked largest that fits the margin.
INV = dict(Q=44, toff=1459.3748802688297, t_count=2.499900279707492,
           rots=33, eps=1.6406054738480745e-13, score=74797.36535717871)


def invsqrt_cost(q, toff, t_count, rots, eps):
    t_per_rot = 0.56 * math.log2(1.0 / eps) + 5.3
    C = toff + (t_count + rots * t_per_rot) / 4.0
    return q * C, t_per_rot, C


# ---------------------------------------------------------------- dqi
# score = R(eps_plus) * Q^2 * T ; R(eps) = ln2 / -ln(1/2 + 2*sqrt(eps))
# clean (k=0) upper Clopper-Pearson bound at delta = 2^-128, N = 102400.
def r_factor(eps):
    return math.log(2) / -math.log(0.5 + 2.0 * math.sqrt(eps))


def cp_upper_zero(N, delta):
    return 1.0 - delta ** (1.0 / N)


DQI = dict(Q=890, T=367120.0042382812, N=102400, delta=2.0 ** -128,
           rep_reported=1.1967314991687559, score=348004440260.464)

# ---------------------------------------------------------------- chem
# score = lambda_eff * T_total * Q_total ; lambda_eff = sqrt(Egap*(2*Lambda-Egap))
CHEM = dict(lam=46.92171681802857, T=14706.0, Q=427, score=294643137.73357135,
            Lambda=283.1458106129289, Egap=3.914898,
            T_angles=8044.0, T_heur=6662.0,
            Q_angles_persist=40, Q_outer_persist=40, Q_inner_persist=44,
            Q_temporary=303, brot=8, J=5)


def main():
    print("=" * 78)
    print("1. INVsqrt:  score = Q * C,  C = Toffolis + T/4")
    print("=" * 78)
    s, tpr, C = invsqrt_cost(INV["Q"], INV["toff"], INV["t_count"], INV["rots"], INV["eps"])
    print(f"  T per non-Clifford rotation = 0.56*log2(1/eps)+5.3 = {tpr:.4f}")
    print(f"  C = {INV['toff']:.4f} (Toffoli) + ({INV['t_count']:.3f} + {INV['rots']}*{tpr:.3f})/4"
          f" = {C:.6f}")
    print(f"  model score = {INV['Q']} * {C:.6f} = {s:.6f}")
    print(f"  official    = {INV['score']:.6f}   residual = {s - INV['score']:+.3e}")
    print(f"  C split: Toffoli {INV['toff']/C:5.2%}   rotations {INV['rots']*tpr/4/C:5.2%}")
    print(f"  one rotation removed frees {tpr/4:.3f} C-units = {tpr/4/C:5.3%} of C")

    print()
    print("=" * 78)
    print("2. DQI:  score = R(eps_plus) * Q^2 * T")
    print("=" * 78)
    eps0 = cp_upper_zero(DQI["N"], DQI["delta"])
    print(f"  clean CP upper bound (k=0, N=102400, delta=2^-128) = {eps0:.6e}")
    print(f"  R(clean) = {r_factor(eps0):.9f}   (JSON repetition_factor for the 1-error")
    print(f"              draw was {DQI['rep_reported']:.9f})")
    cd = r_factor(eps0) * DQI["Q"] ** 2 * DQI["T"]
    print(f"  clean model score = {cd:.4f}")
    print(f"  observed clean     = 346413579540.4963   residual = {cd-346413579540.4963:+.3e}")
    print(f"  lost  (1 error)    = {DQI['rep_reported']*DQI['Q']**2*DQI['T']:.4f}"
          f"   observed 348004440260.464")
    print(f"  Q^2 penalty for 50 ancillas over the 840 contract: "
          f"{(DQI['Q']/840)**2:.6f}x = {100*((DQI['Q']/840)**2-1):.2f}%")

    print()
    print("=" * 78)
    print("3. CHEM:  score = lambda_eff * T_total * Q_total")
    print("=" * 78)
    lam_check = math.sqrt(CHEM["Egap"] * (2 * CHEM["Lambda"] - CHEM["Egap"]))
    print(f"  lambda_eff = sqrt(Egap*(2*Lambda-Egap)) = {lam_check:.9f}"
          f"   (JSON 46.921716818)")
    qsum = (CHEM["Q_angles_persist"] + CHEM["Q_outer_persist"]
            + CHEM["Q_inner_persist"] + CHEM["Q_temporary"])
    tsum = CHEM["T_angles"] + CHEM["T_heur"]
    sc = CHEM["lam"] * tsum * qsum
    print(f"  Q_total = {CHEM['Q_angles_persist']} (angles J*brot={CHEM['J']*CHEM['brot']})"
          f" + {CHEM['Q_outer_persist']} + {CHEM['Q_inner_persist']} + {CHEM['Q_temporary']}"
          f" = {qsum}")
    print(f"  T_total = {CHEM['T_angles']:.0f} (angles) + {CHEM['T_heur']:.0f} (heuristic)"
          f" = {tsum:.0f}")
    print(f"  model score = {CHEM['lam']:.9f} * {tsum:.0f} * {qsum} = {sc:.5f}")
    print(f"  official    = {CHEM['score']:.5f}   residual = {sc - CHEM['score']:+.3e}")
    print(f"  cost/T = lambda*Q = {CHEM['lam']*qsum:.5f}"
          f"   (measured two-point rate 20035.573)")

    print()
    print("=" * 78)
    print("4. GOLD 28.68633 from 28.15083: what each factor must become")
    print("=" * 78)
    k = (28.68633 / 28.15083) ** 3
    print(f"  product must shrink {k:.6f}x")
    print(f"  invsqrt : C {C:.3f} -> {C/k:.3f}   (or Q 44 -> {44/k:.2f},"
          f" or {INV['rots'] - (C - C/k)/(tpr/4):.1f} rotations)")
    print(f"  DQI     : Q^2*T -> /{k:.3f}  = Q {890} -> {890/math.sqrt(k):.2f} at fixed T,"
          f"  or T -> {DQI['T']/k:.0f}")
    print(f"  chem    : T -> {tsum/k:.0f}   or Q -> {qsum/k:.1f}"
          f"   or Lambda {CHEM['Lambda']:.2f} -> "
          f"{(CHEM['Egap'] + (CHEM['lam']/math.sqrt(k))**2/CHEM['Egap'])/2:.2f}")
    print()
    print(f"  current best GM = {gm(INV['score'], 346413579540.4963, CHEM['score']):.5f}")


if __name__ == "__main__":
    main()
