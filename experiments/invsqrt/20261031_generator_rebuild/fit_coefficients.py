"""Refit integer coefficient tables for one explicit precision.

The fit uses the truncated signed-digit arithmetic. It does not truncate a
previously saved table, and it does not build a circuit or call the verifier.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import fit as Fm  # noqa: E402
import model as M  # noqa: E402
from recipe_io import tables_from_recipe  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--F0", type=int, required=True)
    parser.add_argument("--FT", type=int, required=True)
    parser.add_argument("--F2", type=int, required=True)
    parser.add_argument("--G0", type=int, required=True)
    parser.add_argument("--drop-a", default="5")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    drop_a = {int(v) for v in args.drop_a.split(",") if v != ""}
    prm = M.Params(
        F0=args.F0, FT=args.FT, F2=args.F2, G0=args.G0,
        booth=False, sd=True, tcap=True,
        rowsA=tuple(i for i in range(14) if i not in drop_a),
        rowsB=tuple(range(14)),
    )
    tables, worst = Fm.fit_all(prm, rad1=6, rad2=3, verbose=True, workers=args.workers)
    published = tables_from_recipe(even_c0=False)
    same = bool(tables.shape == published.shape and np.array_equal(tables, published))
    truncated = False
    if tables.shape == published.shape:
        # A truncation of the published word would keep the high bits and zero the low bits.
        for shift in range(1, 6):
            if np.array_equal(tables, published >> shift) or np.array_equal(tables, published & (-1 << shift)):
                truncated = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "F0": args.F0, "FT": args.FT, "F2": args.F2, "G0": args.G0,
        "dropA": sorted(drop_a),
        "fit_worst_relative_proxy": worst,
        "identical_to_published_recipe_table": same,
        "is_truncation_of_published_table": truncated,
        "tables": tables.astype(int).tolist(),
        "official_verifier_called": False,
    }
    args.out.write_text(json.dumps(payload) + "\n")
    print(json.dumps({k: payload[k] for k in payload if k != "tables"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
