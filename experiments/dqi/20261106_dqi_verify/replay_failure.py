"""Replay the verifier RNG to recover the error pattern of the failing shot 30178."""
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402

CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx"
FAIL_SHOT = 30178
OUT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify")


def main():
    c = km.Circuit.from_file(CIRC)
    h = V._circuit_sha256(c)
    base = V._initial_seed(h, "")
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=102400)
    tables = V.FieldTables(km.GF2Field(spec.degree))
    wp = V.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    batch = V.DEFAULT_BATCH_SIZE
    print("batch size", batch, "num batches", (spec.num_shots + batch - 1) // batch)
    starts = range(0, spec.num_shots, batch)
    seeds = np.random.SeedSequence(base, pool_size=8).generate_state(
        8 * len(starts), dtype=np.uint64).reshape(-1, 2, 4)
    bi = FAIL_SHOT // batch
    start = bi * batch
    rng = np.random.default_rng(int.from_bytes(seeds[bi, 0], "little"))
    weights = rng.choice(len(wp), size=batch, p=wp)
    mbuc = rng.integers(0, (1 << spec.degree) - 1, size=(batch, spec.m), endpoint=True, dtype=np.int64)
    rows = np.arange(1, spec.n + 1, dtype=np.int64)[:, None]
    found = None
    for shot in np.flatnonzero(weights):
        k = int(weights[shot])
        pos = rng.choice(spec.m, size=k, replace=False)
        vals = rng.integers(1, (1 << spec.degree) - 1, size=k, endpoint=True, dtype=np.int64)
        if int(shot) == FAIL_SHOT - start:
            exps = (tables.log[vals][None, :] + rows * pos[None, :]) % tables.order
            syn = np.bitwise_xor.reduce(tables.antilog[exps], axis=1)
            phase = sum(int(x).bit_count() for x in vals & mbuc[shot, pos]) & 1 == 1
            found = {"shot": FAIL_SHOT, "batch_start": start, "k": k,
                     "pos": pos.tolist(), "vals": vals.tolist(),
                     "phase": bool(phase), "syndrome": syn.tolist(),
                     "mbuc_at_pos": mbuc[shot, pos].tolist()}
            break
    print(json.dumps(found, indent=1)[:2000])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "failing_pattern.json").write_text(json.dumps(found, indent=1) + "\n")


if __name__ == "__main__":
    main()
