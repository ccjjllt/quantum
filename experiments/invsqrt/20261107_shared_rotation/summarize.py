"""Collect the headline numbers of the shared-rotation study into summary.json.

Reads the measured artifacts and prints the table used in README.md.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261107_shared_rotation"


def main() -> None:
    tap = json.loads((ART / "tap_ledger.json").read_text())
    probe = json.loads((ART / "share_probe.json").read_text())
    ph = json.loads((ART / "phase_check.json").read_text())
    anc = json.loads((ART / "ancilla_check.json").read_text())
    led = json.loads((ART / "ledger.json").read_text())

    out = {
        "baseline": {
            "Q": 62, "C": 1575.818980278, "score": 97700.776777236,
            "margin_units": 58597850, "n_rot": 41,
            "rotation_synthesis_C": led["official_baseline"]["official_baseline"]["rotation_synthesis_C"]
            if isinstance(led["official_baseline"].get("official_baseline"), dict)
            else round(ph["A_masks_unchanged"]["rotation_C"], 9),
            "worst_ratio": ph["A_masks_unchanged"]["worst_ratio"],
            "worst_x": ph["A_masks_unchanged"]["worst_x"],
            "stage_split_C": led["official_baseline"]["stage_split_measured_C"],
        },
        "measured": {
            "tap_uses": probe["n_tap_uses"],
            "distinct_tap_functions": probe["n_distinct_clean_products"] and
            len(json.loads((ART / "tap_ledger.json").read_text())["tap_meta"]) and None,
            "paid_tap_uses": probe["n_paid_tap_uses"],
            "uses_static_product_form": probe["n_uses_with_clean_product_form"],
            "uses_state_dependent_mux": probe["n_tap_uses"] - probe["n_uses_with_clean_product_form"],
            "distinct_static_products": probe["n_distinct_clean_products"],
            "shared_static_products": probe["shared_clean_products"],
            "duplicate_taps": [r["tap"] for r in anc["duplicate_taps"]],
            "sharing_saving_dirty_ancilla_C": led["measured_taps"]["sharing_saving_with_dirty_ancilla"],
            "sharing_saving_clean_ancilla_upper_bound_C": led["measured_taps"]["sharing_saving_with_clean_ancilla"],
            "disposable_ancilla_at_62Q": bool(any(r["disposable_candidates"] for r in anc["duplicate_taps"])),
            "zero_wires_at_span_starts": anc["zero_wire_check"],
            "anf": led["measured_anf_monomials"],
        },
        "phase_check": {
            "masks_unchanged": ph["A_masks_unchanged"],
            "B_variants": {k: {"n_rot": v["n_rot"],
                               "exact": v["exact_equal_to_baseline_phase"],
                               "failing_x": v["failing_x"],
                               "max_abs_deviation_turns": v["max_abs_deviation_turns"],
                               "worst_ratio": v["worst_ratio"]}
                           for k, v in ph["variants"].items()},
        },
        "rotation_C_vs_n_rot": ph["rotation_C_vs_n_rot_same_margin"],
        "d_rotation_C_per_extra_rotation": ph["d_rotation_C_per_extra_rotation"],
        "ledger": led["ledger"],
        "q_ledger": led["q_ledger"],
        "external_61q_bound": led["external_61q_bound"],
        "near_equal_angle_pairs": len(ph["near_equal_angle_pairs"]),
        "max_angle_pair_delta_over_margin": max(
            p["delta_over_baseline_margin"] for p in ph["near_equal_angle_pairs"]),
        "candidate_kmb": None,
        "official_verifier_run": False,
    }
    out["measured"]["distinct_tap_functions"] = led["measured_taps"]["distinct_tap_functions"]
    (ART / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("baseline", "measured", "phase_check",
                       "d_rotation_C_per_extra_rotation", "candidate_kmb",
                       "official_verifier_run")}, indent=1))
    print("\nledger")
    for r in out["ledger"]:
        print(f"  {r['variant'][:60]:60s} Q={r['Q']:2d} nrot={r['fine_rotations']:3d} "
              f"C={r['C']:10.4f} score={r['score']:11.3f} dscore={r['dscore_vs_baseline']:+11.3f}")


if __name__ == "__main__":
    main()
