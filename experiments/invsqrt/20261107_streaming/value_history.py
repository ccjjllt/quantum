"""Full-domain value history: when was each wire's value last changed?

Bit-parallel trace over all 3,133,452 legal x on the all-zero HMR branch, up to
op 25392 (the start of the second rotation block).  For every wire we record the
ops at which its value changed.  ``available_since(w, T)`` is then the start of
the final constant run of wire w ending at T, i.e. the earliest op at which the
value that wire holds at T is already present.

Output: artifacts/20261107_streaming/value_history.json
"""
from __future__ import annotations

import json

import common

STOP = 25392


def main() -> None:
    ops, gates = common.load_ops()
    n = common.MAXX
    q = common.initial_bits(n) + [0] * (common.NQ - 22)
    full = (1 << n) - 1
    changes = [[] for _ in range(common.NQ)]
    stack: list[int] = []
    bits: dict[int, int] = {}

    def note(w, delta):
        if delta:
            changes[w].append(i)

    for i, (k, qs, p) in enumerate(gates):
        if i >= STOP:
            break
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k == "X":
            d = active
            note(qs[0], d)
            q[qs[0]] ^= d
        elif k == "CX":
            d = q[qs[0]] & active
            note(qs[1], d)
            q[qs[1]] ^= d
        elif k == "CCX":
            d = q[qs[0]] & q[qs[1]] & active
            note(qs[2], d)
            q[qs[2]] ^= d
        elif k == "SWAP":
            a, b = qs
            d = (q[a] ^ q[b]) & active
            note(a, d)
            note(b, d)
            q[a] ^= d
            q[b] ^= d
        elif k == "CSWAP":
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & q[qs[0]] & active
            note(a, d)
            note(b, d)
            q[a] ^= d
            q[b] ^= d
        elif k in {"HMR", "R"}:
            w = qs[0]
            note(w, q[w])
            q[w] = 0
            if k == "HMR":
                bits[int(p[2][1:])] = 0
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

    print("ops traced:", STOP)
    for w in range(common.NQ):
        print(f"  q{w:2d}: {len(changes[w])} value changes, last "
              f"{changes[w][-8:] if changes[w] else None}")

    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "value_history.json").write_text(json.dumps({
        "scope": "full legal domain, all-zero HMR branch, basis-state values",
        "stop": STOP,
        "changes": {f"q{w}": changes[w] for w in range(common.NQ)},
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
