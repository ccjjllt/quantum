"""Per-x concrete simulation of one prefix of the baseline (diagnostic).

Usage:
  python sim_x.py X START END [--random-branch SEED]

Prints the value of every wire after each operation in [START, END) whose value
changed, plus classical bits.  HMR outcomes are 0 unless --random-branch is given.
"""
from __future__ import annotations

import argparse

import common


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("x", type=int)
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("--random-branch", type=int, default=None)
    args = ap.parse_args()

    import random
    rng = random.Random(args.random_branch)

    ops, gates = common.load_ops()
    q = [0] * common.NQ
    for j in range(22):
        q[j] = (args.x >> j) & 1
    bits: dict[int, int] = {}
    stack: list[int] = []
    prev = None
    for i, (k, qs, p) in enumerate(gates):
        if i >= args.end:
            break
        active = 1
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
            if active:
                q[a], q[b] = q[b], q[a]
        elif k == "CSWAP":
            a, b = qs[-2:]
            if active and q[qs[0]]:
                q[a], q[b] = q[b], q[a]
        elif k == "HMR":
            b = int(p[2][1:])
            bits[b] = 0 if args.random_branch is None else rng.getrandbits(1)
            q[qs[0]] = 0
        elif k == "R":
            q[qs[0]] = 0
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = (old & (1 - active) if k == "BIT_STORE0"
                       else old | active if k == "BIT_STORE1" else old ^ active)
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, k, p))
        if i >= args.start:
            cur = (tuple(q), tuple(sorted(bits.items())))
            if prev is None:
                print(f"{i:6d} {' '.join(p)}")
                print("        wires:", "".join(str(v) for v in q))
                print("        nonz :", [w for w in range(common.NQ) if q[w]])
                prev = cur
            elif cur != prev:
                print(f"{i:6d} {' '.join(p)}")
                print("        wires:", "".join(str(v) for v in q))
                print("        nonz :", [w for w in range(common.NQ) if q[w]])
                prev = cur


if __name__ == "__main__":
    main()
