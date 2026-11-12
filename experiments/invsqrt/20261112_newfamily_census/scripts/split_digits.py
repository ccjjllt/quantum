"""Split the 41 rotation Z_POW angles into indivisible per-x digits.

For each rotation k, delete its Z_POW instruction and evaluate the phase over
the whole x domain.  The phase difference versus the baseline is exactly
`digit_k(x) * theta_k` in half-turns (the circuit is a classical reversible
phase oracle, so the phase is linear in each rotation angle).

Writes `digits.npz` with the per-rotation difference and the baseline phase.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent


def kmx_lines(path: Path) -> list[str]:
    import kickmix as km

    c = km.Circuit.from_file(str(path), format="auto")
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return buf.getvalue().splitlines()


def rotation_indices(lines: list[str]) -> list[int]:
    out = []
    for i, line in enumerate(lines):
        p = line.split()
        if p and p[0] == "Z_POW":
            e = Fraction(p[2])
            if e % Fraction(1, 2) == 0 or e % Fraction(1, 4) == 0:
                continue
            out.append(i)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--max-x", type=int, default=None)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--phase-only", action="store_true", default=True)
    args = ap.parse_args()

    lines = kmx_lines(args.circuit)
    idx = rotation_indices(lines)
    print(f"{len(idx)} rotation Z_POW instructions at lines {idx}")
    args.outdir.mkdir(parents=True, exist_ok=True)

    # baseline
    base_txt = args.outdir / "base.kmx"
    base_txt.write_text("\n".join(lines) + "\n")
    variants = []
    for k, line_no in enumerate(idx):
        mod = list(lines)
        mod[line_no] = "NOP"
        # kickmix has no NOP; drop the line instead
        mod[line_no] = ""
        p = args.outdir / f"drop{k:02d}.kmx"
        p.write_text("\n".join(l for l in mod if l) + "\n")
        variants.append(p)

    tasks = [base_txt] + variants
    cmd_base = [sys.executable, str(HERE / "eval_phase.py"), "--seed", str(args.seed)]
    if args.max_x:
        cmd_base += ["--max-x", str(args.max_x)]
    procs = []
    running: list[tuple[subprocess.Popen, Path]] = []
    import time

    def launch(path: Path) -> subprocess.Popen:
        out = path.with_suffix(".npz")
        cmd = cmd_base + [str(path), "--out", str(out)]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    for path in tasks:
        if len(running) >= args.jobs:
            running[0][0].wait()
            running.pop(0)
        running.append((launch(path), path))
    for proc, _ in running:
        proc.wait()

    base_npz = np.load(base_txt.with_suffix(".npz"))
    xs = base_npz["xs"]
    base_err = base_npz["err"].astype(np.int64)
    tol = base_npz["tol"]
    diffs = []
    dead = []
    for k in range(len(idx)):
        v = np.load((args.outdir / f"drop{k:02d}.npz"))
        # phase difference in 2^-64 turn units: err_variant - err_base
        d = v["err"].astype(np.int64) - base_err
        diffs.append(d)
        unique = np.unique(np.abs(d))
        ratio = np.abs(d).max() / 2**64
        if np.abs(d).max() == 0:
            dead.append(k)
            print(f"  drop{k:02d}: DEAD (phase identical on all {len(xs)} x)")
        else:
            print(f"  drop{k:02d}: distinct |delta|={len(unique)} max={int(np.abs(d).max())} units ({ratio:.3e} turns)")
    print(f"dead rotations: {dead}")
    np.savez(args.outdir / "digits.npz", xs=xs, base_err=base_err, tol=tol,
             diffs=np.array(diffs, dtype=np.int64), theta=np.array(
                 [float(Fraction(lines[i].split()[2])) for i in idx]))


if __name__ == "__main__":
    main()
