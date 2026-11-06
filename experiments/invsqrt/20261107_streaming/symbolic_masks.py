"""Exact symbolic dependency of all 41 fine-rotation masks on their block-start state.

The 41 fine rotations come in two blocks:

  block 1  ops [15247, 15617)   rot 0..14   ancilla q28
  block 2  ops [25392, 25662)   rot 15..40  ancilla q50 / q41 / q40 / q28

Inside a block the only non-diagonal gates are X, CX, CCX, SWAP, CSWAP and
HMR/R, so every rotation mask is an exact Boolean expression of the 62 wire
values present at the block start.  We build those expressions symbolically
(hash-consed DAG with local simplification), report the support of every mask,
and verify each expression bit-exactly against the traced mask on the legal
domain.

Output: artifacts/20261107_streaming/symbolic_masks.json
"""
from __future__ import annotations

import json

import numpy as np

import common

BLOCKS = [(15247, 15617), (25392, 25662)]
VERIFY_N = None          # None = full legal domain


class Expr:
    __slots__ = ("op", "a", "b", "wire")

    def __init__(self, op, a=None, b=None, wire=None):
        self.op = op          # '0','1','v','n','a','x'
        self.a = a
        self.b = b
        self.wire = wire


class Sym:
    def __init__(self):
        self.pool: dict = {}
        self.z = self._mk("0")
        self.o = self._mk("1")

    def _mk(self, op, a=None, b=None, wire=None):
        key = (op, id(a), id(b), wire)
        e = self.pool.get(key)
        if e is None:
            e = Expr(op, a, b, wire)
            self.pool[key] = e
        return e

    def var(self, w):
        return self._mk("v", wire=w)

    def not_(self, a):
        if a is self.z:
            return self.o
        if a is self.o:
            return self.z
        if a.op == "n":
            return a.a
        return self._mk("n", a)

    def xor(self, a, b):
        if a is self.z:
            return b
        if b is self.z:
            return a
        if a is b:
            return self.z
        if a is self.o:
            return self.not_(b)
        if b is self.o:
            return self.not_(a)
        if a.op == "n" and b.op == "n":
            return self.xor(a.a, b.a)
        if (a.op, id(a)) > (b.op, id(b)):
            a, b = b, a
        return self._mk("x", a, b)

    def and_(self, a, b):
        if a is self.z or b is self.z:
            return self.z
        if a is self.o:
            return b
        if b is self.o:
            return a
        if a is b:
            return a
        if (a.op, id(a)) > (b.op, id(b)):
            a, b = b, a
        return self._mk("a", a, b)


def support(e) -> set[int]:
    out: set[int] = set()
    stack = [e]
    seen: set[int] = set()
    while stack:
        x = stack.pop()
        if id(x) in seen:
            continue
        seen.add(id(x))
        if x.op == "v":
            out.add(x.wire)
        elif x.op == "n":
            stack.append(x.a)
        elif x.op in {"a", "x"}:
            stack.append(x.a)
            stack.append(x.b)
    return out


def node_count(e) -> int:
    stack = [e]
    seen: set[int] = set()
    while stack:
        x = stack.pop()
        if id(x) in seen:
            continue
        seen.add(id(x))
        if x.op == "n":
            stack.append(x.a)
        elif x.op in {"a", "x"}:
            stack.append(x.a)
            stack.append(x.b)
    return len(seen)


def to_anf(e, max_terms: int = 4000):
    """ANF as a list of frozensets of positive literals; None if it explodes."""
    memo: dict = {}

    def xr(a, b):
        from collections import Counter
        c = Counter()
        for t in a:
            c[t] ^= 1
        for t in b:
            c[t] ^= 1
        return [t for t, v in c.items() if v]

    def an(a, b):
        from collections import Counter
        c = Counter()
        for t in a:
            for u in b:
                c[t | u] ^= 1
        return [t for t, v in c.items() if v]

    def rec(x):
        key = id(x)
        if key in memo:
            return memo[key]
        if x.op == "0":
            r = []
        elif x.op == "1":
            r = [frozenset()]
        elif x.op == "v":
            r = [frozenset({x.wire})]
        elif x.op == "n":
            r = xr(rec(x.a), [frozenset()])
        elif x.op == "a":
            r = an(rec(x.a), rec(x.b))
        elif x.op == "x":
            r = xr(rec(x.a), rec(x.b))
        else:
            raise ValueError(x.op)
        if len(r) > max_terms:
            raise OverflowError
        memo[key] = r
        return r

    try:
        return rec(e)
    except OverflowError:
        return None


