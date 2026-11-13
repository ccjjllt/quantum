"""Dump the prefix segment (op 0..8550) split into sub-blocks by gate census.

Read-only.  Prints per-window counts of Toffoli-class gates and the qubit
support, so the 193 CCX can be attributed to real sub-functions instead of
being lumped into the "normaliser".
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "20261112_newfamily_census" / "scripts"))
from kmx_parse import load_ops  # noqa: E402


def main() -> None:
    path = Path(sys.argv[1])
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 8550
    ops, nq, _ = load_ops(path)
    print(f"ops={len(ops)} qubits={nq}")

    def count(lo: int, hi: int, kinds=("CCX", "CSWAP", "CCZ")) -> Counter:
        c: Counter = Counter()
        for op in ops[lo:hi]:
            if op.kind in kinds:
                c[op.kind] += 1
        return c

    # coarse windows of 500 ops
    print("\n=== 500-op windows over prefix ===")
    print(f"{'range':>14} {'CCX':>5} {'CSWAP':>6} {'CCZ':>4} {'HMR':>4} {'CX':>5} "
          f"{'CZ':>5} {'SWAP':>5} {'X':>4} {'Z':>5} {'ZP':>3}")
    for lo in range(0, end, 500):
        hi = min(lo + 500, end)
        c = count(lo, hi, ("CCX", "CSWAP", "CCZ", "HMR", "CX", "CZ", "SWAP", "X", "Z", "Z_POW"))
        print(f"{lo:>6}-{hi:<7} {c['CCX']:>5} {c['CSWAP']:>6} {c['CCZ']:>4} {c['HMR']:>4} "
              f"{c['CX']:>5} {c['CZ']:>5} {c['SWAP']:>5} {c['X']:>4} {c['Z']:>5} {c['Z_POW']:>3}")

    # exact windows of the proposed split
    print("\n=== candidate split ===")
    for lo, hi in ((0, 649), (650, 7030), (7031, 8546)):
        c = count(lo, hi)
        print(f"[{lo}:{hi})  CCX={c['CCX']:>4} CSWAP={c['CSWAP']:>3} CCZ={c['CCZ']:>2} "
              f"T={c['CCX'] + c['CSWAP'] + c['CCZ']}")

    # qubit support of the three blocks
    print("\n=== qubit support per block ===")
    for lo, hi in ((0, 649), (650, 7030), (7031, 8546)):
        sup: Counter = Counter()
        for op in ops[lo:hi]:
            if op.kind in ("CCX", "CSWAP", "CCZ"):
                for q in op.qubits:
                    sup[q] += 1
        print(f"[{lo}:{hi})  {sorted(sup.items())}")

    # first/last 40 Toffoli-class ops per block
    for lo, hi in ((0, 649), (650, 7030), (7031, 8546)):
        print(f"\n--- block [{lo}:{hi}) Toffoli-class ops ---")
        shown = 0
        for op in ops[lo:hi]:
            if op.kind in ("CCX", "CSWAP", "CCZ"):
                print(f"{op.index:>6} {op.raw}")
                shown += 1
                if shown >= 30:
                    print(f"        ... ({shown} shown)")
                    break


if __name__ == "__main__":
    main()
