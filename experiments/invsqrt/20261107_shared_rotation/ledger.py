"""Complete Q/C ledger for the shared-rotation architecture at 62/61/63 qubits.

Every number that describes the baseline or the rotation windows is measured
from the real circuit and the real masks; every number that describes a
variant is an explicitly stated lower bound or a measured count.

Sources
  artifacts/20261106_syed_v9/invsqrt/official_run.json   official PASS ledger
  artifacts/20261106_direction_research/cost/census.json  window split
  artifacts/20261107_shared_rotation/tap_ledger.json     179 real tap uses
  artifacts/20261107_shared_rotation/share_probe.json    97 static / 82 mux taps
  artifacts/20261107_shared_rotation/phase_check.json    full-domain checks
  experiments/invsqrt/20261107_streaming/                 ANF of the 41 masks

Writes artifacts/20261107_shared_rotation/ledger.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261107_shared_rotation"
OFFICIAL_C = 1575.818980278
OFFICIAL_SCORE = 97700.776777236
TOFFOLI = 1280.7281563891038
T_BASE = 1.0
M0 = 58597850          # baseline full-domain margin, units 2^-64 turns
N_ROT0 = 41
# executed paid gates per stage (census: 3x16384 uniform-x random-coin samples)
STAGES = {"front_[0,15278)": 247.0,
          "rotation_window_1_[15278,15617)": 62.0,
          "arithmetic_[15617,25408)": 376.985,
          "rotation_window_2_[25408,25649)": 91.0,
          "cleanup_[25649,49051)": 503.751}


def rot_t(eps: float) -> float:
    return 0.56 * math.log2(1 / eps) + 5.3


def rot_C(margin: int, n: int) -> float:
    return n * rot_t(math.pi * margin / 2**64 / n) / 4.0


def total_C(paid: float, margin: int, n_rot: int) -> float:
    return paid + (T_BASE + rot_C(margin, n_rot) * 4) / 4.0


def row(name, *, d_paid=0.0, n_rot=N_ROT0, margin=M0, Q=62,
        paid=None, note="", realisable=True):
    if paid is None:
        paid = TOFFOLI + d_paid
    C = total_C(paid, margin, n_rot)
    return {"variant": name, "Q": Q, "paid_toffoli_like": paid,
            "d_paid_vs_baseline": paid - TOFFOLI,
            "HMR": 867, "R": 74, "fine_rotations": n_rot,
            "rotation_synthesis_C": rot_C(margin, n_rot),
            "T_count": T_BASE, "normalization_cleanup_C": STAGES["front_[0,15278)"] +
            STAGES["cleanup_[25649,49051)"],
            "arithmetic_C": STAGES["arithmetic_[15617,25408)"],
            "C": C, "score": Q * C,
            "dC_vs_baseline": C - OFFICIAL_C,
            "dscore_vs_baseline": Q * C - OFFICIAL_SCORE,
            "beats_baseline_score": Q * C < OFFICIAL_SCORE,
            "realisable": realisable, "note": note}


def probe_row_kind(tid, tap):
    for r in tap["rotations"]:
        for u in r["tap_uses"]:
            if u["tap"] == tid:
                return u["kind"]
    return "CX"


def main() -> None:
    tap = json.loads((ART / "tap_ledger.json").read_text())
    probe = json.loads((ART / "share_probe.json").read_text())
    ph = json.loads((ART / "phase_check.json").read_text())
    anf = json.loads((ROOT / "artifacts/20261107_streaming/symbolic_masks.json").read_text())

    # ---- ANF monomial accounting (measured from the real 41 masks)
    mono = {}
    for r in anf["per_rotation"]:
        for t in r["anf"]:
            mono[tuple(t)] = mono.get(tuple(t), 0) + 1
    n_mono = len(mono)
    n_lin = sum(1 for t in mono if len(t) == 1)
    n_const = sum(1 for t in mono if len(t) == 0)
    n_nonlin = n_mono - n_lin - n_const
    chained = sum(len(t) - 1 for t in mono)
    anf_terms = sum(len(r["anf"]) for r in anf["per_rotation"])
    sharing_saving = sum(c - 1 for t, c in mono.items() if len(t) >= 2)

    # ---- tap accounting (measured from the real circuit)
    uses = {}
    for r in tap["rotations"]:
        for u in r["tap_uses"]:
            uses.setdefault(u["tap"], []).append(r["rot"])
    mult = {}
    for t in uses:
        mult[len(uses[t])] = mult.get(len(uses[t]), 0) + 1
    n_uses = sum(len(v) for v in uses.values())
    n_distinct = len(uses)
    n_paid_uses = probe["n_paid_tap_uses"]
    n_clean_uses = probe["n_uses_with_clean_product_form"]
    n_mux_uses = n_uses - n_clean_uses
    n_dup = n_uses - n_distinct
    dirty_saving = sum(len(v) - 2 for v in uses.values() if len(v) >= 2)

    led = {
        "official_baseline": {"Q": 62, "C": OFFICIAL_C, "score": OFFICIAL_SCORE,
                              "paid": TOFFOLI, "t_base": T_BASE,
                              "rotation_count": N_ROT0,
                              "rotation_eps": 2.434041480874084e-13,
                              "margin_units": M0,
                              "stage_split_measured_C": STAGES},
        "measured_taps": {
            "tap_uses": n_uses, "distinct_tap_functions": n_distinct,
            "paid_tap_uses": n_paid_uses,
            "uses_with_static_product_form": n_clean_uses,
            "uses_that_are_state_dependent_cswap_mux": n_mux_uses,
            "multiplicity_histogram": mult,
            "duplicate_paid_uses": n_dup,
            "sharing_saving_with_dirty_ancilla": dirty_saving,
            "sharing_saving_with_clean_ancilla": n_dup,
            "note": "k=2 taps: a dirty ancilla costs 2 gates (compute + uncompute) "
                    "= the 2 direct materialisations, so dirty sharing saves 0; a "
                    "clean ancilla would save 1 per tap but no wire has popcount 0 "
                    "at op 15315 and no two wires hold the same value",
        },
        "measured_anf_monomials": {
            "anf_term_instances": anf_terms, "distinct_monomials": n_mono,
            "linear_monomials": n_lin, "constant_monomials": n_const,
            "nonlinear_monomials": n_nonlin,
            "lower_bound_CCX_one_and_per_nonlinear_monomial": n_nonlin,
            "chained_product_CCX": chained,
            "sharing_saving_terms": sharing_saving,
            "baseline_rotation_window_paid": 153.0,
            "ratio_vs_rotation_windows": n_nonlin / 153.0,
            "ratio_chained_vs_rotation_windows": chained / 153.0,
        },
        "phase_check_summary": {
            "masks_unchanged_margin": ph["A_masks_unchanged"]["margin_units"],
            "B1_block1_worst_ratio": ph["variants"]["B1_single_value_block1"]["worst_ratio"],
            "B1_block2_worst_ratio": ph["variants"]["B1_single_value_block2"]["worst_ratio"],
            "B2_prefix_worst_ratio": ph["variants"]["B2_prefix_xor_accumulation"]["worst_ratio"],
            "B3_tapmajor_worst_ratio": ph["variants"]["B3_tap_coefficient_transposition"]["worst_ratio"],
            "C_reorder_phase_identical": ph["variants"]["C_reordered_phase_production"]["exact_equal_to_baseline_phase"],
        },
        "rotation_C_vs_n_rot": ph["rotation_C_vs_n_rot_same_margin"],
        "d_rotation_C_per_extra_rotation": ph["d_rotation_C_per_extra_rotation"],
        "ledger": [],
    }

    L = led["ledger"]
    L.append(row("0 baseline (official PASS)", note="reference"))
    L.append(row("A1 shared monomial ANF, one AND per nonlinear monomial",
                 d_paid=n_nonlin, note="lower bound of the monomial-basis architecture"))
    L.append(row("A2 shared monomial ANF, chained products",
                 d_paid=chained, note="each distinct monomial chained from a "
                 "(deg-1) sub-monomial when available"))
    L.append(row("A3 tap-level sharing, dirty ancilla (3 duplicate taps)",
                 d_paid=dirty_saving, note="measured duplicate taps, k=2 each, "
                 "compute+uncompute = same cost, so 0"))
    L.append(row("A4 tap-level sharing, clean ancilla (upper bound, not realisable)",
                 d_paid=-n_dup, note="needs 3 wires at popcount 0 over ops "
                 "15315..15604; measured: none, and no duplicate value on two wires"))
    L.append(row("A4-at-65Q (what 3 extra ancilla wires cost)",
                 d_paid=-n_dup, Q=65, note="one extra wire per duplicate tap span"))
    n_paid_distinct = sum(1 for t in uses
                          if uses and probe_row_kind(t, tap) in {"CCX", "CCZ", "CSWAP"})
    L.append(row("B3 tap transposition IF the phase algebra worked",
                 n_rot=ph["variants"]["B3_tap_coefficient_transposition"]["n_distinct_taps"],
                 d_paid=n_paid_distinct - 153,
                 note="phase check fails on 1,048,575 x; the most favourable gate "
                      "count (one materialisation per distinct paid tap, bare-wire "
                      "taps Z_POWed in place) is used; listed only to show the cost"))
    L.append(row("C pure reorder of the 41 rotations",
                 note="phase identical (Z_POW commute); 0 paid gates moved in or out"))
    L.append(row("BEST of A+B+C at 62Q", note="equal to baseline: no strict improvement"))

    # ---- 61Q / 63Q ledger
    q_led = {}
    for Q, need in ((61, "added C < 25.833098"), (62, "any C below baseline"),
                    (63, "net saving > 25.0130")):
        best_C = total_C(TOFFOLI, M0, N_ROT0)
        realisable = Q == 62
        q_led[Q] = {"requirement": need,
                    "best_architecture_C_at_dC_0": best_C,
                    "best_score_at_dC_0": Q * best_C,
                    "beats_baseline_at_dC_0": Q * best_C < OFFICIAL_SCORE,
                    "break_even_added_C": OFFICIAL_SCORE / Q - OFFICIAL_C,
                    "dC_0_realisable_by_this_architecture": realisable,
                    "note": ("62Q: identical C, score unchanged, fails strict <"
                             if Q == 62 else
                             "61Q: removing one wire needs recomputation; current-sequence "
                             "bound is +53C so score >= 61*(C0+53)"
                             if Q == 61 else
                             "63Q: needs a net saving of 25.013C; best measured saving is 0C")}
        if Q == 61:
            q_led[Q]["score_at_53C_added"] = 61 * (OFFICIAL_C + 53)
        if Q == 63:
            q_led[Q]["score_at_best_measured_saving_0"] = 63 * OFFICIAL_C
    led["q_ledger"] = q_led
    led["external_61q_bound"] = {
        "source": "experiments/invsqrt/20261107_61q_lower_bound/README.md",
        "current_sequence_min_added_C": 53,
        "score_at_53C_added": 61 * (OFFICIAL_C + 53),
        "beats_baseline": 61 * (OFFICIAL_C + 53) < OFFICIAL_SCORE,
    }
    (ART / "ledger.json").write_text(json.dumps(led, indent=1) + "\n")
    for r in L:
        print(f"{r['variant'][:58]:58s} Q={r['Q']:2d} nrot={r['fine_rotations']:3d} "
              f"C={r['C']:11.6f} score={r['score']:12.4f} "
              f"dscore={r['dscore_vs_baseline']:+12.4f} beats={r['beats_baseline_score']}")
    print(json.dumps(q_led, indent=1))


if __name__ == "__main__":
    main()
