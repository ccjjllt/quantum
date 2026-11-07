"""Full-domain integer phase check for the shared-rotation architecture.

Contract (official verifier): 1 unit = 2^-64 turns; target/tolerance are the
verifier's own integer tables (artifacts/20261106_rot33/{target,tol}_units.npy);
masks are the verified 41 truth tables (masks_full.json); angles are the exact
fitted Fractions rounded to 2^-63 half-turns (same convention as
20261107_mask_refit/model.py, which reproduces the official margin bit for bit).

Checked on all x = 1..3,133,452:

  A  masks unchanged (taps computed once, fanned out by free CX)
     -> phase is identical by construction
  B1 multi-output accumulator, one angle per accumulator (several Z_POWs on the
     same value before measurement)  -> phase collapses to (sum theta) * g
  B2 multi-output accumulator, XOR accumulation (triangular / prefix algebra)
     -> the same accumulator value is reused after XOR-ing in more taps
  B3 coefficient transposition over the tap multiset
     -> one rotation per distinct tap, coefficient = sum of the theta_i of every
        rotation that materialised that tap
  C  phase-production reorder, masks unchanged
     -> phase is identical because all Z_POW are diagonal and commute

B1/B2/B3 are the only ways "share measurement across rotations" can change the
gate count; they are what this script tests.  Result: all three fail the official
tolerance by 10+ orders of magnitude, because Z_POW phases add over the reals
while the accumulator combines taps by XOR (two 1-taps cancel instead of adding).

Writes artifacts/20261107_shared_rotation/phase_check.json
"""
from __future__ import annotations

import base64
import collections
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
ART = ROOT / "artifacts/20261107_shared_rotation"
MAXX = 3_133_452
NB = (MAXX + 7) // 8
M64 = (1 << 64) - 1
BLOCKS = [(0, 14), (15, 40)]


def rotation_t_count(eps: float) -> float:
    return 0.56 * math.log2(1 / eps) + 5.3


def rot_C(margin_units: int, n_rot: int) -> float:
    eps = math.pi * margin_units / 2**64 / n_rot
    return n_rot * rotation_t_count(eps) / 4.0


def load():
    data = json.loads((ROT33 / "masks_full.json").read_text())
    thetas = np.array([int(round(Fraction(t) * (1 << 63))) for t in data["angles_half_turns"]],
                      dtype=np.int64)
    masks = []
    for m in data["masks"]:
        v = int.from_bytes(base64.b64decode(m["mask_b64"]), "little")
        masks.append(np.unpackbits(np.frombuffer(v.to_bytes(NB, "little"), dtype=np.uint8),
                                  bitorder="little")[:MAXX].astype(bool))
    T = np.load(ROT33 / "T_units.npy").view(np.int64)
    tol = np.load(ROT33 / "tol_units.npy").view(np.int64)
    return data, thetas, masks, T, tol


def phase_of(masks, thetas) -> np.ndarray:
    ph = np.zeros(MAXX, dtype=np.uint64)
    for m, t in zip(masks, thetas):
        t = int(t)
        if t:
            ph += np.uint64(t & M64) * m.astype(np.uint64)
    return ph


def report(ph, T, tol) -> dict:
    err = (ph - T.view(np.uint64)).view(np.int64)
    used = np.abs(err)
    margin = tol.astype(np.int64) - used
    i = int(np.argmin(margin))
    ratio = used.astype(np.float64) / tol.astype(np.float64)
    j = int(np.argmax(ratio))
    bad = int(np.count_nonzero(margin < 0))
    return {"margin_units": int(margin[i]), "margin_x": i + 1,
            "margin_turns": float(margin[i]) / 2**64,
            "worst_ratio": float(ratio[j]), "worst_x": j + 1,
            "failing_x": bad,
            "worst_abs_error_turns": float(used[j]) / 2**64}


