"""High/low-split refits and recovery-schedule costs.

Coefficient tables are refit for the recipe precision. Each LB/S neighbor is
then tested on that refit. A split whose Horner image is wider than 2^LB
cannot be repaired by changing C0. Recovery schedules count Toffoli-like
gates in cache writes, cache reads, clears, and phase corrections.
This script does not call the official verifier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import build as Bd  # noqa: E402
import circuit  # noqa: E402
import fit as Fm  # noqa: E402
import hsplit as H  # noqa: E402
import kickmix as km  # noqa: E402
import model as M  # noqa: E402
from recipe_io import load_recipe, params_from_recipe, phase_angles  # noqa: E402

OUT = ROOT.parents[2] / "artifacts" / "20261031_invsqrt_generator_rebuild"
TOFFOLI = ("ccx", "ccz", "cswap")


def correction_span(tables, prm):
    a, _p, xn, bounds = Fm.domains(prm)
    b = xn & ((1 << prm.delta_bits) - 1)
    c0, c1, c2 = tables[a, 0], tables[a, 1], tables[a, 2]
    correction = M.eval_Y(c0, M.eval_T(c1, c2, b, prm), b, prm) - c0
    dmin = np.minimum.reduceat(correction, bounds[:-1])
    dmax = np.maximum.reduceat(correction, bounds[:-1])
    present = bounds[1:] > bounds[:-1]
    span = (dmax - dmin)[present]
    return {
        "segments_used": int(present.sum()),
        "max_span": int(span.max()),
        "min_span": int(span.min()),
    }


def c0_fits(c0, dmin, dmax, lb, s):
    if c0 < 0:
        return False
    base = c0 % (1 << s)
    j = 0
    while base + j * (1 << s) + dmin < 0:
        j += 1
        if j > 64:
            return False
    uk = base + j * (1 << s)
    return uk + dmax < (1 << lb) and c0 - uk >= 0


def align_low_word(tables, prm, lb, s, radius=512):
    """Move even C0 values so the refit low word fits this split."""
    a, _p, xn, bounds = Fm.domains(prm)
    b = xn & ((1 << prm.delta_bits) - 1)
    c0, c1, c2 = tables[a, 0], tables[a, 1], tables[a, 2]
    correction = M.eval_Y(c0, M.eval_T(c1, c2, b, prm), b, prm) - c0
    adjusted = tables.copy()
    moved = 0
    for seg in range(prm.n_segments):
        lo, hi = int(bounds[seg]), int(bounds[seg + 1])
        if lo == hi:
            continue
        dmin = int(correction[lo:hi].min())
        dmax = int(correction[lo:hi].max())
        current = int(adjusted[seg, 0])
        if c0_fits(current, dmin, dmax, lb, s):
            continue
        found = None
        for step in range(1, radius + 1):
            for cand in (current - 2 * step, current + 2 * step):
                if c0_fits(cand, dmin, dmax, lb, s):
                    found = cand
                    break
            if found is not None:
                break
        if found is None:
            return None, {"segment": seg, "dmin": dmin, "dmax": dmax, "span": dmax - dmin, "C0": current}
        adjusted[seg, 0] = found
        moved += 1
    return adjusted, {"segments_moved": moved}


def try_layout(tables, prm, lb, s):
    span = correction_span(tables, prm)
    if span["max_span"] >= (1 << lb):
        return {"LB": lb, "S": s, "layout": False, "reason": "Horner image wider than 2^LB; no C0 refit fits", **span}
    lay = H.layout(tables, prm, lb, s)
    if lay is None:
        return {"LB": lb, "S": s, "layout": False, "reason": "no aligned low word for these C0 residues", **span}
    return {"LB": lb, "S": s, "layout": True, "nH": int(lay.nH), "nHf": int(lay.nHf), **span, "layout_object": lay}


class CountingBuilder(Bd.B):
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == "label":
            STAGE[0] = value
            STAGE[1] = STAGE[2].get(value, 0) + 1
            STAGE[2][value] = STAGE[1]


STAGE = ["init", 1, {}]
COUNTS = {}


def install_counter():
    circuit.Bd.B = CountingBuilder
    real_unary = circuit.unary_lookup
    real_inner = circuit.virtual_inner
    real_win = circuit.win_step
    real_phase = circuit.Bd.fused_phase
    real_mdel = circuit.mdel

    def unary(*args, **kwargs):
        STAGE[0] = "lookup-write"
        return real_unary(*args, **kwargs)

    def inner(*args, **kwargs):
        which = STAGE[2].get("inner", 0) + 1
        STAGE[2]["inner"] = which
        STAGE[0] = "derivative-write" if which == 1 else "derivative-clear"
        return real_inner(*args, **kwargs)

    def win(*args, **kwargs):
        which = STAGE[2].get("win", 0) + 1
        STAGE[2]["win"] = which
        STAGE[0] = "cache-write" if which == 1 else "cache-read-clear"
        return real_win(*args, **kwargs)

    def phase(*args, **kwargs):
        which = STAGE[2].get("phase", 0) + 1
        STAGE[2]["phase"] = which
        STAGE[0] = "phase-high" if which == 1 else "phase-low"
        return real_phase(*args, **kwargs)

    def mdel(*args, **kwargs):
        STAGE[0] = "lookup-clear"
        return real_mdel(*args, **kwargs)

    circuit.unary_lookup = unary
    circuit.virtual_inner = inner
    circuit.win_step = win
    circuit.Bd.fused_phase = phase
    circuit.mdel = mdel
    for name in ("ccx", "ccz", "cswap", "hmr", "z_pow", "init_lookup", "del_lookup", "init_and", "del_and"):
        original = getattr(km.CircuitBuilder, name)

        def wrapped(self, *args, _name=name, _original=original, **kwargs):
            key = f"{STAGE[0]}#{STAGE[1]}:{_name}"
            COUNTS[key] = COUNTS.get(key, 0) + 1
            return _original(self, *args, **kwargs)

        setattr(km.CircuitBuilder, name, wrapped)


def bucket(counts):
    """Toffoli-like gates in writes, reads, clears, and phase corrections."""
    groups = {name: {"ccx": 0, "ccz": 0, "cswap": 0, "hmr": 0, "z_pow": 0, "init_lookup": 0, "del_lookup": 0}
              for name in ("cache_write", "cache_read", "clear", "phase_correction", "other")}
    for key, n in counts.items():
        label, _, op = key.partition(":")
        stage, _, visit_s = label.partition("#")
        visit = int(visit_s or "1")
        if stage in ("lookup-write", "cache-write", "derivative-write"):
            kind = "cache_write"
        elif stage == "cache-read-clear":
            kind = "cache_read"
        elif stage in ("derivative-clear", "lookup-clear"):
            kind = "clear"
        elif stage in ("phase-high", "phase-low"):
            kind = "phase_correction"
        elif op in ("hmr", "del_lookup", "del_and"):
            kind = "clear"
        else:
            kind = "other"
        if op in groups[kind]:
            groups[kind][op] += n
    def toffoli(group):
        return group["ccx"] + group["ccz"] + group["cswap"]
    summary = {name: {"toffoli_like": toffoli(group), **group} for name, group in groups.items()}
    return summary, {}


def build_schedule(tables, prm, angles, lb, s, plan, cmax):
    lay_info = try_layout(tables, prm, lb, s)
    lay = lay_info.get("layout_object")
    if lay is None:
        return {"plan": plan, "cmax": cmax, **{k: v for k, v in lay_info.items() if k != "layout_object"}}
    wins = H.parse_plan(plan)
    cbits = H.choose_cbits(tables, prm, lay, wins, cmax=cmax)
    if cbits is None:
        return {"plan": plan, "LB": lb, "S": s, "cmax": cmax, "built": False, "reason": "carry does not fit"}
    _a, p, xn, _b = Fm.domains(prm)
    windows = M.window_ranges1(tables, prm, xn, p)
    if windows["A"] is None:
        return {"plan": plan, "built": False, "reason": "no 1-guard derivative window"}
    COUNTS.clear()
    STAGE[0], STAGE[1], STAGE[2] = "init", 1, {}
    opts = Bd.Opts(WA=windows["A"], gA=1)
    opts.mdel = True
    opts.wins = wins
    opts.wcb = cbits
    opts.kbig = 0
    opts.qcap = None
    opts.retire = 3
    opts.initial_lookup = True
    opts.last = False
    opts.prefix = 0
    circ = circuit.build_ladder(tables, prm, opts, lay, angles)
    groups, detail = bucket(dict(COUNTS))
    raw = dict(COUNTS)
    static = circ.operation_statistics()
    return {
        "plan": plan,
        "LB": lb,
        "S": s,
        "cmax": cmax,
        "built": True,
        "carry_bits": list(cbits),
        "retained_windows": len(wins),
        "qubits": circ.num_qubits,
        "static_toffoli_like": int(static.num_toffoli_like),
        "writes_reads_clears_phase": groups,
        "init_and": sum(v for k, v in raw.items() if k.endswith(":init_and")),
        "del_and": sum(v for k, v in raw.items() if k.endswith(":del_and")),
        "gate_detail_head": dict(list(detail.items())[:12]),
        "peak": list(Bd.LAST_PEAK),
    }


def main() -> int:
    install_counter()
    loaded = load_recipe()
    prm = params_from_recipe(loaded["recipe"])
    tables, proxy = Fm.fit_all(prm, rad1=6, rad2=3, workers=8, verbose=False)
    published = phase_angles()
    span = correction_span(tables, prm)
    splits = []
    neighbors = [(20, 19), (20, 20), (21, 19), (21, 20), (21, 21), (22, 19), (22, 20), (22, 21)]
    for lb, s in neighbors:
        info = try_layout(tables, prm, lb, s)
        info.pop("layout_object", None)
        info["coefficient_refit_proxy"] = proxy
        info["tables"] = "fresh refit of F0=28 FT=19 F2=8 G0=1, not a truncation"
        if not info["layout"]:
            adjusted, note = align_low_word(tables, prm, lb, s)
            info["c0_alignment_refit"] = note if adjusted is None else {"segments_moved": note["segments_moved"]}
            if adjusted is not None:
                laid = H.layout(adjusted, prm, lb, s)
                info["layout_after_c0_refit"] = laid is not None
                if laid is not None:
                    checked = M.full_check(adjusted, prm)
                    info["model_after_c0_refit"] = {k: checked[k] for k in checked if k != "err"}
        splits.append(info)
        print(json.dumps({k: v for k, v in info.items() if k != "layout_object"}), flush=True)
    schedules = []
    plans = {
        "reuse": "17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0",
        "retain_1": "12:11,10,9,8,7,6,5,4,3,2,1,0",
        "retain_2": "14:11,10,9,8,7,6;8:5,4,3,2,1,0",
    }
    for name, plan in plans.items():
        found = None
        for cmax in (3, 4, 5, 6, 8):
            row = build_schedule(tables, prm, published, 21, 20, plan, cmax)
            row["schedule"] = name
            print(json.dumps({k: row[k] for k in row if k != "gate_detail_head"}), flush=True)
            if row.get("built"):
                found = row
                break
            found = row
        schedules.append(found)
    payload = {
        "official_verifier_called": False,
        "five_percent_target": "still open",
        "best_measured_cost": 144556.97,
        "correction_span": span,
        "splits": splits,
        "schedules": schedules,
    }
    path = OUT / "recovery_split.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
