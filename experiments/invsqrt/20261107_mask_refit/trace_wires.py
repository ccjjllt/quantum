"""Trace all wire values at the 41 fine-rotation checkpoints (full legal x).

For each rotation i (the Z_POW op) the state of all 62 wires just before the
gate is saved as packed bits (bit j = x=j+1).  Output:
artifacts/20261107_mask_refit/wires/cp_XX.npz  (keys w0..w61, uint8 packed)

Also writes checkpoint_meta.json with op indices / targets / angles.
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
OUT = ROOT / "artifacts/20261107_mask_refit"
MAXX = 3_133_452
NB = (MAXX + 7) // 8


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    raw = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    ops = []
    for line in raw:
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return c, ops, raw


def is_rotation(theta: Fraction) -> bool:
    return theta % Fraction(1, 2) != 0 and theta % Fraction(1, 4) != 0


def main() -> None:
    t0 = time.time()
    c, ops, raw = load_ops()
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little")
         for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    full = (1 << MAXX) - 1
    outdir = OUT / "wires"
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {"baseline": str(BASE.relative_to(ROOT)), "domain": "x=1..3133452",
            "hmr_branch": "all outcomes 0", "checkpoints": []}
    rot_i = 0
    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k == "Z_POW":
            theta = Fraction(p[2])
            if is_rotation(theta):
                arrs = {f"w{j}": np.frombuffer(v.to_bytes(NB, "little"), dtype=np.uint8).copy()
                        for j, v in enumerate(q)}
                np.savez(outdir / f"cp_{rot_i:02d}.npz", **arrs)
                meta["checkpoints"].append({
                    "rot": rot_i, "op": i, "wire": qs[0], "theta": p[2],
                    "popcounts": [v.bit_count() for v in q],
                })
                print(f"cp {rot_i:2d} op {i} q{qs[0]} saved {time.time()-t0:.1f}s", flush=True)
                rot_i += 1
            continue
        if k in {"X", "CX", "CCX", "SWAP", "CSWAP"}:
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
            else:
                a, b = qs[-2:]
                d = (q[a] ^ q[b]) & active & q[qs[0]]
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
        elif k in {"Z", "CZ", "CCZ", "NEG"}:
            pass
        else:
            raise ValueError((i, k, p))
    assert not stack
    assert rot_i == 41, rot_i
    (OUT / "checkpoint_meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"total {time.time()-t0:.1f}s; rot={rot_i}")


if __name__ == "__main__":
    main()
