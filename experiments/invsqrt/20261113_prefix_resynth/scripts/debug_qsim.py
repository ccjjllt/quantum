"""Locate the first op where qsim diverges from km.Simulator on a basis input.

Builds truncated prefixes through the kmx text form, runs both simulators and
compares all 62 qubit values, for a few x.  Debug aid for qsim.py only.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from qsim import Sim, op_table, run  # noqa: E402


def kmx_lines(path: Path) -> list[str]:
    import kickmix as km

    c = km.Circuit.from_file(str(path), format="auto")
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return buf.getvalue().splitlines()


def flat_line_index(lines):
    flat = []
    for i, line in enumerate(lines):
        head = line.split()[0] if line else ""
        if head in ("APPEND_TO_REGISTER", "REGISTER"):
            continue
        flat.append(i)
    return flat


def km_state(lines, flat, upto: int, xs):
    import kickmix as km

    n_lines = flat[upto - 1] + 1
    body = lines[:n_lines]
    depth = sum(1 for ln in body if ln.split()[0] == "PUSH_CONDITION") - sum(
        1 for ln in body if ln.split()[0] == "POP_CONDITION")
    tail = ["POP_CONDITION"] * depth + ["X q61", "X q61"]  # declare full width
    text = "\n".join(body + tail) + "\n"
    sub = km.Circuit.from_file(io.StringIO(text), format="kmx")
    sim = km.Simulator(batch_size=len(xs), debug_print=False, seed=1)
    sim.clear_for_shot()
    bits = ((np.array(xs, dtype=np.uint64)[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1
    sim.write_across_shots(km.array([km.q(i) for i in range(22)]), bits)
    sim.do(sub)
    return sim.read_across_shots(km.array([km.q(i) for i in range(62)]))


def main() -> None:
    path = Path(sys.argv[1])
    xs = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else [2]
    lines = kmx_lines(path)
    flat = flat_line_index(lines)
    table, nq = op_table(path)
    print(f"ops={len(table)} x={xs}")

    cuts = [int(a) for a in sys.argv[3].split(",")] if len(sys.argv) > 3 else []
    if not cuts:
        cuts = [1] + list(range(0, len(table), max(1, len(table) // 60)))
    for cut in cuts:
        if cut == 0:
            continue
        sim = Sim(len(xs), n_qubits=nq)
        sim.v = np.array(xs, dtype=np.uint64)
        run(sim, table, limit=cut)
        mine = np.stack([(sim.v >> np.uint64(q)) & np.uint64(1) for q in range(nq)], axis=0).astype(bool)
        theirs = km_state(lines, flat, cut, xs)
        ok = np.array_equal(mine, theirs)
        if not ok:
            diff = np.argwhere(mine != theirs)
            print(f"cut {cut}: MISMATCH at {len(diff)} positions, first {diff[:6].tolist()}")
            print("  op:", table[cut - 1])
            return
    print("all cuts match")


if __name__ == "__main__":
    main()
