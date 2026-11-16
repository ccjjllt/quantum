"""Rank census of the shipped table's loader targets, and the cut ceiling.

For loader k the loader loads delta = w_k XOR w_{k-1} (low 7 bits of its five
words).  The planner wants 5 blocks of 3 low forms; a block's cut space is the
nullspace of the 75 determined high slices (h=1..75) restricted to that block.
ceiling(sum_cuts) = sum_blocks (105 - rank_block).

Here: rank of coordinate blocks and of random 3-dim subspaces of the 15-dim low
space, per loader.  Classical GF(2) algebra only.
"""
import sys, json, random, itertools
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SRC = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/syed_v12/src/dfthcsos_source')
sys.path.insert(0, str(HERE / 'compiler'))
from parity_recover import NOUT  # noqa: E402

M35 = (1 << NOUT) - 1
z = np.load(SRC / 'submission.npz', allow_pickle=False)
words = np.asarray(z['angle_words'], dtype=np.int64)


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


def cross_tensor(words, k):
    delta = words[:, 5 * k:5 * k + 5].copy()
    if k: delta ^= words[:, 5 * k - 5:5 * k]
    packed = np.zeros(1232, dtype=np.uint64)
    for j in range(5):
        packed[:len(delta)] |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
    f = packed.reshape(77, 16).copy()
    for b in range(4):
        for lo in range(16):
            if lo & (1 << b): f[:, lo] ^= f[:, lo ^ (1 << b)]
    for b in range(7):
        for hi in range(77):
            if hi & (1 << b): f[hi] ^= f[hi ^ (1 << b)]
    return [sum(int(f[h, l]) << (l - 1) * NOUT for l in range(1, 16)) for h in range(77)]


def rank(vs):
    b = {}
    for x in vs:
        while x:
            p = x.bit_length() - 1
            if p in b: x ^= b[p]
            else: b[p] = x; break
    return len(b)


def block_slices(target, forms, hmax=76):
    """forms: list of 15-bit masks; returns the 105-bit slice vectors for h=1..hmax-1."""
    T = [[(x >> (NOUT * m)) & M35 for m in range(15)] for x in target[1:hmax]]
    out = []
    for th in T:
        v = 0; sh = 0
        for fm in forms:
            a = 0; x = fm
            while x:
                b = x & -x; x ^= b
                a ^= th[b.bit_length() - 1]
            v |= a << sh; sh += NOUT
        out.append(v)
    return out


Wc = complete(words)
rng = random.Random(11)
for k in range(15):
    t = cross_tensor(Wc, k)
    coord = [[1 << (3 * i + j) for j in range(3)] for i in range(5)]
    rc = [rank(block_slices(t, b)) for b in coord]
    vals = []
    for _ in range(60):                     # random 3-dim subspaces
        while True:
            vs = [rng.getrandbits(15) for _ in range(3)]
            if rank(vs) == 3: break
        vals.append(rank(block_slices(t, vs)))
    vals = np.array(vals)
    print(json.dumps({'k': k, 'coord_ranks': rc, 'coord_ceiling': sum(105 - r for r in rc),
                      'rand_rank_min': int(vals.min()), 'rand_rank_max': int(vals.max()),
                      'rand_rank_mean': round(float(vals.mean()), 2)}), flush=True)
