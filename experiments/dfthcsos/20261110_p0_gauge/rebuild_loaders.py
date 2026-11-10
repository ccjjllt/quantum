"""P0 step2: rebuild 15 ANGLE loaders for the new (gauge-flipped) word table.

Method: shared planner tensorqrom.build_family (same as 20261109_angles_r5),
J=5/brot=8/lowbits=4, then recover_words_from_circuits metrology (shots=2).

Writes:
  artifacts/20261110_p0_gauge/candidate/angle_k_<k>.kmb
  artifacts/20261110_p0_gauge/loader_costs.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

WORKTREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKTREE / "data" / "competition" / "verifiers"))
sys.path.insert(0, str(WORKTREE / "artifacts/20261106_high_yield/lera_data/dfthc_refit"))

from dfthcsos.scoreinfra.circuits import (  # noqa: E402
    circuit_costs,
    recover_words_from_circuits,
    register_layout,
)
from dfthcsos.verify import heuristic_costs  # noqa: E402

N = 76
BROT = 8
J = 5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--shots", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261110)
    a = ap.parse_args()

    out = WORKTREE / "artifacts/20261110_p0_gauge"
    words = np.load(out / "new_angle_words.npy")
    assert words.shape == (1220, 75)
    assert not np.any(((words >> (BROT - 1)) ^ (words >> (BROT - 2))) & 1), "signed gauge violated"

    import tensorqrom

    t0 = time.time()
    family = tensorqrom.build_family(words, brot=BROT, j=J, lowbits=4,
                                     trials=a.trials, jobs=a.jobs)
    build_s = round(time.time() - t0, 1)
    print(f"built {len(family)} circuits in {build_s}s", flush=True)

    t0 = time.time()
    w, lay, tof = recover_words_from_circuits(
        family, num_vectors=len(words), num_angles=N - 1,
        shots_per_address=a.shots, seed=a.seed)
    sim_s = round(time.time() - t0, 1)
    ok = bool(np.array_equal(w, words))
    cc = circuit_costs(family)
    static = int(sum(c["max_magic"] for c in cc))
    qmax = int(max(c["num_qubits"] for c in cc))
    sel = len(lay.selection)
    print(f"words_match={ok} sim_toffoli={tof} static={static} qubits_max={qmax} sel={sel}", flush=True)

    hc = heuristic_costs(N, 8, 143, 44, BROT)
    heur = int(hc["toffoli"])
    T = float(tof) + heur
    temp = qmax - sel - J * BROT
    Q = int(hc["persistent_qubits"]) + J * BROT + max(int(hc["temporary_qubits"]), temp)
    print(f"T={T} Q={Q} TQ={T * Q} (heuristic {heur})", flush=True)

    cand = out / "candidate"
    cand.mkdir(parents=True, exist_ok=True)
    for k, circ in enumerate(family):
        circ.to_file(str(cand / f"angle_k_{k}.kmb"), format="kmb")
    rec = {
        "trials": a.trials, "jobs": a.jobs, "shots": a.shots, "seed": a.seed,
        "build_seconds": build_s, "sim_seconds": sim_s,
        "words_match": ok,
        "sim_toffoli_fwd_rev": float(tof), "sim_per_pass": float(tof) / 2,
        "static_sum": static, "qubits_max": qmax, "selection_bits": sel,
        "heuristic_toffoli": heur, "T_total": float(T), "Q_total": int(Q),
        "TQ": float(T) * int(Q),
        "dAngles_vs_8304": float(tof) - 8304.0,
        "dAngles_vs_8296": float(tof) - 8296.0,
        "per_circuit": [{"k": c["k"], "max_magic": c["max_magic"],
                         "num_qubits": c["num_qubits"]} for c in cc],
    }
    (out / "loader_costs.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
