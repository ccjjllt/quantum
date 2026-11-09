"""Same-branch mask comparison for the 11 suspect rotations.

Method: for each of the 11 Z_POW positions, truncate the frontier kmx right after
it and read q28 with the REAL kickmix Simulator. All 11 prefix circuits share the
same op prefix, so with the SAME explicit Simulator seed the HMR outcome stream
on the shared prefix is identical -> same branch -> q28 readouts are comparable
across cuts. Any (x, seed) with differing q28 across cuts disproves equal masks.

Writes branch_check.json.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import kickmix as km
import numpy as np

KMB = "artifacts/20261108_public_frontier/release/invsqrt.kmb"
CUTS = [25852, 25860, 25868, 25876, 25883, 25889, 25895, 25903, 25908, 25918, 25931]
XS = [1, 2, 3, 5, 64, 161, 1000, 3133452]
SEEDS = [101, 202, 303]
W = 22


def load():
    c = km.Circuit.from_file(KMB)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    return hdr, ops


def read_q28_at(hdr, ops, cut, xs, seed):
    kmx = "\n".join(hdr + ops[:cut + 1]) + "\n"
    circ = km.Circuit.from_file(io.StringIO(kmx), format="kmx")
    sim = km.Simulator(batch_size=len(xs), debug_print=False,
                       counting_operations=False, seed=seed)
    sim.clear_for_shot()
    bits = np.array([((np.array(xs, dtype=np.uint64) >> b) & 1).astype(bool).tolist()
                     for b in range(W)])
    sim.write_across_shots(km.array([km.q(i) for i in range(W)]), bits)
    sim.do(circ)
    r = sim.read_across_shots(km.array([km.q(28)]))
    assert r.shape == (1, len(xs)), r.shape
    return [bool(v) for v in r[0].tolist()]


def main():
    hdr, ops = load()
    for cut in CUTS:
        assert ops[cut].startswith("Z_POW q28"), (cut, ops[cut])
    table = {}
    for seed in SEEDS:
        cols = {}
        for cut in CUTS:
            cols[str(cut)] = read_q28_at(hdr, ops, cut, XS, seed)
        table[str(seed)] = cols
    # agreement: for each (x, seed), q28 identical across all 11 cuts?
    disagreements = []
    for seed in SEEDS:
        for xi, x in enumerate(XS):
            vals = [table[str(seed)][str(c)][xi] for c in CUTS]
            if any(v != vals[0] for v in vals):
                disagreements.append({"seed": seed, "x": x,
                                      "q28_across_cuts": vals})
    out = {"cuts": CUTS, "xs": XS, "seeds": SEEDS,
           "q28_table": table,
           "n_disagreements": len(disagreements),
           "disagreements_sample": disagreements[:10]}
    Path("experiments/invsqrt/20261109_tphase_fusion/branch_check.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"disagreements: {len(disagreements)} / {len(SEEDS)*len(XS)} (x,seed) cells")
    for d in disagreements[:10]:
        print(d)
    # per-cut readout strings for eyeballing
    for seed in SEEDS:
        print(f"--- seed {seed} ---")
        for cut in CUTS:
            print(f"  cut {cut}: {''.join('1' if v else '0' for v in table[str(seed)][str(cut)])}")


if __name__ == "__main__":
    main()
