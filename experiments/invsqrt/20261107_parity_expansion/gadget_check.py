"""Gadget check: a real KMB parity-rotation circuit, counted and phase-checked.

Part 1 (official verifier, reduced instance):
  x in [1,60], 22-bit register, K=64 parity terms on bits 0..5.  Any function on
  6 bits is exactly a 64-term parity sum, so this circuit is *exact* by
  construction and must PASS the official verifier.  It validates the gadget
  (parity by free CX, one Z_POW, uncompute), scratch cleanup, x restoration and
  the counted cost formula.  It is NOT an invsqrt competitor: max_x=60.

Part 2 (full domain, sampled):
  the K=41 natural-extension circuit is built for the real 22-bit register and
  simulated on a few hundred x values; the simulator's tracked phase is compared
  with the array model used for every table in this experiment.
"""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261107_parity_expansion"
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt.verify_submission_invsqrt import (  # noqa: E402
    ProblemSpecInvSqrt, from_bits, half_turns_to_units, reference_values,
    to_bits, validate_registers, verify)

N = 1 << 22
M = 3_133_452
MASK64 = (1 << 64) - 1


def fwht(a: np.ndarray) -> np.ndarray:
    a = np.array(a, dtype=np.float64, copy=True)
    n = a.size
    h = 1
    while h < n:
        b = a.reshape(-1, 2, h)
        u = b[:, 0, :].copy()
        v = b[:, 1, :].copy()
        b[:, 0, :] = u + v
        b[:, 1, :] = u - v
        h *= 2
    return a


def build_parity_circuit(terms: list[tuple[int, float]], nbits: int = 22,
                         constant: float = 0.0) -> km.Circuit:
    """Realise sum_S a_S chi_S(x) + constant turns.

    The builder Z_POW exponent is in half-turns (the verifier converts with
    half_turns_to_units), so an exponent h applies h/2 turns on |1>.  On the
    parity ancilla that is h/2 * [parity odd] = h/4 - (h/4) chi_S(x), hence
    h = -4 a_S, and the leftover -sum_S a_S = -P(0) is cancelled by one extra
    constant rotation (X; Z_POW; X, both X free).
    """
    b = km.CircuitBuilder()
    b.set_max_qubits(64)
    x = b.create_quantum_register(nbits, name="x")
    a = b.alloc_qubits(1)
    for S, av in terms:
        idx = [i for i in range(nbits) if (S >> i) & 1]
        for i in idx:
            b.cx(x[i], a[0])
        b.z_pow(a[0], -4 * av)
        for i in reversed(idx):
            b.cx(x[i], a[0])
    if constant:
        b.x(a[0])
        b.z_pow(a[0], 2 * constant)
        b.x(a[0])
    return b.finish_circuit()


def units(v: np.ndarray) -> np.ndarray:
    return np.array([int(round(p * 2**64)) & MASK64 for p in v], dtype=np.uint64)


