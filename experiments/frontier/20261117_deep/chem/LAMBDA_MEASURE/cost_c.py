"""Exact cost model for the C axis at (R=8, B=143) with the shipped loader.

T = angles_toffoli (2 x 15 loader passes = 8044, unchanged: the words do not
depend on C) + heuristic toffoli(8,143,C) ;  Q from the same model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

V = I.V
import importlib.util


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


vmod = load('dfthcsos.verify', str(V / 'verify.py'))

L = 2 * 4022          # ANGLE family: 15 loaders, 2 passes (measured on the shipped circuits)
R, B, N = 8, 143, 76
brot = 8
print(f'{"C":>3} {"K":>4} {"T_h":>6} {"Q":>4} {"T":>7} {"pers":>5} {"temp":>5}'
      f' {"cost@46.921583":>16} {"GM":>9} {"dGM":>8}')
REF = {'invsqrt': 2076774.233715, 'dqi': 24439463583672.93, 'chem': 3355599588.3155375}
CUR = {'invsqrt': 74797.36535717871, 'dqi': 346409762292.7187}
lam = 46.921583
import math
for C in range(46, 31, -1):
    c = vmod.heuristic_costs(N, R, B, C, brot)
    T = L + c['toffoli']
    Q = c['persistent_qubits'] + c['temporary_qubits'] + c['angles_persistent_qubits'] \
        if 'angles_persistent_qubits' in c else None
    print('  heuristic keys:', sorted(c) if C == 46 else '')
    break
for C in range(46, 31, -1):
    c = vmod.heuristic_costs(N, R, B, C, brot)
    T = L + c['toffoli']
    Q = c['qubits'] + 40 + 11     # + J*brot angle registers + 11 selection qubits (angles persistent)
    cost = lam * T * Q
    gm = math.prod([REF['invsqrt'] / CUR['invsqrt'], REF['dqi'] / CUR['dqi'],
                    REF['chem'] / cost]) ** (1 / 3)
    print(f'{C:3d} {R*C:4d} {c["toffoli"]:6d} {Q:4d} {T:7d} {c["qubits"]:5d}'
          f' {c["temporary_qubits"]:5d} {cost:16.2f} {gm:9.5f} {gm-28.15094:+8.5f}')
print('\nshipped reference: T 14706, Q 427, cost 294643137.73, GM 28.15094')
print('8*44*427 + 84 =', 8*44*427+84)
