"""Code census of the shipped (marculera) table, per loader.

A "code" is a linear relation among the 5 output bits of one bit-plane (b) of the
five words that kills the low monomial m everywhere.  Concretely the cut
   e_{7z+b}            (one unit vector, per word z)         -- per-word code
   sum_z e_{7z+b}      (the XOR of the five words)           -- XOR code
is a free forced cut for monomial m iff, for every high slice h=1..hmax-1, the
m-th low-monomial output vector of loader k's delta tensor is orthogonal to it.

This prints, per loader, which of the 6 candidate relations hold on which of the
11 nonlinear low monomials, the block-rank ceiling, and the shipped product
count.
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
from parity_recover import NOUT  # noqa: E402

M35 = (1 << NOUT) - 1
BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
z = np.load(BUILD / 'submission.npz', allow_pickle=False)
words = np.asarray(z['angle_words'], np.int64)
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


def complete(words):
    a = np.zeros((1232, 75), dtype=np.uint8)
    a[:1220] = words.astype(np.uint8)
    f = a.reshape(77, 16, 75)
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(7):
        for h in range(77):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    f[76, 4:] = 0
    for b in range(7):
        for h in range(77):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    return a


def cross_tensor(Wc, k):
    delta = Wc[:, 5 * k:5 * k + 5].astype(np.int64).copy()
    if k: delta ^= Wc[:, 5 * k - 5:5 * k]
    packed = np.zeros(1232, dtype=np.uint64)
    for j in range(5):
        packed |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
    f = packed.reshape(77, 16).copy()
    for b in range(4):
        for lo in range(16):
            if lo & (1 << b): f[:, lo] ^= f[:, lo ^ (1 << b)]
    for b in range(7):
        for hi in range(77):
            if hi & (1 << b): f[hi] ^= f[hi ^ (1 << b)]
    return [sum(int(f[h, l]) << ((l - 1) * NOUT) for l in range(1, 16)) for h in range(77)]


RELS = [('lsb0', 1 << 0), ('lsb1', 1 << 7), ('lsb2', 1 << 14), ('lsb3', 1 << 21), ('lsb4', 1 << 28),
        ('xor_b1', sum(1 << (7 * z + 1) for z in range(5))),
        ('xor_b2', sum(1 << (7 * z + 2) for z in range(5)))]

Wc = complete(words)
for k in range(15):
    t = cross_tensor(Wc, k)
    hold = {}
    for name, rel in RELS:
        per_m = []
        for m in range(15):
            ok = all(bin((((x >> (NOUT * m)) & M35) & rel)).count('1') % 2 == 0 for x in t[1:76])
            per_m.append(ok)
        hold[name] = [m + 1 for m in per_m if ok]
    nl = [m for m in range(1, 16) if bin(m).count('1') >= 2]
    cub = [m for m in nl if bin(m).count('1') >= 3]
    codes = {name: sorted(set(v) & set(nl)) for name, v in hold.items()}
    codes_cub = {name: sorted(set(v) & set(cub)) for name, v in hold.items()}
    prod = SHIPPED[k] - 75
    print(json.dumps({'k': k, 'shipped_T': SHIPPED[k], 'shipped_products': prod,
                      'sum_cuts_implied': 525 - 2 * prod,
                      'n_forced_nonlinear': {n: len(v) for n, v in codes.items()},
                      'n_forced_cubic': {n: len(v) for n, v in codes_cub.items()}}), flush=True)
