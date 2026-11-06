"""Backward liveness with int bitmasks (fast). Read-only; no verifier."""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("artifacts/20261106_eeakernel_rewrite/liveness.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

CLASSICAL = {"INFO_TAG", "APPEND", "REGISTER", "BIT_STORE0", "BIT_STORE1",
             "NEG", "PUSH_CONDITION", "POP_CONDITION"}


def qmask(tokens):
    m = 0
    for t in tokens:
        if t.startswith("q"):
            try:
                m |= (1 << int(t[1:]))
            except ValueError:
                pass
    return m


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
            o = p[0]
            if o == "X" and len(p) >= 2:
                r, w = 0, qmask(p[1:2])
            elif o == "HMR" and len(p) >= 2:
                m = qmask(p[1:2])
                r, w = m, m
            elif o == "CX" and len(p) >= 3:
                a = qmask([p[1]])
                b = qmask([p[2]])
                r, w = a, b
            elif o == "CCX" and len(p) >= 4:
                a = qmask([p[1]])
                b = qmask([p[2]])
                t = qmask([p[3]])
                r, w = a | b, t
            elif o in ("CZ", "Z", "Z_POW"):
                m = 0
                for t in p[1:]:
                    if t.startswith("q"):
                        try:
                            m |= 1 << int(t[1:])
                        except ValueError:
                            pass
                r, w = m, 0
            elif o == "CCZ" and len(p) >= 4:
                m = 0
                for t in p[1:4]:
                    if t.startswith("q"):
                        try:
                            m |= 1 << int(t[1:])
                        except ValueError:
                            pass
                r, w = m, 0
            elif o == "SWAP" and len(p) >= 3:
                m = 0
                for t in p[1:3]:
                    if t.startswith("q"):
                        try:
                            m |= 1 << int(t[1:])
                        except ValueError:
                            pass
                r, w = m, m
            elif o == "CSWAP" and len(p) >= 4:
                ma = qmask([p[1]])
                mb = qmask(p[2:3])
                r, w = ma | mb, mb
            elif o == "R" and len(p) >= 2:
                m = qmask(p[1:2])
                r, w = m, m
            else:
                m = qmask(p[1:])
                r, w = m, m
            ops.append((r, w))
    print(json.dumps({"n_ops": len(ops)}), flush=True)
    live = 0
    ever = 0
    peak = 0
    peak_at = -1
    ALL = (1 << 891) - 1
    for idx in range(len(ops) - 1, -1, -1):
        r, w = ops[idx]
        live = ((live & (ALL ^ w)) | r) & ALL
        ever |= live
        c = bin(live).count("1")
        if c > peak:
            peak = c
            peak_at = idx
    never = [i for i in range(891) if not (ever >> i) & 1]
    out = {"n_ops": len(ops), "true_peak_live": peak, "peak_at_op": peak_at,
           "n_ever_live": bin(ever).count("1"), "never_live_wires": never,
           "alloc_qubits": 891}
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
