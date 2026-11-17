"""Recover the sign representative the shipped table used, and look for its rule."""
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode  # noqa: E402

z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
TREE = np.asarray(z['tree_edges'], np.int64)
WORDS = np.asarray(z['angle_words'], np.int64)
V = decode(WORDS, TREE, 8)
n = V.shape[1]
scale = 128

u = V.copy()
signs = np.ones(n - 1, np.int64)
bad = []
for t in range(n - 2, -1, -1):
    p, c = int(TREE[t][0]), int(TREE[t][1])
    th0 = np.arctan2(u[:, c], u[:, p])
    th0 = np.where(th0 < 0, th0 + 2 * np.pi, th0)
    tgt = np.pi * WORDS[:, t] / scale
    d_plus = np.abs((tgt - th0 + np.pi) % (2 * np.pi) - np.pi)
    d_minus = np.abs((tgt - th0) % (2 * np.pi) - np.pi)   # theta0 + pi
    pick_minus = d_minus < d_plus
    if pick_minus.mean() > 0.5:
        signs[t] = -1
    agree = np.mean(pick_minus == (signs[t] < 0))
    if agree < 0.999:
        bad.append((t, float(agree)))
    s = signs[t]
    u[:, p] = s * np.hypot(u[:, p], u[:, c])
    u[:, c] = 0.0
print('edges where rows disagree on the sign:', bad[:10], 'count', len(bad))
print('sign -1 count', int(np.sum(signs < 0)), 'of', n - 1)

# word-value statistics of the shipped table
print('ship words: frac in [0,64)', float(np.mean(WORDS < 64)),
      ' [64,128)', float(np.mean((WORDS >= 64) & (WORDS < 128))),
      ' [128,192)', float(np.mean((WORDS >= 128) & (WORDS < 192))),
      ' [192,256)', float(np.mean(WORDS >= 192)))
print('ship words: bit7 set frac', float(np.mean(WORDS >= 128)))

# where do the -1 signs sit? depth in the tree?
depth = np.zeros(n, np.int64)
for i, (p, c) in enumerate(TREE):
    depth[int(c)] = depth[int(p)] + 1
flip = signs < 0
print('flip rate by child depth:', {int(d): float(np.mean(flip[depth[TREE[:, 1]] == d]))
                                    for d in sorted(set(depth[TREE[:, 1]].tolist()))})
np.save(str(WORK / 'ship_signs.npy'), signs)
