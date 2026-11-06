"""Bisect the failing M: true-position subset vs non-true subset."""
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi")
ART = ROOT / "artifacts" / "20261106_dqi_verify"
REF = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dqi.kmb"


def bits_of(values, width):
    v = np.asarray(values, dtype=np.int64)
    flat = np.array([(int(x) >> k) & 1 for x in v for k in range(width)], dtype=bool)
    return flat[:, None]


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    m = json.load(open(ART / "e_prime_full_dummy.json")) if False else None
    # original failing M: rebuild from the replay record stored in failing_pattern? use failures backup
    # The original mbuc is in the full-verify failure record; reconstruct from the replay pattern:
    # failing_pattern has pos/vals but not the full M. Read the saved record.
    src = json.load(open(ART / "e_prime_dummy.json")) if False else None
    # Use the mbuc captured in boundary_replay? It used failures.json which was later overwritten.
    # Reconstruct the original M by replaying the verifier RNG (as replay_failure did).
    sys.path.insert(0, str(VER))
    import kickmix as km  # noqa
    from dqi import verify_submission_dqi as V
    CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx"
    cs = km.Circuit.from_file(CIRC)
    h = V._circuit_sha256(cs)
    base = V._initial_seed(h, "")
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=102400)
    tables = V.FieldTables(km.GF2Field(12))
    wp = V.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    batch = V.DEFAULT_BATCH_SIZE
    starts = range(0, spec.num_shots, batch)
    seeds = np.random.SeedSequence(base, pool_size=8).generate_state(
        8 * len(starts), dtype=np.uint64).reshape(-1, 2, 4)
    bi = 30178 // batch
    start = bi * batch
    rng = np.random.default_rng(int.from_bytes(seeds[bi, 0], "little"))
    weights = rng.choice(len(wp), size=batch, p=wp)
    mbuc_all = rng.integers(0, 4095, size=(batch, spec.m), endpoint=True, dtype=np.int64)
    for shot in np.flatnonzero(weights):
        k = int(weights[shot])
        pos = rng.choice(spec.m, size=k, replace=False)
        vals = rng.integers(1, 4095, size=k, endpoint=True, dtype=np.int64)
        if int(shot) == 30178 - start:
            break
    M = mbuc_all[shot]
    c = km.Circuit.from_file(REF)
    mb_arr = km.array([b for j in range(4095) for b in c.register_data["E%d" % j]])
    syn_arr = km.array([q for i in range(70) for q in c.register_data["S%d" % i]])
    syn = np.array(pat["syndrome"], dtype=np.int64)

    def run(Mv):
        sim = km.Simulator(batch_size=1, debug_print=False, seed=777)
        sim.clear_for_shot()
        sim.use_same_registers_as(c)
        sim.write_across_shots(syn_arr, bits_of(syn, 12))
        sim.write_across_shots(mb_arr, bits_of(Mv, 12))
        sim.do(c)
        return bool(sim.read_phase_flipped_across_shots()[0])

    true_pos = set(pat["pos"])
    M_true = np.zeros(4095, dtype=np.int64)
    M_non = np.zeros(4095, dtype=np.int64)
    for p in range(4095):
        (M_true if p in true_pos else M_non)[p] = M[p]
    expected = False
    for name, Mv in (("full", M), ("true_only", M_true), ("non_true_only", M_non)):
        ph = run(Mv)
        print("%-14s phase=%s (expected %s)" % (name, ph, expected), flush=True)
    # multi-seed check on the reference with the correct M
    for seed in (1, 2, 3, 12345):
        sim = km.Simulator(batch_size=1, debug_print=False, seed=seed)
        sim.clear_for_shot(); sim.use_same_registers_as(c)
        sim.write_across_shots(syn_arr, bits_of(syn, 12))
        sim.write_across_shots(mb_arr, bits_of(M, 12))
        sim.do(c)
        print("reference seed %-6d phase=%s" % (seed, bool(sim.read_phase_flipped_across_shots()[0])), flush=True)
    # parity check on true_only
    par = sum(int(x).bit_count() for x in (np.array(pat["vals"], dtype=np.int64) & M_true[pat["pos"]])) & 1 == 1
    print("true_only expected parity:", par)
    print("non_true_only nonzero entries:", int(np.count_nonzero(M_non)))
    print("M_true entries:", int(np.count_nonzero(M_true)))


if __name__ == "__main__":
    main()
