"""Backward qubit-liveness with correct USE/DEF semantics (int bitmasks).

USE[o] = wires whose pre-op value can affect any post-op observable state.
DEF[o] = wires completely overwritten (pre-value irrelevant AND ... see below).
live_in = (live_out - DEF) | USE, where for reversible ops DEF is empty
(they never destroy information), and HMR/CZ/Z/R always USE their wires
(coin recorded / phase depends on values).

Sound for dead-wire removal: a never-live wire's writers can be dropped.
Conservative where noted (may miss opportunities, never wrongly removes).
"""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("artifacts/20261106_eeakernel_rewrite/liveness2.json")
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


def main():
    assert KMX is not None and KMX.exists()
    ops = []  # list of (use_mask, def_mask)
    with open(KMX) as f:
        for line in f:
            if line.startswith(("INFO_TAG", "APPEND", "REGISTER")):
                continue
            p = line.split()
            if not p or p[0] in CLASSICAL:
                continue
            o = p[0]
            if o == "X" and len(p) >= 2:
                use = qmask(p[1:2])
                ops.append((use, 0))  # reversible: nothing killed
            elif o == "HMR" and len(p) >= 2:
                use = qmask(p[1:2])
                ops.append((use, 0))  # coin recorded: pre-value always matters
            elif o == "CX" and len(p) >= 3:
                a = qmask([p[1]])
                b = qmask([p[2]])
                ops.append((a | b, 0))
            elif o == "CCX" and len(p) >= 4:
                m = qmask(p[1:4])
                ops.append((m, 0))
            elif o == "SWAP" and len(p) >= 3:
                m = qmask(p[1:3])
                ops.append((m, 0))
            elif o == "CSWAP" and len(p) >= 4:
                m = qmask(p[1:4])
                ops.append((m, 0))
            elif o in ("CZ", "Z", "Z_POW", "R", "CCZ"):
                m = qmask(p[1:])
                ops.append((m, 0))  # phases/rotations: values matter; never kill
            else:
                m = qmask(p[1:])
                ops.append((m, 0))
    print(json.dumps({"n_ops": len(ops)}), flush=True)
    ALL = (1 << 891) - 1
    live = 0
    ever = 0
    peak = 0
    peak_at = -1
    for idx in range(len(ops) - 1, -1, -1):
        use, kill = ops[idx]
        live = ((live & (ALL ^ kill)) | use) & ALL
        ever |= live
        c = bin(live).count("1")
        if c > peak:
            peak = c
            peak_at = idx
    never = [i for i in range(891) if not (ever >> i) & 1]
    out = {"n_ops": len(ops), "true_peak_live": peak, "peak_at_op": peak_at,
           "n_ever_live": bin(ever).count("1"), "never_live_wires": never,
           "alloc_qubits": 891,
           "note": "USE includes all mentioned wires (conservative); DEF empty (reversible ops never kill); HMR always uses (coin)"}
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "never_live_wires"}))
    print("never_live:", never)


if __name__ == "__main__":
    main()
