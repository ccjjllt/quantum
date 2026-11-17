"""Q-axis arithmetic: the exact inner_temp/k2 selection rule and the (R,B,C,brot) sweep.

PURE ARITHMETIC.  Imports only the verifier's own cost module
(scoreinfra/costs_prepare.SpinFreeData_V1, numpy only) and the stored H spectrum.
No integrals, no kickmix, no circuit, no simulation, no verifier run.

Unknowns are labelled:
  * T_angles is a LOADER DESIGN unknown (no plan exists off 1220 rows).  Three
    models are reported: lin (4022*rows/1220, the shipped density), cons and cut
    (the two `15*(...)` product-form models calibrated at 1220 rows).
  * lambda_eff is held at the measured 46.921716818 (six refits agree to 1e-5).
  * accuracy uses the measured 4-point rho law + the calibrated 8-bit rounding
    term; it is a model, not a verifier result.
"""
import importlib.util
import math
import sys

import numpy as np

ROOT = '/Users/zhaohuaxiang/ccjjllt/quantum'
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location(
    'cp', f'{ROOT}/data/competition/verifiers/dfthcsos/scoreinfra/costs_prepare.py')
CP = importlib.util.module_from_spec(_spec)
sys.modules['cp'] = CP
_spec.loader.exec_module(CP)
M = CP.SpinFreeData_V1

N = 76
CHI = 10
LAM = 46.921716818
LAM_REF = 46.921716818
T_SHIP, Q_SHIP = 14706, 427
COST_SHIP = LAM * T_SHIP * Q_SHIP
REF_CHEM = 3355599588.3155375
GOLD_CHEM = 277662014.70

_ev = np.sort(np.load(f'{ROOT}/artifacts/H_spectrum.npy'))[::-1]
_NEG2 = float((np.minimum(_ev, 0) ** 2).sum())


def floor_mha(K):
    """Rank-K lower bound on the continuous two-body error (mHa)."""
    return 1e3 * math.sqrt(float((np.maximum(_ev, 0) ** 2)[K:].sum()) + _NEG2)


def loader(rows):
    """Toffolis per pass for the ANGLES family; three labelled models."""
    hmax = math.ceil(rows / 16)
    top = hmax - 1
    high = top - len([h for h in range(1, top + 1) if h & (h - 1) == 0])
    cuts = min(5 * (105 - top), 525)
    return {
        'lin': 4022.0 * rows / 1220.0,
        'cons': 15.0 * (6 + high + 193),
        'cut': 15.0 * (6 + high + (525 - cuts) / 2),
    }


ROUND_SHIP = math.sqrt(400.0 - 14.20 ** 2)   # 8-bit rounding at 1220 rows, mHa


def acc(R, B, C, brot):
    """Modelled accuracy. Returns (e2_cont, rounding, e2_total, floor, legal)."""
    K = R * C
    rows = N + R * B
    fl = floor_mha(K)
    # rho is RELATIVE to the rank floor (shipped: 1.93*7.361 = 14.20 mHa exactly)
    rho = 1.93 * (3.25 / (B / C)) ** 1.95
    e2c = max(rho * fl, fl)
    rnd = ROUND_SHIP * math.sqrt(rows / 1220.0) * 2.0 ** (8 - brot)
    tot = math.hypot(e2c, rnd)
    return e2c, rnd, tot, fl, tot <= 20.0


def price(R, B, C, brot, J=5):
    d = M(R=R, B=B, C=C, N=N, chi=CHI, beta=brot)
    oq, iq = d.outer_state_prep_qubit_cost(), d.inner_state_prep_qubit_cost()
    b2 = math.ceil(math.log2(B)) + CHI + 1
    k2 = d.find_qroam_size_to_minimize_global_temp_ancilla(b2)
    rows = N + R * B
    ang_temp = 128 - 11 - J * brot
    Q = J * brot + oq['persistent'] + iq['persistent'] + max(
        oq['temporary'], iq['temporary'], ang_temp)
    Th = d.outer_state_prep() + d.inner_state_prep() + d.givens_rotations()
    return dict(R=R, B=B, C=C, brot=brot, J=J, K=R * C, rows=rows, b2=b2, k2=k2,
                inner_temp=iq['temporary'], outer_temp=oq['temporary'],
                ang_temp=ang_temp, pers=oq['persistent'] + iq['persistent'],
                Q=Q, T_h=Th, Q_th=int(d.inner_state_prep()), Q_o=int(d.outer_state_prep()),
                Q_g=2 * (N - 1) * (2 * brot - 1))


