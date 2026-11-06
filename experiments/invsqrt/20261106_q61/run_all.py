"""Run every q61 analysis script once and record the actual stdout in artifacts/.../run.log.

Manual, read-only over the baseline.  Exists so the research record has one reproducible log
instead of scattered terminal output.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "artifacts/20261106_q61"

STEPS = [
    ("metric_check.py", []),
    ("common.py", []),
    ("scratch_table.py", []),
    ("lifecycle.py", ["49", "34", "53", "35", "33", "23"]),
    ("value_liveness.py", []),
    ("peak_blocks.py", []),
    ("peak_profile.py", []),
    ("effective_use.py", []),
    ("span_test.py", ["0", "1"]),
    ("peak_bound.py", []),
    ("alias_scan.py", ["49", "34", "53", "35", "33", "23"]),
    ("collision_at_peak.py", ["15283", "49", "34", "53", "35", "33", "23"]),
    ("collision_at_peak.py", ["24922", "23"]),
    ("cheap_expr.py", ["15283:q49", "15283:q34", "15283:q53", "15283:q35",
                       "15283:q33", "15283:q23", "24922:q23", "16877:q42",
                       "16963:q22", "16965:q31", "17413:q37", "16886:q61"]),
    ("probe_classical_phase.py", ["0", "10"]),
    ("multibranch.py", ["28380:q50", "28383:q41", "28415:q23"]),
    ("park_cover.py", []),
    ("park_cover_cost.py", []),
    ("park_missing.py", []),
    ("park_rebuild_screen.py", []),
    ("final_table.py", []),
    ("commute_exact.py", []),
    ("commute_blockers.py", []),
    ("commute_v4.py", []),
    ("commute_summary.py", []),
    ("validate_reorder.py", []),
    ("nonlinear_rebuild.py", ["16750:zero", "16887:zero", "18483:zero"]),
    ("verify_products.py", []),
    ("cubic_check.py", []),
    ("quadratic_rank.py", []),
    ("rebuild_blocks.py", []),
    ("nonlinear_summary.py", []),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / "run.log"
    with log.open("w") as fh:
        for name, args in STEPS:
            cmd = [sys.executable, str(HERE / name), *args]
            fh.write(f"$ {' '.join([name, *args])}\n")
            fh.flush()
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            fh.write(p.stdout)
            if p.returncode:
                fh.write(f"[exit {p.returncode}]\n{p.stderr}\n")
            fh.write("\n")
            print(f"{name} {' '.join(args)} -> exit {p.returncode}", flush=True)
    print("log:", log)


if __name__ == "__main__":
    main()
