"""Checkpoint structure: which wires equal the rotation mask, which are live.

Writes artifacts/20261107_mask_refit/checkpoint_stats.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import model as M

OUT = M.ART
WIRES = OUT / "wires"


def load_cp(i: int) -> list[int]:
    z = np.load(WIRES / f"cp_{i:02d}.npz")
    return [int.from_bytes(z[f"w{j}"].tobytes(), "little") for j in range(62)]


def gf2_rank(values: list[int]) -> int:
    basis: dict[int, int] = {}
    for v in values:
        while v:
            p = v.bit_length() - 1
            if p not in basis:
                basis[p] = v
                break
            v ^= basis[p]
    return len(basis)


def main() -> None:
    m = M.load_model()
    masks, thetas, ops, targets = m["masks"], m["thetas"], m["ops"], m["targets"]
    full = (1 << M.MAXX) - 1
    out = []
    for i in range(41):
        wires = load_cp(i)
        pops = [w.bit_count() for w in wires]
        const0 = [j for j, w in enumerate(wires) if w == 0]
        const1 = [j for j, w in enumerate(wires) if w == full]
        live = [j for j, w in enumerate(wires) if 0 < w < full]
        eq_mask = [j for j, w in enumerate(wires) if w == int.from_bytes(np.packbits(masks[i], bitorder="little").tobytes(), "little")]
        # rank of live wire functions (as bitsets)
        rank = gf2_rank([wires[j] for j in live])
        rec = {
            "rot": i, "op": ops[i], "target": targets[i],
            "target_pop": pops[targets[i]],
            "mask_pop": int(masks[i].sum()),
            "wires_equal_mask": eq_mask,
            "const0": const0, "const1": const1, "live": live,
            "rank_live": rank,
            "popcounts": pops,
        }
        out.append(rec)
        print(f"rot {i:2d} op {ops[i]} tgt q{targets[i]} pop {rec['mask_pop']:7d} "
              f"eq={eq_mask} const0={const0} rank={rank}", flush=True)
    (OUT / "checkpoint_stats.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
