"""Verify that Q is the number of distinct qubit indices: deleting one index's lines drops Q.

Read-only: parses the baseline KMX in memory, never writes the baseline.
"""
from __future__ import annotations

import io

import kickmix as km

import common


def main():
    c = km.Circuit.from_file(common.BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    print("baseline num_qubits:", c.num_qubits, "kmx lines:", len(lines))
    for w in (61, 60, 49, 34, 23, 22):
        kept = [l for l in lines if f"q{w} " not in l and not l.endswith(f"q{w}")]
        try:
            c2 = km.Circuit("\n".join(kept))
            print(f"drop every line mentioning q{w}: num_qubits={c2.num_qubits} "
                  f"(kept {len(kept)}/{len(lines)})")
        except Exception as ex:  # noqa: BLE001 - report, do not fail the run
            print(f"drop q{w}: parse error {ex}")


if __name__ == "__main__":
    main()
