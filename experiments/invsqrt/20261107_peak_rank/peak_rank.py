"""Rank of the 62 value-live wires at every 62-peak operation.

If the live values are linearly dependent at a peak, a linear/CX re-encoding can
drop a wire there.  If the rank is 62, no linear or classical-parity re-encoding
can free a wire at that operation; a nonlinear representation is required.

The live intervals come from the q61 value-liveness analysis.  The rank is
measured on a 20,000-x random-HMR-branch sample; a full-rank sample is a valid
witness that the functions are not linearly related on the reachable domain.
"""
from __future__ import annotations

import io
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
LIVENESS = ROOT / "artifacts/20261106_q61/value_liveness.json"
OUT = ROOT / "artifacts/20261107_peak_rank"
N = 20000


def rank(vecs):
    basis = []
    for v in vecs:
        x = v
        for b, piv in basis:
            if (x >> piv) & 1:
                x ^= b
        if x:
            piv = x.bit_length() - 1
            basis.append((x, piv))
            basis.sort(key=lambda t: -t[1])
    return len(basis)


def main():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    intervals = json.loads(LIVENESS.read_text())["value_liveness"]
    max_op = len(ops)
    diff = [0] * (max_op + 2)
    for ivs in intervals.values():
        for a, b in ivs:
            if 0 <= a <= b < max_op:
                diff[a] += 1
                diff[b + 1] -= 1
    live = []
    cur = 0
    for i in range(max_op):
        cur += diff[i]
        live.append(cur)
    peaks = [i for i, v in enumerate(live) if v >= 62]
    target = set(peaks)

    rng = random.Random(1)
    mask = (1 << N) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(N)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    result = {}
    for i, (k, qs, p) in enumerate(gates):
        if i > peaks[-1]:
            break
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if i in target:
            ls = [int(w[1:]) for w, ivs in intervals.items() if any(a <= i <= b for a, b in ivs)]
            result[i] = {"live": len(ls), "rank": rank([q[w] for w in ls])}
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
            raise ValueError((i, p))
    dist = Counter(v["rank"] for v in result.values())
    full = [i for i, v in result.items() if v["rank"] == 62]
    payload = {"scope": "rank of value-live wires at 62-peak ops, 20k random branch",
               "peak_ops": len(peaks), "rank_distribution": dict(sorted(dist.items())),
               "full_rank_ops": len(full), "full_rank_first_last": [min(full), max(full)] if full else None,
               "per_op": {str(k): v for k, v in result.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "peak_rank.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: v for k, v in payload.items() if k != "per_op"}, indent=2))


if __name__ == "__main__":
    main()
