"""Compare the global phase of Syed V9 prefixes with the full circuit.

The circuit is a classical permutation plus global phase, so truncating the
recovery pass is legal only if the remaining phase still equals the target
phase. This script cuts the .kmx stream at top-level stage boundaries and
simulates every prefix on the same official-distribution shots.
"""
import argparse
import io
import json
from pathlib import Path
import time

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
import importlib.util
import sys
spec_path = ROOT / 'data/competition/verifiers/dqi/verify_submission_dqi.py'
spec = importlib.util.spec_from_file_location('v', spec_path)
v = importlib.util.module_from_spec(spec)
sys.modules['v'] = v
spec.loader.exec_module(v)

CUTS = {
    'scan': 41252602,
    'unconvert': 46497681,
    'unsynthesis': 52196367,
}


def dump_kmx(target: Path) -> None:
    if target.exists():
        return
    c = km.Circuit.from_file(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb', format='kmb')
    t = time.monotonic()
    with open(target, 'wb') as f:
        c.to_file(f, format='kmx')
    print(f'dumped {target} ({target.stat().st_size/1e9:.2f} GB) in {time.monotonic()-t:.1f}s')


def make_prefixes(src: Path, out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    with open(src, 'rb') as f:
        current = io.BytesIO()
        written = set()
        for i, line in enumerate(f):
            current.write(line)
            if i + 1 in CUTS.values():
                name = next(k for k, x in CUTS.items() if x == i + 1)
                p = out / f'prefix_{name}.kmx'
                p.write_bytes(current.getvalue())
                paths[name] = p
                written.add(name)
        full = out / 'full.kmx'
        if not full.exists():
            full.write_bytes(current.getvalue())
        paths['full'] = full
    print('prefix sizes:', {k: f'{p.stat().st_size/1e9:.2f}GB' for k, p in paths.items()})
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=int, default=256)
    ap.add_argument('--seed', type=int, default=12345)
    ap.add_argument('--work', default='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/dqi_phase')
    args = ap.parse_args()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    kmx = work / 'syed_v9.kmx'
    dump_kmx(kmx)
    prefixes = make_prefixes(kmx, work)

    dqi = v.ProblemSpecDQI.benchmark_instance(num_shots=args.shots)
    tables = v.FieldTables(km.GF2Field(dqi.degree))
    weights = v.optimal_dqi_weights(dqi.m, dqi.max_errors, dqi.degree, dqi.r) ** 2
    rng = np.random.default_rng(987654321)
    syndromes, mbuc, phases = v.sample_shots(dqi, tables, rng, args.shots, weights)
    syn_bits = v.to_bits(syndromes, dqi.degree)
    mask_bits = v.to_bits(mbuc, dqi.degree)

    results = {}
    for name, path in prefixes.items():
        t = time.monotonic()
        c = km.Circuit.from_file(path, format='kmx')
        syn, masks, anc = v.validate_registers(c, dqi)
        sim = km.Simulator(batch_size=args.shots, debug_print=False, counting_operations=True, seed=args.seed)
        sim.use_same_registers_as(c)
        sim.write_across_shots(km.array(syn), syn_bits)
        sim.write_across_shots(km.array(masks), mask_bits)
        sim.do(c)
        actual_phase = sim.read_phase_flipped_across_shots()
        syn_after = sim.read_across_shots(km.array(syn))
        junk = sim.read_across_shots(anc) if len(anc) else np.zeros((0, args.shots), dtype=bool)
        stats = sim.operation_statistics()
        results[name] = {
            'ops': len(c),
            'qubits': c.num_qubits,
            'static_T': c.operation_statistics().num_toffoli_like,
            'mean_T': stats.num_toffoli_like / args.shots,
            'phase_mismatch': int((actual_phase ^ phases).sum()),
            'syndrome_changed_shots': int((syn_after ^ syn_bits).any(axis=0).sum()),
            'junk_shots': int(junk.any(axis=0).sum()),
            'elapsed_seconds': time.monotonic() - t,
        }
        print(name, json.dumps(results[name]), flush=True)
    out = work / 'phase_probe.json'
    out.write_text(json.dumps({'shots': args.shots, 'seed': args.seed, 'cuts': CUTS, 'results': results}, indent=1))
    print('wrote', out)


if __name__ == '__main__':
    main()
