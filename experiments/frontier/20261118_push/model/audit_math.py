"""Pure-arithmetic audit of the submission-controlled score parameters.

No circuit simulation. Uses only the official cost-model code copied into the
verifier package plus closed-form arithmetic from the three verifier sources.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402

N_ORB = 76
KEEP_BITS = 10


# ---------------------------------------------------------------- chem heuristics
def heur(R: int, B: int, C: int, brot: int) -> dict:
    m = SpinFreeData_V1(R=R, B=B, C=C, N=N_ORB, chi=KEEP_BITS, beta=brot)
    oq = m.outer_state_prep_qubit_cost()
    iq = m.inner_state_prep_qubit_cost()
    return dict(
        outer=m.outer_state_prep(),
        inner=m.inner_state_prep(),
        givens=m.givens_rotations(),
        outer_p=int(oq["persistent"]),
        outer_t=int(oq["temporary"]),
        inner_p=int(iq["persistent"]),
        inner_t=int(iq["temporary"]),
    )


def chem_score(R, B, C, brot, J, angles_toffoli, lam):
    h = heur(R, B, C, brot)
    T = angles_toffoli + h["outer"] + h["inner"] + h["givens"]
    Q = (h["outer_p"] + h["inner_p"]) + J * brot + max(h["outer_t"], h["inner_t"])
    return dict(T=T, Q=Q, score=lam * T * Q, **h)


def sec(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------- 1. reproduce shipped chem
SHAPE = (8, 143, 44)
LAM = 46.92171681802857
sec("1. chem: reproduce the shipped verifier numbers (R,B,C=8,143,44, brot=8, J=5)")
r = chem_score(*SHAPE, brot=8, J=5, angles_toffoli=8044, lam=LAM)
for k, v in r.items():
    print(f"  {k:10s} {v}")
print("  measured receipt: T=14706 Q=427 toffoli=14706 qubits=427 score=294643137.73357135")
print(f"  model score = {r['score']:.8f}")

# ---------------------------------------------------------------- 2. brot axis
sec("2. chem: brot axis (shipped shape, J=5, angles kept at 8044)")
print(f"  {'brot':>4} {'givens':>7} {'inner_T':>8} {'outer_T':>8} {'inner_t':>8} {'T_total':>9} {'Q_total':>8} {'score':>14} {'vs b=8':>8}")
base = chem_score(*SHAPE, brot=8, J=5, angles_toffoli=8044, lam=LAM)
for brot in range(4, 13):
    s = chem_score(*SHAPE, brot=brot, J=5, angles_toffoli=8044, lam=LAM)
    print(f"  {brot:>4} {s['givens']:>7} {s['inner']:>8} {s['outer']:>8} {s['inner_t']:>8} "
          f"{s['T']:>9} {s['Q']:>8} {s['score']:>14.2f} {s['score']/base['score']-1:>+8.4%}")

# ---------------------------------------------------------------- 3. J axis
sec("3. chem: J axis (Q is exact; T needs a measurement)")
print("  Q_total = 84 + J*brot + max(outer_t, inner_t), and max(.,.)=303 > any angles_temp<=117")
print("  so Q_total = (84+303) + J*brot = 387 + J*brot exactly, for every legal J.")
print()
# linear model of the loader cube count measured on the shipped family:
PROD_PER_WORD = 189 / 5.0     # 189 products per circuit at J=5
FIXED_PER_CIRCUIT = 69 + 6    # high_cache + low_computes, per circuit
print(f"  measured per-circuit static Toffoli at J=5: {PROD_PER_WORD:.1f}/word + {FIXED_PER_CIRCUIT}")
print(f"  {'J':>3} {'K=ceil(75/J)':>13} {'est. products':>14} {'est. T_angles':>14} {'Q':>6} {'score':>13} {'vs J=5':>8}")
for J in (1, 2, 3, 4, 5, 6, 8, 10, 15, 25, 38, 75):
    K = math.ceil(75 / J)
    per_circ = PROD_PER_WORD * J + FIXED_PER_CIRCUIT
    tang = 2 * K * per_circ
    s = chem_score(*SHAPE, brot=8, J=J, angles_toffoli=tang, lam=LAM)
    b5 = chem_score(*SHAPE, brot=8, J=5, angles_toffoli=2 * 15 * (PROD_PER_WORD * 5 + FIXED_PER_CIRCUIT), lam=LAM)
    print(f"  {J:>3} {K:>13} {PROD_PER_WORD*J:>14.0f} {tang:>14.0f} {s['Q']:>6} {s['score']:>13.2f} {s['score']/b5['score']-1:>+8.3%}")

# ---------------------------------------------------------------- 4. shape axis (brot 8 / 7)
sec("4. chem: shape axis at brot=8 and 7 (angles held at the 8-bit measurement)")
print(f"  {'R,B,C':>12} {'brot':>4} {'inner_T':>8} {'givens':>7} {'T_h':>7} {'inner_t':>8} {'Q(J=5)':>8}")
for shape in ((8, 143, 44), (8, 136, 46), (4, 303, 128), (8, 303, 44)):
    for brot in (8, 7):
        h = heur(*shape, brot)
        Th = h["outer"] + h["inner"] + h["givens"]
        Q = h["outer_p"] + h["inner_p"] + 5 * brot + max(h["outer_t"], h["inner_t"])
        print(f"  {str(shape):>12} {brot:>4} {h['inner']:>8} {h['givens']:>7} {Th:>7} {h['inner_t']:>8} {Q:>8}")

# ---------------------------------------------------------------- 5. DQI repetition pricing
sec("5. DQI: score vs the number of failed shots (log2_delta=-128, N=102400)")
sys.path.insert(0, str(ROOT / "data/competition/verifiers/dqi"))
from verify_submission_dqi import clopper_pearson_upper_bound, repetition_overhead  # noqa: E402

NSHOT = 102400
print(f"  {'errors k':>9} {'eps_plus':>12} {'rep_factor':>11} {'d(score)':>10} {'T saving to break even':>24}")
base_rep = repetition_overhead(clopper_pearson_upper_bound(0, NSHOT, -128))
T0 = 367116.06
for k in (0, 1, 2, 3, 5, 10, 30, 100, 300, 1000, 3000, 5000):
    eps = clopper_pearson_upper_bound(k, NSHOT, -128)
    if eps >= 1 / 16:
        print(f"  {k:>9} {eps:>12.5g} {'REJECT':>11}")
        continue
    rep = repetition_overhead(eps)
    # how many Toffolis may the cheaper circuit cost to break even:
    # rep(k) * Q^2 * T' = rep(0) * Q^2 * T0  ->  T' = T0 * rep(0)/rep(k)
    dT = T0 * (1 - base_rep / rep)
    print(f"  {k:>9} {eps:>12.5g} {rep:>11.6f} {rep/base_rep-1:>+10.3%} {dT:>24.1f}")

# ---------------------------------------------------------------- 6. invsqrt rotation pricing
sec("6. invsqrt: rotation pricing and the structural floor")
T_PER_TOFFOLI = 4
MAX_X = 3 * (2 ** 10 - 2) ** 2
TOL_MAX = (math.isqrt((1 << 130) // MAX_X)) >> 25


def rot(eps):
    return 0.56 * math.log2(1 / eps) + 5.3


print(f"  max_x={MAX_X}  tol(max_x)={TOL_MAX} units of 2^-64 turns")
margin_max = TOL_MAX
print(f"  {'n_rot':>6} {'eps (margin=tol max)':>22} {'T/rotation':>11} {'T total':>10}")
for n in (1, 8, 16, 33, 41, 64):
    eps = math.pi * margin_max / 2 ** 64 / n
    print(f"  {n:>6} {eps:>22.4e} {rot(eps):>11.3f} {n*rot(eps):>10.2f}")
# shipped point
n, eps = 33, 1.6406054738480745e-13
print(f"  shipped: n_rot=33 eps={eps:.4e} T/rot={rot(eps):.4f} total={33*rot(eps)+2.4999:.3f}")
print(f"  implied min_margin = {eps*2**64*n/math.pi:.4e} units  (max possible {margin_max:.4e})")
print(f"  d(score)/d(n_rot) at the shipped point = "
      f"{rot(eps) + 0.56/math.log(2):.3f} T per extra rotation (eps(n) recomputed, margin held)")
print(f"  d(score)/d(margin) per decade of margin = {0.56*math.log2(10)*33:.2f} T")
