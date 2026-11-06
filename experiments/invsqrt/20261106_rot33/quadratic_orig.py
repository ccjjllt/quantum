"""Sample test: original rotation masks and ideal-bit deltas in quadratic spans.

At each rotation checkpoint, test which of the 41 original rotation control
masks are in the degree-<=2 span of the live wires, and which ideal bits g_w
differ from the local mask by a quadratic function.
"""
from __future__ import annotations

import base64
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
    rng = np.random.default_rng(20261108)
    xs = np.concatenate([np.arange(1, N_SAMPLE // 2 + 1, dtype=np.uint64),
                         rng.integers(1, MAXX + 1, N_SAMPLE // 2, dtype=np.uint64)])
    n = len(xs)
    idx = xs.astype(np.int64) - 1

    N = np.load(OUT / "N.npy")
    g = {w: as_int(((N[idx] >> (35 - w)) & 1).astype(np.uint8)) for w in range(2, 35)}

    md = json.loads((OUT / "masks_full.json").read_text())
    f = {}
    for j, m in enumerate(md["masks"]):
        full = int.from_bytes(base64.b64decode(m["mask_b64"]), "little")
        f[j] = as_int(np.unpackbits(np.frombuffer(
            full.to_bytes((MAXX + 7) // 8, "little"), dtype=np.uint8),
            bitorder="little")[:MAXX][idx])

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
            values = [q[j] & full for j in range(62)] + [v & full for v in bits.values()]
            lin_basis: dict[int, int] = {}
            add_basis(full, lin_basis)
            for v in values:
                add_basis(v, lin_basis)
            bl = list(lin_basis.values())
            quad: dict[int, int] = {}
            add_basis(full, quad)
            for a in bl:
                add_basis(a, quad)
            for a in range(len(bl)):
                for b in range(a + 1, len(bl)):
                    add_basis(bl[a] & bl[b], quad)
            local = [j for j in range(41) if f[j] == q[qs[0]] & full]
            orig_memb = [j for j in range(41) if in_span(f[j], quad)]
            # Ideal bit deltas relative to the local mask(s).
            deltas = {}
            for w, t in g.items():
                if local:
                    deltas[w] = in_span(t ^ f[local[0]], quad)
            results[i] = {
                "op": i, "local_rotation": local, "orig_in_quad": orig_memb,
                "ideal_delta_quadratic": [w for w, ok in deltas.items() if ok],
                "n_ideal_delta_quadratic": sum(deltas.values()),
            }
            print(i, "orig_in_quad", len(orig_memb), orig_memb[:8],
                  "ideal_delta", results[i]["n_ideal_delta_quadratic"], flush=True)

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

    (OUT / "quadratic_orig_sample.json").write_text(json.dumps(
        {"n_sample": n, "results": results}, indent=2) + "\n")
    print("\nsummary: checkpoint, #orig masks quadratically available, #ideal deltas quadratic")
    for i, r in results.items():
        print(i, len(r["orig_in_quad"]), r["n_ideal_delta_quadratic"])


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"time {time.time() - t0:.1f}s")
