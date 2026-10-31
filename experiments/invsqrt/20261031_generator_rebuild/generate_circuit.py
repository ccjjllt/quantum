"""Deterministic invsqrt circuit generation.

Inputs are parameters plus integer coefficient and exact phase tables.
The run writes a circuit, static resource counts, and a source manifest.
It does not call the official verifier and it does not read a baseline circuit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import circuit  # noqa: E402
import hsplit as H  # noqa: E402
import model as M  # noqa: E402
import build as Bd  # noqa: E402
from recipe_io import (  # noqa: E402
    DEFAULT_PLAN,
    load_recipe,
    params_from_recipe,
    phase_angles,
    tables_from_recipe,
)


UNITS = """
integer truncation and rounding:
  shift shr(v, e) floors. A negative exponent is a left shift, exact.
  signed-digit rows use rd(v, s) = floor(v / 2^s) + the next bit (round half up).
  coefficient fit rounds the continuous minimax (C1, C2) to integers, then
  searches a neighbourhood. C0 is the integer minimax offset of the truncated Horner sum.
  the virtual-bit recipe adds 1 to an odd C0 so the constant word is even.
overflow:
  T must lie in [0, 2^(FT-1)) because tcap is on (T register width FT-1).
  Y' must lie in [0, 2^(F0-1)). The layout rejects a segment whose low word
  leaves [0, 2^LB). A circuit build does not wrap those registers.
