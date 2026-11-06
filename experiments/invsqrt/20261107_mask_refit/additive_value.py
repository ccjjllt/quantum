"""Value of ADDING one mask direction (free coefficient, no mask lost).

This bounds what a mask *replacement* could possibly buy: replacement is the
same direction with a tied coefficient and the loss of f_i's contribution.
Writes artifacts/20261107_mask_refit/additive_value.json.
"""
from __future__ import annotations

import json

import numpy as np

import model as M
from fast_eval import Evaluator

OUT = M.ART
WIRES = OUT / "wires"


def main() -> None:
    m = M.load_model()
    base = int(M.OFFICIAL["baseline_margin"])
    z = np.load(WIRES / "cp_15.npz")
    W = [np.unpackbits(z[f"w{j}"], bitorder="little")[: M.MAXX].astype(bool) for j in range(62)]
    fixed = {
        "guard Y1&(e1^e2)": W[54] & (W[18] ^ W[27]),
        "pair 10&24": W[10] & W[24],
        "pair 31&44": W[31] & W[44],
        "lin2 21^23": W[21] ^ W[23],
        "lin q23": W[23],
    }
    rng = np.random.default_rng(3)
    pairs = [(a, b) for a in range(62) for b in range(a + 1, 62)]
    sel = rng.choice(len(pairs), 24, replace=False)
    rand = {f"pair {pairs[k][0]}&{pairs[k][1]}": W[pairs[k][0]] & W[pairs[k][1]] for k in sel}
    rows = []
    for name, g in {**fixed, **rand}.items():
        m2 = dict(m)
        m2["masks"] = list(m["masks"]) + [g]
        m2["thetas"] = np.r_[m["thetas"], 0]
        ev = Evaluator(m2)
        out = ev.eval(41, g)  # identity replacement == pure addition
        mg = out["margin"]
        rows.append({"direction": name, "margin": mg,
                     "gain_frac": mg / base - 1,
                     "gain_C": M.margin_saving_C(base, mg) if mg and mg > 0 else 0.0})
        print(f"ADD {name:20s} margin {mg:12d} gain {mg/base-1:+.4%} "
              f"C {rows[-1]['gain_C']:+.3f}", flush=True)
    rows.sort(key=lambda r: -r["margin"])
    (OUT / "additive_value.json").write_text(json.dumps(
        {"baseline_margin": base, "rows": rows}, indent=2) + "\n")
    print("best", rows[0]["direction"], f"{rows[0]['gain_frac']:+.4%}",
          f"{rows[0]['gain_C']:.3f}C")


if __name__ == "__main__":
    main()
