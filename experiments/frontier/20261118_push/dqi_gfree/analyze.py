#!/usr/bin/env python3
"""Re-aggregate the already-measured DQI tape block tables for the gfree question.

Reads (all small, already in the repo):
  artifacts/20261118_push_dqi_normeea/out_sched/sched.json      # every CCX block, both passes
  experiments/frontier/20261118_push/dqi_algo/region_split.json # region census + dynamic means

Writes summary.json next to this file. Pure arithmetic; no tape read, no simulation.

Block table row = [size, wa, wb, wt, op_start, gap_after].

Conventions
-----------
* T_MEAN = 367,116.0572 is the official verifier mean executed Toffoli count; it is the
  number in the score. All GM/pricing uses it. Static block sums are used for Delta-T and
  are 0.24% conservative (mean/static = 0.99763).
* A hold of k extra qubits breaks even when Delta-T >= T_MEAN * (1 - (890/(890+k))^2).
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCHED = ROOT / "artifacts/20261118_push_dqi_normeea/out_sched/sched.json"
REGION = ROOT / "experiments/frontier/20261118_push/dqi_algo/region_split.json"

T_STATIC = 367_989
T_MEAN = 367_116.0572
Q = 890
GM = 28.18065942104198
TARGET = 31.42723

# Region boundaries as measured (dqi_surgery / dqi_algo).
FWD = (17_576_206, 30_335_416)
CHIEN = (30_335_416, 35_627_262)      # 4,024 cells; the 4,025th sits at 35,627,287 in "rev"
REV = (35_627_262, 52_910_631)
EPI = (52_910_631, 57_520_821)


def load_blocks(reg):
    d = json.load(open(SCHED))
    return d[reg]["table"]


def t_between(rows, lo, hi):
    sel = [r for r in rows if lo <= r[4] < hi]
    return {
        "T": sum(r[0] for r in sel),
        "T_big": sum(r[0] for r in sel if r[0] >= 24),
        "blocks": len(sel),
        "n42": sum(1 for r in sel if r[0] == 42),
    }


def class_table(rows):
    c = Counter()
    for size, *_ in rows:
        c[size] += 1
    out = {}
    for size in sorted(c, reverse=True):
        if size >= 24:
            out[str(size)] = {"blocks": c[size], "T": size * c[size]}
    out["<24"] = {
        "blocks": sum(v for k, v in c.items() if k < 24),
        "T": sum(k * v for k, v in c.items() if k < 24),
    }
    out["total"] = {"blocks": len(rows), "T": sum(r[0] for r in rows)}
    return out


def dT_required(k, t=T_MEAN, q=Q):
    """Minimum Delta-T for +k qubits to break even."""
    return t * (1 - (q / (q + k)) ** 2)


def kmax(dT, t=T_MEAN, q=Q):
    """Maximum +k for a given Delta-T to break even."""
    return q * (math.sqrt(t / (t - dT)) - 1)


def gm_new(dT, q_delta):
    q = Q + q_delta
    ratio = (q / Q) ** 2 * ((T_MEAN - dT) / T_MEAN)
    return GM * ratio ** (-1 / 3), ratio


def main():
    f = load_blocks("fwd")
    r = load_blocks("rev")

    # Level boundaries: narrow = block-pattern boundary (last EEA division vs convert);
    # wide = last/first 10 of 34 equal op segments (generous upper bound for convert).
    fwd_narrow_convert = t_between(f, 29_600_000, FWD[1])
    # Block-pattern criterion: the four scaling/convolution groups at 29.655-29.804M
    # and their mirrors at 36.295-36.44M. The intervening rev-head ops are classical
    # bookkeeping; keep a second row that charges all of it to the unconvert.
    rev_narrow_unconvert = t_between(r, 36_290_000, 36_450_000)
    rev_narrow_ctl = t_between(r, REV[0], 36_450_000)
    rev_narrow_ctl = dict(rev_narrow_ctl, T=rev_narrow_ctl["T"] - 10)

    fwd_wide_convert = t_between(f, FWD[0] + (FWD[1] - FWD[0]) * 24 // 34, FWD[1])
    rev_wide_unconvert = t_between(r, REV[0], REV[0] + (REV[1] - REV[0]) * 10 // 34)
    rev_wide_unconvert = dict(rev_wide_unconvert, T=rev_wide_unconvert["T"] - 10)

    fwd_T = t_between(f, *FWD)["T"]
    rev_T = t_between(r, *REV)["T"]

    # Algorithmic Chien: 4,025 cells; move the 10 CCX of the last cell out of rev.
    chien_T = 40_250 + 4_025  # static CCX+CCZ
    rev_T_algo = rev_T - 10

    out = {
        "inputs": {"sched": str(SCHED), "region": str(REGION)},
        "conventions": {"T_static": T_STATIC, "T_mean": T_MEAN, "Q": Q, "GM": GM,
                        "mean_over_static": T_MEAN / T_STATIC},
        "regions": {
            "fwd": {"ops": FWD, **t_between(f, *FWD), "classes": class_table(f)},
            "chien": {"ops": CHIEN, "T_static": 44_264, "ccx": 40_240, "ccz": 4_024,
                      "cells": 4_024, "T_cell": 11, "R": 40_240},
            "chien_algo": {"cells": 4_025, "ccx": 40_250, "ccz": 4_025, "T_static": chien_T},
            "rev": {"ops": REV, **t_between(r, *REV), "classes": class_table(r)},
            "rev_algo": {"T_ccx": rev_T_algo, "T_total": rev_T_algo + 1_951},
            "epilogue": {"ops": EPI, "T_static": 0},
        },
        "chien_cell": {
            "ccx_compute": 10, "ccz": 1,
            "R_before_each_ccx": 10, "HMR": 10, "CZ_IF": 10, "X": 24, "SWAP": 22,
            "CX_forney_prefactor": 24,
            "uncompute_toffoli": 0,
            "criterion": ("region census: Chien CCX 40,240 = 4,024 x 10; CCZ 4,024; "
                          "HMR 40,240 = 4,024 x 10; CZ 40,240 (all _IF) = 4,024 x 10; "
                          "op listing wins_chien_block1: X12, 10x(R,CCX), CCZ, "
                          "10x(HMR,CZ_IF), X12; no inverse AND chain"),
        },
        "multiply_block": {
            "words": 3, "qubits": 36, "ccx": 42, "cx_free": "~1,250-1,460",
            "scratch_bits": 5, "tensor": "GF(2^12) mul mod 0x1053 (rev0, 363 ones)",
            "internal_uncompute": 0,
            "criterion": "dqi_block R=41-CCX c132_0 listing + dqi_fastshift ANF/bit-slice 6/6",
        },
        "levels_narrow": {
            "extract": {"compute_ccx": fwd_T - fwd_narrow_convert["T"],
                        "uncompute_ccx": rev_T_algo - rev_narrow_unconvert["T"]},
            "convert": {"compute_ccx": fwd_narrow_convert["T"],
                        "uncompute_ccx": rev_narrow_unconvert["T"]},
            "synthesis": {"compute_ccx_ccz": chien_T, "uncompute": 0},
        },
        "levels_narrow_ctl": {
            "extract": {"compute_ccx": fwd_T - fwd_narrow_convert["T"],
                        "uncompute_ccx": rev_T_algo - rev_narrow_ctl["T"]},
            "convert": {"compute_ccx": fwd_narrow_convert["T"],
                        "uncompute_ccx": rev_narrow_ctl["T"]},
            "synthesis": {"compute_ccx_ccz": chien_T, "uncompute": 0},
        },
        "levels_wide": {
            "extract": {"compute_ccx": fwd_T - fwd_wide_convert["T"],
                        "uncompute_ccx": rev_T_algo - rev_wide_unconvert["T"]},
            "convert": {"compute_ccx": fwd_wide_convert["T"],
                        "uncompute_ccx": rev_wide_unconvert["T"]},
            "synthesis": {"compute_ccx_ccz": chien_T, "uncompute": 0},
        },
        "whole_reverse": {"ccx": rev_T_algo, "with_ccz": rev_T_algo + 1_951},
        "hold_budget": {str(k): {"dT_required": dT_required(k),
                                  "fits_reverse_all": dT_required(k) <= rev_T_algo + 1_951}
                        for k in (0, 50, 158, 171, 319, 326, 370, 420, 816, 840)},
        "pricing": {},
        "best_losing": {},
    }

    for name, dT in [
        ("convert_narrow", rev_narrow_unconvert["T"]),
        ("convert_narrow_ctl", rev_narrow_ctl["T"]),
        ("convert_wide", rev_wide_unconvert["T"]),
        ("extract_narrow", rev_T_algo - rev_narrow_unconvert["T"]),
        ("extract_narrow_ctl", rev_T_algo - rev_narrow_ctl["T"]),
        ("extract_wide", rev_T_algo - rev_wide_unconvert["T"]),
        ("reverse_all", rev_T_algo + 1_951),
        ("target_31_427_at_890", T_MEAN * (1 - 1 / (TARGET / GM) ** 3)),
    ]:
        row = {"dT": dT, "k_breakeven": kmax(dT), "T_new": T_MEAN - dT}
        for hold in (158, 171, 319, 370, 384, 420, 816, 840):
            g, ratio = gm_new(dT, hold)
            row[f"gm_at_+{hold}"] = g
            row[f"ratio_at_+{hold}"] = ratio
        out["pricing"][name] = row

    req = (TARGET / GM) ** 3
    out["target"] = {
        "required_cost_ratio": req,
        "at_Q": {str(q): {"T_new": Q ** 2 * T_MEAN / (q ** 2 * req),
                          "dT": T_MEAN - Q ** 2 * T_MEAN / (q ** 2 * req),
                          "k_breakeven": kmax(T_MEAN - Q ** 2 * T_MEAN / (q ** 2 * req))}
                 for q in (890, 902, 914, 1260, 1310, 1730)},
    }

    for label, hold in [("errors_420_minus_pool_50", 370), ("errors_420", 420),
                        ("syndrome_816", 816)]:
        g, ratio = gm_new(rev_T_algo + 1_951, hold)
        out["best_losing"][label] = {"Q": Q + hold, "dT": rev_T_algo + 1_951,
                                      "T_new": T_MEAN - rev_T_algo - 1_951,
                                      "dT_required": dT_required(hold),
                                      "shortfall": dT_required(hold) - (rev_T_algo + 1_951),
                                      "cost_ratio": ratio, "GM": g}

    (HERE / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
