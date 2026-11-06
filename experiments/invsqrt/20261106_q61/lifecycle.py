"""Per-wire lifecycle dump for the baseline KMB (read-only)."""
from __future__ import annotations

import collections
import json
import sys

import common

KIND = {
    "X": "X", "Z": "Z", "CX": "CX", "CZ": "CZ", "CCX": "AND", "CCZ": "ANDZ",
    "SWAP": "SWAP", "CSWAP": "CSWAP", "NEG": "NEG", "R": "RESET", "HMR": "HMR",
    "BIT_STORE0": "CL0", "BIT_STORE1": "CL1", "BIT_INVERT": "CLX",
    "PUSH_CONDITION": "PUSH", "POP_CONDITION": "POP", "Z_POW": "ROT",
}


def role(kind, qs, q):
    """How q participates: target/control/both."""
    if kind in common.WRITES_ONE:
        return "target" if qs[0] == q else "control"
    if kind in common.WRITES_LAST:
        return "target" if qs[-1] == q else "control"
    if kind in common.WRITES_TWO:
        return "control" if qs[0] == q else "target"
    if kind in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
        return "phase-control" if q in qs else "-"
    return "-"


def profile(q, ops, gates, stacks, segs):
    rows = []
    for i, (k, qs, p) in enumerate(gates):
        if q not in qs:
            continue
        cond = stacks[i]
        rows.append({
            "op": i, "kind": k, "role": role(k, qs, q), "paid": k in common.PAID,
            "if": p[-1] if "if" in p else None,
            "cond_depth": len(cond), "cond": list(cond),
            "instr": ops[i],
        })
    return {
        "q": q,
        "segments": [[a, b] for a, b, _ in segs],
        "touch_count": len(rows),
        "paid_touch_count": sum(r["paid"] for r in rows),
        "paid_as_target": sum(r["paid"] and r["role"] == "target" for r in rows),
        "paid_as_control": sum(r["paid"] and r["role"] == "control" for r in rows),
        "kinds": dict(collections.Counter(r["kind"] for r in rows)),
        "roles": dict(collections.Counter(r["role"] for r in rows)),
        "first": rows[0]["op"] if rows else None,
        "last": rows[-1]["op"] if rows else None,
        "touches": rows,
    }


def main():
    targets = [int(a.lstrip("q")) for a in sys.argv[1:]] or [49, 34, 53, 35, 33, 40, 41, 23]
    _, ops, gates, stacks = common.load_ops()
    segs_all = {q: common.conservative_segments(gates, stacks, q) for q in range(62)}
    common.main()
    out = {}
    for q in targets:
        prof = profile(q, ops, gates, stacks, segs_all[q])
        out[f"q{q}"] = prof
        print(f"\n=== q{q} segments={prof['segments']} touches={prof['touch_count']} "
              f"paid={prof['paid_touch_count']} kinds={prof['kinds']} roles={prof['roles']}")
        for r in prof["touches"]:
            cond = f" [d{len(r['cond'])}]" if r["cond"] else ""
            print(f"  {r['op']:6d} {r['kind']:<14} {r['role']:<14} {'PAID' if r['paid'] else '    '}{cond} {r['instr']}")
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "lifecycle.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
