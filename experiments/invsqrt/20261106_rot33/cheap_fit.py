"""Greedy (OMP/IRLS) 33-term fit over a cheap-control dictionary.

Dictionary at the 41 rotation checkpoints:
  * the 41 original masks (free at their own checkpoint),
  * f_i XOR w  (free linear form),
  * f_i AND w  (one CCX),
  * w_a AND w_b for random live-wire pairs (one CCX),
  * the 33 ideal fixed-point bits as an oracle sanity check.

The fit minimises the tolerance-weighted squared error on a 4096-x sample,
then the selected 33 features are re-evaluated on all 3,133,452 x.
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
N_SAMPLE = 4096


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


def bits_of_int(v: int, n: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((n + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:n].astype(bool)


def main() -> None:
    rng = np.random.default_rng(20261110)
    xs = np.concatenate([np.arange(1, N_SAMPLE // 2 + 1, dtype=np.uint64),
                         rng.integers(1, MAXX + 1, N_SAMPLE // 2, dtype=np.uint64)])
    n = len(xs)
    idx = xs.astype(np.int64) - 1

    T = np.load(OUT / "T_units.npy")[idx].astype(np.float64) / 2**64  # turns
    tol = np.load(OUT / "tol_units.npy")[idx].astype(np.float64) / 2**64
    wgt = 1.0 / np.maximum(tol, 1e-300)
    N = np.load(OUT / "N.npy")
    g = {w: ((N[idx] >> (35 - w)) & 1).astype(bool) for w in range(2, 35)}

    md = json.loads((OUT / "masks_full.json").read_text())
    f_full = [int.from_bytes(base64.b64decode(m["mask_b64"]), "little") for m in md["masks"]]
    f_s = [bits_of_int(v, MAXX)[idx] for v in f_full]

    ops = load_ops()
    rot_ops = [i for i, (k, _, p) in enumerate(ops)
               if k == "Z_POW" and classify(Fraction(p[2])) == "rotation"]

    # Trace the sample and snapshot live wires at each rotation checkpoint.
    q = [as_int(((xs >> j) & 1).astype(np.uint8)).to_bytes((n + 7) // 8, "little") for j in range(22)]
    q = [int.from_bytes(v, "little") for v in q] + [0] * 40
    bits: dict[int, int] = {}
    stack: list[int] = []
    full = (1 << n) - 1
    snaps = {}

    def snap():
        return ([v & full for v in q], {b: v & full for b, v in bits.items()})

    for i, (k, qs, p) in enumerate(ops):
        if i in rot_ops:
            snaps[i] = snap()
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

    # Build dictionary on the sample.
    feats = []  # (definition tuple, values bool[n])
    rot_target = {op: md["targets"][k] for k, op in enumerate(md["ops"])}
    def add(defn, vals):
        if vals.any() and not vals.all():
            feats.append((defn, vals))
    for j in range(41):
        add(("orig", j), f_s[j])
    for i in rot_ops:
        wires_i, _ = snaps[i]
        wires = [bits_of_int(v, n) for v in wires_i]
        local = wires[rot_target[i]]
        # local should equal the rotation mask at this checkpoint
        for w in range(62):
            add(("xor", i, w), local ^ wires[w])
            add(("and", i, w), local & wires[w])
        for _ in range(32):
            a, b = rng.integers(0, 62, 2)
            if a != b:
                add(("pair", i, int(a), int(b)), wires[a] & wires[b])
    print("features", len(feats), flush=True)
    A = np.stack([v for _, v in feats], axis=1).astype(np.float64)  # n x d

    # OMP with weighted least squares.
    selected = []
    resid = T.copy()
    for step in range(33):
        denom = np.sqrt((A * A).T @ (wgt * wgt))
        corr = np.abs(A.T @ (wgt * wgt * resid)) / np.maximum(denom, 1e-300)
        corr[selected] = -1
        j = int(np.argmax(corr))
        selected.append(j)
        As = A[:, selected]
        W = wgt
        coef, *_ = np.linalg.lstsq(As * W[:, None], T * W, rcond=None)
        resid = T - As @ coef
        ratio = np.abs(resid) / tol
        if step % 4 == 3 or step == 32:
            print(f"step {step+1}: pick {feats[j][0]} maxratio {ratio.max():.3f}", flush=True)

    As = A[:, selected]
    coef, *_ = np.linalg.lstsq(As * wgt[:, None], T * wgt, rcond=None)
    ratio = np.abs(As @ coef - T) / tol
    print("final sample worst ratio", float(ratio.max()))
    defs = [feats[j][0] for j in selected]
    print("selected definitions:")
    for d, c in zip(defs, coef):
        print("  ", d, float(c))
    (OUT / "cheap_fit.json").write_text(json.dumps(
        {"n_sample": n, "features": len(feats),
         "selected": [{"def": d, "coef": float(c)} for d, c in zip(defs, coef)],
         "sample_worst_ratio": float(ratio.max())}, indent=2) + "\n")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("time", time.time() - t0)