def cost(rows, Th, Q, model='lin'):
    L = loader(rows)[model]
    T = 2 * L + Th
    return L, T, LAM * T * Q


def hdr(s):
    print('\n' + '=' * 100)
    print(s)
    print('=' * 100)


# ---------------------------------------------------------------- 1. exact form
hdr('1. EXACT reproduction of the shipped point (8,143,44,brot=8,J=5)')
p = price(8, 143, 44, 8)
for k in ('K', 'rows', 'b2', 'k2', 'outer_temp', 'inner_temp', 'ang_temp', 'pers',
          'Q', 'T_h', 'Q_th', 'Q_o', 'Q_g'):
    print(f'  {k:11s} {p[k]}')
print(f'  inner_temp = temp_uniform + temp_for_qroam')
d = M(R=8, B=143, C=44, N=N, chi=CHI, beta=8)
iq = d.inner_state_prep_qubit_cost()
print(f'    temp_uniform      = max(0, ceil(log2(B+1))-2) = {iq["uniform_temporary"]}'
      f'   [ceil(log2 144)={math.ceil(math.log2(144))}]')
print(f'    temp_for_qroam    = ceil(log2(RC*ceil((B+1)/2^k2))) + (2^k2-1)*b2')
print(f'                      = ceil(log2(352*9)) + 15*19 = 12 + 285 = '
      f'{iq["temporary_for_qroam"]}')
print(f'  Q = {p["pers"]} + J*brot({5*8}) + max({p["outer_temp"]}, {p["inner_temp"]}, '
      f'{p["ang_temp"]}) = {p["Q"]}')
assert p['Q'] == 427 and p['T_h'] == 6662

hdr('1b. k2 selection trace: QR start, then decrement, FIRST success wins')
RC, B, beta = 352, 143, 8
b2 = math.ceil(math.log2(B)) + CHI + 1
print(f'  b2 = ceil(log2 B)+chi+1 = {math.ceil(math.log2(B))}+{CHI}+1 = {b2}')
print(f'  k2_opt(QR) = QR(RC*B, b2) = QR({RC*B}, {b2}) = {CP.QR(RC*B, b2)}')
print(f'  threshold  = brot*(N-1) = {beta}*75 = {beta*(N-1)}  (STRICT <)')
print(f'  {"k2":>3} {"ceil(log2(RC*ceil(B/2^k2)))":>30} {"(2^k2-1)*b2":>12} '
      f'{"sum":>6} {"<600?":>6}  action')
for k2 in range(CP.QR(RC * B, b2)[0], -1, -1):
    t = math.ceil(math.log2(RC * math.ceil(B / 2 ** k2)))
    s = t + (2 ** k2 - 1) * b2
    ok = s < beta * (N - 1)
    print(f'  {k2:3d} {t:30d} {(2**k2-1)*b2:12d} {s:6d} {str(ok):>6}  '
          f'{"ACCEPT -> k2=" + str(k2) if ok else "reject, try k2-1"}')
    if ok:
        break

hdr('2. WHERE k2 = 3 IS REACHABLE  (a) minimum B at each brot, RC=352')
print('  need k2=4 to FAIL:  ceil(log2(RC*ceil(B/16))) + 15*b2 >= brot*75')
print(f'  {"brot":>4} {"thr":>5} {"min B with k2=3":>16} {"b2":>3} {"rows(R=8)":>10} '
      f'{"inner_temp":>11} {"Q":>4}')
for beta in range(2, 13):
    found = None
    for e in range(3, 46):
        Bc = 1 << e
        for Bt in (Bc, Bc + 1):
            d = M(R=8, B=Bt, C=44, N=N, chi=CHI, beta=beta)
            b2 = math.ceil(math.log2(Bt)) + CHI + 1
            if d.find_qroam_size_to_minimize_global_temp_ancilla(b2) == 3:
                found = Bt
                break
        if found:
            break
    if found is None:
        print(f'  {beta:4d} {beta*75:5d} {"never (B<=2^45)":>16}')
    else:
        p = price(8, found, 44, beta)
        print(f'  {beta:4d} {beta*75:5d} {found:16d} {p["b2"]:3d} {p["rows"]:10d} '
              f'{p["inner_temp"]:11d} {p["Q"]:4d}')

