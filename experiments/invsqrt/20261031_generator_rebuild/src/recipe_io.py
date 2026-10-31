"""Load an explicit parameter set and integer tables. No circuit and no verifier."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import model as M

HERE = Path(__file__).resolve().parents[1]
RECIPE = HERE / "recipe" / "selected_invsqrt.json"
PHASE = HERE / "recipe" / "selected_phase_fit.json"

# Upstream window plan recorded with the v39 selected recipe.
DEFAULT_PLAN = "17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0"


def load_recipe(path: Path | None = None) -> dict:
    return json.loads((path or RECIPE).read_text())


def params_from_recipe(recipe: dict | None = None) -> M.Params:
    recipe = recipe if recipe is not None else load_recipe()["recipe"]
    f0, ft, f2, g0 = (int(v) for v in recipe["params"])
    drop_a = {int(v) for v in recipe.get("dropA", [])}
    drop_b = {int(v) for v in recipe.get("dropB", [])}
    return M.Params(
        F0=f0,
        FT=ft,
        F2=f2,
        G0=g0,
        booth=False,
        sd=True,
        tcap=True,
        rowsA=tuple(i for i in range(14) if i not in drop_a),
        rowsB=tuple(i for i in range(14) if i not in drop_b),
    )


def tables_from_recipe(recipe: dict | None = None, *, even_c0: bool = True) -> np.ndarray:
    recipe = recipe if recipe is not None else load_recipe()["recipe"]
    tables = np.array(recipe["tables"], dtype=np.int64)
    if even_c0:
        # Virtual low bit of Y' requires an even constant word. Odd words move up by one.
        tables = tables.copy()
        tables[:, 0] += tables[:, 0] & 1
    return tables


def phase_angles(path: Path | None = None) -> list[list[int]]:
    payload = json.loads((path or PHASE).read_text())
    return [[int(a) for a in row] for row in payload["angles"]]
