"""Extract the fine-rotation phase masks of the Syed V9 baseline.

The circuit is a phase-polynomial circuit: X/CX/CCX/SWAP/CSWAP are basis
permutations, Z/CZ/CCZ/NEG/Z_POW are diagonal, and HMR/R measure and reset.
On a shot with fixed HMR outcomes every wire is therefore in a computational
basis state, and a Z_POW on wire w contributes theta * w.  This script traces
bit-parallel over a list of x values and records the control-wire truth table
of all 41 fine rotations.

Outputs (artifacts/20261106_rot33/):
  masks_full.json     metadata + masks over all legal x (all-zero HMR branch)
  masks_sample.json   metadata + masks over a 65536-x sample
  branch_compare.json masks for two nonzero HMR branches on a small sample
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452

PAID = {"CCX", "CCZ", "CSWAP"}


def load_ops(path: Path):
    circuit = km.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    raw = [line for line in buf.getvalue().splitlines()
           if not line.startswith(("APPEND", "REGISTER"))]
    ops = []
    for line in raw:
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return circuit, ops, raw


def classify(theta: Fraction) -> str:
    if theta % Fraction(1, 2) == 0:
        return "clifford"
    if theta % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def initial_bits(xs: np.ndarray) -> list[int]:
    """Bit-parallel x register: wire j holds bit j of every x."""
    n = len(xs)
    out = []
    for j in range(22):
        packed = np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little")
        out.append(int.from_bytes(packed.tobytes(), "little"))
    return out


def trace(ops, n: int, xs: np.ndarray | None = None, *, hmr_bits=None,
          stop_at_rotation: bool = False, record_wires_at_rotations: bool = False):
    """Run bit-parallel over n shots.

    hmr_bits: optional list of Python ints, one per HMR instruction, giving the
    outcome bitmask over the n shots.  None means outcome 0 everywhere.
    Returns rotation records (control mask, angle, op index, target) and
    optionally the full wire/classical-bit state at every rotation.
    """
    q = initial_bits(xs) + [0] * (62 - 22)
    bits: dict[int, int] = {}
    stack: list[int] = []
    full = (1 << n) - 1
    hmr_index = 0
    rotations = []
    snapshots = []

    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
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
                d = (q[a] ^ q[b]) & q[qs[0]] & active
                q[a] ^= d
                q[b] ^= d
        elif k == "HMR":
            b = int(p[2][1:])
            bits[b] = 0 if hmr_bits is None else hmr_bits[hmr_index]
            hmr_index += 1
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
        elif k == "Z_POW":
            theta = Fraction(p[2])
            if classify(theta) == "rotation":
                mask = q[qs[0]] & active
                rotations.append({"op": i, "wire": qs[0], "theta": p[2],
                                  "theta_fraction": theta, "mask": mask})
                if record_wires_at_rotations:
                    snapshots.append({"op": i, "q": list(q), "bits": dict(bits),
                                      "stack": list(stack)})
        elif k in {"Z", "CZ", "CCZ", "NEG"}:
            pass
        else:
            raise ValueError((i, k, p))
    assert not stack
    return rotations, snapshots


def masks_to_json(rotations, n):
    return [{"op": r["op"], "wire": r["wire"], "theta": r["theta"],
             "mask_b64": _int_b64(r["mask"], n),
             "popcount": r["mask"].bit_count()} for r in rotations]


def _int_b64(v: int, n: int) -> str:
    import base64
    return base64.b64encode(v.to_bytes((n + 7) // 8, "little")).decode()


def main() -> None:
    t0 = time.time()
    circuit, ops, raw = load_ops(BASE)
    sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    print(f"ops={len(ops)} sha={sha[:16]}", flush=True)

    # Count classes.
    counts = {"clifford": 0, "t": 0, "rotation": 0}
    for k, qs, p in ops:
        if k == "Z_POW":
            counts[classify(Fraction(p[2]))] += 1
    print("Z_POW classes", counts, flush=True)
    assert counts["rotation"] == 41

    # Full legal domain, all-zero HMR branch.
    xs_all = np.arange(1, MAXX + 1, dtype=np.uint64)
    t1 = time.time()
    rots_all, _ = trace(ops, MAXX, xs_all, hmr_bits=None)
    print(f"full trace {time.time() - t1:.1f}s", flush=True)
    meta = {"baseline": str(BASE.relative_to(ROOT)), "sha256": sha,
            "domain": "x=1..3133452", "hmr_branch": "all outcomes 0",
            "num_rotations": len(rots_all),
            "angles_half_turns": [r["theta"] for r in rots_all],
            "targets": [r["wire"] for r in rots_all],
            "ops": [r["op"] for r in rots_all]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "masks_full.json").write_text(json.dumps(
        {**meta, "masks": masks_to_json(rots_all, MAXX)}, indent=1) + "\n")

    # 65536-x sample for later feature work.
    rng = np.random.default_rng(20261106)
    xs_s = np.concatenate([np.arange(1, 32769, dtype=np.uint64),
                           rng.integers(1, MAXX + 1, 32768, dtype=np.uint64)])
    rots_s, snaps = trace(ops, len(xs_s), xs_s, hmr_bits=None,
                          record_wires_at_rotations=True)
    (OUT / "masks_sample.json").write_text(json.dumps(
        {**meta, "domain": "32768 smallest x + 32768 uniform random x",
         "xs": [int(v) for v in xs_s],
         "masks": masks_to_json(rots_s, len(xs_s))}, indent=1) + "\n")

    # Two nonzero HMR branches on 4096 x, to test branch dependence of f_i.
    n_b = 4096
    xs_b = np.arange(1, n_b + 1, dtype=np.uint64)
    branches = {}
    n_hmr = sum(1 for k, _, _ in ops if k == "HMR")
    for seed in (1, 2):
        rr = random.Random(seed)
        hb = [rr.getrandbits(n_b) for _ in range(n_hmr)]
        rots_b, _ = trace(ops, n_b, xs_b, hmr_bits=hb)
        branches[f"random_seed_{seed}"] = [r["mask"].bit_count() for r in rots_b]
        # XOR distance from all-zero branch on the same x range.
        if seed == 1:
            zero_b, _ = trace(ops, n_b, xs_b, hmr_bits=None)
            branches["xor_distance_vs_zero"] = [
                (a["mask"] ^ b["mask"]).bit_count() for a, b in zip(zero_b, rots_b)]
    (OUT / "branch_compare.json").write_text(json.dumps(
        {"n": n_b, "branches": branches,
         "note": "popcounts of control masks on nonzero HMR branches; xor_distance "
                 "is the number of x in 1..4096 where the mask differs from the "
                 "all-zero branch"}, indent=2) + "\n")

    print(f"total {time.time() - t0:.1f}s", flush=True)
    print(json.dumps({"rotations": len(rots_all),
                      "popcounts_min": min(r["mask"].bit_count() for r in rots_all),
                      "popcounts_max": max(r["mask"].bit_count() for r in rots_all),
                      "branch": branches}, indent=2)[:3000])


if __name__ == "__main__":
    main()
