"""Validate the mask/refit pipeline against the public guard-bit correction.

Rot 15 (op 25408) already contains F15 XOR [Y1 AND (e1 XOR e2)] where
Y1=q54, e1=q18, e2=q27.  Removing it (g = f15 XOR guard) and refitting must
reproduce the public pre-guard margin 47,884,702 units of 2^-64 turns.
"""
from __future__ import annotations

import json

import numpy as np

import model as M

OUT = M.ART
WIRES = OUT / "wires"


def load_cp(i: int) -> list[int]:
    z = np.load(WIRES / f"cp_{i:02d}.npz")
    return [int.from_bytes(z[f"w{j}"].tobytes(), "little") for j in range(62)]


def wire_bool(i: int, j: int) -> np.ndarray:
    z = np.load(WIRES / f"cp_{i:02d}.npz")
    return np.unpackbits(z[f"w{j}"], bitorder="little")[: M.MAXX].astype(bool)


def main() -> None:
    m = M.load_model()
    masks, thetas, T, tol = m["masks"], m["thetas"], m["T"], m["tol"]
    base = M.margins(M.phase_of(masks, thetas), T, tol)
    print("baseline", base)

    ref_wires = load_cp(15)
    guard = (ref_wires[54] & (ref_wires[18] ^ ref_wires[27]))
    gmask = np.frombuffer(guard.to_bytes(M.NB, "little"), dtype=np.uint8)
    guard_b = np.unpackbits(gmask, bitorder="little")[: M.MAXX].astype(bool)
    # sanity: is the guard already part of f15?  f15 XOR guard must differ.
    print("guard popcount", int(guard_b.sum()),
          "f15 popcount", int(masks[15].sum()),
          "xor popcount", int((masks[15] ^ guard_b).sum()))

    # Remove the guard from rot 15 and refit.
    new_mask = masks[15] ^ guard_b
    cand = list(masks)
    cand[15] = new_mask
    ph0 = M.phase_of(cand, thetas)
    st0 = M.margins(ph0, T, tol)
    print("no-guard, old angles", st0)

    rng = np.random.default_rng(20261107)
    tight = np.argsort(tol - np.abs(M.err_of(ph0, T)))[:2000]
    idx = np.unique(np.concatenate([np.arange(8192), rng.integers(0, M.MAXX, 12000), tight]))
    out = M.refit(cand, thetas, T, tol, idx, max_iter=10, verbose=True)
    print("no-guard refit margin", out["margin"],
          "public pre-guard 47,884,702; ratio", out["margin"] / 47884702)

    rec = {"baseline": base, "guard_popcount": int(guard_b.sum()),
           "no_guard_old_angles": st0,
           "no_guard_refit": {"margin": out["margin"], "history": out["history"],
                              "public_pre_guard": 47884702,
                              "ratio_to_public": out["margin"] / 47884702}}
    (OUT / "validate_guard.json").write_text(json.dumps(rec, indent=2) + "\n")
    print("wrote validate_guard.json")


if __name__ == "__main__":
    main()
