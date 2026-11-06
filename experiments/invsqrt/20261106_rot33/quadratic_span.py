"""Sample test: are the 33 ideal phase bits in the degree-<=2 span of live wires?

At each rotation checkpoint we take the live quantum wires and classical bits
on the all-zero HMR branch, compute a GF(2) basis of their values on a sample
of x, and test membership of each ideal fixed-point bit g_w in the span of
{1, p_i, p_i p_j}.  A negative result on a sample is a valid disproof of the
full-domain identity in this fixed feature family.
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
N_SAMPLE = 8192


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


def classify(theta: Fraction) -> str:
    if theta % Fraction(1, 2) == 0:
        return "clifford"
    if theta % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def bits_of(v: int, n: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((n + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:n]


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
    # Sample x, spread over the domain: include small and uniform values.
    rng = np.random.default_rng(20261107)
    xs = np.concatenate([np.arange(1, N_SAMPLE // 2 + 1, dtype=np.uint64),
                         rng.integers(1, MAXX + 1, N_SAMPLE // 2, dtype=np.uint64)])
    n = len(xs)
    idx = xs.astype(np.int64) - 1

    # Ideal bits on the sample from N.
    N = np.load(OUT / "N.npy")
    g = {}
    for w in range(2, 35):
        g[w] = as_int(((N[idx] >> (35 - w)) & 1).astype(np.uint8))
    print("sample", n, flush=True)

    ops = load_ops()
    q = [as_int(((xs >> j) & 1).astype(np.uint8)) for j in range(22)] + [0] * 40
    bits: dict[int, int] = {}
    stack: list[int] = []
    full = (1 << n) - 1
    results = {}

    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)

        if k == "Z_POW" and classify(Fraction(p[2])) == "rotation":
            # Live wire values (all quantum wires + defined classical bits).
            values = [q[j] & full for j in range(62)]
            values += [v & full for v in bits.values()]
            # GF(2) basis of the linear span, including the constant.
            lin_basis: dict[int, int] = {}
            add_basis(full, lin_basis)
            for v in values:
                add_basis(v, lin_basis)
            basis_list = list(lin_basis.values())
            r = len(basis_list)
            # Quadratic span: 1, p, p q.
            quad_basis: dict[int, int] = {}
            add_basis(full, quad_basis)
            for a in basis_list:
                add_basis(a, quad_basis)
            for a in range(len(basis_list)):
                va = basis_list[a]
                for b in range(a + 1, len(basis_list)):
                    add_basis(va & basis_list[b], quad_basis)
            memb = {w: in_span(t, quad_basis) for w, t in g.items()}
            results[i] = {
                "op": i, "linear_rank": r, "quadratic_rank": len(quad_basis),
                "ideal_in_quadratic_span": [w for w in g if memb[w]],
                "ideal_missing": [w for w in g if not memb[w]],
            }
            print(i, "lin", r, "quad", len(quad_basis),
                  "in", len(results[i]["ideal_in_quadratic_span"]), flush=True)

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

    (OUT / "quadratic_span_sample.json").write_text(json.dumps(
        {"n_sample": n, "sample_kind": "4096 smallest x + 4096 uniform random",
         "results": results}, indent=2) + "\n")
    total = sum(len(r["ideal_in_quadratic_span"]) for r in results.values())
    print("\ncheckpoints with any ideal bit in quadratic span:", total)
    for i, r in results.items():
        if r["ideal_in_quadratic_span"]:
            print(i, r["op"], r["ideal_in_quadratic_span"])


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"time {time.time() - t0:.1f}s")
