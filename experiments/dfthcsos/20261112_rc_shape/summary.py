"""Final numbers for the README (cost with both loaders, rank wall, seeds)."""
import numpy as np, common as C
prob, ref = C.get_target()
T = np.asarray(prob[0])
e = np.linalg.eigvalsh(T)[::-1]
print('||T||_F %.4f trace %.4f' % (np.linalg.norm(T), np.trace(T)))
for k in (6, 32, 64, 88, 120, 176, 240, 352):
    print('  rank %3d truncation error %8.2f mHa' % (k, 1e3*np.sqrt(max((e[k:]**2).sum(), 0))))

# cost: T = heurT + 2*loader_pass ; loader_pass = 3.35*rows (Maoxin-linear) or 3611+1.26*rows (tensorqrom8)
import sys
sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers')
from dfthcsos.verify import heuristic_costs
rows = {'8,143,44': (8,143,44), '7,143,55': (7,143,55), '6,143,64': (6,143,64), '5,143,75': (5,143,75),
        '4,220,120': (4,220,120), '4,200,120': (4,200,120), '4,180,120': (4,180,120),
        '4,180,100': (4,180,100), '4,180,90': (4,180,90)}
lam = { '4,220,120': 48.4563 }
print('\ncost table (lambda 46.9074 unless measured)')
for k,(R,B,Cc) in rows.items():
    r = 76+R*B
    h = heuristic_costs(76,R,B,Cc,8)
    Q = h['qubits']+40
    T_mao = h['toffoli'] + 2*3.35*r
    T_tq8 = h['toffoli'] + 2*(3611+1.26*r)
    L = lam.get(k, 46.9074)
    print('  %-11s rows %4d heurT %5d Q %3d | Maoxin T %6.0f cost %6.1fM | tq8 T %6.0f cost %6.1fM' % (
        k, r, h['toffoli'], Q, T_mao, L*T_mao*Q/1e6, T_tq8, L*T_tq8*Q/1e6))
