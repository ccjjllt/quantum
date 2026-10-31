"""Manually probe fixed error weights; deliberately NOT the scoring distribution.

This uses official shot generation and register/phase checks, without calling
verify(), changing the verifier, or assigning PASS/FAIL or a competition score.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
import kickmix as km
import numpy as np
from dqi.verify_submission_dqi import (
    ProblemSpecDQI, FieldTables, sample_shots, to_bits, validate_registers,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('circuit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--weights', nargs='+', type=int, default=[0, 2, 8, 16, 20, 35])
    parser.add_argument('--shots-per-weight', type=int, default=256)
    parser.add_argument('--seed', type=int, default=20261030)
    args = parser.parse_args()
    with args.circuit.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    circuit = km.Circuit.from_file(args.circuit, format='kmb')
    spec = ProblemSpecDQI.benchmark_instance()
    syndromes, records, ancillas = validate_registers(circuit, spec)
    syndromes, records = km.array(syndromes), km.array(records)
    tables = FieldTables(km.GF2Field(spec.degree))
    rows = []
    for weight in args.weights:
        started = time.monotonic()
        if not 0 <= weight <= spec.max_errors:
            raise ValueError('weight must be in 0..35')
        probs = np.zeros(spec.max_errors + 1)
        probs[weight] = 1
        seed = args.seed + 1000 * weight
        values, masks, phases = sample_shots(
            spec, tables, np.random.default_rng(seed), args.shots_per_weight, probs)
        sim = km.Simulator(batch_size=args.shots_per_weight,
                           counting_operations=True, debug_print=False, seed=seed+1)
        sim.use_same_registers_as(circuit)
        input_bits = to_bits(values, spec.degree)
        sim.write_across_shots(syndromes, input_bits)
        sim.write_across_shots(records, to_bits(masks, spec.degree))
        sim.do(circuit)
        restored = sim.read_across_shots(syndromes)
        junk = sim.read_across_shots(ancillas)
        value_errors = (restored ^ input_bits).any(axis=0) | junk.any(axis=0)
        phase_errors = (sim.read_phase_flipped_across_shots() ^ phases) & ~value_errors
        rows.append({'weight':weight,'shots':args.shots_per_weight,'input_seed':seed,
                     'measurement_seed':seed+1,'value_errors':int(value_errors.sum()),
                     'phase_errors_with_correct_values':int(phase_errors.sum()),
                     'mean_toffoli_like':sim.operation_statistics().num_toffoli_like/args.shots_per_weight,
                     'elapsed_seconds':time.monotonic()-started})
        print(json.dumps(rows[-1]),flush=True)
    out={'scope':'Local fixed-weight diagnostic, not official distribution/full validation/score',
         'circuit_sha256':digest,'num_qubits':circuit.num_qubits,
         'shots':args.shots_per_weight*len(args.weights),'rows':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n')


if __name__ == '__main__':
    main()
