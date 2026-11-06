"""Build a real KMB for a single-mask replacement with its Clifford repair.

Recipe (validated against the public guard correction):
  1. before the rotation Z_POW, XOR h into the target wire (1 CCX / CX);
  2. after the following HMR q b<k>, apply the Clifford repair of the extra
     kickback (-1)^{m*h(x)}: for h = w_j one `Z qj if b<k>`, for h = w_a AND w_b
     one `CZ qa qb if b<k>`, for h = w_a AND (w_b XOR w_c) two CZs.
No extra qubit, no extra T; the repair is Clifford (free in the verifier model).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

import kickmix as km
import model as M
import patch

OUT = M.ART
WIRES = OUT / "wires"


def load_wire(i: int, j: int) -> np.ndarray:
    z = np.load(WIRES / f"cp_{i:02d}.npz")
    return np.unpackbits(z[f"w{j}"], bitorder="little")[: M.MAXX].astype(bool)


def build(theta, rot: int, pre_gates: list[str], repair: list[str]) -> km.Circuit:
    header, body = patch.load_lines(M.BASE_KMB)
    rot_idx = patch.rotation_indices(body)
    assert len(rot_idx) == 41
    tgt_line = rot_idx[rot]
    hmr_line = tgt_line + 1
    assert body[hmr_line].split()[0] == "HMR", body[hmr_line]
    out = []
    for i, line in enumerate(body):
        if i == tgt_line:
            out.extend(pre_gates)
        if i == hmr_line + 1:
            out.extend(repair)
        if i in rot_idx:
            p = line.split()
            out.append(f"Z_POW q{p[1][1:]} {patch.fmt_half_turns(theta[rot_idx.index(i)])}")
        else:
            out.append(line)
    text = "\n".join(header + out) + "\n"
    return km.Circuit.from_file(io.StringIO(text), format="kmx")


def main() -> None:
    # neutral free candidate: rot 15, g = f15 XOR w21, cost 0
    recs = json.loads((OUT / "search_lin_rot15.json").read_text())
    rec = next(r for r in recs if r["name"] == "lin 21" and not r["rejected"])
    theta = np.array(rec["theta_units"], dtype=np.int64)
    print("model margin", rec["margin"], "iters", rec["iters"])
    rep = [l for l in patch.load_lines(M.BASE_KMB)[1] if False]
    c = build(theta, 15, ["CX q21 q50"], ["Z q21 if b350"])
    print("nq", c.num_qubits, "nops", len(c))
    patch.write(c, OUT / "cand_rot15_lin21.kmb")
    (OUT / "cand_rot15_lin21.json").write_text(json.dumps(
        {"rot": 15, "name": "lin 21", "pre": ["CX q21 q50"],
         "repair": ["Z q21 if b350"], "theta_units": theta.tolist(),
         "model_margin": rec["margin"]}, indent=2) + "\n")
    print("wrote cand_rot15_lin21.kmb")


if __name__ == "__main__":
    main()
