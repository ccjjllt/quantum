"""Greedy loader-by-loader choice of the 5-word batches, over value-preserving
edge permutations of the shipped table (decode is identical, metrics cannot move).

Per stage k the candidate batches are random valid next-5 choices; the objective is
loader k's floor from proxy.loader_dims (products a perfect pairing would reach).
"""
import json
import sys
from pathlib import Path

import numpy as np

WORK = Path('/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
sys.path.insert(0, str(WORK))
from common import decode, check_tree  # noqa: E402
from proxy import loader_dims  # noqa: E402
from parity_recover import NOUT  # noqa: E402

z = np.load(str(WORK / 'build' / 'submission.npz'), allow_pickle=False)
TREE = np.asarray(z['planet_N'] if False else z['tree_edges'], np.int64)
SHIP = np.asarray(z['angle_words'], np.int64)
V = decode(SHIP, TREE, 8)
N = V.shape[1]


def floor_of_batch(words_batch_cols, k):
    """Loader-k floor for a full 75-column table assembled from a partial order."""
    w = np.asarray(words_batch_cols, np.uint8)
    dims, _ = loader_dims(w, k)
    scm = sum(f + s for f, s in dims)
    return (15 * NOUT - scm) // 2, scm


def loader_floor(words, k):
    """`words` is a full 75-column table; only batch k and k-1 matter, but
    complete_words() wants the full width.  Embedding a batch is equivalent
    because the completion and the Mobius transform are column-wise."""
    dims, _ = loader_dims(np.asarray(words, np.uint8), k)
    scm = sum(f + s for f, s in dims)
    return (15 * NOUT - scm) // 2, [f for f, s in dims], [s for f, s in dims]


def embed(cur5, prev5=None, k=0):
    t = np.zeros((cur5.shape[0], 75), np.uint8)
    t[:, 5 * k:5 * k + 5] = np.asarray(cur5, np.uint8)
    if k > 0:
        t[:, 5 * k - 5:5 * k] = np.asarray(prev5, np.uint8)
    return t


def batches(words, order):
    """Split the permuted table into the 15 five-column batches."""
    wp = words[:, order]
    return [wp[:, 5 * k:5 * k + 5] for k in range(15)]


def loader_floor_from_batches(bs, k):
    """Loader k's target is batch k XOR batch k-1 (batch 0 alone)."""
    if k == 0:
        w = bs[0]
    else:
        w = bs[k] ^ bs[k - 1]
    return loader_floor(w, k)


if __name__ == '__main__':
    rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    ch = {}
    for i, (p, c) in enumerate(TREE):
        ch.setdefault(int(p), []).append(i)

    best = (10 ** 9, None, None)
    for restart in range(int(sys.argv[3]) if len(sys.argv) > 3 else 3):
        ptr = {v: 0 for v in ch}
        ready = [0] if ch.get(0) else []
        order = []
        bs = []
        tot = 0
        for k in range(15):
            # candidate 5-column groups drawn from valid continuations
            cands = []
            for _ in range(trials):
                p2 = dict(ptr)
                r2 = list(ready)
                o = []
                ok = True
                for step in range(5):
                    if not r2:
                        ok = False
                        break
                    j = int(rng.integers(0, len(r2)))
                    v = r2[j]
                    i = ch[v][p2[v]]
                    p2[v] += 1
                    if p2[v] == len(ch[v]):
                        r2.pop(j)
                    o.append(i)
                    c = int(TREE[i][1])
                    if ch.get(c):
                        r2.append(c)
                if not ok:
                    continue
                cols = [order + o]  # placeholder
                wb = SHIP[:, order + o][:, len(order):]
                prev = SHIP[:, order[-5:]] if k > 0 else None
                tgt = embed(SHIP[:, order + o][:, len(order):], prev, k)
                fl = loader_floor(tgt, k)[0]
                cands.append((fl, o))
            if not cands:
                break
            cands.sort(key=lambda x: x[0])
            fl, o = cands[0]
            # commit
            for i in o:
                v = int(TREE[i][0])
                assert ptr[v] < len(ch[v]) and ch[v][ptr[v]] == i
                ptr[v] += 1
                if ptr[v] == len(ch[v]):
                    ready.remove(v)
                c = int(TREE[i][1])
                if ch.get(c):
                    ready.append(c)
            order.extend(o)
            bs.append(SHIP[:, o])
            tot += fl
            print(f'  restart {restart} k{k}: floor {fl} (running {tot})', flush=True)
        if len(order) == len(TREE) and tot < best[0]:
            best = (tot, np.array(order, np.int64), [r for r in range(15)])
    print('BEST greedy floor total', best[0], 'vs shipped 2366', flush=True)
    if best[1] is not None:
        o = best[1]
        e1 = TREE[o]
        check_tree(e1, N)
        print('resid', float(np.linalg.norm(decode(SHIP[:, o], e1, 8) - V)))
        np.save(str(WORK / 'perm_greedy_order.npy'), o)
        json.dump({'order': o.tolist(), 'floor_total': int(best[0])},
                  open(WORK / 'perm_greedy.json', 'w'))