hdr('2b. Does forcing k2=3 pay?  best k2=3 config per brot, all three loader models')
print(f'  {"brot":>4} {"B":>8} {"rows":>9} {"k2":>3} {"inner":>6} {"Q":>4} {"T_h":>7} '
      f'{"T(lin)":>8} {"cost(lin) M":>11} {"cost(cut) M":>11} {"e2 mod":>7}')
best3 = []
for beta in range(2, 9):
    cands = []
    for e in range(3, 20):
        for B in (1 << e, (1 << e) + 1):
            if B < 8:
                continue
            p = price(8, B, 44, beta)
            if p['k2'] == 3:
                L, T, c = cost(p['rows'], p['T_h'], p['Q'], 'lin')
                _, _, cc = cost(p['rows'], p['T_h'], p['Q'], 'cut')
                cands.append((c, cc, p))
    if not cands:
        print(f'  {beta:4d}  none up to B=2^19')
        continue
    c, cc, p = min(cands)
    e2c, rnd, tot, fl, ok = acc(p['R'], p['B'], p['C'], p['brot'])
    print(f'  {beta:4d} {p["B"]:8d} {p["rows"]:9d} {p["k2"]:3d} {p["inner_temp"]:6d} '
          f'{p["Q"]:4d} {p["T_h"]:7d} {2*loader(p["rows"])["lin"]+p["T_h"]:8.0f} '
          f'{c/1e6:11.1f} {cc/1e6:11.1f} {tot:7.1f}')
    best3.append((c, cc, p, tot))

hdr('3. SWEEP  R 4..16, B 96..256, C 24..128, brot 6..10, J=5')
rows_out = []
Bs = sorted(set(list(range(96, 257, 8)) + [129, 143, 255]))
Cs = [24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 112, 128]
Rs = [4, 5, 6, 7, 8, 9, 10, 12, 14, 16]
for R in Rs:
    for B in Bs:
        for C in Cs:
            if B < 2:
                continue
            for beta in (6, 7, 8, 9, 10):
                p = price(R, B, C, beta)
                L = loader(p['rows'])
                e2c, rnd, tot, fl, ok = acc(R, B, C, beta)
                cm = {m: LAM * (2 * L[m] + p['T_h']) * p['Q'] for m in L}
                rows_out.append(dict(p, e2c=e2c, rnd=rnd, e2=tot, floor=fl, legal=ok,
                                     cost_lin=cm['lin'], cost_cut=cm['cut'],
                                     cost_cons=cm['cons'], L_lin=L['lin']))
print(f'  evaluated {len(rows_out)} configurations')

legal = [r for r in rows_out if r['legal']]
print(f'  accuracy-legal (model): {len(legal)}')
print('\n  best 12 legal by cost_lin (the shipped loader density held constant):')
print(f'  {"shape":>16} {"brot":>4} {"rows":>6} {"K":>4} {"k2":>3} {"itemp":>6} {"Q":>4} '
      f'{"T_h":>6} {"T":>7} {"cost M":>9} {"dGM":>7} {"e2":>5}')
legal.sort(key=lambda r: r['cost_lin'])
for r in legal[:12]:
    gm = 28.15082863 * (COST_SHIP / r['cost_lin']) ** (1 / 3)
    print(f'  ({r["R"]},{r["B"]},{r["C"]:>3}) {r["brot"]:4d} {r["rows"]:6d} {r["K"]:4d} '
          f'{r["k2"]:3d} {r["inner_temp"]:6d} {r["Q"]:4d} {r["T_h"]:6d} '
          f'{2*r["L_lin"]+r["T_h"]:7.0f} {r["cost_lin"]/1e6:9.2f} {gm:7.4f} {r["e2"]:5.1f}')

print('\n  best 8 legal by cost_cut (the pessimistic loader model):')
legal.sort(key=lambda r: r['cost_cut'])
for r in legal[:8]:
    gm = 28.15082863 * (COST_SHIP / r['cost_cut']) ** (1 / 3)
    print(f'  ({r["R"]},{r["B"]},{r["C"]:>3}) brot {r["brot"]} rows {r["rows"]:5d} '
          f'Q {r["Q"]:4d} T_h {r["T_h"]:5d} cost_cut {r["cost_cut"]/1e6:8.2f} M '
          f'dGM {gm:7.4f} e2 {r["e2"]:5.1f}')

