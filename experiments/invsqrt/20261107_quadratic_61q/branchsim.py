"""Condition-aware basis-state simulation of the invsqrt baseline.

The q61 helpers (`nonlinear_rebuild.simulate`, `multibranch.run_branch`) apply every
conditional CX/CCX/X unconditionally.  That is not a branch of the real circuit.  This
module tracks the classical bits written by HMR and applies each conditional gate only
where all bits on its condition stack are 1.

Classical bit names are reused (HMR writes b0 at several different ops), so the bit value
is a mutable register: each HMR occurrence assigns it a fresh branch mask.

A "branch" is a choice of one bit mask per HMR occurrence (a mask over the sampled x).
  * all-zero branch: every HMR mask is 0 (every measurement outcome 0).
  * random branch:    independent uniform random mask per HMR occurrence; a seeded RNG
                      makes each occurrence's mask reproducible.

Values are packed Python ints over the sample / full domain (bit i = value at x_i).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261106_q61"))
import common  # noqa: E402

NQ = 62


def hmr_ops(gates):
    return [i for i, (k, _, _) in enumerate(gates) if k == "HMR"]


def branch_masks(gates, xs, branch="zero", seed=0):
    """Return {hmr_op_index: mask} for one branch."""
    n = len(xs)
    ops = hmr_ops(gates)
    if branch == "zero":
        return {i: 0 for i in ops}
    if branch == "random":
        rng = np.random.default_rng(seed)
        out = {}
        for i in ops:
            bits = rng.integers(0, 2, n, dtype=np.uint8)
            out[i] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
        return out
    return dict(branch)


def stack_mask(stacks_i, bitmask, full):
    m = full
    for bit in stacks_i:
        m &= bitmask.get(bit, 0)
    return m


def _initial(gates, xs):
    n = len(xs)
    q = [0] * NQ
    for j in range(22):
        b = ((xs >> j) & 1).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(b, bitorder="little").tobytes(), "little")
    return q


def simulate(gates, stacks, stop, xs, branch="zero", seed=0):
    """Return wire masks at op `stop` (before applying it)."""
    n = len(xs)
    full = (1 << n) - 1
    q = _initial(gates, xs)
    masks = branch_masks(gates, xs, branch, seed)
    bitvalue = {}
    for i, (k, qs, p) in enumerate(gates[:stop]):
        if k == "HMR":
            q[qs[0]] = 0
            bitvalue[p[2]] = masks[i]
        elif k == "R":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[0]] &= ~m
        elif k == "X":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[0]] ^= m
        elif k == "CX":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[1]] ^= q[qs[0]] & m
        elif k == "SWAP":
            m = stack_mask(stacks[i], bitvalue, full)
            a, b = qs
            d = (q[a] ^ q[b]) & m
            q[a] ^= d
            q[b] ^= d
        elif k == "CSWAP":
            m = stack_mask(stacks[i], bitvalue, full)
            c, a, b = qs
            d = (q[a] ^ q[b]) & q[c] & m
            q[a] ^= d
            q[b] ^= d
        elif k == "CCX":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & m
    return q


def snapshot(gates, stacks, stops, xs, branch="zero", seed=0):
    """One pass; return {op: [62 masks]} for each op in stops."""
    n = len(xs)
    full = (1 << n) - 1
    q = _initial(gates, xs)
    masks = branch_masks(gates, xs, branch, seed)
    bitvalue = {}
    want = set(stops)
    out = {}
    for i, (k, qs, p) in enumerate(gates):
        if i in want:
            out[i] = list(q)
            if len(out) == len(want):
                break
        if k == "HMR":
            q[qs[0]] = 0
            bitvalue[p[2]] = masks[i]
        elif k == "R":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[0]] &= ~m
        elif k == "X":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[0]] ^= m
        elif k == "CX":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[1]] ^= q[qs[0]] & m
        elif k == "SWAP":
            m = stack_mask(stacks[i], bitvalue, full)
            a, b = qs
            d = (q[a] ^ q[b]) & m
            q[a] ^= d
            q[b] ^= d
        elif k == "CSWAP":
            m = stack_mask(stacks[i], bitvalue, full)
            c, a, b = qs
            d = (q[a] ^ q[b]) & q[c] & m
            q[a] ^= d
            q[b] ^= d
        elif k == "CCX":
            m = stack_mask(stacks[i], bitvalue, full)
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & m
    return out


if __name__ == "__main__":
    _, ops, gates, stacks = common.load_ops()
    print("ops", len(gates), "HMR", len(hmr_ops(gates)))
