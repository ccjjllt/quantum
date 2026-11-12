"""Givens-tree constructions on the 76 orbital labels (root 0, edges parent-before-child).

Every edge list here is a valid forward order for ``reconstruct_u_vectors``: when an edge (p, q)
is applied, q has not been used yet, so every node is a child exactly once.
"""
from __future__ import annotations

import numpy as np

N = 76


def log_depth_tree(n: int = N) -> np.ndarray:
    """The current table's tree (encode.log_depth_tree, BFS order of the binary tree)."""
    edges, level, depth = [], [0], 0
    while len(edges) < n - 1:
        nxt = []
        for label in level:
            nxt.append(label)
            right = label + (1 << depth)
            if right < n:
                edges.append((label, right))
                nxt.append(right)
        level, depth = nxt, depth + 1
    return np.asarray(edges, dtype=np.int64)


def path_tree(n: int = N) -> np.ndarray:
    return np.column_stack((np.arange(n - 1), np.arange(1, n))).astype(np.int64)


def star_tree(n: int = N) -> np.ndarray:
    return np.column_stack((np.zeros(n - 1, np.int64), np.arange(1, n))).astype(np.int64)


def heap_tree(n: int = N) -> np.ndarray:
    """Binary heap labelling (parent i -> 2i+1, 2i+2), emitted in increasing parent order."""
    edges = []
    for p in range(n):
        for q in (2 * p + 1, 2 * p + 2):
            if q < n:
                edges.append((p, q))
    assert len(edges) == n - 1
    return np.asarray(edges, dtype=np.int64)


def random_tree(n: int = N, seed: int = 0, order: str = 'child') -> np.ndarray:
    """Uniform random recursive tree: node q attaches to a uniform parent in [0, q).

    ``order='child'`` emits edges in increasing child label, which is a valid forward order.
    ``order='bfs'`` emits a BFS order from the root.
    """
    rng = np.random.default_rng(seed)
    parent = np.zeros(n, np.int64)
    for q in range(1, n):
        parent[q] = rng.integers(0, q)
    if order == 'child':
        return np.column_stack((parent[1:], np.arange(1, n))).astype(np.int64)
    children = [[] for _ in range(n)]
    for q in range(1, n):
        children[parent[q]].append(q)
    edges, queue = [], [0]
    while queue:
        p = queue.pop(0)
        for q in children[p]:
            edges.append((p, q))
            queue.append(q)
    assert len(edges) == n - 1
    return np.asarray(edges, dtype=np.int64)


def greedy_merge_tree(vectors: np.ndarray, n: int = N, root: int = 0) -> np.ndarray:
    """Huffman-like bottom-up merge on the row norms (a low-depth, amplitude-greedy construction).

    One live node per orbital carrying its mean squared amplitude over the rows; repeatedly merge the
    two nodes with the smallest mass (heavier = parent), keeping ``root`` out of the pool so it ends
    as the root the Givens encoding needs. Merge order is a valid forward order: a node's
    child-edge always precedes its parent-edges.
    """
    u = np.asarray(vectors, np.float64)
    mass = np.mean(u ** 2, axis=0) + 1e-30
    live = {i: mass[i] for i in range(n)}
    edges = []
    while len(live) > 1:
        items = sorted((m, i) for i, m in live.items() if i != root)
        if len(items) == 1:
            edges.append((root, items[0][1]))
            break
        m1, i1 = items[0]
        m2, i2 = items[1]
        p, c = (i1, i2) if m1 >= m2 else (i2, i1)
        edges.append((p, c))
        live[p] = m1 + m2
        del live[c]
    return _valid_order(np.asarray(edges, dtype=np.int64))


def balanced_mass_tree(vectors: np.ndarray, n: int = N, root: int = 0) -> np.ndarray:
    """Top-down bisection on amplitude mass: a shallow binary tree whose subtrees carry equal mass."""
    u = np.asarray(vectors, np.float64)
    mass = np.mean(u ** 2, axis=0) + 1e-30
    edges: list[tuple[int, int]] = []

    def build(group: list[int]) -> int:
        if len(group) == 1:
            return group[0]
        p = root if root in group else max(group, key=lambda i: mass[i])
        rest = sorted((i for i in group if i != p), key=lambda i: -mass[i])
        if len(rest) == 1:
            edges.append((p, rest[0]))
            return p
        half, acc, left = 0.5 * sum(mass[i] for i in rest), 0.0, []
        for i in rest:
            if acc < half:
                left.append(i)
                acc += mass[i]
        right = [i for i in rest if i not in left]
        if not left or not right:
            left, right = rest[:-1], rest[-1:]
        edges.append((p, build(left)))
        edges.append((p, build(right)))
        return p

    build(list(range(n)))
    return _valid_order(np.asarray(edges, dtype=np.int64))


def two_star_tree(n: int = N, groups: int = 9, root: int = 0) -> np.ndarray:
    """Depth-3 fan-out: the root feeds ``groups`` representatives, each feeds its members."""
    members = np.array_split(np.arange(1, n), groups)
    edges = []
    for g in members:
        rep = int(g[0])
        edges.append((root, rep))
        for q in g[1:]:
            edges.append((rep, int(q)))
    assert len(edges) == n - 1
    return np.asarray(edges, dtype=np.int64)


def _valid_order(edges: np.ndarray, root: int = 0) -> np.ndarray:
    """Reorder edges to a forward order: when (p, q) is applied, p carries amplitude, q does not."""
    edges = [tuple(map(int, e)) for e in edges]
    out, pending, active = [], list(edges), {root}
    while pending:
        for k, (p, q) in enumerate(pending):
            if p in active and q not in active:
                out.append((p, q))
                active.add(q)
                pending.pop(k)
                break
        else:  # pragma: no cover - a malformed tree would land here
            raise ValueError('no valid elimination order')
    return np.asarray(out, dtype=np.int64)


TREES = {
    'current': log_depth_tree,
    'path': path_tree,
    'star': star_tree,
    'heap': heap_tree,
}
