"""Re-rank shapes with the MEASURED rho(B/C), not the Q_AXIS 1.95-power law.

Measured points (exact full-space error_2, this session, same protocol):
    (8,143,44) B/C 3.25  e2 16.55 mHa  floor 7.361  rho 2.25   <- shipped shape
    (8,129,44) B/C 2.93  e2 28.9  mHa  floor 7.361  rho 3.9    (still descending)
    (8, 96,44) B/C 2.18  e2 89.2  mHa  floor 7.361  rho 12.1
    (8, 62,44) B/C 1.41  e2 280   mHa  floor 7.361  rho 38
    (5,136,96) B/C 1.42  e2 168   mHa  floor 1.630  rho 103
The two-point log fit rho = 2.25*(3.25/(B/C))**p gives p ~ 4-6 (vs 1.95 assumed).

Cost: exact SpinFreeData_V1 T_h/Q at brot 8, J 5, and the shipped loader density
L = 4022*rows/1220 per pass (the only modelled leg; no loader exists off 1220).
"""
import importlib.util
import json
import math
import sys

import numpy as np

ROOT = '/Users/zhaohuaxiang/ccjjllt/quantum'
spec = importlib.util.spec_from_file_location(
    'cp', f'{ROOT}/data/competition/verifiers/dfthcsos/scoreinfra/costs_prepare.py')
CP = importlib.util.module_from_spec(spec)
sys.modules['cp'] = CP
spec.loader.exec_module(CP)
M = CP.SpinFreeData_V1
N, CHI = 76, 10

ev = np.load(f'{ROOT}/artifacts/20261117_lambda_measure/spectrum.npz')['ev']
NEG2 = float(np.sum(np.minimum(ev, 0) ** 2))


def floor_mha(K):
    return 1e3 * math.sqrt(float(np.sum(np.maximum(ev[K:], 0) ** 2) + NEG2))


P_MEAS = 5.0        # measured exponent between B/C 3.25 and 2.93...
RHO_REF, BC_REF = 2.25, 3.25
COST_SHIP = 46.921716818 * 14706 * 427
GM0 = 28.15082863


def price(R, B, C, brot=8, J=5):
    d = M(R=R, B=B, C=C, N=N, chi=CHI, beta=brot)
    oq, iq = d.outer_state_prep_qubit_cost(), d.inner_state_prep_qubit_cost()
    Q = J * brot + oq['persistent'] + iq['persistent'] + max(
        oq['temporary'], iq['temporary'], 128 - 11 - J * brot)
    Th = d.outer_state_prep() + d.inner_state_prep() + d.givens_rotations()
    return Th, Q


def cost(rows, Th, Q, lam=46.921716818):
    L = 4022.0 * rows / 1220.0
    return (2 * L + Th), lam * (2 * L + Th) * Q


rows_out = []
for R in range(4, 17):
    for B in sorted(set(list(range(96, 257, 4)) + [129, 136, 143, 152, 255])):
        for C in (24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 112, 128):
            K = R * C
            rows = N + R * B
            if rows > 1400:
                continue
            fl = floor_mha(K)
            rho = RHO_REF * (BC_REF / (B / C)) ** P_MEAS
            e2 = max(rho * fl, fl)
            Th, Q = price(R, B, C)
            T, c = cost(rows, Th, Q)
            rows_out.append(dict(R=R, B=B, C=C, K=K, rows=rows, bc=B / C, floor=fl,
                                 rho=rho, e2=e2, Th=Th, Q=Q, T=T, cost=c,
                                 legal=e2 <= 20.0))

legal = [r for r in rows_out if r['legal']]
legal.sort(key=lambda r: r['cost'])
print(f'{"shape":>17} {"rows":>5} {"K":>4} {"B/C":>5} {"floor":>6} {"rho":>7} '
      f'{"e2":>6} {"Q":>4} {"T":>6} {"cost M":>8} {"dGM":>7}')
for r in legal[:15]:
    gm = GM0 * (COST_SHIP / r['cost']) ** (1 / 3)
    print(f'({r["R"]},{r["B"]:>3},{r["C"]:>3}) {r["rows"]:5d} {r["K"]:4d} {r["bc"]:5.2f} '
          f'{r["floor"]:6.2f} {r["rho"]:7.2f} {r["e2"]:6.1f} {r["Q"]:4d} {r["T"]:6.0f} '
          f'{r["cost"]/1e6:8.2f} {gm:7.4f}')

print('\nwhere the shipped shape sits under this measured law:')
for sh in [(8, 143, 44)]:
    r = [x for x in rows_out if (x['R'], x['B'], x['C']) == sh]
    if r:
        r = r[0]
        print(f'  ({r["R"]},{r["B"]},{r["C"]}) rows {r["rows"]} K {r["K"]} B/C {r["bc"]:.2f} '
              f'rho_law {r["rho"]:.2f} (measured 2.25)  e2_law {r["e2"]:.1f}  '
              f'cost {r["cost"]/1e6:.2f} M')

print('\ncheapest legal shape at each R (measured law):')
best = {}
for r in legal:
    if r['R'] not in best or r['cost'] < best[r['R']]['cost']:
        best[r['R']] = r
for R in sorted(best):
    r = best[R]
    gm = GM0 * (COST_SHIP / r['cost']) ** (1 / 3)
    print(f'  R={R:2d}: ({r["R"]},{r["B"]},{r["C"]}) rows {r["rows"]} K {r["K"]} '
          f'B/C {r["bc"]:.2f} e2 {r["e2"]:.1f} cost {r["cost"]/1e6:.2f} M GM {gm:.4f}')
