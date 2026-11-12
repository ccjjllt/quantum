"""Mean executed Toffoli-like count of a DQI circuit on a fixed shot sample.

Uses the official verifier's sampler and simulator exactly as `verify` does, but
with a pre-generated sample so the run is a local mean-T measurement, not a
full 102,400-shot verification.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
VERIFIER_DIR = ROOT / "data/competition/verifiers"
sys.path.insert(0, str(VERIFIER_DIR))

import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("circuit", type=Path)
    p.add_argument("--shots", type=int, default=8192)
    p.add_argument("--salt", default="mean-t")
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    circuit = km.Circuit.from_file(a.circuit, format="kmb")
    spec = V.ProblemSpecDQI.benchmark_instance()
    weights = V.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    tables = V.FieldTables(km.GF2Field(spec.degree))
    seed = V._initial_seed(V._circuit_sha256(circuit), a.salt)
    rng = np.random.default_rng(seed)
    shots = V.sample_shots(spec, tables, rng, a.shots, weights)
    r = V.verify(circuit, spec, shots=shots, batch_size=a.shots, max_workers=4)
    out = dict(circuit=str(a.circuit), shots=a.shots, Q=r["num_qubits"],
               static_T=r["max_toffoli_count"], mean_T=r["toffoli_count"],
               value_errors=r["value_errors"], phase_errors=r["phase_errors"],
               score_if_zero=r["repetition_factor"] * r["num_qubits"] ** 2 * r["toffoli_count"],
               rep_factor=r["repetition_factor"])
    print(json.dumps(out, indent=2))
    if a.out:
        a.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
