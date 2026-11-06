"""Consolidated summary of the rot33 experiment artifacts."""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261106_rot33"


def gf2_rank(values):
    basis = {}
    for v in values:
        while v:
            p = v.bit_length() - 1
            if p not in basis:
                basis[p] = v
                break
            v ^= basis[p]
    return len(basis)


def main() -> None:
    md = json.loads((OUT / "masks_full.json").read_text())
    masks = [int.from_bytes(base64.b64decode(m["mask_b64"]), "little") for m in md["masks"]]
    out = {
        "baseline": md["baseline"],
        "baseline_sha256": md["sha256"],
        "rotations": len(masks),
        "distinct_masks": len(set(masks)),
        "gf2_rank": gf2_rank(masks),
        "angles_half_turns": [m["theta"] for m in md["masks"]],
        "targets": md["targets"],
        "ops": md["ops"],
        "popcounts": [m.bit_count() for m in masks],
    }

    bc = json.loads((OUT / "branch_check_random.json").read_text())
    out["branch_check"] = {"conclusion": bc["conclusion"],
                           "n": bc["n"],
                           "total_xor_distance": {k: v["total_distance"]
                                                  for k, v in bc["branches"].items()}}

    g = json.loads((OUT / "g_meta.json").read_text())
    out["truncation"] = {
        "worst_ratio": g["truncation_worst_ratio"],
        "worst_x": g["truncation_worst_x"],
        "N_max": g["N_max"],
        "N_bit_length": g["N_bit_length"],
        "weights_half_turn_exponents": g["weights_half_turn_exponents"],
        "dropped_weight": g["dropped_weight"],
    }

    ls = json.loads((OUT / "linear_span.json").read_text())
    out["linear_span"] = {
        "rotation_checkpoints": len(ls),
        "ideal_bits_in_span_per_checkpoint": sorted(set(len(v["ideal_bits_in_span"])
                                                        for v in ls.values())),
        "original_masks_in_span_per_checkpoint": {
            k: v["original_masks_in_span"] for k, v in ls.items()},
    }
    qs = json.loads((OUT / "quadratic_span_sample.json").read_text())
    out["quadratic_span"] = {
        "n_sample": qs["n_sample"],
        "ideal_bits_in_span_per_checkpoint": sorted(
            set(len(v["ideal_in_quadratic_span"]) for v in qs["results"].values())),
    }
    qo = json.loads((OUT / "quadratic_orig_sample.json").read_text())["results"]
    out["quadratic_original_cross_checkpoint"] = {
        k: v["orig_in_quad"] for k, v in qo.items() if len(v["orig_in_quad"]) > 1}
    cm = json.loads((OUT / "cubic_monomial_probe_support.json").read_text())
    out["cubic_monomial_probe"] = cm

    ss = json.loads((OUT / "subset_baseline.json").read_text())
    out["subset_baseline"] = {
        "drop_one_min_worst": min((r["worst"], r["drop"]) for r in ss["drop_one"]),
        "keep_33_largest_worst": ss["keep_33_largest"]["worst"],
        "greedy_kept_worst": ss["greedy_worst"],
    }
    out["subset_lp"] = {}
    for name in ("subset_lp_15_16_17_18_19_20_21_22.json",
                 "subset_lp_15_16_17_18_19_20_21_23.json"):
        d = json.loads((OUT / name).read_text())
        h = d["history"][-1]
        out["subset_lp"][name] = {
            "remove": d["remove"],
            "full_worst_ratio": h["full_worst_ratio"],
            "full_min_margin_turns": h["full_min_margin_turns"],
            "lp_eps_turns": h["lp_eps_turns"],
        }
    out["economics"] = json.loads((OUT / "economics33.json").read_text())
    (OUT / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("rotations", "distinct_masks", "gf2_rank", "truncation",
                       "subset_baseline", "subset_lp")}, indent=2))


if __name__ == "__main__":
    main()
