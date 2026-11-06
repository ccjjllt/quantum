"""Backward qubit-liveness with correct conditional USE rules.

CCX(a,b,t): if t live: add {a,b} (t stays). Else no change.
CX(a,b): if b live: add a. Else no change.
X: no-op. HMR(w): always add w (coin recorded).
SWAP(a,b): if either live: add both.
CSWAP(a,b,t): if b or t live: add {a,b,t}.
CZ/Z/R/CCZ/unknown-with-q: add involved wires (conservative for phases).
Classical/structural: ignore.
Sound for dead-wire removal (may miss opportunities, never wrongly removes).
"""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("artifacts/20261106_eeakernel_rewrite/liveness3.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

CLASSICAL = {"INFO_TAG", "APPEND", "REGISTER", "BIT_STORE0", "BIT_STORE1",
             "NEG", "PUSH_CONDITION", "POP_CONDITION"}


def qmask(tokens):
    m = 0
    for t in tokens:
        if t.startswith("q"):
            try:
                m |= 1 << int(t[1:])
            except ValueError:
                pass
    return m


def has_bit(s, i):
    return (s >> i) & 1


def main():
    assert KMX is not None and KMX.exists()
    ops = []
    with open(KMX) as f:
        for line in f:
            if line.startswith(("INFO_TAG", "APPEND", "REGISTER")):
                continue
            p = line.split()
            if not p or p[0] in CLASSICAL:
                continue
            ops.append(p)
    print(json.dumps({"n_ops": len(ops)}), flush=True)
    live = 0
    ever = 0
    peak = 0
    peak_at = -1
    for idx in range(len(ops) - 1, -1, -1):
        p = ops[idx]
        o = p[0]
        if o == "X":
            pass
        elif o == "HMR":
            w = qmask(p[1:2])
            live |= w
        elif o == "CX":
            a = qmask([p[1]])
            b = qmask([p[2]])
            if live & b:
                live |= a
        elif o == "CCX":
            a = qmask([p[1]])
            b = qmask([p[2]])
            t = qmask([p[3]])
            if live & t:
                live |= a | b
        elif o == "SWAP":
            m = qmask(p[1:3])
            if live & m:
                live |= m
        elif o == "CSWAP":
            a = qmask([p[1]])
            bt = qmask(p[2:4])
            if live & bt:
                live |= a | bt
        elif o in ("CZ", "Z", "Z_POW", "R", "CCZ"):
            live |= qmask(p[1:])
        else:
            live |= qmask(p[1:])
        ever |= live
        c = bin(live).count("1")
        if c > peak:
            peak = c
            peak_at = idx
    never = [i for i in range(891) if not (ever >> i) & 1]
    out = {"n_ops": len(ops), "true_peak_live": peak, "peak_at_op": peak_at,
           "n_ever_live": bin(ever).count("1"), "never_live_wires": never,
           "alloc_qubits": 891,
           "note": "conditional USE (reversible ops add only when output live); HMR/CZ/Z/R always add; sound for dead-wire removal"}
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "never_live_wires"}))
    print("never_live:", never)


if __name__ == "__main__":
    main()
