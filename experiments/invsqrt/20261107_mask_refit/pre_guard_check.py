"""Circuit-level check of the HMR kickback repair (guard correction).

The public guard correction is the CCX `CCX q54 q18 q50` before Z_POW 15 plus
the two Clifford repairs `CZ q54 q18 if b350` / `CZ q54 q27 if b350` after the
HMR.  Removing only the CCX leaves an over-correction: the phase becomes
measurement-branch dependent.  Removing both restores branch independence and
the phase difference to the baseline is exactly -theta_15 on guard(x)=1.

Writes artifacts/20261107_mask_refit/pre_guard_branch_check.json and
pre_guard_v2.kmb.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np

import kickmix as km
import model as M
import patch

OUT = M.ART
XS = np.array([161, 258, 1000, 8192, 52229, 1_000_000], dtype=np.uint64)
XREG = km.array([km.q(i) for i in range(22)])


def phase_units(path: Path, xs: np.ndarray, seed: int) -> list[int]:
    c = km.Circuit.from_file(path)
    sim = km.Simulator(batch_size=len(xs), debug_print=False,
                       counting_operations=True, seed=seed)
    sim.clear_for_shot()
    bits = ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1
    sim.write_across_shots(XREG, bits)
    sim.do(c)
    out = []
    for i in range(len(xs)):
        fr = sim.read_shot_phase(i)
        n, d = fr.as_integer_ratio()
        out.append(((n << 63) // d) & ((1 << 64) - 1))
    return out


def build_variant(remove: tuple[int, ...], dst: Path) -> None:
    header, body = patch.load_lines(M.BASE_KMB)
    nb = [l for i, l in enumerate(body) if i not in remove]
    text = "\n".join(header + nb) + "\n"
    c = km.Circuit.from_file(io.StringIO(text), format="kmx")
    patch.write(c, dst)


def main() -> None:
    # ops: 25406 = CCX guard, 25410/25411 = the two CZ repairs
    build_variant((25406,), OUT / "pre_guard_no_repair.kmb")
    build_variant((25406, 25410, 25411), OUT / "pre_guard_v2.kmb")
    res = {"xs": XS.tolist(), "seeds": [1, 2, 3, 4]}
    for name, path in [("baseline", M.BASE_KMB),
                       ("remove_ccx_only", OUT / "pre_guard_no_repair.kmb"),
                       ("remove_ccx_and_cz", OUT / "pre_guard_v2.kmb")]:
        runs = [phase_units(path, XS, s) for s in res["seeds"]]
        distinct = [len(set(v)) for v in zip(*runs)]
        res[name] = {"distinct_phases_per_x": distinct, "phases_seed1": runs[0]}
        print(name, "distinct phases per x over 4 seeds:", distinct, flush=True)
    base = res["baseline"]["phases_seed1"]
    d = [(int(a) - int(b)) % (1 << 64) for a, b in zip(res["remove_ccx_and_cz"]["phases_seed1"], base)]
    d = [v if v < 2**63 else v - 2**64 for v in d]
    res["v2_minus_baseline_turns"] = [v / 2**64 for v in d]
    res["theta15_turns"] = float(M.load_model()["thetas"][15]) / 2**63
    print("v2 - baseline (turns):", res["v2_minus_baseline_turns"])
    print("theta15 (turns):", res["theta15_turns"])
    (OUT / "pre_guard_branch_check.json").write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
