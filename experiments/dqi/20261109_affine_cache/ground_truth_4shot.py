"""Ground truth: run frontier dqi.kmb under km.Simulator (4 shots,
verifier-grade inputs) and check S restoration + ancilla zero."""
from __future__ import annotations

import sys
import time

import numpy as np

sys.path.insert(0, "data/competition/verifiers")
from dqi.verify_submission_dqi import (  # noqa: E402
    FieldTables,
    ProblemSpecDQI,
    default_num_accepted_values,
    optimal_dqi_weights,
    sample_shots,
    to_bits,
    validate_registers,
)

import kickmix as km  # noqa: E402

t0 = time.time()
c = km.Circuit.from_file("artifacts/20261108_public_frontier/release/dqi.kmb")
print(f"loaded {len(c)} ops in {time.time()-t0:.1f}s", flush=True)

spec = ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=4)
tables = FieldTables(km.GF2Field(12))
wp = optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
rng = np.random.default_rng(7)
syndromes, mbuc, phases = sample_shots(spec, tables, rng, 4, wp)

sq, mb, anc = validate_registers(c, spec)
sim = km.Simulator(batch_size=4, debug_print=False, seed=12345)
t0 = time.time()
sim.use_same_registers_as(c)
sim.write_across_shots(km.array(sq), to_bits(syndromes, 12))
sim.write_across_shots(km.array(mb), to_bits(mbuc, 12))
sim.do(c)
print(f"simulated in {time.time()-t0:.1f}s", flush=True)
reg_diff = sim.read_across_shots(km.array(sq)) ^ to_bits(syndromes, 12)
junk = sim.read_across_shots(km.array(anc))
print("S restore fails:", int(reg_diff.any()), f"({int(reg_diff.sum())} bit-errors)")
print("ancilla nonzero:", int(junk.any()), f"({int(junk.sum())} bit-errors)")
print("phase_flipped:", sim.read_phase_flipped_across_shots(), "expected:", phases)
