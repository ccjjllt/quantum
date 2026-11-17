"""Tree + edge-order candidates, cheap loader proxy sweep (local, GF(2) only)."""
import json
import random
import sys

import numpy as np

WORK = '/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work'
sys.path.insert(0, WORK)
from common import decode, encode, check_tree  # noqa: E402
from proxy import proxy  # noqa: E402

NPZ = WORK + '/build/submission.npz'
z = np.load(NPZ, allow_pickle=False)
SHIP_TREE = np.asarray(z['tree_edges'], np.int64)
SHIP_WORDS = np.asarray(z['angle_words'], np.int64)
V = decode(SHIP_WORDS, SHIP_TREE, 8)          # the exact vectors the shipped table scores
N = V.shape[1]
assert N == 76


# ---------------------------------------------------------------- topologies
def heap_tree(n=76):
    """parent of v is (v-1)//2 -- the shipped shape; edge order = BFS by vertex."""
    return np.array([[(v - 1) // 2, v] for v in range(1, n)], np.int64)


def chain_tree(n=76):
    return np.array([[v - 1, v] for v in range(1, n)], np.int64)


def star_tree(n=76):
    return np.array([[0, v] for v in range(1, n)], np.int64)


def random_tree(n, rng, kind='attach'):
    """Random spanning tree rooted at 0; `kind` picks the attachment bias."""
    if kind == 'attach':                      # each new vertex attaches to a random old one
        edges = []
        for v in range(1, n):
            u = int(rng.integers(0, v))
            edges.append([u, v])
        return np.array(edges, np.int64)
    if kind == 'prufer':
        seq = [int(rng.integers(0, n)) for _ in range(n - 2)]
        deg = [1] * n
        for s in seq:
            deg[s] += 1
        edges = []
        for s in seq:
            leaf = next(i for i in range(n) if deg[i] == 1)
            edges.append([leaf, s] if rng.random() < 0.5 else [s, leaf])
            deg[leaf] -= 1
            deg[s] -= 1
        u, w = [i for i in range(n) if deg[i] == 1]
        edges.append([u, w])
        # root at 0 and orient parent-before-child
        adj = {i: [] for i in range(n)}
        for a, b in edges:
            adj[a].append(b)
            adj[b].append(a)
        out, seen, frontier = [], {0}, [0]
        while frontier:
            v = frontier.pop(0)
            for w in adj[v]:
                if w not in seen:
                    seen.add(w)
                    out.append([v, w])
                    frontier.append(w)
        return np.array(out, np.int64)
    if kind == 'deep':                        # catenary-ish: prefer recent vertices
        edges = []
        for v in range(1, n):
            u = int(max(0, v - 1 - int(rng.integers(0, 3))))
            edges.append([u, v])
        return np.array(edges, np.int64)
    if kind == 'bushy':
        edges = []
        for v in range(1, n):
            u = int(rng.integers(0, max(1, (v + 1) // 2)))
            edges.append([u, v])
        return np.array(edges, np.int64)
    raise ValueError(kind)


def canonical_order(edges, n=76):
    """BFS order of the edges, so children of a node keep a stable relative order."""
    children = [[] for _ in range(n)]
    for i, (p, c) in enumerate(edges):
        children[int(p)].append((int(c), i))
    order, q = [], [0]
    while q:
        v = q.pop(0)
        for c, i in children[v]:
            order.append(i)
            q.append(c)
    return np.array(order, np.int64)


def reorder(edges, order):
    """Apply a permutation of edge indices (must remain parent-before-child)."""
    return np.asarray(edges, np.int64)[np.asarray(order, np.int64)]


def random_shuffle_blocks(edges, rng, n=76, group=5):
    """Valid topological edge order built by repeatedly taking a random ready edge,
    then regrouping the resulting column order into blocks of `group`."""
    children = [[] for _ in range(n)]
    indeg = [0] * n
    for i, (p, c) in enumerate(edges):
        children[int(p)].append(i)
        indeg[int(c)] += 1
    ready = [i for i in range(n - 1) if indeg[int(edges[i][1])] == 0]
    # ready = edges whose parent is available... use standard Kahn on vertices
    avail_v = [0]
    node_done = {0}
    pending = {int(edges[i][1]): i for i in range(n - 1)}
    order = []
    while len(order) < n - 1:
        v = int(rng.choice(avail_v))
        kids = [i for i in children[v]]
        rng.shuffle(kids)
        for i in kids:
            order.append(i)
            c = int(edges[i][1])
            avail_v.append(c)
    return np.array(order, np.int64)


def topo_shuffle(edges, rng, n=76):
    """A uniformly-ish random linear extension: repeatedly pick a random ready edge."""
    children = [[] for _ in range(n)]
    for i, (p, c) in enumerate(edges):
        children[int(p)].append(i)
    ready = list(children[0])
    rng.shuffle(ready)
    order = []
    while ready:
        i = ready.pop(int(rng.integers(0, len(ready))))
        order.append(i)
        c = int(edges[i][1])
        ready.extend(children[c])
        rng.shuffle(ready)
    assert len(order) == n - 1
    return np.array(order, np.int64)


def run(name, edges, order=None, verbose=False):
    e = np.asarray(edges, np.int64) if order is None else reorder(edges, order)
    check_tree(e, N)
    words = encode(V, e, 8)
    p = proxy(words.astype(np.uint8))
    q = float(np.linalg.norm(decode(words, e, 8) - V))
    rec = {'name': name, 'sum_c_max': p['sum_c_max'],
           'ceil_total': p['sum_ceiling_products'], 'ceil_max': p['max_ceiling_products'],
           'ceil_per_k': [r['ceiling_products'] for r in p['rows']],
           'forced_per_k': [sum(r['forced_per_k']) if 'forced_per_k' in r else sum(r['forced']) for r in p['rows']],
           'quant_resid': q, 'edges': e.tolist()}
    if verbose:
        print(json.dumps({k: v for k, v in rec.items() if k != 'edges'}), flush=True)
    return rec


if __name__ == '__main__':
    rng = np.random.default_rng(20261118)
    out = []
    out.append(run('ship', SHIP_TREE, verbose=True))
    out.append(run('chain_id', chain_tree(), verbose=True))
    out.append(run('star_id', star_tree(), verbose=True))
    # the shipped tree with random topological re-orderings (same words, new grouping)
    for t in range(12):
        out.append(run(f'heap_topo{t}', SHIP_TREE, topo_shuffle(SHIP_TREE, rng), verbose=True))
    json.dump(out, open(WORK + '/sweep0.json', 'w'), indent=1)


def _chain_perm(n, rng):
    """Chain whose vertex labels follow a random orbital permutation (root 0)."""
    perm = np.concatenate([[0], rng.permutation(np.arange(1, n))]).astype(np.int64)
    return np.array([[int(perm[v - 1]), int(perm[v])] for v in range(1, n)], np.int64)


def relabel_bfs(edges, perm, n):
    """Relabel vertices with perm (0 must map to 0) and return a BFS edge order."""
    e = np.asarray(edges, np.int64)
    e2 = np.stack([np.asarray(perm)[e[:, 0]], np.asarray(perm)[e[:, 1]]], axis=1)
    adj = {i: [] for i in range(n)}
    for a, b in e2:
        adj[int(a)].append(int(b))
    out, seen, q = [], {int(perm[0]) if False else 0}, [0]
    while q:
        v = q.pop(0)
        for w in adj[v]:
            if w not in seen:
                seen.add(w)
                out.append([v, w])
                q.append(w)
    return np.array(out, np.int64)


def _heap_perm(n, rng):
    perm = np.concatenate([[0], rng.permutation(np.arange(1, n))]).astype(np.int64)
    return relabel_bfs(heap_tree(n), perm, n)
