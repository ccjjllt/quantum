"""Full-domain test: are the 33 ideal phase bits linear forms of live wires?

At each of the 41 rotation checkpoints the circuit state is a basis state on
the all-zero HMR branch.  Any XOR of the current quantum wires and classical
bits is free to load with CX gates.  This script tests, exactly on all
3,133,452 legal x, whether each of the 33 ideal fixed-point bits g_w is in the
GF(2) span of the live wires at that checkpoint.
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


def initial_bits(xs: np.ndarray) -> list[int]:
    return [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8),
                                       bitorder="little").tobytes(), "little")
            for j in range(22)]


def classify(theta: Fraction) -> str:
    if theta % Fraction(1, 2) == 0:
        return "clifford"
    if theta % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def reduce_to_basis(v: int, basis: dict[int, int]) -> int:
    while v:
        p = v.bit_length() - 1
        if p not in basis:
            return v
        v ^= basis[p]
    return 0


def add_basis(v: int, basis: dict[int, int]) -> None:
    while v:
        p = v.bit_length() - 1
        if p not in basis:
            basis[p] = v
            return
        v ^= basis[p]


def main() -> None:
    # Load the ideal bits.
    z = np.load(OUT / "g_bits.npz")
    weights = list(range(2, 35))
    g = {}
    for w in weights:
        packed = z[f"w{w}"]
        g[w] = int.from_bytes(packed.tobytes(), "little")
    print("loaded", len(g), "ideal bits", flush=True)

    ops = load_ops()
    n_ops = len(ops)
    rot_ops = [i for i, (k, _, p) in enumerate(ops)
               if k == "Z_POW" and classify(Fraction(p[2])) == "rotation"]
    print("rotation checkpoints", len(rot_ops), flush=True)
    fmasks = [int.from_bytes(base64.b64decode(m["mask_b64"]), "little")
              for m in json.loads((OUT / "masks_full.json").read_text())["masks"]]

    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    q = initial_bits(xs) + [0] * 40
    bits: dict[int, int] = {}
    stack: list[int] = []
    full = (1 << MAXX) - 1
    results = {}

    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)

        if k == "Z_POW" and classify(Fraction(p[2])) == "rotation":
            # Test membership at this checkpoint.
            wires = {f"q{j}": q[j] & full for j in range(62)}
            for b, v in bits.items():
                wires[f"b{b}"] = v & full
            # Drop constant-zero and constant-full wires from the basis but
            # keep the full mask as the constant term for affine span.
            basis: dict[int, int] = {}
            add_basis(full, basis)  # constant term
            for name, v in wires.items():
                add_basis(v, basis)
            memb = {}
            for w, tgt in g.items():
                memb[w] = reduce_to_basis(tgt, basis) == 0
            # Which original rotation masks are in the span here?
            orig = {}
            for j, vv in enumerate(fmasks):
                orig[j] = reduce_to_basis(vv, basis) == 0
            results[i] = {
                "op": i,
                "quantum_wires": 62,
                "classical_bits": len(bits),
                "rank_including_constant": len(basis),
                "ideal_bits_in_span": [w for w in weights if memb[w]],
                "ideal_bits_missing": [w for w in weights if not memb[w]],
                "original_masks_in_span": [j for j in orig if orig[j]],
            }
            print(i, "rank", len(basis), "ideal", len(results[i]["ideal_bits_in_span"]),
                  "orig", len(results[i]["original_masks_in_span"]), flush=True)

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

    (OUT / "linear_span.json").write_text(json.dumps(results, indent=2) + "\n")
    # Summary table.
    print("\ncheckpoint  rank  #ideal  #orig  ideal weights")
    for i, r in results.items():
        print(f"{i:5d} {r['rank_including_constant']:5d} {len(r['ideal_bits_in_span']):5d} "
              f"{len(r['original_masks_in_span']):5d}  {r['ideal_bits_in_span']}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"time {time.time() - t0:.1f}s")
