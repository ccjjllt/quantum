"""Find paid-gate controls (or Fredkin differences) equal to a classical bit.

If CCX(c1,c2,t) has c2 equal to classical bit b (or its complement), the gate is
a classically controlled CX and is free.  The same applies to CCZ controls and
to CSWAP when its control or its swapped difference is classical.  This script
samples measurement branches, records candidates on one branch, and rechecks
them on independent branches.  It does not modify a circuit.
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
N = 4000
PAID = {"CCX", "CCZ", "CSWAP"}


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return c, [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]


def simulate(ops, seed, candidates=None):
    rng = random.Random(seed)
    mask = (1 << N) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(N)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    val2bit = {}
    stack = []
    found = []

    def setbit(bid, v):
        old = bits.get(bid)
        if old is not None and old in val2bit:
            del val2bit[old]
        bits[bid] = v
        if 0 < v < mask:
            val2bit[v] = bid

    for i, line in enumerate(ops):
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k in PAID and active == mask and (candidates is None or i in candidates):
            if k in {"CCX", "CCZ"}:
                probes = {f"q{w}": q[w] for w in qs[:-1]}
            else:
                probes = {f"q{qs[0]}": q[qs[0]], "diff": q[qs[1]] ^ q[qs[2]]}
            for wire, v in probes.items():
                if 0 < v < mask and v in val2bit:
                    found.append({"op": i, "gate": line, "wire": wire, "bit": val2bit[v], "polarity": 1})
                elif v ^ mask in val2bit:
                    found.append({"op": i, "gate": line, "wire": wire, "bit": val2bit[v ^ mask], "polarity": 0})
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
            setbit(int(p[2][1:]), 0)
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
            setbit(bid, old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active)
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError(line)
    return found


def main():
    _, ops = load_ops()
    first = simulate(ops, 20261106)
    keys = {(h["op"], h["wire"], h["bit"], h["polarity"]) for h in first}
    print("branch1 candidates", len(keys))
    stable = []
    for seed in (20261107, 20261108):
        second = simulate(ops, seed, {k[0] for k in keys})
        have = {(h["op"], h["wire"], h["bit"], h["polarity"]) for h in second}
        stable.append(have)
    survivors = [k for k in keys if all(k in s for s in stable)]
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"branch1": len(keys), "stable": len(survivors),
              "survivors": [{"op": k[0], "wire": k[1], "bit": k[2], "polarity": k[3]} for k in sorted(survivors)]}
    (OUT / "wire_bit_stable.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
