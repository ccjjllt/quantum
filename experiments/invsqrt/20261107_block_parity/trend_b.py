"""Cheap trend check beyond b = 12: the Bessel lower bound on K per block size.

The task fixes b = 6..12.  This script only answers the obvious follow-up
("would a bigger block rescue the family?") without a full water-fill: for
b = 13, 14, 15, 16 it computes the method-independent lower bound of
block_fit.bessel_lb (sorting + cumsum only, no iterative WHT) and prices the
cheapest possible circuit at that K.

Output: artifacts/20261107_block_parity/trend_b.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import block_fit as bf  # noqa: E402

OUT = bf.OUT
FRONT_ROT = 694.840824
TOL_MIN = 621_138_291 / 2.0**64


def c_rot(n_rot: int, margin: float) -> float:
    eps = math.pi * margin / n_rot
    return (0.56 * math.log2(1.0 / eps) + 5.3) / 4.0


def main() -> None:
    res = {}
    bs = [int(v) for v in sys.argv[1:]] or [13, 14, 15, 16]
    f = OUT / "trend_b.json"
    if f.exists():                       # keep results of earlier partial runs
        res = json.loads(f.read_text())
    for b in bs:
        t0 = time.time()
        bl = bf.load_blocks(b)
        Klb, info = bf.bessel_lb(bl)
        n_rot = Klb
        C = Klb + n_rot * c_rot(n_rot, TOL_MIN)     # paid = K (walk + terms)
        res[str(b)] = {"nb": bl["nb"], "hb": bl["hb"], "K_lower_bound": Klb,
                       "C_floor": C, "x_front_rot": C / FRONT_ROT,
                       "lb_info": info}
        print(f"b={b:3d} B={bl['hb']:4d} nb={bl['nb']:6d}: K_LB={Klb:7d} "
              f"-> cheapest possible C={C:9.1f} ({C/FRONT_ROT:6.1f}x front+rot)"
              f"  ({time.time()-t0:.0f}s)", flush=True)
        f.write_text(json.dumps(res, indent=1, default=float))
    print("wrote", f)


if __name__ == "__main__":
    main()
