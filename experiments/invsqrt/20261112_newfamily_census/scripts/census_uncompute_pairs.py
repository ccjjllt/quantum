"""Read-only census of compute/uncompute Toffoli-like triples.

For every CCX/CCZ/CSWAP gate, look for the next gate with the same operands
(the reverse direction) and classify what happens to the target in between.
No circuit is modified.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kmx_parse import Op, load_ops  # noqa: E402

DIAG = {"CZ", "Z", "CCZ", "Z_POW", "NEG", "BIT_INVERT", "BIT_STORE0", "BIT_STORE1"}
TOFF = {"CCX", "CCZ", "CSWAP"}


def operands(op: Op) -> tuple[tuple[int, ...], int] | None:
    qs = op.qubits
    if op.kind in ("CCX", "CCZ") and len(qs) == 3:
        return (qs[:2], qs[2])
    if op.kind == "CSWAP" and len(qs) == 3:
        return (qs[:2], qs[2])
    return None


def main(path: Path) -> None:
    ops, nq, _ = load_ops(path)
    # index ops by target
    by_target: dict[int, list[int]] = defaultdict(list)
    for op in ops:
        operands_ = operands(op)
        if operands_ is not None:
            by_target[operands_[1]].append(op.index)

    pairs = []
    for op in ops:
        if op.kind not in TOFF:
            continue
        operands_ = operands(op)
        if operands_ is None:
            continue
        controls, target = operands_
        for j in by_target[target]:
            if j <= op.index:
                continue
            other = ops[j]
            if other.kind != op.kind:
                continue
            o_controls, o_target = operands(other)
            if o_target != target:
                continue
            if set(o_controls) != set(controls):
                continue
            pairs.append((op.index, j, op.kind, tuple(sorted(controls)), target, len(op.cond), len(other.cond)))
            break

    print(f"ops={len(ops)} toffoli-like={sum(1 for o in ops if o.kind in TOFF)}")
    print(f"matched compute/uncompute pairs: {len(pairs)}")
    span = Counter()
    for i, j, kind, controls, target, ci, cj in pairs:
        span[("guards-equal" if ci == cj else "guards-differ")] += 1
    print(span)

    rows = []
    for i, j, kind, controls, target, ci, cj in pairs:
        uses = []
        clean = True
        diag_only = True
        hmr = False
        recomp = False
        for k in range(i + 1, j):
            op = ops[k]
            if target not in op.qubits:
                continue
            qs = op.qubits
            is_target = qs[-1] == target and op.kind in ("CCX", "CCZ", "CSWAP", "CX", "X", "Z", "HMR")
            if op.kind == "HMR":
                hmr = True
                clean = False
                diag_only = False
                uses.append((k, op.kind, "hmr"))
                continue
            if target in qs[:-1]:
                uses.append((k, op.kind, "ctrl"))
                if op.kind not in ("CZ", "Z", "CCZ", "Z_POW"):
                    diag_only = False
                    clean = False
            else:
                uses.append((k, op.kind, "targ"))
                diag_only = False
                clean = False
                if op.kind in TOFF:
                    recomp = True
        rows.append(dict(i=i, j=j, kind=kind, controls=controls, target=target,
                         ci=ci, cj=cj, span=j - i, uses=uses,
                         diag_only=diag_only, clean=clean, hmr=hmr, recomp=recomp))

    # population summary
    print("\n-- by interval use class --")
    cls = Counter()
    for r in rows:
        if r["clean"]:
            cls["a) no use of target between"] += 1
        elif r["diag_only"]:
            cls["b) only diagonal control use"] += 1
        elif r["recomp"]:
            cls["c) target also written by another toffoli"] += 1
        elif r["hmr"]:
            cls["d) target measured between"] += 1
        else:
            cls["e) other non-diagonal use"] += 1
    for k, v in sorted(cls.items()):
        print(f"  {k}: {v}")

    print("\n-- class a/b pairs (candidate measurement-based uncompute) --")
    n = 0
    for r in rows:
        if r["clean"] or r["diag_only"]:
            n += 1
            if n <= 60:
                print(f"  [{r['i']}->{r['j']}] {r['kind']} ctrl={r['controls']} tgt={r['target']} "
                      f"span={r['span']} guards={r['ci']}/{r['cj']} uses={len(r['uses'])} "
                      f"diagonly={r['diag_only']}")
    print(f"  total class a+b: {n}")

    print("\n-- distribution of span for class a/b --")
    print(Counter(min(r["span"] // 100 * 100, 5000) for r in rows if r["clean"] or r["diag_only"]))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
