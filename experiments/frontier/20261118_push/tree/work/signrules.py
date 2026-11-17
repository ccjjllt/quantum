"""Per-(row, edge) sign representatives: every row may choose, independently at
each edge, the positive or negative pre-rotation amplitude.  All choices decode
to the same vector, so the accuracy metrics are untouched; only the words move.
"""
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode  # noqa: E402


def encode_rule(vectors, edges, brot=8, rule='cos_pos'):
    """rule: 'pos' = positive amplitude (canonical), 'cos_pos' = sign(v_p),
    'lowmag' = branch closer to 0 mod pi (|angle| minimal)."""
    u = np.array(vectors, np.float64, copy=True)
    edges = np.asarray(edges, np.int64)
    n = len(edges)
    scale = 1 << (brot - 1)
    words = np.zeros((u.shape[0], n), np.int64)
    for t in range(n - 1, -1, -1):
        p, c = int(edges[t][0]), int(edges[t][1])
        r = np.hypot(u[:, p], u[:, c])
        th0 = np.arctan2(u[:, c], u[:, p])
        th0 = np.where(th0 < 0, th0 + 2 * np.pi, th0)
        if rule == 'pos':
            s = np.ones_like(u[:, p])
        elif rule == 'cos_pos':
            s = np.where(u[:, p] < 0, -1.0, 1.0)
        elif rule == 'lowmag':
            s = np.where(th0 > 0.5 * np.pi, -1.0, 1.0)
        else:
            raise ValueError(rule)
        th = np.where(s < 0, th0 + np.pi, th0)
        th = np.where(r < 1e-12, 0.0, th)
        words[:, t] = np.round(th / np.pi * scale).astype(np.int64) % (2 * scale)
        u[:, p] = s * r
        u[:, c] = 0.0
    return words


if __name__ == '__main__':
    z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
    TREE = np.asarray(z['tree_edges'], np.int64)
    SHIP = np.asarray(z['angle_words'], np.int64)
    V = decode(SHIP, TREE, 8)
    for rule in ('pos', 'cos_pos', 'lowmag'):
        w = encode_rule(V, TREE, 8, rule)
        print(rule, 'mismatch vs shipped', int(np.sum(w != SHIP)),
              ' resid', float(np.linalg.norm(decode(w, TREE, 8) - V)),
              ' frac |w|<64 or >=192', float(np.mean((w < 64) | (w >= 192))))
    print('shipped          frac', float(np.mean((SHIP < 64) | (SHIP >= 192))))
