"""Measure the measurement-based uncompute already present in the ANGLE loaders.

For each loader: count CCX / HMR / CZ, check that no CCX follows the last HMR
(the MBU block), and report the saved coherent-uncompute cost.  Then run the
official ``recover_words_from_circuits`` on one loader (batch 0) and on the
full family at 2 shots/address.  No ``verify.py`` call.
"""
from __future__ import annotations

import collections
import sys
import tempfile
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "data/competition/verifiers"))

from dfthcsos.scoreinfra.circuits import (  # noqa: E402
    load_circuits,
    recover_words_from_circuits,
    register_layout,
)

DEFAULT = WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos"


def counts(circuit):
    with tempfile.NamedTemporaryFile(suffix=".kmx") as f:
        circuit.to_file(f.name, format="kmx")
        lines = [
            line.strip()
            for line in Path(f.name).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    nccx = sum(line.startswith("CCX") for line in lines)
    nhmr = sum(line.startswith("HMR") for line in lines)
    ncz = sum(line.startswith("CZ") for line in lines)
    last = max(i for i, line in enumerate(lines) if line.startswith("CCX"))
    tail = collections.Counter(line.split()[0] for line in lines[last + 1 :])
    return nccx, nhmr, ncz, tail


def main() -> None:
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    fam = load_circuits(directory)
    layout = register_layout(fam)
    sub = np.load(directory / "submission.npz")
    words = np.asarray(sub["angle_words"])
    total_ccx = total_hmr = 0
    for k, circuit in enumerate(fam):
        nccx, nhmr, ncz, tail = counts(circuit)
        total_ccx += nccx
        total_hmr += nhmr
        print(
            f"k{k:2d} ccx={nccx:3d} hmr={nhmr:2d} cz={ncz:2d} "
            f"ccx_after_last_hmr={tail.get('CCX', 0)} tail={dict(tail)}"
        )
    print(f"TOTAL ccx={total_ccx} hmr={total_hmr}")
    print(f"coherent uncompute would add {total_hmr} CCX/pass = {2 * total_hmr} T_total")
    print(f"current angle T = {2 * total_ccx}; MBU share already banked = "
          f"{2 * total_hmr / (2 * total_ccx):.4%}")

    # One loader, one batch (batch 0).  Forward must load batch 0; reverse must
    # clear; selection/workspace/phase checks are inside the function.
    w1, _, tof1 = recover_words_from_circuits(
        (fam[0],), num_vectors=len(words), num_angles=5,
        shots_per_address=2, seed=20261111,
    )
    print(f"single loader k0: words_match={np.array_equal(w1, words[:, :5])} "
          f"toffoli_fwd_rev={tof1} expected={2 * counts(fam[0])[0]}")
    w15, _, tof15 = recover_words_from_circuits(
        fam, num_vectors=len(words), num_angles=words.shape[1],
        shots_per_address=2, seed=20261111,
    )
    print(f"full 15 loaders: words_match={np.array_equal(w15, words)} "
          f"toffoli_fwd_rev={tof15} expected={2 * total_ccx}")
    print(f"layout J={layout.batch_size} brot={layout.brot} selection={len(layout.selection)}")


if __name__ == "__main__":
    main()
