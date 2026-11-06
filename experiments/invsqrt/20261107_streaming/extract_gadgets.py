"""Extract the exact loading gadget of each of the 41 fine rotations.

For rotation i the baseline clears q28 (HMR) and then builds the control value in
q28 from other wires with CX/CCX/CSWAP, applies Z_POW q28, then HMR q28.
This script prints, for every rotation, the op interval and the loading gates, and
re-derives the mask as a XOR of controlled-copy terms (verified against the traced
mask from artifacts/20261106_rot33/masks_full.json).
"""
from __future__ import annotations

import json

import common

CHECKS_OPS = []


def main() -> None:
    ops, gates = common.load_ops()
    masks, rops, rwires, angles = common.load_masks_full()
    n = common.MAXX

    # locate HMR q28 ops
    hmr28 = [i for i, (k, qs, p) in enumerate(gates) if k == "HMR" and qs == [28]]
    print("HMR q28 count:", len(hmr28))

    rows = []
    for i, rop in enumerate(rops):
        # previous q28-clearing op
        prev = max((h for h in hmr28 if h < rop), default=None)
        start = 0 if prev is None else prev + 1
        gadget = []
        for j in range(start, rop + 1):
            k, qs, p = gates[j]
            gadget.append((j, k, qs, p))
        rows.append({"rot": i, "op": rop, "wire": rwires[i], "angle": angles[i],
                     "start": start, "gadget": gadget})
        print(f"\n--- rot{i:2d}  Z_POW op{rop} q{rwires[i]}  theta={angles[i]}")
        for j, k, qs, p in gadget:
            print(f"    {j} {' '.join(p)}")

    (common.OUT / "rotation_gadgets.json").write_text(json.dumps(
        [{"rot": r["rot"], "op": r["op"], "wire": r["wire"], "angle": r["angle"],
          "start": r["start"],
          "gadget": [{"op": j, "kind": k, "qubits": qs, "tokens": p}
                     for j, k, qs, p in r["gadget"]]}
         for r in rows], indent=1) + "\n")


if __name__ == "__main__":
    main()