def eval_expr(e, base_state, n, cache):
    key = id(e)
    v = cache.get(key)
    if v is not None:
        return v
    full = (1 << n) - 1
    if e.op == "0":
        r = 0
    elif e.op == "1":
        r = full
    elif e.op == "v":
        r = base_state[e.wire]
    elif e.op == "n":
        r = full ^ eval_expr(e.a, base_state, n, cache)
    elif e.op == "a":
        r = eval_expr(e.a, base_state, n, cache) & eval_expr(e.b, base_state, n, cache)
    elif e.op == "x":
        r = eval_expr(e.a, base_state, n, cache) ^ eval_expr(e.b, base_state, n, cache)
    else:
        raise ValueError(e.op)
    cache[key] = r
    return r


def block_of(op, rops):
    for bstart, bend in BLOCKS:
        if bstart <= op < bend:
            return bstart, bend
    raise ValueError(op)


def main() -> None:
    ops, gates = common.load_ops()
    masks, rops, rwires, angles = common.load_masks_full()
    mask_by_op = dict(zip(rops, masks))

    n = common.MAXX if VERIFY_N is None else VERIFY_N
    starts = {b[0] for b in BLOCKS}
    base_state, _ = common.trace_checkpoints(gates, starts, n=n)

    per_rot = []
    full = (1 << n) - 1
    for bstart, bend in BLOCKS:
        sym = Sym()
        # substitute block-start constants: wires that are identically 0 / 1
        bs = base_state[bstart]
        q = []
        for w in range(common.NQ):
            if bs[w] == 0:
                q.append(sym.z)
            elif bs[w] == full:
                q.append(sym.o)
            else:
                q.append(sym.var(w))
        exprs = {}
        qwire = dict(zip(rops, rwires))
        rop_set = set(rops)
        for i in range(bstart, bend):
            k, qs, p = gates[i]
            if k == "Z_POW":
                if i in rop_set:
                    exprs[i] = q[qwire[i]]
                continue
            if k in {"Z", "CZ", "CCZ", "NEG"}:
                continue
            if k == "HMR":
                q[qs[0]] = sym.z
                continue
            if k == "R":
                q[qs[0]] = sym.z
                continue
            if k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
                     "PUSH_CONDITION", "POP_CONDITION"}:
                continue
            activated = "if" not in p and not any(True for _ in ())
            if k == "X":
                if activated:
                    q[qs[0]] = sym.xor(q[qs[0]], sym.o)
            elif k == "CX":
                if activated:
                    q[qs[1]] = sym.xor(q[qs[1]], q[qs[0]])
            elif k == "CCX":
                if activated:
                    q[qs[2]] = sym.xor(q[qs[2]], sym.and_(q[qs[0]], q[qs[1]]))
            elif k == "SWAP":
                a, b = qs
                if activated:
                    q[a], q[b] = q[b], q[a]
            elif k == "CSWAP":
                c, a, b = qs
                if activated:
                    qa, qb = q[a], q[b]
                    d = sym.and_(q[c], sym.xor(qa, qb))
                    q[a] = sym.xor(qa, d)
                    q[b] = sym.xor(qb, d)
            else:
                raise ValueError((i, k, p))

        for rop in sorted(exprs):
            i = rops.index(rop)
            e = exprs[rop]
            sup = sorted(support(e))
            cache = {}
            val = eval_expr(e, base_state[bstart], n, cache)
            exact = (val == mask_by_op[rop]) if VERIFY_N is None else None
            if VERIFY_N is not None:
                # compare on the sample domain by re-tracing masks on that domain
                exact = "sample-domain"
            anf = to_anf(e)
            per_rot.append({
                "rot": i, "op": rop, "block_start": bstart,
                "wire": qwire[rop],
                "support": sup, "support_size": len(sup),
                "nodes": node_count(e),
                "anf_terms": None if anf is None else len(anf),
                "anf": None if anf is None else
                       sorted([sorted(t) for t in anf], key=lambda t: (len(t), t)),
                "exact_full_domain": exact,
            })
            print(f"rot{i:2d} op{rop:5d} block{bstart} support={len(sup):2d} "
                  f"nodes={node_count(e):5d} anf={'-' if anf is None else len(anf)} "
                  f"exact={exact}")

    union1 = sorted({w for r in per_rot if r["block_start"] == BLOCKS[0][0]
                     for w in r["support"]})
    union2 = sorted({w for r in per_rot if r["block_start"] == BLOCKS[1][0]
                     for w in r["support"]})
    print("\nblock1 support union size", len(union1), union1)
    print("block2 support union size", len(union2), union2)
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "symbolic_masks.json").write_text(json.dumps(
        {"blocks": BLOCKS, "verify_n": n,
         "per_rotation": per_rot,
         "block1_union": union1, "block2_union": union2}, indent=1) + "\n")
    if VERIFY_N is None and not all(r["exact_full_domain"] for r in per_rot):
        raise SystemExit("expression mismatch on the full legal domain")


if __name__ == "__main__":
    main()