def main() -> None:
    # ---------------- part 1: exact 64-term instance on x <= 60 ------------
    K = 6
    xv = np.arange(1 << K, dtype=np.float64)
    t = np.zeros(1 << K)
    t[1:] = 1.0 / np.sqrt(xv[1:])
    coef = fwht(t) / (1 << K)            # exact 64-term expansion on 6 bits
    terms = [(int(s), float(coef[s])) for s in range(1 << K) if abs(coef[s]) > 1e-18]
    const1 = float(sum(v for _, v in terms))
    circ = build_parity_circuit(terms, constant=const1)
    stats = circ.operation_statistics()
    print("part1: qubits", circ.num_qubits, "instructions", len(circ),
          "rotations", int(stats.num_z_pow(min_clifford_hierarchy_level=4)),
          "toffoli_like", int(stats.num_toffoli_like), "CX", dict(stats)["CX"])
    circ.to_file(OUT / "parity_exact_x60.kmb", format="kmb")

    spec = ProblemSpecInvSqrt(width=22, max_x=60, beta=Fraction(1),
                             precision_bits=24, shots_per_x=8, system_qubits=0)
    res = verify(circ, spec, seed=20261107, batch_size=8)
    print("part1 official verifier:", json.dumps(
        {k: res[k] for k in ("status", "score", "toffoli_equivalent", "toffoli_count",
                             "t_count", "rotation_count", "rotation_eps",
                             "worst_error_over_tolerance", "worst_x", "num_qubits")},
        indent=2))
    c_rot = (0.56 * math.log2(1 / res["rotation_eps"]) + 5.3) / 4
    print(f"  counted C = {res['toffoli_equivalent']:.6f}; "
          f"K*c_rot = {res['rotation_count']*c_rot:.6f}")

    # ---------------- part 2: full-domain K=41 phase model vs simulator ----
    f = np.zeros(N)
    f[1:] = 1.0 / np.sqrt(np.arange(1, N, dtype=np.float64))
    f[0] = f[1]
    coef41 = fwht(f) / N
    order = np.argsort(np.abs(coef41))[::-1][:41]
    terms41 = [(int(s), float(coef41[s])) for s in order]
    const41 = float(sum(v for _, v in terms41))
    circ41 = build_parity_circuit(terms41, constant=const41)
    C = np.zeros(N)
    C[order] = coef41[order]
    p_model = fwht(C)[1:M + 1]
    g = 1.0 / np.sqrt(np.arange(1, M + 1, dtype=np.float64))
    g[0] = 0.0
    print("\npart2: qubits", circ41.num_qubits, "instructions", len(circ41),
          "rotations", int(circ41.operation_statistics().num_z_pow(
              min_clifford_hierarchy_level=4)))

    full = ProblemSpecInvSqrt(width=22, max_x=M, beta=Fraction(1),
                             precision_bits=24, shots_per_x=1, system_qubits=0)
    x_reg, scratch = validate_registers(circ41, full)
    rng = np.random.default_rng(7)
    xs = np.array(sorted(set(
        list(range(1, 65))
        + [1 << j for j in range(0, 22)]
        + [(1 << j) + d for j in range(1, 22) for d in (-1, 0, 1)]
        + [M - i for i in range(8)]
        + rng.integers(1, M + 1, 96).tolist())), dtype=np.uint64)
    sim = km.Simulator(batch_size=len(xs), debug_print=False,
                       counting_operations=True, seed=20261107)
    sim.clear_for_shot()
    sim.write_across_shots(x_reg, to_bits(xs, 22))
    sim.do(circ41)
    xr = from_bits(sim.read_across_shots(x_reg))
    dirty = sim.read_across_shots(scratch)
    sim_units = np.array([half_turns_to_units(sim.read_shot_phase(i))
                          for i in range(len(xs))], dtype=np.uint64)
    du = (sim_units - units(p_model[xs.astype(np.int64) - 1])).view(np.int64)
    tgt, tlu = reference_values(full, xs)
    e = (sim_units - tgt).view(np.int64)
    ratio_sim = np.abs(e) / tlu.astype(np.int64)
    em = p_model[xs.astype(np.int64) - 1] - g[xs.astype(np.int64) - 1]
    em -= np.round(em)
    ratio_model = np.abs(em) / (tlu.astype(np.float64) / 2**64)
    print("  x restored:", bool(np.array_equal(xr, xs)),
          "| scratch clean:", not bool(dirty.any()),
          "| sample", len(xs))
    print("  simulator phase - array model: max |diff| =", int(np.abs(du).max()),
          "units of 2^-64 turns =", float(np.abs(du).max() / 2**64), "turns")
    print("  worst error/tol on sample: simulator", float(ratio_sim.max()),
          "| array model", float(ratio_model.max()))
    json.dump({"part1": {k: res[k] for k in res},
               "part2": {"sample": int(len(xs)),
                         "x_restored": bool(np.array_equal(xr, xs)),
                         "scratch_clean": not bool(dirty.any()),
                         "max_phase_model_diff_units": int(np.abs(du).max()),
                         "worst_ratio_simulator": float(ratio_sim.max()),
                         "worst_ratio_model": float(ratio_model.max()),
                         "num_qubits": circ41.num_qubits,
                         "rotations": int(circ41.operation_statistics().num_z_pow(
                             min_clifford_hierarchy_level=4))}},
              open(OUT / "gadget_check.json", "w"), indent=2)
    print("\nwrote", OUT / "gadget_check.json")


if __name__ == "__main__":
    main()