def main() -> None:
    data, thetas, masks, T, tol = load()
    led = json.loads((ART / "tap_ledger.json").read_text())
    rots = led["rotations"]

    ph0 = phase_of(masks, thetas)
    base = report(ph0, T, tol)
    m0 = base["margin_units"]
    out = {"domain": "x=1..3133452", "units": "2^-64 turns",
           "tolerance_units_max_x": int(tol[-1]),
           "A_masks_unchanged": {**base, "phase_identical": True,
                                 "n_rot": 41, "rotation_C": rot_C(m0, 41)},
           "variants": {}}
    print("A baseline", json.dumps(base))

    def cmp(name, ph, n_rot, note):
        st = report(ph, T, tol)
        d = (ph - ph0).view(np.int64)
        st.update({
            "n_rot": n_rot, "note": note,
            "exact_equal_to_baseline_phase": bool(np.array_equal(ph, ph0)),
            "x_with_nonzero_deviation": int(np.count_nonzero(d)),
            "max_abs_deviation_turns": float(np.abs(d).max()) / 2**64,
            "deviation_over_tolerance_at_worst":
                float(np.abs(d).max()) / float(tol[-1]),
            "rotation_C_at_same_n_rot": rot_C(m0, n_rot),
        })
        out["variants"][name] = st
        print(name, "exact", st["exact_equal_to_baseline_phase"],
              "fail_x", st["failing_x"], "maxdev_turns", st["max_abs_deviation_turns"],
              "worst_ratio", st["worst_ratio"])
        return st

    # ---------------- B1: several Z_POWs on one unchanged accumulator value
    # each block collapses to (sum theta) * last mask of the block
    for tag, (lo, hi) in zip(("block1", "block2"), BLOCKS):
        m = np.zeros(MAXX, dtype=bool)
        for i in range(lo, hi + 1):
            m = m ^ masks[i]          # accumulator value if nothing resets it
        s = int(sum(int(thetas[i]) for i in range(lo, hi + 1)))
        ph = phase_of([masks[i] for i in range(0 if lo == 0 else 0, lo)] +
                      [m] +
                      [masks[i] for i in range(hi + 1, 41)], 
                      [int(thetas[i]) for i in range(0, lo)] + [s] +
                      [int(thetas[i]) for i in range(hi + 1, 41)])
        cmp(f"B1_single_value_{tag}", ph, 41 - (hi - lo + 1) + 1,
            "all Z_POWs of the block applied to one fixed accumulator value; the "
            "angle sums to one rotation, so the block loses its extra masks")

    # ---------------- B2: XOR accumulation (prefix / triangular algebra)
    pm, pt = [], []
    for lo, hi in BLOCKS:
        acc = np.zeros(MAXX, dtype=bool)
        for i in range(lo, hi + 1):
            acc = acc ^ masks[i]
            pm.append(acc.copy())
            pt.append(int(thetas[i]) - (int(thetas[i + 1]) if i < hi else 0))
    cmp("B2_prefix_xor_accumulation", phase_of(pm, pt), 41,
        "cumulative XOR masks, alpha_i = theta_i - theta_{i+1}; exact only if XOR "
        "were real addition")

    # ---------------- B3: coefficient transposition over the tap multiset
    ts = np.load(ART / "taps_full.npz")
    ids, pk = ts["ids"], ts["taps"]

    def tt(tid):
        j = int(np.searchsorted(ids, tid))
        return np.unpackbits(pk[j], bitorder="little")[:MAXX].astype(bool)

    uses = collections.defaultdict(list)
    for r in rots:
        for u in r["tap_uses"]:
            uses[u["tap"]].append(r["rot"])
    tap_masks, tap_coef = [], []
    cls = collections.Counter()
    for tid, rr in uses.items():
        c = int(sum(int(thetas[r]) for r in rr))
        q = Fraction(c, 1 << 63)
        if c == 0:
            cls["zero"] += 1
        elif q % Fraction(1, 2) == 0:
            cls["clifford"] += 1
        elif q % Fraction(1, 4) == 0:
            cls["t"] += 1
        else:
            cls["rotation"] += 1
        tap_masks.append(tt(tid))
        tap_coef.append(c)
    st = cmp("B3_tap_coefficient_transposition", phase_of(tap_masks, tap_coef),
             len(tap_masks),
             "one rotation per distinct materialisation tap, coefficient = sum of "
             "the theta_i of every rotation that used that tap")
    st["n_distinct_taps"] = len(tap_masks)
    st["angle_classes"] = dict(cls)
    st["rotation_C_if_algebra_worked"] = rot_C(m0, len(tap_masks))
    st["delta_rotation_C_vs_41"] = rot_C(m0, len(tap_masks)) - rot_C(m0, 41)

    # ---------------- C: pure reorder (masks unchanged)
    perm = list(range(41))[::-1]
    cmp("C_reordered_phase_production", phase_of([masks[i] for i in perm],
                                                 [int(thetas[i]) for i in perm]),
        41, "same 41 masks and angles applied in reverse order; all Z_POW commute")

    # ---------------- budget tables
    out["rotation_C_vs_n_rot_same_margin"] = [
        {"n_rot": n, "rotation_C": rot_C(m0, n), "delta_vs_41": rot_C(m0, n) - rot_C(m0, 41)}
        for n in (33, 41, 50, 100, 176)
    ]
    out["d_rotation_C_per_extra_rotation"] = rot_C(m0, 42) - rot_C(m0, 41)

    # near-equal dyadic weights (boundary note; not a proposed candidate)
    pairs = []
    for a in range(41):
        for b in range(a + 1, 41):
            d = int(thetas[a]) - int(thetas[b])
            if abs(d) < int(thetas[a]) * 0.01:
                pairs.append({"rot_a": a, "rot_b": b,
                              "delta_half_turns": float(Fraction(d, 1 << 63)),
                              "delta_turns": float(Fraction(d, 1 << 63)) / 2,
                              "delta_over_baseline_margin":
                                  abs(float(Fraction(d, 1 << 63)) / 2) / base["margin_turns"]})
    out["near_equal_angle_pairs"] = pairs
    (ART / "phase_check.json").write_text(json.dumps(out, indent=1) + "\n")
    print("rotation C at m0 for n=33,41,50,100,176:",
          [round(rot_C(m0, n), 3) for n in (33, 41, 50, 100, 176)])
    print("d rot C per extra rotation:", out["d_rotation_C_per_extra_rotation"])
    print("near-equal angle pairs:", len(pairs),
          "max delta/margin", max((p["delta_over_baseline_margin"] for p in pairs), default=0))


if __name__ == "__main__":
    main()
