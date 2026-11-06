"""Scan deletion of unconditional paid gates whose product is rare on legal x.

The support is computed on the all-zero HMR branch over all legal x.  Gates with
0 < support < 200 are deleted one at a time and checked with the official
verifier on a small x prefix first.  A PASS there is only a filter; the full
verification is run separately for survivors.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_rare_gate_scan"
VERIFIER_DIR = ROOT / "data/competition/verifiers"
MAXX = 3_133_452
PAID = {"CCX", "CCZ", "CSWAP"}


def load():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return c, [l for l in lines if l.startswith(("APPEND", "REGISTER"))], [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def rare_gates(ops):
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    mask = (1 << MAXX) - 1
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    rare = []
    for i, (k, qs, p) in enumerate(gates):
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k in PAID:
            if k == "CCX":
                prod = q[qs[0]] & q[qs[1]] & active
            elif k == "CCZ":
                prod = q[qs[0]] & q[qs[1]] & q[qs[2]] & active
            else:
                prod = q[qs[0]] & (q[qs[1]] ^ q[qs[2]]) & active
            n = prod.bit_count()
            if 0 < n < 200 and active == mask:
                rare.append({"op": i, "gate": ops[i], "support": n})
        if k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif k in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & active
            if k == "CSWAP":
                d &= q[qs[0]]
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = bits.get(int(p[2][1:]), 0) & ~active
            q[qs[0]] &= ~active
        elif k == "R":
            q[qs[0]] &= ~active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            bid = int(p[1][1:])
            old = bits.get(bid, 0)
            bits[bid] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, p))
    return rare


def make_candidate(header, ops, delete_op):
    out = ops[:delete_op] + ops[delete_op + 1:]
    c = km.Circuit.from_file(io.StringIO("\n".join(header + out) + "\n"), format="kmx")
    path = OUT / f"delete_{delete_op}.kmb"
    c.to_file(path, format="kmb")
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _, header, ops = load()
    rare = rare_gates(ops)
    print("rare gates", len(rare), flush=True)
    results = []
    for r in rare:
        path = make_candidate(header, ops, r["op"])
        cmd = [sys.executable, "-m", "invsqrt.verify_submission_invsqrt", str(path),
               "--max-x", "4096", "--shots-per-x", "1", "--salt", "rare-scan"]
        env = {"PYTHONPATH": str(VERIFIER_DIR), "PATH": "/usr/bin:/bin"}
        proc = subprocess.run(cmd, cwd=ROOT, env={**env}, capture_output=True, text=True)
        ok = proc.returncode == 0 and '"status": "PASS"' in proc.stdout
        row = {**r, "small_pass": ok, "stdout": proc.stdout[-500:], "stderr": proc.stderr[-300:]}
        results.append(row)
        print(r["op"], r["gate"], r["support"], "PASS" if ok else "FAIL", flush=True)
        path.unlink(missing_ok=True)
    (OUT / "small_scan.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"total": len(results), "pass": [r for r in results if r["small_pass"]]}, indent=2))


if __name__ == "__main__":
    main()
