"""At every use of a candidate wire, find other wires holding the identical value.

Full legal domain, one fixed all-zero HMR branch (basis states only).  A match means the
two wires agree bit-for-bit for every legal x at that operation, i.e. an exact local alias
on that branch; a global elimination still needs the match to hold on every measurement
branch, which is checked separately with extra random branches.
"""
from __future__ import annotations

import collections
import json
import sys

import numpy as np

import common

MAXX = 3133452


def masks_for_all_ops(gates):
    n = MAXX
    q = [0] * 62
    for j in range(22):
        a = np.arange(1, n + 1, dtype=np.uint64)
        bits = ((a >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
    mask = (1 << n) - 1
    yield 0, q
    for i, (k, qs, p) in enumerate(gates):
        if k in {"X", "R", "HMR"}:
            q[qs[0]] = 0 if k in {"R", "HMR"} else q[qs[0]] ^ mask
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]]
        elif k == "SWAP":
            q[qs[0]], q[qs[1]] = q[qs[1]], q[qs[0]]
        elif k == "CSWAP":
            c, a, b = qs
            d = (q[a] ^ q[b]) & q[c]
            q[a] ^= d
            q[b] ^= d
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]]
        yield i + 1, q


def main():
    targets = [int(a.lstrip("q")) for a in sys.argv[1:]] or [49, 34, 53, 35, 33, 23, 59, 56, 38, 39]
    _, ops, gates, stacks = common.load_ops()
    use_ops = {t: [i for i, (k, qs, p) in enumerate(gates) if t in qs] for t in targets}
    report = {t: {} for t in targets}
    for i, q in masks_for_all_ops(gates):
        for t in targets:
            if i not in set(use_ops[t]):
                continue
            v = q[t]
            matches = [w for w in range(62) if w != t and q[w] == v]
            kind = gates[i][0]
            report[t][i] = {"kind": kind, "matches": matches,
                            "constant": (0 if v == 0 else ("ALL" if v == (1 << MAXX) - 1 else None)),
                            "instr": ops[i]}
    out = {}
    for t in targets:
        rows = report[t]
        cnt = collections.Counter()
        for i, r in rows.items():
            cnt[tuple(r["matches"])] += 1
        per_wire = collections.Counter()
        for r in rows.values():
            for w in r["matches"]:
                per_wire[w] += 1
        out[f"q{t}"] = {
            "use_ops": len(rows),
            "matched_any": sum(1 for r in rows.values() if r["matches"]),
            "constant_hits": sum(1 for r in rows.values() if r["constant"] is not None),
            "per_partner_use_coverage": dict(per_wire.most_common()),
            "rows": rows,
        }
        print(f"q{t}: uses={len(rows)} with_any_alias={out[f'q{t}']['matched_any']} "
              f"constant={out[f'q{t}']['constant_hits']} top_partners={per_wire.most_common(6)}")
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "alias_scan.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
