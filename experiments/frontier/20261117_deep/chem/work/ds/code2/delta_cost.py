"""Decisive measurements for the delta-helper emitter question (RESULT5).

 answered here, all classical numpy/GF(2), no simulation:
  1. per-batch helper mismatch vs batch 0, separability, delta-helper D shape
     -> D is LOW-ONLY (highD = 0) for k9/k10/k14; D=0 for k11-13.
  2. X_pre/X_post low parts are SINGLE degree-2 monomials with singleton
     SELF masks (rep = own live function). Adding one needs a fresh AND
     (no correct-valued qubit holds it; hi-cache is high-only).
  3. the shipped 6-AND low synth READS helper qubits (q34/q50 as AND inputs;
     reps reference q18/26/34/42/50), so b7 must equal the synth table during
     products -> a prefix fix is unavoidable when Hp != slow.
  4. needed high-rank for the stored k14 plan = 77 (full) -> 68-high cache
     impossible -> the D-AND (+1T) cannot be offset on our plan.
  5. correct-emission cost table (prefix ANDs + post ANDs, addr-only, +1 spare
     qubit, MBU-uncomputed): every stored plan emits at LOSS vs shipped.

Usage: uv run python delta_cost.py   (numpy only, ~1 min, mostly the rank scan)
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from planner import (  # noqa: E402
    complete_words, cross_tensor, padded_words, BlockPlan,
)
from lowbasis import inverse15, to_physical, transform_target  # noqa: E402
from extract_matching import matching, bitinds  # noqa: E402
from transport_cuts import coordinate_basis, coordinates  # noqa: E402
from parity_recover import outer, basis  # noqa: E402
from helper_coordinates import separate as separate_helpers  # noqa: E402
import low_helper_cache as LHC  # noqa: E402

BASE = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
W = np.load(BASE / 'submission.npz', allow_pickle=False)['angle_words'].astype(np.uint8)
Wc = complete_words(W)
S0 = (((Wc[:, :5] >> 7) ^ (Wc[:, :5] >> 6)) & 1)
slow, _ = separate_helpers(S0)
comps, reps, _ = LHC.synthesize(slow, 51)

print('== 1. helper mismatch / separability / D shape ==')
for k in range(1, 15):
    prev = Wc[:, 5 * k - 5:5 * k]
    cur = Wc[:, 5 * k:5 * k + 5]
    Hp = (((prev >> 7) ^ (prev >> 6)) & 1)
    Hc = (((cur >> 7) ^ (cur >> 6)) & 1)
    d0 = int((Hp != S0).sum() + (Hc != S0).sum())
    D = Hp ^ Hc
    print(f'k={k:2d} prev/cur vs S0 diffs={d0:4d} D-entries={int(D.sum()):4d} D-low-only=', end='')
    if D.any():
        lowD = D[:16].copy()
        highD = D[::16].copy() ^ lowD[0]
        n = len(D)
        ok = bool(np.array_equal(D, lowD[np.arange(n) % 16] ^ highD[np.arange(n) // 77 * 0 + np.arange(n) // 16]))
        print(ok, ' lowD-pops=', [int(D[:16, j].sum()) for j in range(5)])
    else:
        print(True)


def mob(a):
    a = a.copy()
    for b in range(4):
        for m in range(16):
            if m & (1 << b):
                a[m] ^= a[m ^ (1 << b)]
    return a


print('== 2/3. X low parts: single degree-2 monomials, singleton SELF masks ==')
print('   (mask qubits: 18=w0 26=w1 34=w2 42=w3 50=w4 = own b7 target)')
for k in (9, 10, 12, 14):
    prev = Wc[:, 5 * k - 5:5 * k]
    cur = Wc[:, 5 * k:5 * k + 5]
    Hp = (((prev >> 7) ^ (prev >> 6)) & 1)
    Hc = (((cur >> 7) ^ (cur >> 6)) & 1)
    lowP, _ = separate_helpers(Hp)
    lowC, _ = separate_helpers(Hc)
    for tag, L in (('pre', lowP ^ slow), ('post', slow ^ lowC)):
        for j in range(5):
            t = np.asarray(L[:, j], dtype=np.uint8)
            if not t.any():
                continue
            anf = mob(t)
            terms = [l for l in range(16) if anf[l]]
            ms = []
            for l in terms:
                if l == 0:
                    ms.append('const')
                else:
                    mm, _ = reps[l]
                    ms.append(sorted(q for q in range(200) if (mm >> q) & 1))
            print(f'   k={k} {tag} w{j}: terms={terms} '
                  f'deg={[bin(l).count("1") for l in terms]} masks={ms}')


def gfrank(vs):
    b = {}
    for v in vs:
        x = v
        while x:
            p = x.bit_length() - 1
            if p in b:
                x ^= b[p]
            else:
                b[p] = x
                break
    return len(b)


print('== 4. needed high-rank for stored k14 plan (need <= 76 for 68-high) ==')
st = json.loads((HERE / 'basis_plan_k14.json').read_text())
k = 14
Wpad = padded_words(W, k, int(st['F']))
target = cross_tensor(Wpad, k)
parts, cuts, rows = st['parts'], st['cuts'], st['rows']
B = inverse15(rows)
pairs, _ = matching({'parts': parts, 'cuts': cuts})
D = []
for p in pairs:
    D.append(outer(int(to_physical(p[2], B)), int(p[4])))
    if p[3]:
        D.append(outer(int(to_physical(p[3], B)), int(p[4])))
co = coordinate_basis(D)
hs = [0] * len(D)
for h in range(1, 77):
    for i in bitinds(coordinates(target[h], co)):
        hs[i] |= 1 << h
pos = 0
ps = []
pphys = [{'l1': int(to_physical(p[2], B)), 'l2': int(to_physical(p[3], B)), 'out': int(p[4])}
         for p in pairs]
for p in pphys:
    h2 = hs[pos]
    pos += 1
    h1 = hs[pos] if p['l2'] else 0
    if p['l2']:
        pos += 1
    if h1 or h2:
        ps.append(dict(p, h1=h1, h2=h2))
addr = np.arange(1232)
low = addr % 16
high = addr // 16
prev = Wpad[:, 5 * k - 5:5 * k]
cur = Wpad[:, 5 * k:5 * k + 5]
delta = prev ^ cur
corr = np.zeros(1232, dtype=np.uint64)
for j in range(5):
    corr |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
for p in ps:
    a = np.zeros(1232, dtype=np.uint8)
    b = a.copy()
    for i in bitinds(p['l1']):
        a ^= ((low & (i + 1)) == i + 1)
    for i in bitinds(p['l2']):
        b ^= ((low & (i + 1)) == i + 1)
    for i in bitinds(p['h1']):
        a ^= ((high & i) == i)
    for i in bitinds(p['h2']):
        b ^= ((high & i) == i)
    corr ^= (a & b).astype(np.uint64) * np.uint64(p['out'])
ch = corr.reshape(77, 16)[:, 0]
ahvecs = [sum(int((ch[h] >> bit) & 1) << h for h in range(77)) for bit in range(35)]
print('   product-col rank:', gfrank(hs), ' ah rank:', gfrank(ahvecs),
      ' combined:', gfrank(hs + ahvecs), ' -> 68-high',
      'possible' if gfrank(hs + ahvecs) <= 76 else 'IMPOSSIBLE')

print('== 5. correct-emission cost (prefix ANDs + post ANDs, all addr-only) ==')
print('   k  shipped  plan  prefix+post ANDs  correct-T  delta')
for k, ship in ((9, 264), (10, 265), (12, 265), (14, 266)):
    stx = json.loads((HERE / f'basis_plan_k{k}.json').read_text())
    nprod = (525 - int(stx['sum_cuts'])) // 2
    prev = Wc[:, 5 * k - 5:5 * k]
    cur = Wc[:, 5 * k:5 * k + 5]
    Hp = (((prev >> 7) ^ (prev >> 6)) & 1)
    Hc = (((cur >> 7) ^ (cur >> 6)) & 1)
    lowP, _ = separate_helpers(Hp)
    lowC, _ = separate_helpers(Hc)
    npre = sum(bool(np.asarray((lowP ^ slow)[:, j], np.uint8).any()) for j in range(5))
    npost = sum(bool(np.asarray((slow ^ lowC)[:, j], np.uint8).any()) for j in range(5))
    t = nprod + 69 + 6 + npre + npost
    print(f'   {k}  {ship}      {nprod}    {npre}+{npost}              {t}        {t - ship:+d}')
