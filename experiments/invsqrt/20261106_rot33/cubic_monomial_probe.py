"""Support-aware probe for single quadratic/cubic monomials of live wires.

The previous random 4096-x sample was vacuous for sparse masks (a mask with
support 114 is almost surely all-zero on 4096 random x, so any all-zero
product matches).  This version includes the full support of the sparse
targets plus a random sample, and verifies any hit on all 3,133,452 x.
"""
from __future__ import annotations

import base64
import io
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = []
    for line in buf.getvalue().splitlines():
        if line.startswith(("APPEND", "REGISTER")):
            continue
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return ops


def classify(t: Fraction) -> str:
    if t % Fraction(1, 2) == 0:
        return "clifford"
    if t % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def as_int(a):
    return int.from_bytes(np.packbits(a.astype(np.uint8), bitorder="little").tobytes(), "little")


def unpack(v: int):
    return np.unpackbits(np.frombuffer(v.to_bytes((MAXX + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:MAXX].astype(bool)


def main() -> None:
    md = json.loads((OUT / "masks_full.json").read_text())
    fmask = [int.from_bytes(base64.b64decode(m["mask_b64"]), "little") for m in md["masks"]]
    fbool = [unpack(v) for v in fmask]
    # Include full support of the sparse targets (indices 36..40) and a random sample.
    support = np.zeros(0, dtype=np.int64)
    for j in (36, 37, 38, 39, 40):
        support = np.union1d(support, np.flatnonzero(fbool[j]))
    rng = np.random.default_rng(20261115)
    rand = rng.integers(1, MAXX + 1, 8192, dtype=np.int64)
    xs = np.union1d(support + 1, rand).astype(np.uint64)
    N = len(xs)
    print("sample", N, "sparse support points", len(support), flush=True)
    idx = xs.astype(np.int64) - 1

    def sample_mask(j):
        return as_int(fbool[j][idx])

    ops = load_ops()
    rot_ops = [i for i, (k, _, p) in enumerate(ops)
               if k == "Z_POW" and classify(Fraction(p[2])) == "rotation"]
    checkpoints = {14: rot_ops[14], 40: rot_ops[40]}
    targets = {14: list(range(33, 41)), 40: list(range(0, 8))}

    q = [as_int(((xs >> j) & 1).astype(np.uint8)) for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    full = (1 << N) - 1
    results = {}

    def test_at(cp, local_targets):
        values = [v & full for v in q] + [v & full for v in bits.values()]
        names = [f"q{j}" for j in range(62)] + [f"b{b}" for b in bits]
        uniq = {}
        for n, v in zip(names, values):
            if v and v != full:
                uniq.setdefault(v, n)
        vals = list(uniq)
        nm = [uniq[v] for v in vals]
        tg = {j: sample_mask(j) for j in local_targets}
        out = {"checkpoint_rot": cp, "live_nonconstant": len(vals),
               "n_sample": N, "targets": local_targets, "hits": []}
        # linear and pair products
        for i, a in enumerate(vals):
            for j, t in tg.items():
                if a == t:
                    out["hits"].append({"kind": "linear", "target": j, "wires": [nm[i]]})
            for j2 in range(i + 1, len(vals)):
                p = a & vals[j2]
                for j, t in tg.items():
                    if p == t:
                        out["hits"].append({"kind": "quadratic", "target": j,
                                            "wires": [nm[i], nm[j2]]})
        # single triple products
        for i, a in enumerate(vals):
            for j2 in range(i + 1, len(vals)):
                ab = a & vals[j2]
                for k in range(j2 + 1, len(vals)):
                    p = ab & vals[k]
                    for j, t in tg.items():
                        if p == t:
                            out["hits"].append({"kind": "cubic", "target": j,
                                                "wires": [nm[i], nm[j2], nm[k]]})
        out["n_hits"] = len(out["hits"])
        results[str(cp)] = out
        print(cp, "live", len(vals), "hits", out["n_hits"],
              out["hits"][:5], flush=True)

    for k, (kk, qs, p) in enumerate(ops):
        if k in checkpoints.values():
            cp = [c for c, op in checkpoints.items() if op == k][0]
            test_at(cp, targets[cp])
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if kk == "X":
            q[qs[0]] ^= active
        elif kk == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif kk == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif kk == "SWAP":
            a, b = qs
            d = (q[a] ^ q[b]) & active
            q[a] ^= d
            q[b] ^= d
        elif kk == "CSWAP":
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & q[qs[0]] & active
            q[a] ^= d
            q[b] ^= d
        elif kk == "HMR":
            bits[int(p[2][1:])] = 0
            q[qs[0]] = 0
        elif kk == "R":
            q[qs[0]] = 0
        elif kk in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = old & ~active if kk == "BIT_STORE0" else old | active if kk == "BIT_STORE1" else old ^ active
        elif kk == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif kk == "POP_CONDITION":
            stack.pop()
        elif kk in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((k, kk, p))
    (OUT / "cubic_monomial_probe_support.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
