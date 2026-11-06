"""Search every paid-gate control for membership in the span of measurement bits.

If a control wire equals a parity of existing classical bits, that control can be
replaced by a classical condition and the paid gate becomes a free classically
controlled gate.  The first pass uses 512 sampled x values per branch; candidates
are rechecked on independent branches with 20k samples.
"""
from __future__ import annotations

import io
import json
import random
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_cache_search"
N_SMALL = 512
N_BIG = 20000
PAID = {"CCX", "CCZ", "CSWAP"}


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return c, [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]


def solve(vec, bits, mask):
    """Return (bit_ids, const) with vec = const XOR XOR(bits), or None."""
    basis = {}
    ids = sorted(bits)
    for idx, b in enumerate(ids):
        v = bits[b]
        if v in (0, mask):
            continue
        combo = 1 << idx
        while v:
            piv = v.bit_length() - 1
            if piv in basis:
                bv, bc = basis[piv]
                v ^= bv
                combo ^= bc
            else:
                basis[piv] = (v, combo)
                break
    v = vec
    combo = 0
    while v:
        piv = v.bit_length() - 1
        if piv in basis:
            bv, bc = basis[piv]
            v ^= bv
            combo ^= bc
        else:
            return None
    # the all-ones constant is not in `bits`; a remaining const is handled by its own row
    chosen = [ids[i] for i in range(len(ids)) if (combo >> i) & 1]
    return chosen


def simulate(ops, seed, n, targets=None):
    rng = random.Random(seed)
    mask = (1 << n) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(n)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    found = []
    for i, line in enumerate(ops):
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k in PAID and active == mask and (targets is None or i in targets):
            controls = qs[:-1] if k in {"CCX", "CCZ"} else [qs[0]]
            for wire in controls:
                v = q[wire]
                if 0 < v < mask:
                    rel = solve(v, bits, mask)
                    polarity = 1
                    if rel is None:
                        rel = solve(v ^ mask, bits, mask)
                        polarity = 0
                    if rel is not None:
                        found.append({"op": i, "gate": line, "wire": f"q{wire}", "bits": rel, "polarity": polarity})
        if k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif k in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & active
            if k == "CSWAP":
                d &= q[qs[0]]
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = rng.getrandbits(n) & mask
            q[qs[0]] &= ~active
        elif k == "R":
            q[qs[0]] &= ~active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            bid = int(p[1][1:])
            old = bits.get(bid, 0)
            bits[bid] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError(line)
    return found


def check(ops, seed, candidate):
    """Check one candidate relation on a fresh branch."""
    op_id = candidate["op"]
    wire = int(candidate["wire"][1:])
    target_bits = candidate["bits"]
    n = N_BIG
    rng = random.Random(seed)
    mask = (1 << n) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(n)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    for i, line in enumerate(ops[:op_id + 1]):
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if i == op_id:
            v = q[wire]
            par = 0
            for b in target_bits:
                par ^= bits.get(b, 0)
            return (v == par) if candidate["polarity"] else (v ^ mask == par)
        if k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif k in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & active
            if k == "CSWAP":
                d &= q[qs[0]]
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = rng.getrandbits(n) & mask
            q[qs[0]] &= ~active
        elif k == "R":
            q[qs[0]] &= ~active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            bid = int(p[1][1:])
            old = bits.get(bid, 0)
            bits[bid] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError(line)
    raise AssertionError("op not reached")


def main():
    _, ops = load_ops()
    first = simulate(ops, 20261106, N_SMALL)
    # dedupe
    uniq = []
    seen = set()
    for h in first:
        key = (h["op"], h["wire"], tuple(h["bits"]), h["polarity"])
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    print("branch1 candidates", len(uniq))
    survivors = []
    for h in uniq:
        if all(check(ops, seed, h) for seed in (20261107, 20261108)):
            survivors.append(h)
    result = {"branch1": len(uniq), "stable": len(survivors), "survivors": survivors}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "control_span_stable.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "survivors"}, indent=2))
    for h in survivors[:30]:
        print(h["op"], h["gate"], h["wire"], "nbits", len(h["bits"]))


if __name__ == "__main__":
    main()
