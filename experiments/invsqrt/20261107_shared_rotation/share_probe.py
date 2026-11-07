"""Probe the real sharing potential of the 41 masks' accumulator taps.

For every write into a rotation accumulator (wires 28/50/41/40), record
  * the increment function d (full domain, deduplicated)
  * for CSWAP `c a b` that writes the accumulator: whether d == (partner & c),
    i.e. the conditional replacement degenerates to a clean XOR product of two
    live wires because the accumulator's own pre-value is disjoint from the
    control
  * the natural product form (q{a}, q{a}&q{b}, ...)
then joins with tap_ledger.json's per-use (rot, op, kind) records and
deduplicates the resulting functions across all 41 rotations.

This is the concrete measurement of "shared monomial basis ... use real
monomial sharing from the 41 masks", not a generic estimate.

Writes artifacts/20261107_shared_rotation/share_probe.json
"""
from __future__ import annotations

import hashlib
import io
import json
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261107_shared_rotation"
MAXX = 3_133_452
ROT_WIRES = {28, 50, 41, 40}


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    raw = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    ops = []
    for line in raw:
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return c, ops


def main() -> None:
    t0 = time.time()
    circuit, ops = load_ops()
    sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    led = json.loads((OUT / "tap_ledger.json").read_text())
    uses = [(r["rot"], u["op"], u["kind"], u["tap"]) for r in led["rotations"] for u in r["tap_uses"]]
    use_by_op = {}
    for rot, op, kind, tap in uses:
        use_by_op.setdefault(op, []).append((rot, tap))

    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    full = (1 << MAXX) - 1
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little")
         for j in range(22)] + [0] * (circuit.num_qubits - 22)
    bits: dict[int, int] = {}
    stack: list[int] = []
    intern: dict[int, int] = {}

    def ident(v: int) -> int:
        if v not in intern:
            intern[v] = len(intern)
        return intern[v]

    prod_id: dict[int, int] = {}    # clean product value -> id
    prod_tt: dict[int, int] = {}
    opinfo: dict[int, dict] = {}

    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k in {"X", "CX", "CCX", "SWAP", "CSWAP"}:
            if k == "X":
                w = qs[0]
                d = active
                if w in ROT_WIRES:
                    opinfo[i] = {"d": ident(d), "form": "const1", "clean": True, "paid": False}
                q[w] ^= d
            elif k == "CX":
                a, w = qs
                d = q[a] & active
                if w in ROT_WIRES:
                    opinfo[i] = {"d": ident(d), "form": f"q{a}", "clean": True, "paid": False}
                q[w] ^= d
            elif k == "CCX":
                a, b, w = qs
                d = q[a] & q[b] & active
                if w in ROT_WIRES:
                    opinfo[i] = {"d": ident(d), "form": f"q{a}&q{b}", "clean": True, "paid": True,
                                 "form_tt": prod_id.setdefault(d, len(prod_id))}
                q[w] ^= d
            elif k == "SWAP":
                a, b = qs
                d = (q[a] ^ q[b]) & active
                q[a] ^= d
                q[b] ^= d
            else:
                c_, a, b = qs
                d = (q[a] ^ q[b]) & q[c_] & active
                if a in ROT_WIRES:
                    partner, acc = b, a
                elif b in ROT_WIRES:
                    partner, acc = a, b
                else:
                    partner = acc = None
                if acc is not None:
                    pure = q[partner] & q[c_] & active
                    clean = bool(pure == d)
                    opinfo[i] = {"d": ident(d), "form": f"q{c_}&q{partner}", "clean": clean,
                                 "paid": True,
                                 "acc_pre_and_ctrl_empty": bool((q[acc] & q[c_] & active) == 0),
                                 "form_tt": prod_id.setdefault(pure, len(prod_id))}
                q[a] ^= d
                q[b] ^= d
        elif k in {"HMR", "R"}:
            w = qs[0]
            if k == "HMR":
                bits[int(p[2][1:])] = 0
            q[w] = 0
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"Z_POW", "Z", "CZ", "CCZ", "NEG"}:
            pass
        else:
            raise ValueError((i, k, p))
    print(f"trace {time.time()-t0:.1f}s forms={len(intern)} products={len(prod_id)}", flush=True)

    # join
    rows = []
    for op, lst in use_by_op.items():
        info = opinfo[op]
        for rot, tap in lst:
            rows.append({"rot": rot, "op": op, "kind": ops[op][0],
                         "clean_form": info["clean"], "form": info["form"],
                         "form_id": info.get("form_tt"), "d_tap": tap})
    by_form = Counter()
    by_form_tt = {}
    for r in rows:
        by_form[(r["form"], r["clean_form"])] += 1
    # dedupe the clean product functions (the candidate shared monomial basis)
    for r in rows:
        if r["clean_form"] and r["form_id"] is not None:
            by_form_tt.setdefault(r["form_id"], []).append(r["rot"])
    mult = Counter(len(v) for v in by_form_tt.values())
    out = {
        "baseline": str(BASE.relative_to(ROOT)), "sha256": sha,
        "n_tap_uses": len(rows),
        "n_paid_tap_uses": sum(1 for r in rows if r["kind"] in {"CCX", "CCZ", "CSWAP"}),
        "n_uses_with_clean_product_form": sum(1 for r in rows if r["clean_form"]),
        "n_distinct_clean_products": len(by_form_tt),
        "clean_product_multiplicity_histogram": dict(sorted(mult.items())),
        "shared_clean_products": {str(k): v for k, v in by_form_tt.items() if len(v) > 1},
        "form_histogram": {f"{f}|clean={c}": n for (f, c), n in by_form.most_common()},
        "target_wire_forms": {},
    }
    # group forms per accumulator wire for the report
    per_wire = {}
    for r in rows:
        per_wire.setdefault(r["kind"], Counter())[(r["form"], r["clean_form"])] += 1
    out["form_histogram_by_kind"] = {
        k: {f"{f}|clean={c}": n for (f, c), n in cnt.most_common()}
        for k, cnt in per_wire.items()
    }
    (OUT / "share_probe.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("n_tap_uses", "n_paid_tap_uses", "n_uses_with_clean_product_form",
                       "n_distinct_clean_products", "clean_product_multiplicity_histogram")}, indent=1))
    print("shared clean products:", out["shared_clean_products"])


if __name__ == "__main__":
    main()
