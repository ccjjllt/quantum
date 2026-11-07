"""Is the 3C tap-sharing upper bound realisable at 62 qubits?

A tap used at ops t1 < t2 can be shared at cost 1 gate instead of 2 iff some
wire `a` can hold the product between t1 and t2 and be restored for free, i.e.
  (i)  `a` is not touched at all in [t1, t2]                     (it may not be read)
  (ii) the first operation on `a` after t2 either resets it (HMR / R) or
       overwrites it (X), so no explicit uncompute CCX is needed.

This scans all 62 wires for the three real duplicate taps and also reports the
weaker "dirty ancilla" criterion (untouched span, any restoring op) so the two
cost models are separated.

Writes artifacts/20261107_shared_rotation/ancilla_check.json
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
ART = ROOT / "artifacts/20261107_shared_rotation"


def main() -> None:
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    raw = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    ops = []
    for line in raw:
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    # full wire values at the start of each duplicate-tap span: is any wire
    # constant 0, or does any pair of wires carry the same value?
    import numpy as np
    MAXX = 3_133_452
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    full = (1 << MAXX) - 1
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8),
                                    bitorder="little").tobytes(), "little")
         for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    spans = set()
    led0 = json.loads((ART / "tap_ledger.json").read_text())
    from collections import defaultdict as _dd
    _u = _dd(list)
    for r in led0["rotations"]:
        for u in r["tap_uses"]:
            _u[u["tap"]].append(u["op"])
    for t, v in _u.items():
        if len(v) > 1:
            spans.add(min(v))
    span_state = {}
    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if i in spans:
            vals = {}
            for j, v in enumerate(q):
                vals.setdefault(v, []).append(j)
            span_state[i] = {
                "zero_wires": [j for j, v in enumerate(q) if v == 0],
                "duplicate_value_groups": [[j for j in js] for v, js in vals.items()
                                           if len(js) > 1],
            }
        if k in {"X", "CX", "CCX", "SWAP", "CSWAP"}:
            if k == "X":
                q[qs[0]] ^= active
            elif k == "CX":
                q[qs[1]] ^= q[qs[0]] & active
            elif k == "CCX":
                q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
            elif k == "SWAP":
                a, b = qs
                d = (q[a] ^ q[b]) & active
                q[a] ^= d
                q[b] ^= d
            else:
                cc, a, b = qs
                d = (q[a] ^ q[b]) & q[cc] & active
                q[a] ^= d
                q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = 0
            q[qs[0]] = 0
        elif k == "R":
            q[qs[0]] = 0
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = (old & ~active if k == "BIT_STORE0" else
                       old | active if k == "BIT_STORE1" else old ^ active)
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
    touches = [[] for _ in range(62)]
    for i, (k, qs, p) in enumerate(ops):
        for w in qs:
            touches[w].append(i)

    led = json.loads((ART / "tap_ledger.json").read_text())
    from collections import defaultdict
    uses = defaultdict(list)
    for r in led["rotations"]:
        for u in r["tap_uses"]:
            uses[u["tap"]].append((r["rot"], u["op"], u["kind"]))
    rep = []
    for tid, v in uses.items():
        if len(v) < 2:
            continue
        t1 = min(o for _, o, _ in v)
        t2 = max(o for _, o, _ in v)
        cand = []
        for w in range(62):
            ts = touches[w]
            a = np.searchsorted(ts, t1)
            b = np.searchsorted(ts, t2)
            if b - a:
                continue                          # touched inside the span
            nxt = [i for i in ts if i > t2]
            nxt = nxt[0] if nxt else None
            prvs = [i for i in ts if i < t1]
            prev = prvs[-1] if prvs else None
            free_restore = nxt is not None and (
                ops[nxt][0] in {"HMR", "R"} or ops[nxt][0] == "X")
            cand.append({"wire": w, "prev_op": prev, "next_op": nxt,
                         "next_instruction": " ".join(ops[nxt][2]) if nxt else None,
                         "free_restore": bool(free_restore),
                         "cost_with_dirty_ancilla": 2,
                         "cost_with_disposable_ancilla": 1 if free_restore else None})
        rep.append({"tap": tid, "kind": v[0][2], "rots": [r for r, _, _ in v],
                    "first_op": t1, "last_op": t2,
                    "untouched_wires": [x["wire"] for x in cand],
                    "disposable_candidates": [x for x in cand if x["free_restore"]]})
    for r in rep:
        r["span_start_state"] = span_state.get(r["first_op"], {})
    out = {"criterion": "untouched over the span and freely restorable after it",
           "duplicate_taps": rep,
           "zero_wire_check": {str(i): span_state[i]["zero_wires"] for i in span_state},
           "saving_C": sum(1 for r in rep if r["disposable_candidates"]),
           "conclusion": ("at least one disposable ancilla exists"
                          if any(r["disposable_candidates"] for r in rep)
                          else "no disposable ancilla at 62Q: every untouched wire's "
                               "next operation reads it or XORs into it, so an explicit "
                               "uncompute CCX is needed and sharing costs the same 2 gates")}
    (ART / "ancilla_check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["duplicate_taps"], indent=1))
    print("saving_C", out["saving_C"])
    print(out["conclusion"])


if __name__ == "__main__":
    main()
