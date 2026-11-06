"""Search paid gates for a classical guard bit that implies a zero product.

For an unconditional paid gate with quantum-control product p, if a classical
bit b satisfies `b=0 => p=0`, adding `if b` to the gate is semantically safe and
saves the fraction of shots with b=0.  The first pass samples one measurement
branch; candidates are rechecked on independent branches.
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
OUT = ROOT / "artifacts/20261106_guard_search"
N = 4000
PAID = {"CCX", "CCZ", "CSWAP"}


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return c, [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]


def simulate(ops, seed, collect):
    rng = random.Random(seed)
    mask = (1 << N) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(N)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    hits = []
    for i, line in enumerate(ops):
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if collect and k in PAID and active == mask:
            if k in {"CCX", "CCZ"}:
                prod = q[qs[0]] & q[qs[1]]
                if k == "CCZ":
                    prod &= q[qs[2]]
            else:
                prod = q[qs[0]] & (q[qs[1]] ^ q[qs[2]])
            if 0 < prod < mask:
                for b, v in bits.items():
                    if 0 < v < mask:
                        # b=0 => prod=0
                        if prod & (mask ^ v) == 0:
                            hits.append({"op": i, "gate": line, "bit": b, "guarded_fraction": (mask ^ v).bit_count() / N})
                        # b=1 => prod=0
                        elif prod & v == 0:
                            hits.append({"op": i, "gate": line, "bit": b, "guarded_fraction": v.bit_count() / N, "complement": True})
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
            bits[int(p[2][1:])] = rng.getrandbits(N) & mask
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
    return hits


def check(ops, seed, candidate):
    rng = random.Random(seed)
    mask = (1 << N) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(N)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    op_id = candidate["op"]
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
            if k in {"CCX", "CCZ"}:
                prod = q[qs[0]] & q[qs[1]]
                if k == "CCZ":
                    prod &= q[qs[2]]
            else:
                prod = q[qs[0]] & (q[qs[1]] ^ q[qs[2]])
            v = bits.get(candidate["bit"], 0)
            if candidate.get("complement"):
                return prod & v == 0
            return prod & (mask ^ v) == 0
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
            bits[int(p[2][1:])] = rng.getrandbits(N) & mask
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
    return False


def main():
    _, ops = load_ops()
    first = simulate(ops, 20261106, True)
    # keep the strongest guard per gate
    best = {}
    for h in first:
        key = h["op"]
        if key not in best or h["guarded_fraction"] > best[key]["guarded_fraction"]:
            best[key] = h
    candidates = list(best.values())
    print("branch1 candidates", len(candidates))
    stable = [h for h in candidates if check(ops, 20261107, h) and check(ops, 20261108, h)]
    result = {"branch1": len(candidates), "stable": len(stable), "survivors": stable}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "guard_stable.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "survivors"}, indent=2))
    for h in sorted(stable, key=lambda z: -z["guarded_fraction"])[:40]:
        print(h)


if __name__ == "__main__":
    main()