hdr('4. Q-LEGALITY FRONTIER: min Q over shapes that clear the modelled gate')
print(f'  {"Q":>4} {"min cost M (lin)":>17} {"shape":>16} {"brot":>4} {"rows":>5} '
      f'{"K":>4} {"k2":>3} {"itemp":>6} {"T_h":>5} {"e2":>5}')
byq = {}
for r in legal:
    q = r['Q']
    if q not in byq or r['cost_lin'] < byq[q]['cost_lin']:
        byq[q] = r
for q in sorted(byq)[:14]:
    r = byq[q]
    print(f'  {q:4d} {r["cost_lin"]/1e6:17.2f} ({r["R"]},{r["B"]},{r["C"]:>3}) {r["brot"]:4d} '
          f'{r["rows"]:5d} {r["K"]:4d} {r["k2"]:3d} {r["inner_temp"]:6d} {r["T_h"]:5d} '
          f'{r["e2"]:5.1f}')

hdr('5. WHAT THE k2=3 BRANCH WOULD BE WORTH IF IT WERE LEGAL (counterfactual)')
p = price(8, 143, 44, 8)
qi3 = 84 + 40 + (133 + math.ceil(math.log2(352 * 18)) + 6)
print(f'  hypothetical inner_temp(k2=3) = 7*19 + ceil(log2(352*18)) + 6 = '
      f'{133 + math.ceil(math.log2(352*18)) + 6}')
print(f'  hypothetical Q = {qi3}  (vs 427, {qi3/427-1:+.1%})')
print(f'  hypothetical chem cost = {LAM*T_SHIP*qi3/1e6:.2f} M  '
      f'(vs {COST_SHIP/1e6:.2f} M), GM '
      f'{28.15082863*(COST_SHIP/(LAM*T_SHIP*qi3))**(1/3):.4f}')
print(f'  ... but unreachable: see section 2a (B >= 2^27 at brot=8, or brot<=4).')

hdr('6. MEASURED-SUPPORTED BAND ONLY  (K 320..360, B/C 1.50..3.60: inside or <1.1x '
    'below the 4 measured points)')
band = [r for r in legal if 320 <= r['K'] <= 360 and 1.50 <= r['B'] / r['C'] <= 3.60]
band.sort(key=lambda r: r['cost_lin'])
print(f'  {len(band)} legal shapes in band; best 10 by cost_lin')
print(f'  {"shape":>16} {"brot":>4} {"rows":>5} {"K":>4} {"B/C":>5} {"k2":>3} {"Q":>4} '
      f'{"T_h":>5} {"T":>6} {"cost M":>8} {"dGM":>7} {"e2":>5}')
for r in band[:10]:
    gm = 28.15082863 * (COST_SHIP / r['cost_lin']) ** (1 / 3)
    print(f'  ({r["R"]},{r["B"]},{r["C"]:>3}) {r["brot"]:4d} {r["rows"]:5d} {r["K"]:4d} '
          f'{r["B"]/r["C"]:5.2f} {r["k2"]:3d} {r["Q"]:4d} {r["T_h"]:5d} '
          f'{2*r["L_lin"]+r["T_h"]:6.0f} {r["cost_lin"]/1e6:8.2f} {gm:7.4f} {r["e2"]:5.1f}')

hdr('7. DOES ANY LEGAL SHAPE BEAT THE SHIPPED POINT *IN THE MEASURED BOX*?')
ref = [r for r in rows_out if (r['R'], r['B'], r['C'], r['brot']) == (8, 143, 44, 8)][0]
print(f'  shipped (8,143,44,8): rows {ref["rows"]} K {ref["K"]} Q {ref["Q"]} '
      f'T_h {ref["T_h"]} e2 {ref["e2"]:.2f} cost_lin {ref["cost_lin"]/1e6:.2f} M')
print(f'  cheapest in-band legal: {band[0]["cost_lin"]/1e6:.2f} M  '
      f'({band[0]["cost_lin"]/ref["cost_lin"]-1:+.2%})')

hdr('8. VERDICT ARITHMETIC')
print(f'  shipped chem cost          {COST_SHIP:,.2f}')
print(f'  gold needs <=              {GOLD_CHEM:,.2f}  ({GOLD_CHEM/COST_SHIP-1:+.2%})')
print(f'  cheapest modelled-legal    {min(r["cost_lin"] for r in legal):,.2f}'
      f'   ({min(r["cost_lin"] for r in legal)/1e6:.2f} M)')
