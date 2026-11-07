"""Decompose each of the 41 fine-rotation masks into the XOR of the real taps
that the baseline circuit materialises into the rotation accumulator.

A "tap" is a single basis-permutation write into the rotation accumulator wire
(X / CX / CCX / CSWAP) between two resets of that wire.  On the all-zero HMR
branch every wire is a definite function of x, so its increment is a Boolean
function of x that we record bit-parallel over all legal x.

Verified here: XOR(taps of rotation i) == f_i from artifacts/20261106_rot33
for all 41 rotations over all 3,133,452 legal x.

Outputs (artifacts/20261107_shared_rotation/):
  taps_full.npz      distinct tap truth tables (packed uint8) + metadata
  tap_ledger.json    per-rotation tap lists, paid/free class, verification
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
ROT33 = ROOT / "artifacts/20261106_rot33"
OUT = ROOT / "artifacts/20261107_shared_rotation"
MAXX = 3_133_452
NB = (MAXX + 7) // 8
PAID = {"CCX", "CCZ", "CSWAP"}
TARGET_WIRES = (28, 50, 41, 40)   # rotation accumulator wires of the baseline


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


def main() -> None:
    t0 = time.time()
    circuit, ops, raw = load_ops()
    sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    full = (1 << MAXX) - 1

    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little")
         for j in range(22)] + [0] * (circuit.num_qubits - 22)
    pend: list[list[int]] = [[] for _ in q]
    pend_uses: list[list[dict]] = [[] for _ in q]
    tap_ids: dict[int, int] = {}
    tap_meta: list[dict] = []
    bits: dict[int, int] = {}
    stack: list[int] = []
    rotations: list[dict] = []

    def intern(v: int, op_i: int, kind: str, qs) -> int:
        if v not in tap_ids:
            tid = len(tap_meta)
            tap_ids[v] = tid
            tap_meta.append({"tap": tid, "first_op": op_i, "first_kind": kind,
                             "first_wires": list(qs), "popcount": v.bit_count(),
                             "paid_first": kind in PAID, "uses": 0})
        return tap_ids[v]

    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k == "X":
            w = qs[0]
            d = active
            t = intern(d, i, k, qs)
            pend[w].append(t); pend_uses[w].append({"op": i, "kind": k, "tap": t})
            q[w] ^= d
        elif k == "CX":
            a, w = qs
            d = q[a] & active
            t = intern(d, i, k, qs)
            pend[w].append(t); pend_uses[w].append({"op": i, "kind": k, "tap": t})
            q[w] ^= d
        elif k == "CCX":
            a, b, w = qs
            d = q[a] & q[b] & active
            t = intern(d, i, k, qs)
            pend[w].append(t); pend_uses[w].append({"op": i, "kind": k, "tap": t})
            q[w] ^= d
        elif k == "SWAP":
            a, b = qs
            d = (q[a] ^ q[b]) & active
            q[a] ^= d
            q[b] ^= d
            pend[a], pend[b] = pend[b], pend[a]
            pend_uses[a], pend_uses[b] = pend_uses[b], pend_uses[a]
        elif k == "CSWAP":
            c_, a, b = qs
            d = (q[a] ^ q[b]) & q[c_] & active
            t = intern(d, i, k, qs)
            pend[a].append(t); pend_uses[a].append({"op": i, "kind": k, "tap": t})
            pend[b].append(t); pend_uses[b].append({"op": i, "kind": k, "tap": t})
            q[a] ^= d
            q[b] ^= d
        elif k in {"HMR", "R"}:
            w = qs[0]
            if k == "HMR":
                bits[int(p[2][1:])] = 0
            q[w] = 0
            pend[w] = []
            pend_uses[w] = []
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
            if theta % Fraction(1, 2) != 0 and theta % Fraction(1, 4) != 0:
                rotations.append({
                    "rot": len(rotations), "op": i, "wire": qs[0], "theta": p[2],
                    "theta_units63": int(round(theta * (1 << 63))),
                    "tap_list": list(pend[qs[0]]),
                    "tap_uses": list(pend_uses[qs[0]]),
                    "target_value_popcount": q[qs[0]].bit_count(),
                })
        elif k in {"Z", "CZ", "CCZ", "NEG"}:
            pass
        else:
            raise ValueError((i, k, p))
    assert not stack
    assert len(rotations) == 41, len(rotations)
    print(f"trace done {time.time()-t0:.1f}s distinct taps={len(tap_meta)}", flush=True)

    data = json.loads((ROT33 / "masks_full.json").read_text())
    ref = []
    for m in data["masks"]:
        v = int.from_bytes(base64.b64decode(m["mask_b64"]), "little")
        ref.append(np.unpackbits(np.frombuffer(v.to_bytes(NB, "little"), dtype=np.uint8),
                                 bitorder="little")[:MAXX].astype(bool))
    del data
    id_to_int = {v: kk for kk, v in tap_ids.items()}
    tap_tt: dict[int, np.ndarray] = {}

    def tt(tid):
        if tid not in tap_tt:
            v = id_to_int[tid]
            tap_tt[tid] = np.unpackbits(np.frombuffer(v.to_bytes(NB, "little"), dtype=np.uint8),
                                        bitorder="little")[:MAXX].astype(bool)
        return tap_tt[tid]

    ok = True
    for r in rotations:
        x = np.zeros(MAXX, dtype=bool)
        for tid in r["tap_list"]:
            x ^= tt(tid)
        r["xor_matches_mask"] = bool(np.array_equal(x, ref[r["rot"]]))
        r["xor_popcount"] = int(x.sum())
        r["mask_popcount"] = int(ref[r["rot"]].sum())
        ok &= r["xor_matches_mask"]
    print("all XOR(taps)==mask:", ok, flush=True)
    for r in rotations:
        if not r["xor_matches_mask"]:
            print("  MISMATCH rot", r["rot"], r["xor_popcount"], r["mask_popcount"],
                  [(t, tap_meta[t]["first_kind"], tap_meta[t]["popcount"]) for t in r["tap_list"]])

    for r in rotations:
        for tid in r["tap_list"]:
            tap_meta[tid]["uses"] += 1

    order = sorted(tap_tt)
    packed = np.stack([np.packbits(tap_tt[t], bitorder="little") for t in order])
    np.savez_compressed(OUT / "taps_full.npz", taps=packed,
                        ids=np.array(order, dtype=np.int32))
    ledger = {
        "baseline": str(BASE.relative_to(ROOT)), "sha256": sha,
        "domain": "x=1..3133452", "hmr_branch": "all outcomes 0",
        "n_rotations": len(rotations),
        "n_distinct_taps": len(tap_meta),
        "total_tap_uses": sum(len(r["tap_list"]) for r in rotations),
        "all_xor_match": bool(ok),
        "tap_meta": tap_meta,
        "rotations": rotations,
    }
    (OUT / "tap_ledger.json").write_text(json.dumps(ledger, indent=1) + "\n")
    print(f"distinct taps {len(tap_meta)} total uses {ledger['total_tap_uses']} "
          f"{time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