phase units:
  one turn is the full circle. Circuit Z_POW angles are half-turns (Fraction).
  Stored angles and the model accumulator are integers in units of 2^-64 turns.
  phase = 2^(s-10) * (Y' * 2^-F0 + 1/2), with s the number of leading-zero pairs.
  HMR phase identity, measurement record version 1:
    after an even unshift of width d, the flag qubit equals 1 iff the top d
    bits of x are 0. HMR moves that qubit onto a fresh classical bit m and
    leaves |+> or the measured branch. The conditional X on those d bits,
    the conditional CZ ladder that computes their parity, and the closing X
    put a minus on the m=1 branch exactly when the parity of the restored
    prefix is odd, cancelling the |-> phase of the measurement. The classical
    bit is freed with the condition. The same identity is used for the
    curvature-mask and lookup-mask records: mdel applies
    (-1)^{m . table[address]} and discards m.
recipe identity:
  F0, FT, F2, G0, LB, S select one published coefficient recipe.
  That recipe is a different circuit from baseline SHA-256
  6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4.
  This generator does not reconstruct that file.
""".strip()


def canonical_sha256(circuit_obj) -> str:
    buf = __import__("io").BytesIO()
    circuit_obj.to_file(buf, format="kmb")
    return hashlib.sha256(buf.getvalue()).hexdigest()


def build_from_tables(tables, prm, angles, *, lb, s, plan, retire, initial_lookup, last, prefix=0, derivative_split=None):
    lay = H.layout(tables, prm, lb, s)
    if lay is None:
        raise SystemExit(f"no high/low layout for LB={lb} S={s}")
    wins = H.parse_plan(plan)
    cbits = H.choose_cbits(tables, prm, lay, wins)
    if cbits is None:
        raise SystemExit(f"window plan does not fit a 3-bit carry: {plan}")
    domains = H.Fm.domains() if H.Fm._D is None else H.Fm._D
    _a, p, xn, _bounds = domains
    windows = M.window_ranges1(tables, prm, xn, p)
    if windows["A"] is None and derivative_split is None:
        raise SystemExit("step A has no 1-guard window")
    wa = windows["A"] if derivative_split is None else int(derivative_split)
    opts = Bd.Opts(WA=wa, gA=1)
    opts.mdel = True
    opts.wins = wins
    opts.wcb = cbits
    opts.kbig = 0
    opts.qcap = None
    opts.retire = retire
    opts.initial_lookup = initial_lookup
    opts.last = last
    opts.prefix = int(prefix or 0)
    circ = circuit.build_ladder(tables, prm, opts, lay, angles)
    static = dict(circ.operation_statistics())
    resources = {
        "qubits": circ.num_qubits,
        "operations": len(circ),
        "static_operations": {str(k): int(v) for k, v in static.items()},
        "static_toffoli_like": int(circ.operation_statistics().num_toffoli_like),
        "peak_allocated": list(Bd.LAST_PEAK),
        "window_A": wa,
        "window_B": windows["B"],
        "carry_bits": cbits,
        "LB": lay.LB,
        "S": lay.S,
        "nH": lay.nH,
        "plan": plan,
        "retire": retire,
        "initial_lookup": initial_lookup,
        "last": last,
        "prefix": int(prefix or 0),
    }
    return circ, resources


def angles_sha256(angles) -> str:
    raw = json.dumps(angles).encode()
    return hashlib.sha256(raw).hexdigest()


def resolve_angles(tables, prm, lb, s, angles_path, recipe):
    """Published angles stay on the published table. Any other table is calibrated."""
    published_angles = phase_angles()
    published_tables = tables_from_recipe(recipe, even_c0=True)
    published_params = tuple(int(v) for v in recipe["params"])
    same_params = (prm.F0, prm.FT, prm.F2, prm.G0) == published_params
    same_table = tables.shape == published_tables.shape and np.array_equal(tables, published_tables)
    if same_params and same_table:
        return published_angles, {
            "angle_source": "published recipe calibration",
            "angles_calibrated_to_table": True,
            "refused_published_angles": False,
            "angles_sha256": angles_sha256(published_angles),
        }
    refused = False
    if angles_path is not None:
        given = phase_angles(angles_path)
        if given == published_angles:
            refused = True
            print("refused published angles for a non-recipe table", flush=True)
    lay = H.layout(tables, prm, lb, s)
    if lay is None:
        raise SystemExit(f"no high/low layout for angle calibration at LB={lb} S={s}")
    calibrated = H.calibrate_multi(tables, prm, lay, drop=1, iters=12, verbose=False)
    if calibrated is None:
        raise SystemExit("absolute-margin angle calibration failed")
    angles, worst, margin, nrot = calibrated
    return angles, {
        "angle_source": "absolute-margin calibration of this table",
        "angles_calibrated_to_table": True,
        "refused_published_angles": refused,
        "angles_sha256": angles_sha256(angles),
        "published_angles_sha256": angles_sha256(published_angles),
        "angles_differ_from_published": angles != published_angles,
        "calibration_worst_ratio": worst,
        "calibration_margin": margin,
        "calibration_nrot": nrot,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--F0", type=int, default=28)
    parser.add_argument("--FT", type=int, default=19)
    parser.add_argument("--F2", type=int, default=8)
    parser.add_argument("--G0", type=int, default=1)
    parser.add_argument("--LB", type=int, default=21)
    parser.add_argument("--S", type=int, default=20)
    parser.add_argument("--plan", default=DEFAULT_PLAN)
    parser.add_argument("--retire", type=int, default=3)
    parser.add_argument("--prefix", type=int, default=0)
    parser.add_argument("--initial-lookup", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--last", action="store_true")
    parser.add_argument("--tables", type=Path, default=None, help="JSON list of [C0,C1,C2] rows, or a recipe file.")
    parser.add_argument("--angles", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    loaded = load_recipe()
    recipe = loaded["recipe"]
    if [args.F0, args.FT, args.F2, args.G0] != [int(v) for v in recipe["params"]] or args.tables:
        if args.tables is None:
            raise SystemExit("a precision other than the published recipe needs --tables from a refit")
        payload = json.loads(args.tables.read_text())
        rows = payload["tables"] if isinstance(payload, dict) else payload
        tables = np.array(rows, dtype="int64")
        prm = M.Params(
            F0=args.F0, FT=args.FT, F2=args.F2, G0=args.G0,
            booth=False, sd=True, tcap=True,
            rowsA=tuple(i for i in range(14) if i not in set(recipe.get("dropA", [5]))),
            rowsB=tuple(range(14)),
        )
    else:
        prm = params_from_recipe(recipe)
        tables = tables_from_recipe(recipe, even_c0=True)
    angles, angle_info = resolve_angles(tables, prm, args.LB, args.S, args.angles, recipe)

    circ, resources = build_from_tables(
        tables, prm, angles,
        lb=args.LB, s=args.S, plan=args.plan, retire=args.retire,
        initial_lookup=args.initial_lookup, last=args.last, prefix=args.prefix,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    circ.to_file(args.out, format="kmb")
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    canonical = canonical_sha256(circ)
    resources.update({
        "kmb_sha256": digest,
        "canonical_kmb_sha256": canonical,
        "F0": prm.F0, "FT": prm.FT, "F2": prm.F2, "G0": prm.G0,
        "rowsA": list(prm.rowsA), "rowsB": list(prm.rowsB),
        "sd": prm.sd, "tcap": prm.tcap,
        **angle_info,
    })
    manifest = {
        "generator": "experiments/invsqrt/20261031_generator_rebuild/generate_circuit.py",
        "algorithm": "normalized signed-digit quadratic, high/low split, fused phase",
        "dataset": "dmitriigluzdov/vqcc-femoco-public-factorization",
        "dataset_version": 39,
        "license": "Apache-2.0",
        "dependencies": ["vendor/model.py", "vendor/build.py", "vendor/hsplit.py", "vendor/round10_virtual.py", "vendor/round10_lookup.py"],
        "provenance": "PROVENANCE.json",
        "does_not_reconstruct_baseline_sha256": "6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4",
        "official_verifier_called": False,
        "baseline_kmb_read": False,
        "resources": resources,
        "units": UNITS,
    }
    manifest["angles"] = angles
    manifest_path = args.manifest or args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (args.out.with_suffix(".resources.json")).write_text(json.dumps(resources, indent=2) + "\n")
    angles_path = args.out.with_suffix(".angles.json")
    angles_path.write_text(json.dumps({"angles": angles, **angle_info}, indent=2) + "\n")
    print(UNITS)
    print(json.dumps({
        "canonical_kmb_sha256": canonical,
        "qubits": resources["qubits"],
        "static_toffoli_like": resources["static_toffoli_like"],
        "official_verifier_called": False,
        "baseline_kmb_read": False,
        **angle_info,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
