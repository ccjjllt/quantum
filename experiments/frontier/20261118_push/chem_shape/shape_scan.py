"""Shape arithmetic for the chem leg against the brief's target.

Pure numpy.  Reads only small local files:
  * the verifier's own cost model  data/competition/verifiers/dfthcsos/scoreinfra/costs_prepare.py
  * artifacts/H_spectrum.npy        (2,926 eigenvalues of the vech target H)
  * /tmp/int_correct/sub/dfthcsos/submission.npz  (shipped (8,143,44) factorization)

The rank floor below is a *lower bound over every possible factorization* with
K = R*C terms:  error_2 >= sqrt(sum_{i>K} max(ev_i,0)^2 + sum_i min(ev_i,0)^2).
Therefore a shape whose floor exceeds 20 mHa cannot pass, regardless of U, w, W,
training budget or optimizer.

Two loader models, both calibrated to the shipped 15-loaders/pass = 4,022:
  lin  L = 4022 * rows / 1220                      (optimistic; angles scale with rows)
  cons L = 15 * (6 + high(rows) + 193)             (products frozen at the shipped 193)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402

N, BROT, J, LAM = 76, 8, 5, 46.92171681802857      # shipped lambda_eff
ANG_TEMP = 77                                     # shipped angle workspace
SHIPPED = (8, 143, 44)
SPECTRUM = np.load(ROOT / "artifacts/H_spectrum.npy")
NEG2 = float(np.sum(np.minimum(SPECTRUM, 0.0) ** 2))


def floor_mha(K: int) -> float:
    tail = np.maximum(SPECTRUM[K:], 0.0)
    return 1e3 * math.sqrt(float(np.sum(tail**2)) + NEG2)


def high(rows: int) -> int:
    top = math.ceil(rows / 16) - 1
    return top - len([h for h in range(1, top + 1) if h & (h - 1) == 0])


def cost(R: int, B: int, C: int) -> dict:
    m = SpinFreeData_V1(R=R, B=B, C=C, N=N, chi=10, beta=BROT)
    oq, iq = m.outer_state_prep_qubit_cost(), m.inner_state_prep_qubit_cost()
    Th = int(m.outer_state_prep()) + int(m.inner_state_prep()) + int(m.givens_rotations())
    hp = int(oq["persistent"]) + int(iq["persistent"])
    ht = max(int(oq["temporary"]), int(iq["temporary"]))
    rows = N + R * B
    Q = hp + J * BROT + max(ht, ANG_TEMP)
    Llin = 4022.0 * rows / 1220.0
    Lcons = 15 * (6 + high(rows) + 193)
    return dict(rows=rows, K=R * C, Th=Th, Q=Q, Llin=Llin, Lcons=Lcons,
                Tlin=2 * Llin + Th, Tcons=2 * Lcons + Th)


def line(tag, R, B, C, e2=None):
    c = cost(R, B, C)
    s_lin = LAM * c["Tlin"] * c["Q"]
    s_cons = LAM * c["Tcons"] * c["Q"]
    fl = floor_mha(c["K"])
    est = "PASS" if fl <= 20 else "IMPOSSIBLE"
    print(f"{tag:22s} R={R:2d} B={B:3d} C={C:3d} rows={c['rows']:4d} K={c['K']:3d} "
          f"floor={fl:8.2f} {est:10s} T_h={c['Th']:5d} Q={c['Q']:3d} "
          f"T_lin={c['Tlin']:7.0f} score_lin={s_lin/1e6:7.1f}M "
          f"T_cons={c['Tcons']:7.0f} score_cons={s_cons/1e6:7.1f}M"
          + (f"  e2={e2:7.3f}" if e2 is not None else ""))


if __name__ == "__main__":
    print(f"lambda_eff {LAM:.9f}  target <= 278.55M  (gold 28.71339)")
    print(f"shipped floor(352) = {floor_mha(352):.2f} mHa\n")
    line("shipped", *SHIPPED, e2=16.554)
    print()
    for C in (44, 43, 42, 40, 38, 37, 36, 35):
        line("R=8 shipped U", 8, 143, C)
    print()
    for B in (143, 136, 129, 96, 76):
        line("R=8 fixed K", 8, B, 44)
    print()
    line("brief (4,200,44)", 4, 200, 44)
    line("brief (6,143,44)", 6, 143, 44)
    line("brief (4,200,40)", 4, 200, 40)
    print()
    for B, C in ((143, 88), (136, 96), (129, 60), (161, 88), (129, 88), (239, 128)):
        line("R=4 legal-by-rank", 4, B, C)
    print()
    line("(7,143,51)", 7, 143, 51)
    line("(5,136,96)", 5, 136, 96, e2=344.942)
    line("(4,143,128)", 4, 143, 128, e2=176.756)
