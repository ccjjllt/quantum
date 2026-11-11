"""S1 compute/uncompute same-triplet census on new family 26ebf39d (read-only).

Input (readonly, main repo): artifacts/20261110_gengsr_252268/release/invsqrt.kmb
  SHA-256 26ebf39df3b13e5fd2d923d1b9988043b107b64f6e21efc5cc9bc76f5d56adec
  62Q / 36686 ops. S1=[8893:16329), A3=[16329:16499), S2=[16499:36427).

Method (verbatim caliber of 20261110_s1m1/s1m1_pilot.py):
  - k2: unordered-control + target identical CCX pairs, both inside S1,
    inline-conditional excluded (CCX control-symmetric口径).
  - k3+: same key with >=3 occurrences inside S1 (reported, not expanded).
  - convertibility = reachable-state product equality over all 3133452 inputs
    via bit-parallel word trace (audit_gengsr.py::run_bit_parallel_audit口径,
    unconditional classical skeleton X/CX/CCX/SWAP/CSWAP/HMR; diagonal gates
    do not affect bits). diff>0 => accumulator reuse / line recycle, not a
    Bennett-true recompute => not convertible.
  - A3 pre-step: static bound only (deletion shift <= ang/2 vs min tol from
    verifier reference_values). Full 21x24 Simulator grid + the single
    official-verifier arbitration already exist in 20261110_hosen_sens and
    are cited, not rerun.

Writes only census.json in this dir. No .kmb built. No verifier run.
macOS: .venv PyPI kickmix (never the Kaggle-Linux kickmix.so in data/).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

WORK = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt")
MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"
NEW_SHA = "26ebf39df3b13e5fd2d923d1b9988043b107b64f6e21efc5cc9bc76f5d56adec"
HERE = Path(__file__).parent

S1 = (8893, 16329)
A3 = (16329, 16499)
S2 = (16499, 36427)
N_INPUTS = 3133452
A3LEVELS = [16337, 16347, 16355, 16363, 16371, 16378, 16386, 16394, 16402,
            16410, 16417, 16424, 16431, 16438, 16446, 16454, 16462, 16470,
            16478, 16486, 16493]

sys.path.insert(0, str(MAIN / "data/competition/verifiers/invsqrt"))
import verify_submission_invsqrt as V  # noqa: E402  (readonly: reference_values only)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ops(kmb_path: Path) -> list[str]:
    c = km.Circuit.from_file(str(kmb_path))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [ln for ln in buf.getvalue().splitlines()
            if ln and not ln.startswith(("APPEND", "REGISTER"))]


def same_triplet_groups(ops: list[str]) -> tuple[list, list]:
    pos: dict = defaultdict(list)
    for g, ln in enumerate(ops):
        if ln.startswith("CCX") and " if " not in ln:
            p = ln.split()
            pos[(tuple(sorted([p[1], p[2]])), p[3])].append(g)
    k2 = [(k, v) for k, v in pos.items()
          if len(v) == 2 and S1[0] <= v[0] < S1[1] and S1[0] <= v[1] < S1[1]]
    k3 = [(k, v) for k, v in pos.items()
          if len(v) >= 3 and all(S1[0] <= g < S1[1] for g in v)]
    return k2, k3


def reachable_product_diffs(ops: list[str], pairs) -> list[dict]:
    n_words = (N_INPUTS + 63) // 64
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = n_words * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(n_words, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    last_mask = ((np.uint64(1) << np.uint64(N_INPUTS % 64)) - np.uint64(1)) \
        if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
    ones = np.full(n_words, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = last_mask
    watch = {g: k for k, v in pairs for g in v}
    rec: dict = {}
    depth = 0
    for idx, ln in enumerate(ops):
        if idx in watch:
            (ct, _) = watch[idx]
            a = (q[int(ct[0][1:])] & q[int(ct[1][1:])]).copy()
            a[-1] &= last_mask
            rec[idx] = a
        if ln.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if ln.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in ln):
            continue
        p, op = ln.split(), ln.split()[0]
        if op in ("HMR", "R"):
            q[int(p[1][1:])].fill(0)
        elif op == "X":
            q[int(p[1][1:])] ^= ones
        elif op == "CX":
            q[int(p[2][1:])] ^= q[int(p[1][1:])]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[a], q[b] = q[b].copy(), q[a].copy()
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = q[a] & q[b]
            prod[-1] &= last_mask
            q[t] ^= prod
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = q[cc] & (q[a] ^ q[b])
            prod[-1] &= last_mask
            q[a] ^= prod
            q[b] ^= prod
    out = []
    for k, v in sorted(pairs, key=lambda kv: kv[1][1] - kv[1][0]):
        d = rec[v[0]] ^ rec[v[1]]
        d[-1] &= last_mask
        mid = ops[v[0] + 1:v[1]]
        out.append({
            "product": [list(k[0]), k[1]], "occurrences": v,
            "span": v[1] - v[0],
            "hmr_between": sum(1 for m in mid if m.startswith(("HMR", "R "))),
            "pop1": int(np.sum(np.bitwise_count(rec[v[0]]))),
            "pop2": int(np.sum(np.bitwise_count(rec[v[1]]))),
            "reachable_diff": int(np.sum(np.bitwise_count(d))),
        })
    return out


def main() -> None:
    assert sha256_file(NEW_KMB) == NEW_SHA, "new KMB hash mismatch"
    ops = parse_ops(NEW_KMB)
    assert len(ops) == 36686, len(ops)

    def cnt(reg, op):
        lo, hi = reg
        return sum(1 for i in range(lo, hi) if ops[i].split()[0] == op)

    region = {"S1_CCX": cnt(S1, "CCX"), "S2_CCX": cnt(S2, "CCX"),
              "A3_CCX": cnt(A3, "CCX"), "A3_Z_POW": cnt(A3, "Z_POW"),
              "A3_CSWAP": cnt(A3, "CSWAP"), "A3_HMR": cnt(A3, "HMR")}
    assert region["S1_CCX"] == 365, region
    assert region["S2_CCX"] == 499, region
    assert (region["A3_CCX"], region["A3_Z_POW"], region["A3_CSWAP"],
            region["A3_HMR"]) == (7, 21, 70, 24), region
    assert all(ops[i].startswith("Z_POW q28 ") for i in A3LEVELS)

    k2, k3 = same_triplet_groups(ops)
    rows = reachable_product_diffs(ops, k2)
    convertible = [r for r in rows if r["reachable_diff"] == 0]

    spec = V.ProblemSpecInvSqrt.for_n_p(10)
    xs = np.array([1, 2, 3, 5, 64, 161, 1000, 3133452], dtype=np.uint64)
    _, tol = V.reference_values(spec, xs)
    min_tol = int(tol.min())
    static_rows = []
    for i in A3LEVELS:
        ang = Fraction(ops[i].split()[2])
        maxd = (int(ang.numerator) << 64) // (2 * int(ang.denominator))
        static_rows.append({"drop_idx": i,
                            "angle_turns": float(ang) / 2,
                            "max_shift_units": maxd,
                            "static_safe_all_x": bool(maxd < min_tol)})
    static_rows.sort(key=lambda r: r["angle_turns"])

    out = {
        "inputs": {"new_kmb": str(NEW_KMB), "new_sha256": NEW_SHA,
                   "new_ops": len(ops), "S1": list(S1), "A3": list(A3),
                   "S2": list(S2), "n_inputs_verified": N_INPUTS},
        "region_gate_check": region,
        "s1_same_triplet": {"n_k2_pairs": len(k2),
                            "n_k3plus_groups": len(k3),
                            "k3plus": [{"product": [list(k[0]), k[1]],
                                        "occurrences": v} for k, v in k3],
                            "pairs_ascending_span": rows},
        "convertible_pairs": len(convertible),
        "criterion_ge3_met": bool(len(convertible) >= 3),
        "A3_static_bound": {"min_tol_units": min_tol,
                            "rows_ascending": static_rows},
        "refs": {
            "s1m1_pilot": "experiments/invsqrt/20261110_s1m1/s1m1_pilot.py",
            "hosen_census": "experiments/invsqrt/20261110_hosen_sens/hosen_census.py",
            "full_grid": "experiments/invsqrt/20261110_hosen_sens/sens_check.json",
            "verifier_fail": "experiments/invsqrt/20261110_hosen_sens/verifier_drop16337.log"},
    }
    (HERE / "census.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"region_gate_check": region,
                      "n_k2_pairs": len(k2), "n_k3plus_groups": len(k3),
                      "convertible_pairs": len(convertible),
                      "criterion_ge3_met": bool(len(convertible) >= 3),
                      "min_reachable_diff": min(r["reachable_diff"] for r in rows),
                      "A3_static_safe": [r["drop_idx"] for r in static_rows
                                         if r["static_safe_all_x"]],
                      "min_tol_units": min_tol}, indent=1))


if __name__ == "__main__":
    main()
