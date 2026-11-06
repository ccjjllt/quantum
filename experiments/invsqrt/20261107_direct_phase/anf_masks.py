"""Algebraic normal form of the 41 fine-rotation masks over the 22 x bits.

The masks are traced on the all-zero HMR branch for every 22-bit x (including
x=0 and x>max_x).  A fast Moebius transform gives the ANF coefficients; we
report nonzero coefficient count, algebraic degree and the number of high-degree
monomials.  This is a full-cube extension, not a don't-care minimization over
the legal domain.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
ROT = ROOT / "artifacts/20261106_rot33/summary.json"
OUT = ROOT / "artifacts/20261107_direct_phase"
N = 1 << 22


def main():
    rot = json.loads(ROT.read_text())
    ops_list = rot["ops"]
    circuit = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    xs = np.arange(N, dtype=np.uint64)
    full = (1 << N) - 1
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    masks = np.zeros((len(ops_list), N), dtype=np.uint8)
    where = {op: idx for idx, op in enumerate(ops_list)}
    for i, (k, qs, p) in enumerate(gates):
        if i in where:
            v = q[qs[0]]
            masks[where[i]] = np.unpackbits(np.frombuffer(v.to_bytes(N // 8, "little"), dtype=np.uint8), bitorder="little")[:N]
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
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
            bits[int(p[2][1:])] = 0
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
    # Fast Moebius transform along the 2^22 axis.
    a = masks
    for k in range(22):
        step = 1 << k
        for start in range(0, N, step << 1):
            a[:, start + step:start + (step << 1)] ^= a[:, start:start + step]
    idx = np.arange(N, dtype=np.uint32)
    deg = np.bitwise_count(idx)
    result = []
    for r in range(a.shape[0]):
        nz = a[r] != 0
        cnt = int(nz.sum())
        d = int(deg[nz].max()) if cnt else 0
        result.append({"rotation": r, "op": ops_list[r], "nonzero_anf": cnt,
                       "degree": d, "density": cnt / N,
                       "high_degree_monomials": int((deg[nz] >= d - 1).sum()) if cnt else 0})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "anf_masks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"masks": len(result), "min_degree": min(x["degree"] for x in result),
                      "max_degree": max(x["degree"] for x in result),
                      "min_nonzero": min(x["nonzero_anf"] for x in result),
                      "max_nonzero": max(x["nonzero_anf"] for x in result),
                      "first": result[:5]}, indent=2))


if __name__ == "__main__":
    main()
