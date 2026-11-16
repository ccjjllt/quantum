"""Static live-wire analysis of a kickmix circuit (no simulation).

Usage: python analyze_live.py <circuit.kmx|kmb> [--dump profile.json]

Liveness model (backward):
  - quantum arg that is only consumed by an op        -> read
  - op that transforms the value (CX target, X, CCX target, SWAP) -> read+write
  - HMR q b                                            -> read + reset(write); b is a classical bit
  - Z / Z_POW / CZ / CCZ                               -> read (phase kickback / control)
  - PUSH_CONDITION / POP_CONDITION / NEG / BIT_*       -> classical only, no quantum effect

A wire is "live" at a point if its current value is read later before being reset.
Peak live count is a lower bound on the qubit width of any re-labelling of the same op sequence.
"""
import json
import sys
from pathlib import Path

import kickmix


def load_ops(path: Path):
    if path.suffix == ".kmb":
        circuit = kickmix.Circuit.from_file(path, format="auto")
        tmp = Path("/tmp/_analyze_live.kmx")
        circuit.to_file(tmp)
        text = tmp.read_text()
    else:
        text = path.read_text()
    ops = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        mnem = parts[0]
        qargs, bargs, angle = [], [], None
        for tok in parts[1:]:
            if tok.startswith("q"):
                qargs.append(int(tok[1:]))
            elif tok.startswith("b"):
                bargs.append(int(tok[1:]))
            elif tok == "if":
                continue
            else:
                try:
                    angle = float(tok)
                except ValueError:
                    pass
        ops.append({"i": len(ops), "op": mnem, "q": qargs, "b": bargs, "angle": angle})
    return ops


# effect tables: (reads, writes)
def effect(o):
    m, q = o["op"], o["q"]
    if m == "CX":
        return [q[0]], [q[1]]
    if m == "CCX":
        return [q[0], q[1]], [q[2]]
    if m in ("CZ", "CCZ", "Z", "Z_POW"):
        return list(q), []
    if m == "X":
        return [], list(q)
    if m == "HMR":
        return list(q), list(q)
    if m == "SWAP":
        return list(q), list(q)
    return [], []


def analyze(ops):
    n = max((max(o["q"]) for o in ops if o["q"]), default=-1) + 1
    live = set()
    live_after = [0] * len(ops)
    live_before = [0] * len(ops)
    live_mask = [0] * len(ops)
    reads_all = [0] * len(ops)
    for o in reversed(ops):
        rd, wr = effect(o)
        live_after[o["i"]] = len(live)
        live_before[o["i"]] = len((live - set(wr)) | set(rd))
        live = (live - set(wr)) | set(rd)
        live_mask[o["i"]] = sum(1 << w for w in live)
    # first/last touch per wire
    first, last = {}, {}
    for o in ops:
        for w in o["q"]:
            first.setdefault(w, o["i"])
            last[w] = o["i"]
    return {
        "num_qubits": n,
        "ops": len(ops),
        "live_after": live_after,
        "live_before": live_before,
        "live_mask": live_mask,
        "first": first,
        "last": last,
    }


def main() -> None:
    path = Path(sys.argv[1])
    dump = None
    if "--dump" in sys.argv:
        dump = Path(sys.argv[sys.argv.index("--dump") + 1])
    ops = load_ops(path)
    res = analyze(ops)
    print(f"ops {res['ops']} qubits {res['num_qubits']}")
    peak = max(res["live_before"])
    print(f"peak live {peak}  min live {min(res['live_before'])}")
    # contiguous runs at peak
    runs = []
    start = None
    for i, c in enumerate(res["live_before"]):
        if c == peak and start is None:
            start = i
        elif c != peak and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(res["live_before"]) - 1))
    print(f"runs at peak: {len(runs)}  longest {max((b - a + 1) for a, b in runs)}")
    print("top runs:", sorted(((b - a + 1, a, b) for a, b in runs), reverse=True)[:8])
    print("wire first/last:", {w: (res["first"][w], res["last"][w]) for w in sorted(res["first"])})
    # histogram
    from collections import Counter
    print("live histogram:", sorted(Counter(res["live_before"]).items()))
    if dump:
        dump.write_text(json.dumps({
            "path": str(path),
            "num_qubits": res["num_qubits"],
            "ops": res["ops"],
            "peak": peak,
            "live_before": res["live_before"],
            "live_mask": res["live_mask"],
            "op_names": [o["op"] for o in ops],
        }))
        print("wrote", dump)


if __name__ == "__main__":
    main()
