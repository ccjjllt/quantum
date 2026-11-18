"""Tiny local correctness check of dqi_fast (few shots, small parameters).

Not evidence of a pass -- the official verifier on Kaggle is.  This only checks
the algebra/register contract on a handful of shots so that the expensive
verifier run is not wasted.
"""
import sys
import numpy as np
import kickmix as km

sys.path.insert(0, 'data/competition/verifiers')
sys.path.insert(0, 'experiments/frontier/20261118_push/dqi_gen')
from dqi.verify_submission_dqi import (FieldTables, ProblemSpecDQI, optimal_dqi_weights,
                                      sample_shots, to_bits, validate_registers)
from dqi_fast import build_fast_circuit


def check(m, n, degree, shots=16, seed=0, n_iter=None, verbose=True):
    spec = ProblemSpecDQI.benchmark_instance(m=m, n=n, degree=degree, num_shots=shots)
    circuit = build_fast_circuit(m, n, degree, n_iter=n_iter)
    stats = circuit.operation_statistics()
    tables = FieldTables(km.GF2Field(degree))
    wp = optimal_dqi_weights(m, spec.max_errors, degree, spec.r) ** 2
    rng = np.random.default_rng(seed)
    syndromes, mbuc, phases = sample_shots(spec, tables, rng, shots, wp)
    synd_q, mbuc_b, anc = validate_registers(circuit, spec)
    sim = km.Simulator(batch_size=shots, debug_print=False, counting_operations=True, seed=seed)
    sim.use_same_registers_as(circuit)
    in_syn = to_bits(syndromes, degree)
    sim.write_across_shots(km.array(synd_q), in_syn)
    sim.write_across_shots(km.array(mbuc_b), to_bits(mbuc, degree))
    sim.do(circuit)
    got_phase = sim.read_phase_flipped_across_shots()
    reg_diff = sim.read_across_shots(km.array(synd_q)) ^ in_syn
    junk = sim.read_across_shots(anc) if len(anc) else np.zeros((0, shots), dtype=bool)
    val_err = reg_diff.any(axis=0) | junk.any(axis=0)
    ph_err = (got_phase ^ phases) & ~val_err
    st = sim.operation_statistics()
    if verbose:
        print(f'({m},{n},{degree}) n_iter={n_iter}: Q={circuit.num_qubits} '
              f'static_T={stats.num_toffoli_like} exec_T={st.num_toffoli_like/shots:.1f} '
              f'val_err={int(val_err.sum())} phase_err={int(ph_err.sum())} / {shots}')
    return int(val_err.sum()), int(ph_err.sum()), circuit, stats


if __name__ == '__main__':
    bad = 0
    for (m, n, d, ni) in [(15, 6, 4, 8), (15, 6, 4, 15), (63, 6, 6, 10), (255, 10, 8, 14)]:
        ve, pe, c, s = check(m, n, d, shots=16, n_iter=ni)
        bad += ve + pe
    print('TOTAL BAD', bad)
