"""End-to-end check of one commutation rewrite: move two reads of q25 out of block
[17007,17043) and compare phase + restored registers against the baseline.

Both circuits are run with the same kickmix seed on the same x values.  The moved gates do
not cross an HMR (HMR is a barrier in the analysis), so the random-coin order is unchanged
and the two runs must agree shot by shot.
"""
from __future__ import annotations

import io

import numpy as np

import kickmix as km

import common

BLOCK = 17007
MOVE = [17021, 17042]          # CX q25 q17, CX q25 q20


def split_lines(circuit):
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    head = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    body = [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]
    return head, body


def reordered_text(head, body):
    moved = [body[i] for i in MOVE]
    keep = [l for i, l in enumerate(body) if i not in set(MOVE)]
    # insertion point: count of kept lines that were before BLOCK
    at = sum(1 for i in range(BLOCK) if i not in set(MOVE))
    return "\n".join(head + keep[:at] + moved + keep[at:])


def run(circuit, xs, seed=11):
    sim = km.Simulator(batch_size=len(xs), seed=seed, counting_operations=True)
    xreg = circuit.register_data["x"]
    arr = np.asarray(xs, dtype=np.uint64)
    raw = ((arr[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1).astype(np.bool_)
    sim.clear_for_shot()
    sim.write_across_shots(xreg, raw)
    sim.do(circuit)
    return [sim.read_shot_phase(i) for i in range(len(xs))], sim.operation_statistics()


def main():
    base = km.Circuit.from_file(common.BASE)
    head, body = split_lines(base)
    txt = reordered_text(head, body)
    new = km.Circuit(txt)
    print("baseline qubits", base.num_qubits, "ops", len(body))
    print("reordered qubits", new.num_qubits, "ops", len(new))
    xs = [1, 2, 3, 5, 7, 11, 13, 63, 161, 1000, 12345, 999999, 1974272, 3133452]
    ph1, st1 = run(base, xs)
    ph2, st2 = run(new, xs)
    ok = all(a == b for a, b in zip(ph1, ph2))
    print("phase equal on all shots:", ok)
    for x, a, b in zip(xs, ph1, ph2):
        print(f"  x={x:>8} baseline={a} reordered={b} {'OK' if a == b else 'DIFF'}")
    print("toffoli baseline", st1.num_toffoli_like, "reordered", st2.num_toffoli_like)
    print("T baseline", st1.num_t_like, "reordered", st2.num_t_like)
    print("zpow baseline", st1.num_z_pow(min_clifford_hierarchy_level=4),
          "reordered", st2.num_z_pow(min_clifford_hierarchy_level=4))


if __name__ == "__main__":
    main()
