"""Rank structure of low-coordinate columns and their differences.

Y_l = 76x35 matrix (rows h=1..76, values F[h][l]).  rank(Y_l) is the minimum
number of rank-1 terms needed to write column l alone.  rank(Y_l ^ Y_l') tells
how much two columns can share a common pool when the shared part is peeled.
Also computes the best "common part" C over a small candidate pool.
"""
import sys, json, itertools
import common as C

FREE = {(76, l) for l in range(4, 16)}


def rows_of(k):
    W, Wc, target, cl = C.build(k)
    req = {c: v for c, v in cl.items() if c[0] >= 1 and c not in FREE}
    # rows h=1..76 ; missing cells are 0
    Y = []
    for l in range(1, 16):
        Y.append([req.get((h, l), 0) for h in range(1, 77)])
    return Y


def rank(xs):
    return C.gf2_rank([x for x in xs if x])


def rank_xor(a, b):
    return rank([x ^ y for x, y in zip(a, b)])


def main(k):
    Y = rows_of(k)
    R = [rank(c) for c in Y]
    print(json.dumps({'k': k, 'rank_l': R, 'sum': sum(R)}), flush=True)
    D = {}
    for i, j in itertools.combinations(range(15), 2):
        D[(i + 1, j + 1)] = rank_xor(Y[i], Y[j])
    print(json.dumps({'k': k, 'pair_diff_ranks': {f'{a},{b}': v for (a, b), v in D.items()},
                      'min': min(D.values()), 'max': max(D.values()),
                      'mean': sum(D.values()) / len(D)}), flush=True)
    # greedy prefix chain in all 15! / 2 orders is too many; use best-neighbour chain
    # cheap heuristic: cost(prefix scheme) = rank(Y_first) + sum rank(Y_next ^ Y_prev)
    best = None
    for start in range(15):
        order = [start]
        left = set(range(15)) - {start}
        while left:
            cur = order[-1]
            nxt = min(left, key=lambda j: D.get((min(cur, j) + 1, max(cur, j) + 1), 0))
            order.append(nxt)
            left.remove(nxt)
        cost = rank(Y[order[0]]) + sum(rank_xor(Y[order[i]], Y[order[i - 1]]) for i in range(1, 15))
        if best is None or cost < best[0]:
            best = (cost, [o + 1 for o in order])
    print(json.dumps({'k': k, 'chain_cost': best[0], 'chain_order': best[1]}), flush=True)


if __name__ == '__main__':
    for k in [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '4')]:
        main(k)
