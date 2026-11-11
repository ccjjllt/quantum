"""q28 branch-activity sweep at A3 ladder sites (prefix Simulator reads).

For candidate levels (16337, 16347): truncate circuit just before the
Z_POW, run prefix on a wider x grid x seeds, read q28 per shot.
Deletion shifts tracked phase by theta/2 * q28 exactly, so activity=1
shots are where the deletion bites; activity pattern + static bound
(theta/2 < min tol for L1/L2) decides the single .kmb candidate.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

import kickmix as km

HERE = Path(__file__).parent
MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"
OUT = HERE / "activity_sweep.json"

sys.path.insert(0, str(MAIN / ".worktree/invsqrt/data/competition/verifiers/invsqrt"))
import verify_submission_invsqrt as V  # noqa: E402

SPEC = V.ProblemSpecInvSqrt.for_n_p(10)
XS = np.array(sorted(set(
    [1, 2, 3, 4, 5, 7, 10, 16, 32, 64, 100, 161, 256, 500, 1000, 2000,
     5000, 10000, 50000, 100000, 500000, 1000000, 2000000, 3000000,
     3133452, 3133451, 2000001, 123456] +
    list(np.logspace(0, np.log10(3133452), 40).astype(int)))), dtype=np.uint64)
XS = XS[(XS >= 1) & (XS <= 3133452)]
SEEDS = (101, 202, 303)
SITES = (16337, 16347)


def load() -> tuple[list[str], list[str]]:
    c = km.Circuit.from_file(str(NEW_KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    txt = buf.getvalue().splitlines()
    return ([l for l in txt if l.startswith(("APPEND", "REGISTER"))],
            [l for l in txt if l and not l.startswith(("APPEND", "REGISTER"))])


def prefix_circuit(header, ops, k: int, path: Path) -> km.Circuit:
    path.write_text("\n".join(header) + "\n" + "\n".join(ops[:k]) + "\n")
    try:
        return km.Circuit.from_file(str(path))
    finally:
        path.unlink()


def main() -> None:
    header, ops = load()
    out: dict = {"xs": XS.tolist(), "seeds": list(SEEDS), "sites": {}}
    for k in SITES:
        assert ops[k].startswith("Z_POW q28 "), ops[k]
        circ = prefix_circuit(header, ops, k, HERE / f"tmp_prefix_{k}.kmx")
        x_reg, _ = V.validate_registers(circ, SPEC)
        tab: dict[str, list[int]] = {}
        for seed in SEEDS:
            sim = km.Simulator(batch_size=len(XS), seed=seed)
            sim.clear_for_shot()
            sim.write_across_shots(x_reg, V.to_bits(XS, SPEC.width))
            sim.do(circ)
            # NB: truncated prefix does not restore x; only q28 is read.
            q28 = np.asarray(
                sim.read_across_shots(km.array([km.q(28)]))).astype(int).ravel()
            assert q28.shape == XS.shape, q28.shape
            tab[str(seed)] = q28.tolist()
        m = np.array([tab[str(s)] for s in SEEDS])
        out["sites"][str(k)] = {
            "angle": ops[k].split()[2], "reads": tab,
            "frac_active": float(m.mean()),
            "active_xs": [int(x) for x in XS[m.any(axis=0)]],
        }
        print(k, "frac_active=%.3f" % float(m.mean()),
              "n_active_x=%d/%d" % (int(m.any(axis=0).sum()), len(XS)),
              flush=True)
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
