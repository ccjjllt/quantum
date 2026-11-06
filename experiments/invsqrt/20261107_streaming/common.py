"""Shared read-only helpers for the streaming investigation of the invsqrt baseline."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261107_streaming"
ROT33 = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452
NQ = 62


def load_ops(path: Path = BASE):
    """Return (ops, gates): ops[i] raw KMX line (register decls removed),
    gates[i] = (kind, [qubit indices], token list)."""
    circuit = km.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines()
           if not l.startswith(("APPEND", "REGISTER"))]
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p)
             for p in map(str.split, ops)]
    return ops, gates


def initial_bits(n: int) -> list[int]:
    """Bit-parallel x register over x = 1..n: wire j holds bit j of every x."""
    a = np.arange(1, n + 1, dtype=np.uint64)
    out = []
    for j in range(22):
        packed = np.packbits(((a >> np.uint64(j)) & 1).astype(np.uint8),
                             bitorder="little")
        out.append(int.from_bytes(packed.tobytes(), "little"))
    return out


def packbits_np(mask: int, n: int) -> np.ndarray:
    return np.unpackbits(
        np.frombuffer(mask.to_bytes((n + 7) // 8, "little"), dtype=np.uint8),
        bitorder="little")[:n]


def int_from_b64(s: str) -> int:
    return int.from_bytes(base64.b64decode(s), "little")


def load_masks_full():
    """The 41 fine-rotation masks over x=1..MAXX from the rot33 extraction."""
    data = json.loads((ROT33 / "masks_full.json").read_text())
    masks = [int_from_b64(m["mask_b64"]) for m in data["masks"]]
    ops = [m["op"] for m in data["masks"]]
    wires = [m["wire"] for m in data["masks"]]
    angles = data["angles_half_turns"]
    return masks, ops, wires, angles


def trace_checkpoints(gates, checkpoints: set[int], n: int = MAXX):
    """Bit-parallel basis-state trace on the all-zero HMR branch.

    Returns cp_state[op] = list of 62 wire masks (value as function of x) with the
    *pre-gate* state at that op index, and hv[op] = list of masks touched at op
    (for structure diagnostics).
    """
    q = initial_bits(n) + [0] * (NQ - 22)
    mask = (1 << n) - 1
    stack: list[int] = []
    bits: dict[int, int] = {}
    state: dict[int, list[int]] = {}
    touched: dict[int, list[int]] = {}
    for i, (k, qs, p) in enumerate(gates):
        if i in checkpoints:
            state[i] = list(q)
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if i in checkpoints:
            touched[i] = [int(w[1:]) for w in p[1:] if w.startswith("q")]
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
            bits[b] = (old & ~active if k == "BIT_STORE0"
                       else old | active if k == "BIT_STORE1" else old ^ active)
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, k, p))
    return state, touched


def describe(mask: int, n: int = MAXX) -> dict:
    return {"popcount": int(mask.bit_count()), "of": n}
