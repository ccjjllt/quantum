"""Exact cost / GM table for (8,143,C) with the unchanged loader, and the
break-even lambda_eff at which each C would just match the shipped cost."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import importlib.util


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


vmod = load('dfthcsos.verify', str(I.V / 'verify.py'))
REF = {'invsqrt': 2076774.233715, 'dqi': 24439463583672.93, 'chem': 3355599588.3155375}
CUR = {'invsqrt': 74797.36535717871, 'dqi': 346409762292.7187, 'chem': 294643137.73}
SHIP_COST = 294643137.73
LAM = 46.921583


def gm(cost):
    return math.prod([REF['invsqrt'] / CUR['invsqrt'], REF['dqi'] / CUR['dqi'],
                      REF['chem'] / cost]) ** (1 / 3)


print(f'{"C":>3} {"K":>4} {"T_h":>6} {"T":>7} {"Q":>4} {"cost(M)":>10} {"GM":>9}'
      f' {"dGM":>8} {"break-even lam_eff":>18}')
g0 = gm(SHIP_COST)
for C in range(44, 33, -1):
    c = vmod.heuristic_costs(76, 8, 143, C, 8)
    T = 2 * 4022 + c['toffoli']
    Q = c['qubits'] + 40
    cost = LAM * T * Q
    print(f'{C:3d} {8*C:4d} {c["toffoli"]:6d} {T:7d} {Q:4d} {cost/1e6:10.3f}'
          f' {gm(cost):9.5f} {gm(cost)-g0:+8.5f} {SHIP_COST/(T*Q):18.5f}')
print(f'\nshipped: C=44 T=14706 Q=427 cost 294643137.73 GM {g0:.5f} (lam_eff {LAM})')
