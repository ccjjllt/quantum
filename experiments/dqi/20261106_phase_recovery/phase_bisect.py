"""Locate the point inside the recovery pass where the target phase becomes exact."""
import argparse
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import kickmix as km

import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('v', ROOT / 'data/competition/verifiers/dqi/verify_submission_dqi.py')
v = importlib.util.module_from_spec(spec)
sys.modules['v'] = v
spec.loader.exec_module(v)

CUTS = [52196367, 52775846, 53355326, 53934806, 54514285, 55093765,
        55673245, 56252724, 56832204, 57411684, 57701424, 57991164]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=int, default=128)
    ap.add_argument('--seed', type=int, default=12345)
    ap.add_argument('--work', default='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/dqi_phase')
    args = ap.parse_args()
    work = Path(args.work)
    src = work / 'syed_v9.kmx'

    dqi = v.ProblemSpecDQI.benchmark_instance(num_shots=args.shots)
    tables = v.FieldTables(km.GF2Field(dqi.degree))
    weights = v.optimal_dqi_weights(dqi.m, dqi.max_errors, dqi.degree, dqi.r) ** 2
    syndromes, mbuc, phases = v.sample_shots(dqi, tables, np.random.default_rng(987654321), args.shots, weights)
    syn_bits = v.to_bits(syndromes, dqi.degree)
    mask_bits = v.to_bits(mbuc, dqi.degree)

    rows = []
    for cut in CUTS:
        path = work / f'cut_{cut}.kmx'
        if not path.exists():
            with open(path, 'wb') as out:
                subprocess.run(['head', '-n', str(cut), str(src)], stdout=out, check=True)
        t = time.monotonic()
        c = km.Circuit.from_file(path, format='kmx')
        syn, masks, anc = v.validate_registers(c, dqi)
        sim = km.Simulator(batch_size=args.shots, debug_print=False, counting_operations=True, seed=args.seed)
        sim.use_same_registers_as(c)
        sim.write_across_shots(km.array(syn), syn_bits)
        sim.write_across_shots(km.array(masks), mask_bits)
        sim.do(c)
        actual = sim.read_phase_flipped_across_shots()
        syn_after = sim.read_across_shots(km.array(syn))
        junk = sim.read_across_shots(anc) if len(anc) else np.zeros((0, args.shots), dtype=bool)
        stats = sim.operation_statistics()
        row = {
            'cut': cut,
            'ops': len(c),
            'static_T': c.operation_statistics().num_toffoli_like,
            'mean_T': stats.num_toffoli_like / args.shots,
            'phase_mismatch': int((actual ^ phases).sum()),
            'syndrome_changed': int((syn_after ^ syn_bits).any(axis=0).sum()),
            'junk_shots': int(junk.any(axis=0).sum()),
            'seconds': round(time.monotonic() - t, 2),
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    (work / f'phase_bisect_{args.shots}.json').write_text(json.dumps({'shots': args.shots, 'seed': args.seed, 'rows': rows}, indent=1))


if __name__ == '__main__':
    main()
