"""Paired native comparison Kirill-V5 baseline vs migrated nofallback (actual bytes).

Deterministic 21760-input set (inputs(20261103,16384) + MAXX repeats to 256-block),
seeds 101/202/303. Reports restore/scratch/phase/tolerance diffs. Sampling only.
"""
from __future__ import annotations
import argparse, hashlib, json, random
from pathlib import Path
import numpy as np
import kickmix as km

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
import sys
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official

BASE = ROOT / "artifacts/20261104_public_refresh/kirill_v5_invsqrt.kmb"
BASE_SHA = "ed77292a0e4a267e62235055cc2ab7faaa30b15d8a150bab79f34e5c1b8f172b"
MAXX = 3133452


def inputs(seed, n):
    rng = random.Random(seed)
    xs = set(range(1, 4097))
    xs.update(rng.randrange(1, MAXX + 1) for _ in range(n))
    for bit in range(22):
        xs.update(x for x in (2 ** bit - 2, 2 ** bit - 1, 2 ** bit, 2 ** bit + 1, 2 ** bit + 2)
                  if 1 <= x <= MAXX)
    for a in range(256):
        for d in (0, 1, 8191, 8192, 16382, 16383):
            m = (1 << 21) | ((a & 127) << 14) | d
            for lz in (a >> 7, 2 + (a >> 7)):
                if not m % (1 << lz) and 1 <= m >> lz <= MAXX:
                    xs.add(m >> lz)
    return sorted(xs)


def run(circuit, xs, seed):
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    xreg, scratch = official.validate_registers(circuit, spec)
    sim = km.Simulator(batch_size=256, seed=seed, counting_operations=True)
    phases, failures = [], []
    pad = 0
    for pos in range(0, len(xs), 256):
        real = xs[pos:pos + 256]
        arr = np.asarray(real + [real[-1]] * (256 - len(real)), dtype=np.uint64)
        pad += 256 - len(real)
        sim.clear_for_shot()
        sim.write_across_shots(xreg, official.to_bits(arr, 22))
        sim.do(circuit)
        restored = official.from_bits(sim.read_across_shots(xreg))
        dirty = np.asarray(sim.read_across_shots(scratch)).any(axis=0)
        for k, x in enumerate(real):
            if restored[k] != x or dirty[k]:
                failures.append({'x': x, 'input_restored': bool(restored[k] == x),
                                 'scratch_dirty': bool(dirty[k])})
            phases.append(official.half_turns_to_units(sim.read_shot_phase(k)))
    stats = sim.operation_statistics()
    n_total = len(xs) + pad
    return {'seed': seed, 'inputs': len(xs), 'padding': pad, 'failures': failures[:20],
            'n_failures': len(failures),
            'mean_toffoli_with_padding': int(stats.num_toffoli_like) / n_total,
            'mean_T_with_padding': int(stats.num_t_like) / n_total,
            'mean_rotations_with_padding': int(stats.num_z_pow(min_clifford_hierarchy_level=4)) / n_total}, phases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--n", type=int, default=16384)
    args = ap.parse_args()
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    orig = km.Circuit.from_file(BASE)
    cand = km.Circuit.from_file(args.candidate)
    assert orig.num_qubits == cand.num_qubits == 62
    xs = inputs(20261103, args.n)
    xs += [MAXX] * (256 - len(xs) % 256) if len(xs) % 256 else []
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    target, tol = official.reference_values(spec, np.asarray(xs, dtype=np.uint64))
    rows = []
    for seed in (101, 202, 303):
        rb, pb = run(orig, xs, seed); rc, pc = run(cand, xs, seed)
        errs, mismatch, worst = [], [], (0., 0)
        for j, x in enumerate(xs):
            err = (pc[j] - int(target[j]) + (1 << 63)) % (1 << 64) - (1 << 63)
            if abs(err) > int(tol[j]): errs.append(x)
            if pc[j] != pb[j]: mismatch.append(x)
            worst = max(worst, (abs(err) / int(tol[j]), x))
        row = {'seed': seed, 'baseline': rb, 'candidate': rc,
               'phase_mismatches': len(mismatch), 'phase_mismatch_examples': mismatch[:10],
               'tolerance_failures': len(errs), 'worst_ratio': worst[0], 'worst_x': worst[1],
               'toffoli_saved': rb['mean_toffoli_with_padding'] - rc['mean_toffoli_with_padding']}
        rows.append(row); print(json.dumps(row), flush=True)
    result = {'scope': 'sampled circuit comparison; NOT full official verification',
              'baseline_sha256': BASE_SHA,
              'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'qubits': cand.num_qubits, 'rows': rows,
              'pass': all(not r['candidate']['n_failures'] and not r['phase_mismatches']
                          and not r['tolerance_failures'] for r in rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    raise SystemExit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
