"""Shared helpers for the tree_edges research line (local, small-numpy only).

The Givens map is the verifier's own unmodified code:
    vectors = reconstruct_u_vectors(theta/pi, tree_edges)
    forward edge (p, c):  P,C -> (cos P - sin C, sin P + cos C), starting from e_0.
Because every edge is parent-before-child, C == 0 at the moment its edge runs,
so the map is exactly invertible in reverse edge order.
"""
import pathlib
import sys

import numpy as np

VER = pathlib.Path('/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers')
if str(VER) not in sys.path:
    sys.path.insert(0, str(VER))

from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors  # noqa: E402


def decode(words, edges, brot=8):
    """words -> (num_vectors, N) vectors, exactly as the verifier does."""
    return reconstruct_u_vectors(np.asarray(words, np.int64) / float(1 << (brot - 1)), edges)


def encode(vectors, edges, brot=8):
    """Exact inverse of decode(): vectors -> integer words in [0, 2**brot)."""
    u = np.array(vectors, np.float64, copy=True)
    edges = np.asarray(edges, np.int64)
    n = len(edges)
    scale = 1 << (brot - 1)
    words = np.zeros((u.shape[0], n), np.int64)
    for t in range(n - 1, -1, -1):
        p, c = int(edges[t][0]), int(edges[t][1])
        th = np.arctan2(u[:, c], u[:, p])
        th = np.where(th < 0.0, th + 2.0 * np.pi, th)
        th = np.where(np.hypot(u[:, p], u[:, c]) < 1e-12, 0.0, th)
        words[:, t] = np.round(th / np.pi * scale).astype(np.int64) % (2 * scale)
        u[:, p] = np.hypot(u[:, p], u[:, c])
        u[:, c] = 0.0
    return words


def check_tree(edges, n):
    """The verifier's own validity rule: rooted at 0, parent visited before child."""
    edges = np.asarray(edges, np.int64)
    assert edges.shape == (n - 1, 2), edges.shape
    seen = {0}
    for p, c in edges:
        assert int(p) in seen and int(c) not in seen, f'bad edge {(p, c)}'
        seen.add(int(c))
    assert len(seen) == n


def relabel(edges, perm):
    """perm[v] = new label of old vertex v (a bijection on range(N))."""
    e = np.asarray(edges, np.int64)
    return np.stack([np.asarray(perm)[e[:, 0]], np.asarray(perm)[e[:, 1]]], axis=1)


def subtree_masks(edges, n):
    """For every vertex, the sorted array of its subtree vertices."""
    children = [[] for _ in range(n)]
    for p, c in edges:
        children[int(p)].append(int(c))
    order = []
    stack = [0]
    while stack:
        v = stack.pop()
        order.append(v)
        stack.extend(children[v])
    sub = {v: [v] for v in range(n)}
    for v in reversed(order):
        for c in children[v]:
            sub[v].extend(sub[c])
    return {v: np.array(sorted(s), np.int64) for v, s in sub.items()}


def valid_order_score(edges, order):
    """True iff `order` (a permutation of edge indices) is parent-before-child."""
    pos = np.empty(len(order), np.int64)
    pos[np.asarray(order)] = np.arange(len(order))
    for i, (p, c) in enumerate(edges):
        if pos[i] < 0:
            return False
    # every edge whose child is a vertex must come after that vertex's parent edge
    parent_edge = {}
    for i, (p, c) in enumerate(edges):
        parent_edge[int(c)] = i
    for i, (p, c) in enumerate(edges):
        if int(p) in parent_edge and pos[parent_edge[int(p)]] > pos[i]:
            return False
    return True
