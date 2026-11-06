"""Backward qubit-liveness over the full DQI kmx. Finds true peak live count
and never-read wires. Read-only; no verifier run."""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("artifacts/20261106_qq51_count/liveness.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

CLASSICAL = {"INFO_TAG", "APPEND", "REGISTER", "BIT_STORE0", "BIT_STORE1",
             "NEG", "PUSH_CONDITION", "POP_CONDITION"}


def qnum(tok):
    if tok.startswith("q"):
        try:
            return int(tok[1:])
        except ValueError:
            return None
    return None


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
            args = [qnum(t) for t in p[1:]]
            args = [a for a in args if a is not None]
            if o == "X" and args:
                r, w = set(), {args[0]}
            elif o == "HMR" and args:
                r, w = {args[0]}, {args[0]}
            elif o == "CX" and len(args) >= 2:
                r, w = {args[0]}, {args[1]}
            elif o == "CCX" and len(args) >= 3:
                r, w = {args[0], args[1]}, {args[2]}
            elif o in ("CZ", "Z", "Z_POW") and args:
                r, w = set(args), set()
            elif o == "CCZ" and len(args) >= 3:
                r, w = set(args[:3]), set()
            elif o == "SWAP" and len(args) >= 2:
                r, w = set(args[:2]), set(args[:2])
            elif o == "CSWAP" and len(args) >= 3:
                r, w = set(args[:3]), {args[1], args[2]}
            elif o == "R" and args:
                r, w = {args[0]}, {args[0]}
            else:
                r, w = set(args), set(args)
            ops.append((o, frozenset(r), frozenset(w)))
    print(json.dumps({"n_ops": len(ops)}), flush=True)
    live = set()
    peak = 0
    peak_at = -1
    ever_live = set()
    for idx in range(len(ops) - 1, -1, -1):
        _, r, w = ops[idx]
        live = (live - w) | r
        ever_live |= live
        if len(live) > peak:
            peak = len(live)
            peak_at = idx
    never_live = sorted(set(range(891)) - ever_live)
    out = {"n_ops": len(ops), "true_peak_live": peak, "peak_at_op": peak_at,
           "n_ever_live": len(ever_live), "never_live_wires": never_live,
           "alloc_qubits": 891}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
