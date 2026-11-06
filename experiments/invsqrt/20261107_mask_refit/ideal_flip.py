"""Ideal single-mask flip and its fixed-angle gain, per rotation.

For rotation i with residual R = T - phase and mask f_i, flipping f_i at x
changes R by -theta_i (0->1) or +theta_i (1->0).  The locally ideal flip set is
  h = {f_i=0 and R > theta_i/2} union {f_i=1 and R < -theta_i/2},
which moves R toward zero by theta_i everywhere it is large.  This script
measures the fixed-angle margin of that ideal h and the raw upside theta_i.
"""
from __future__ import annotations

import json
import time

import numpy as np

import model as M

OUT = M.ART


def main() -> None:
    m = M.load_model()
    masks, thetas, T, tol = m["masks"], m["thetas"], m["T"], m["tol"]
    ph = M.phase_of(masks, thetas)
    R = M.err_of(ph, T)  # phase - T; flip 0->1 adds +theta to phase -> +theta to R
    M0 = int((tol - np.abs(R)).min())
    print("baseline margin", M0, flush=True)
    rec = []
    for i in range(41):
        th = int(thetas[i])
        f = masks[i]
        # R = phase - T.  Flipping f 0->1 changes R by +theta, 1->0 by -theta.
        # Ideal: flip 0->1 when R < -theta/2, flip 1->0 when R > theta/2.
        h = ((~f) & (R < -th / 2)) | (f & (R > th / 2))
        Rn = np.where(h, R + np.where(f, -th, th), R)
        Mn = int((tol - np.abs(Rn)).min())
        # theoretical: |R| reduced by th where flipped
        rec.append({
            "rot": i, "theta_units": th, "theta_turns": th / 2**64,
            "flip_count": int(h.sum()),
            "margin_fixed": Mn,
            "gain_fixed": Mn - M0,
            "gain_over_M0": Mn / M0,
            "cost_C_if_1ccx": 41 * 0.56 / 4 * np.log2(max(Mn, 1) / M0) - 1.0,
            "cost_C_if_free": 41 * 0.56 / 4 * np.log2(max(Mn, 1) / M0),
        })
        print(f"rot {i:2d} th={th:>18d} flips={int(h.sum()):8d} "
              f"margin {Mn/1e6:10.2f}M gain {Mn/M0:6.2f}x "
              f"C_free={rec[-1]['cost_C_if_free']:+6.2f} "
              f"C_1ccx={rec[-1]['cost_C_if_1ccx']:+6.2f}", flush=True)
    (OUT / "ideal_flip.json").write_text(json.dumps({"baseline_margin": M0, "rows": rec}, indent=2) + "\n")


if __name__ == "__main__":
    main()
