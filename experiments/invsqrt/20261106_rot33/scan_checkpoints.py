"""Scan every ~100th circuit checkpoint for linear availability of the 33 bits.

If all 33 ideal fixed-point bits are linear forms of the live wires at some
checkpoint, the 33 rotations can be applied there with only CX loading gates
(free) and one scratch wire.  This is a sample scan; hits are confirmed on the
full domain separately.
"""
from __future__ import annotations

import io
import json
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452
N_SAMPLE = 2048


def load_ops():
    circuit = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    ops = []
    for line in buf.getvalue().splitlines():
        if line.startswith(("APPEND", "REGISTER")):
            continue
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return ops


def as_int(a: np.ndarray) -> int:
    return int.from_bytes(np.packbits(a.astype(np.uint8), bitorder="little").tobytes(), "little")


def add_basis(v: int, basis: dict[int, int]) -> None:
    while v:
        p = v.bit_length() - 1
        if p not in basis:
            basis[p] = v
            return
        v ^= basis[p]


def in_span(v: int, basis: dict[int, int]) -> bool:
    while v:
        p = v.bit_length() - 1
        if p not in basis:
            return False
        v ^= basis[p]
    return True


def main() -> None:
    rng = np.random.default_rng(20261109)
    xs = np.concatenate([np.arange(1, N_SAMPLE // 2 + 1, dtype=np.uint64),
                         rng.integers(1, MAXX + 1, N_SAMPLE // 2, dtype=np.uint64)])
    n = len(xs)
    idx = xs.astype(np.int64) - 1
    N = np.load(OUT / "N.npy")
    g = {w: as_int(((N[idx] >> (35 - w)) & 1).astype(np.uint8)) for w in range(2, 35)}
    g_list = list(g.items())

    ops = load_ops()
    q = [as_int(((xs >> j) & 1).astype(np.uint8)) for j in range(22)] + [0] * 40
    bits: dict[int, int] = {}
    stack: list[int] = []
    full = (1 << n) - 1
    best = []
    t0 = time.time()

    for i, (k, qs, p) in enumerate(ops):
        if i % 1 == 0:
            basis: dict[int, int] = {}
            add_basis(full, basis)
            for v in q:
                add_basis(v & full, basis)
            for v in bits.values():
                add_basis(v & full, basis)
            hits = [w for w, t in g_list if in_span(t, basis)]
            if len(hits) >= 1:
                best.append({"op": i, "rank": len(basis), "hits": hits})
                print(i, "rank", len(basis), "hits", len(hits), hits, flush=True)
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
        elif k == "SWAP":
            a, b = qs
            d = (q[a] ^ q[b]) & active
            q[a] ^= d
            q[b] ^= d
        elif k == "CSWAP":
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & q[qs[0]] & active
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = 0
            q[qs[0]] = 0
        elif k == "R":
            q[qs[0]] = 0
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, k, p))
    assert not stack
    best.sort(key=lambda r: -len(r["hits"]))
    (OUT / "checkpoint_scan.json").write_text(json.dumps(
        {"n_sample": n, "stride": 100, "best": best[:50]}, indent=2) + "\n")
    print("time", time.time() - t0, "best", best[:10])


if __name__ == "__main__":
    main()
