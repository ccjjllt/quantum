"""Classical ANF analysis of the current angle-word table (no circuit simulation).

Loader model (validated against syed_v12 source, emit_plan.py):
  per-loader Toffolis = #monomials(weight>=2) in the union of ANF supports of its
  40 loaded bits, split as  #mixed(products) + #pure-high(high cache) + #pure-low(low cache)
with the address bits split low = bits 0..LO-1, high = the rest.
Unreachable rows (>=1220) are don't-cares.
"""
import numpy as np, itertools, json, sys

NPZ = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/chem_sub1/submission.npz"
z = np.load(NPZ, allow_pickle=False)
words = z["angle_words"].astype(np.int64)   # (1220, 75)
NV, NA = words.shape
NB = 11
print(f"angle_words {words.shape}, values {words.min()}..{words.max()}, tree {z['tree_edges'].shape}")

# truth tables over 2048 addresses: T[col, addr] bit b of word
A = 1 << NB
def column_bits():
    # returns (NA*8, A) uint8 array: for each word bit (word j, bit b), value on every address
    out = np.zeros((NA*8, A), dtype=np.uint8)
    for j in range(NA):
        w = words[:, j]
        for b in range(8):
            f = np.zeros(A, dtype=np.uint8)
            f[:NV] = (w >> b) & 1
            out[j*8+b] = f
    return out

F = column_bits()

def anf_support(f):
    """in-place mobius over 2048 points -> ANF coefficients"""
    a = f.astype(np.uint8).copy()
    for b in range(NB):
        m = 1 << b
        idx = np.arange(A)
        sel = (idx & m) != 0
        a[sel] ^= a[idx[sel] ^ m]
    return a

ANF = np.stack([anf_support(F[i]) for i in range(len(F))])   # (600, 2048)

def classify(mask, LO):
    """weight, nlow, nhigh for monomial bitmask"""
    w = bin(mask).count("1")
    lo = bin(mask & ((1 << LO) - 1)).count("1")
    return w, lo, w - lo

def cost_report(LO, J=5, anf=ANF):
    tot = dict(mixed=0, high=0, low=0, per_loader=[])
    for k in range(NA // J):
        cols = slice(k*J*8, (k+1)*J*8)
        union = np.any(anf[cols] != 0, axis=0)
        masks = np.flatnonzero(union)
        c = dict(mixed=0, high=0, low=0)
        for m in masks:
            w, nl, nh = classify(int(m), LO)
            if w < 2: continue
            if nl == 0: c['high'] += 1
            elif nh == 0: c['low'] += 1
            else: c['mixed'] += 1
        tot['per_loader'].append(c)
        for key in c: tot[key] += c[key]
    return tot

for LO in (3,4,5):
    r = cost_report(LO)
    pl = r['per_loader']
    print(f"LO={LO}: mixed={r['mixed']} high={r['high']} low={r['low']} "
          f"total/pass={r['mixed']+r['high']+r['low']} per-loader-avg={(r['mixed']+r['high']+r['low'])/15:.1f}")
    print("   first loaders:", [p['mixed']+p['high']+p['low'] for p in pl[:5]])
