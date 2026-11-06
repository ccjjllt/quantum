"""Cost accounting for a hypothetical 33-rotation merged-phase representation."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452
MASK64 = (1 << 64) - 1
MASK28 = (1 << 28) - 1

BASELINE_C = 1575.8189802780
BASELINE_ROT_SYNTH = 294.8408238889
BASELINE_ROT_COUNT = 41
LOGIC_PER_ROT = 3.5  # user-supplied reference for the existing gadget


def main() -> None:
    T = np.load(OUT / "T_units.npy")
    tol = np.load(OUT / "tol_units.npy")
    N = np.load(OUT / "N.npy")

    # 33-term truncation: weights 2^-2..2^-34, drop 2^-35.
    phase = np.zeros(MAXX, dtype=np.uint64)
    for w in range(2, 35):
        gw = ((N >> (35 - w)) & 1).astype(bool)
        phase[gw] += np.uint64(1 << (63 - w))
    err = (phase - T).view(np.int64)
    used = np.abs(err).view(np.uint64)
    ratio = np.divide(used, tol, out=np.zeros(MAXX), where=tol > 0)
    margin = (tol.astype(np.int64) - used.astype(np.int64))
    imin = int(np.argmin(margin))
    min_margin_units = int(margin[imin])
    min_margin_turns = min_margin_units / 2**64
    print("33-term truncation:")
    print("  worst ratio", float(ratio.max()), "at x", int(np.argmax(ratio)) + 1)
    print("  min margin units", min_margin_units, "turns", min_margin_turns,
          "at x", imin + 1)
    eps33 = math.pi * min_margin_turns / 33
    synth33 = 33 * (0.56 * math.log2(1 / eps33) + 5.3) / 4
    print("  eps33", eps33, "synthesis C", synth33)
    print("  baseline synthesis C", BASELINE_ROT_SYNTH)

    saved_synth = BASELINE_ROT_SYNTH - synth33
    saved_logic = 8 * LOGIC_PER_ROT
    saved_total = saved_synth + saved_logic
    print("  saved synthesis", saved_synth, "saved logic", saved_logic,
          "total saved", saved_total)

    # Lower bounds on new arithmetic.
    # phase_fused-style two shift ladders over an n-bit word, forward+reverse:
    # ~4*n CSWAP/CCX Toffolis (n=34 for the 34-bit N word).
    word_width = 34
    shift_lb = 4 * word_width
    # Gidney gadd: n-1 Toffolis forward, called forward and reverse.
    adder_lb = 2 * (word_width - 1)
    print("  shift-ladder lower bound (4*width)", shift_lb)
    print("  adder lower bound (2*(width-1))", adder_lb)
    print("  new arithmetic lower bound", shift_lb + adder_lb)
    print("  net if only shift ladder", saved_total - shift_lb)
    print("  net if shift+adder", saved_total - shift_lb - adder_lb)

    # Break-even: new C < saved_total.
    print("  break-even new C", saved_total)
    print("  62Q score if net = saved_total - 136:",
          62 * (BASELINE_C - (saved_total - shift_lb)))

    # Width penalty if the 8 overlapping bits are added at the first block,
    # where the conservative live count is already 62.
    for qnew in (63, 64, 70):
        print(f"  {qnew}Q break-even C {97700.776777236 / qnew:.3f}, "
              f"extra C budget {BASELINE_C - 97700.776777236 / qnew:.3f}")

    out = {
        "baseline_C": BASELINE_C,
        "baseline_synthesis_C": BASELINE_ROT_SYNTH,
        "baseline_rotation_count": BASELINE_ROT_COUNT,
        "truncation_worst_ratio": float(ratio.max()),
        "truncation_worst_x": int(np.argmax(ratio)) + 1,
        "truncation_min_margin_units_2^-64_turns": min_margin_units,
        "truncation_min_margin_turns": min_margin_turns,
        "truncation_min_margin_x": imin + 1,
        "eps33": eps33,
        "synth33_C": synth33,
        "saved_synthesis_C": saved_synth,
        "saved_logic_C_reference": saved_logic,
        "saved_total_C": saved_total,
        "word_width_bits": word_width,
        "shift_ladder_lower_bound_C": shift_lb,
        "adder_lower_bound_C": adder_lb,
        "new_arithmetic_lower_bound_C": shift_lb + adder_lb,
        "net_shift_only_C": saved_total - shift_lb,
        "net_shift_plus_adder_C": saved_total - shift_lb - adder_lb,
    }
    (OUT / "economics33.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
