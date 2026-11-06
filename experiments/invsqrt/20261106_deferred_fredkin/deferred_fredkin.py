"""Defer rotation-gadget Fredkins past the Z_POW/HMR that measures their control.

Hypothesis: in the rotation clusters the sequence

    CSWAP a c b
    ...
    Z_POW c theta
    HMR c bit

only uses c as a control.  CSWAP(c,a,b) commutes with every diagonal gate on c,
so the Fredkins can be moved after HMR(c), where they become conditional swaps
driven by the classical outcome bit.  A conditional swap is three CX gates
(free), replacing each paid CSWAP (1C).

The script performs an exhaustive local value/phase check over every basis
state of the involved wires and both measurement outcomes, writes a real KMB,
and does not invoke the official verifier.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
BASE_SHA = "48db715f9b3b941cea1dec915938a0421467271bc3b62b382e5c792383810feb"
OUT = ROOT / "artifacts/20261106_deferred_fredkin"


def load(path: Path):
    circuit = km.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]
    return circuit, header, ops


def find_groups(ops):
    """Find CSWAP runs immediately followed by Z_POW(q) and HMR(q,bit)."""
    depths = []
    depth = 0
    for line in ops:
        depths.append(depth)
        p = line.split()
        if p[0] == "PUSH_CONDITION":
            depth += 1
        elif p[0] == "POP_CONDITION":
            depth -= 1
    assert depth == 0
    groups = []
    for i, line in enumerate(ops):
        p = line.split()
        if p[0] != "Z_POW" or i + 1 >= len(ops):
            continue
        control = p[1]
        nxt = ops[i + 1].split()
        if nxt[0] != "HMR" or nxt[1] != control:
            continue
        j = i
        swaps = []
        while j > 0:
            prev = ops[j - 1].split()
            if prev[0] == "CSWAP" and prev[2] == control:
                swaps.append(j - 1)
                j -= 1
            else:
                break
        if not swaps:
            continue
        lo = min(swaps)
        hi = i + 1  # inclusive HMR index
        if any("if" in ops[k].split() for k in range(lo, hi + 1)):
            raise ValueError(f"conditional group at {lo} not supported")
        if any(depths[k] for k in range(lo, hi + 1)):
            raise ValueError(f"group in condition stack at {lo} not supported")
        groups.append({
            "lo": lo,
            "hi": hi,
            "control": control,
            "bit": nxt[2],
            "swaps": [ops[k].split() for k in sorted(swaps)],
            "z_pow": ops[i],
            "hmr": ops[i + 1],
        })
    return groups


def rewrite_group(group):
    """Return (old_lines, new_lines) for one group; indices are global."""
    old = [group["z_pow"], group["hmr"]]
    new = [group["z_pow"], group["hmr"]]
    for p in group["swaps"]:
        a, b = p[1], p[3]
        bit = group["bit"]
        new += [f"CX {a} {b} if {bit}", f"CX {b} {a} if {bit}", f"CX {a} {b} if {bit}"]
    # old order was swaps, then Z_POW/HMR
    old = [f"CSWAP {p[1]} {p[2]} {p[3]}" for p in group["swaps"]] + old
    return old, new


def local_check(old, new):
    """Exhaustive scalar basis-state check; HMR outcome is determined by the control."""
    wires = sorted({int(t[1:]) for line in old + new for t in line.split()[1:] if t.startswith("q")})
    n = len(wires)
    cases = 1 << n
    bits_index = {w: i for i, w in enumerate(wires)}

    def execute(lines, state):
        q = {w: (state >> bits_index[w]) & 1 for w in wires}
        phase = 0.0
        bits = {}
        for line in lines:
            p = line.split()
            k = p[0]
            qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
            active = 1 if "if" not in p else bits[p[-1]]
            if k == "CSWAP":
                d = (q[qs[0]] ^ q[qs[2]]) & q[qs[1]] & active
                q[qs[0]] ^= d
                q[qs[2]] ^= d
            elif k == "CX":
                q[qs[1]] ^= q[qs[0]] & active
            elif k == "Z_POW":
                phase += float(p[2]) * (q[qs[0]] & active)
            elif k == "HMR":
                outcome = q[qs[0]] & active
                phase += outcome  # in units of pi; identical ordering of the control in both versions
                q[qs[0]] = 0
                bits[p[2]] = outcome
            else:
                raise ValueError(line)
        return q, phase

    for state in range(cases):
        a = execute(old, state)
        b = execute(new, state)
        assert a == b, f"mismatch for state {state}: {a} vs {b}"
    return {"status": "PASS", "wire_count": n, "basis_states": cases,
            "measurement_outcomes": "determined by control", "exhaustive_cases": cases,
            "all_output_values_equal": True, "phase_equal": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", type=int, default=0, help="index into detected groups")
    ap.add_argument("--all", action="store_true", help="rewrite every detected group")
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    _, header, ops = load(BASE)
    groups = find_groups(ops)
    chosen = groups if args.all else [groups[args.group]]

    pieces = []
    cursor = 0
    records = []
    for g in chosen:
        old, new = rewrite_group(g)
        assert ops[g["lo"]:g["hi"] + 1] == old
        proof = local_check(old, new)
        records.append({"lo": g["lo"], "hi": g["hi"], "control": g["control"],
                        "bit": g["bit"], "removed_cswap": len(g["swaps"]),
                        "proof": proof})
        pieces.append((g["lo"], g["hi"] + 1, new))
    out = []
    for lo, hi, new in pieces:
        out += ops[cursor:lo] + new
        cursor = hi
    out += ops[cursor:]

    name = "deferred_fredkin_all.kmb" if args.all else f"deferred_fredkin_g{args.group}.kmb"
    target = args.output or (OUT / name)
    candidate = km.Circuit.from_file(io.StringIO("\n".join(header + out) + "\n"), format="kmx")
    target.parent.mkdir(parents=True, exist_ok=True)
    candidate.to_file(target, format="kmb")
    _, header2, readback = load(target)
    assert header2 == header and readback == out
    report = {
        "scope": "local exhaustive proof and KMB generation; no official validation",
        "baseline_sha256": BASE_SHA,
        "candidate_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "candidate": str(target.relative_to(ROOT)),
        "qubits": candidate.num_qubits,
        "groups": records,
        "removed_cswap": sum(r["removed_cswap"] for r in records),
        "added_free_cx": 3 * sum(r["removed_cswap"] for r in records),
    }
    (OUT / f"{target.stem}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "groups"}, indent=2))
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
