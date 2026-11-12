"""Role census of the eae ancilla qubits q840..q891 from a .kmx text stream.

Reports, per top-level stage and per sub-mark:
  * which ops touch an ancilla, and in which role (control vs target)
  * T-gate (CCX/CCZ/CSWAP) counts that touch an ancilla, split by role
  * for each ancilla qubit: first/last line, stages seen
Read-only; no state simulation.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION", "PUSH", "POP")

QRE = re.compile(r"q(\d+)")


def main(path: Path, lo: int, hi: int) -> None:
    stage = None
    stack: list[str] = []
    sub = None
    # (stage, op) -> count
    ops = Counter()
    # (stage, sub, op) -> count
    ops_sub = Counter()
    # per-qubit
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    stages: dict[int, set] = defaultdict(set)
    # T detail: (stage, op, role) counts where role in {anc-control, anc-target, mixed}
    tdetail = Counter()
    # all-ancilla ops vs mixed
    scope = Counter()
    # qubits appearing together with a non-ancilla qubit
    partners = Counter()
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            n += 1
            if line.startswith("INFO_TAG "):
                try:
                    tag = line.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    name = tag[7:]
                    if stage is None:
                        stage = name
                    elif len(stack) == 1:
                        sub = name
                    stack.append(name)
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    if not stack:
                        stage = None
                    elif len(stack) == 1:
                        sub = None
                continue
            if not line or line.startswith(SKIP):
                continue
            parts = line.split()
            op = parts[0]
            qs = [int(m.group(1)) for m in QRE.finditer(line)]
            aq = [q for q in qs if lo <= q < hi]
            if not aq:
                continue
            for q in aq:
                first.setdefault(q, n)
                last[q] = n
                stages[q].add(stage)
            ops[(stage, op)] += 1
            ops_sub[(stage, sub, op)] += 1
            if len(aq) == len(qs):
                scope[(stage, "all_ancilla")] += 1
            else:
                scope[(stage, "mixed")] += 1
                for q in qs:
                    if not (lo <= q < hi):
                        partners[q] += 1
            if op in PAID:
                # roles: in kmx, last operand is target
                tgt = qs[-1] if qs else -1
                ctl = qs[:-1]
                if lo <= tgt < hi:
                    role = "anc_target"
                elif any(lo <= c < hi for c in ctl):
                    role = "anc_control_only"
                else:
                    role = "other"
                tdetail[(stage, op, role)] += 1

    print(f"lines={n}  ancilla range [{lo},{hi})  distinct={len(first)}")
    print("\n=== per-qubit first/last stage set")
    for q in sorted(first):
        print(f"q{q}: first={first[q]} last={last[q]} stages={sorted(x for x in stages[q] if x)}")
    print("\n=== ops touching ancilla, by stage")
    for (st, op), c in sorted(ops.items(), key=lambda kv: (str(kv[0][0]), -kv[1])):
        print(f"{str(st):18s} {op:10s} {c}")
    print("\n=== T gates touching ancilla (role split)")
    for (st, op, role), c in sorted(tdetail.items(), key=lambda kv: (str(kv[0][0]), kv[0][2])):
        print(f"{str(st):18s} {op:10s} {role:18s} {c}")
    print("\n=== scope (all-ancilla vs mixed)")
    for k, c in sorted(scope.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        print(f"{str(k[0]):18s} {k[1]:12s} {c}")
    print("\n=== most frequent non-ancilla partners (top 30)")
    for q, c in partners.most_common(30):
        print(f"q{q}\t{c}")
    print("\n=== per-stage per-sub T detail (sub marks with ancilla T > 0)")
    for (st, sb, op), c in sorted(ops_sub.items(), key=lambda kv: -kv[1]):
        if op in PAID:
            print(f"{str(st):16s} {str(sb):34s} {op:8s} {c}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
