"""Is a metric-legal row permutation also legal for the *loader emitter*?

The shipped loaders rely on the word bit-7 helper table being decomposable as
   helper(a) = low[a % 16] ^ high[a // 16]
(emit_plan.separate_helpers asserts it; the low 16 table supplies the five free
low monomials for the low cache).  The helper is  bit7 ^ bit6  of the words.

This script applies candidate permutations and reports, for each, whether the
permuted table still satisfies that decomposition, plus the block-rank proxy.
"""
import json, random
import numpy as np
from common import load_words, gf2_rank, NOUT, M35
from planner import complete_words, cross_tensor
from lowbasis import inverse15, transform_target

N = 1220
NBODY_START = 76
RB, R = 143, 8


def helper_ok(W):
    """helper table of the *completed* (1232-row) table, as emit_plan sees it."""
    W = complete_words(W)
    h = ((W[:, :5] >> 7) ^ (W[:, :5] >> 6)) & 1
    t = np.asarray(h, dtype=np.uint8)
    M = len(t)
    if M % 16:
        return None
    low = t[:16].copy()
    high = t[::16].copy() ^ low[0]
    addr = np.arange(M)
    return bool(np.array_equal(t, low[addr % 16] ^ high[addr // 16]))


def block_rank_proxy(W, k):
    Wc = complete_words(W)
    t = cross_tensor(Wc, k)
    rid = [1 << i for i in range(15)]
    tt = transform_target(t, inverse15(rid))
    ranks = []
    for b in range(5):
        loc = []
        for x in tt[1:76]:
            v = 0
            for j, i in enumerate([3 * b, 3 * b + 1, 3 * b + 2]):
                v |= ((x >> (NOUT * i)) & M35) << (NOUT * j)
            loc.append(v)
        ranks.append(gf2_rank(loc))
    return ranks


def main():
    W = load_words().astype(np.uint8)
    rng = random.Random(20261118)
    cands = {'identity': np.arange(N)}
    # reverse the two-body rows
    p = np.arange(N)
    p[NBODY_START:] = p[NBODY_START:][::-1]
    cands['reverse_twobody'] = p
    # sort each rho block by the 40-bit word vector of its first 5 words
    p = np.arange(N)
    for r in range(R):
        idx = np.arange(NBODY_START + r * RB, NBODY_START + (r + 1) * RB)
        key = [int.from_bytes(W[i, :5].astype(np.uint8).tobytes(), 'little') for i in idx]
        p[idx] = idx[np.argsort(key)]
    cands['sort_by_word_in_rho'] = p
    # Gray/TSP-like: greedy nearest neighbour within each rho block by Hamming distance
    p = np.arange(N)
    for r in range(R):
        idx = list(range(NBODY_START + r * RB, NBODY_START + (r + 1) * RB))
        bits = W[idx, :5].astype(np.uint8)
        used = [False] * len(idx)
        order = [0]
        used[0] = True
        for _ in range(len(idx) - 1):
            cur = bits[order[-1]]
            best, bd = None, 1e9
            for j in range(len(idx)):
                if used[j]:
                    continue
                d = int(np.count_nonzero(np.bitwise_xor(cur, bits[j])))
                if d < bd:
                    bd, best = d, j
            order.append(best)
            used[best] = True
        p[idx] = np.array(idx)[order]
    cands['nn_in_rho'] = p

    # 16-aligned low-group permutations (rows 0..75 one-body, then 76.. in 16-row groups)
    p = np.arange(N)
    for g in range(0, N, 16):
        idx = np.arange(g, min(g + 16, N))
        q = idx.copy(); rng.shuffle(q); p[idx] = q
    cands['shuffle_16aligned_groups'] = p
    # one-body rows only, sorted by word vector
    p = np.arange(N)
    idx = np.arange(0, 76)
    key = [int.from_bytes(W[i, :5].astype(np.uint8).tobytes(), 'little') for i in idx]
    p[idx] = idx[np.argsort(key)]
    cands['sort_onebody_by_word'] = p
    # one-body rows only, random
    p = np.arange(N)
    q = p[:76].copy(); rng.shuffle(q); p[:76] = q
    cands['random_onebody'] = p
    # full random shuffle of the two-body rows
    p = np.arange(N)
    q = p[NBODY_START:].copy()
    rng.shuffle(q)
    p[NBODY_START:] = q
    cands['random_twobody'] = p

    out = []
    for name, p in cands.items():
        Wp = W[p]
        row = {'perm': name, 'rows_moved': int(np.count_nonzero(p != np.arange(N))),
               'helper_low_high_ok': helper_ok(Wp)}
        row['block_ranks_k4'] = block_rank_proxy(Wp, 4)
        row['block_ranks_k2'] = block_rank_proxy(Wp, 2)
        # does the helper agree across all 15 word groups (emit_plan k>=9 assert)?
        h = ((Wp[:, :5] >> 7) ^ (Wp[:, :5] >> 6)) & 1
        agree = [k for k in range(15) if np.array_equal(((Wp[:, 5 * k:5 * k + 5] >> 7) ^ (Wp[:, 5 * k:5 * k + 5] >> 6)) & 1, h)]
        row['groups_matching_group0'] = len(agree)
        print(json.dumps(row), flush=True)
        out.append(row)
    json.dump(out, open('/tmp/perm_probe.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
