"""Exact official heuristic costs for candidate shapes, and the break-even lambda.

The ANGLE Toffoli term is held at the measured baseline 8,246 (2 x 4,123);
the report also shows the linear-loader-scaling projection for the 721-vector
shape, which is an assumption, not a measured circuit.
"""
from __future__ import annotations

import sys
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "data/competition/verifiers"))

from dfthcsos.verify import heuristic_costs  # noqa: E402

ANGLES_T = 8246
LAM_BASE = 46.90753743257459
SCORE_BASE = 298600061.555139
SHAPES = [(8, 143, 44), (5, 129, 68), (5, 129, 44), (5, 135, 70),
          (4, 131, 83), (6, 143, 59), (6, 180, 90), (5, 129, 60)]


def main() -> None:
    for R, B, C in SHAPES:
        h = heuristic_costs(76, R, B, C, 8)
        Q = h["persistent_qubits"] + 40 + max(90, h["temporary_qubits"])
        T = ANGLES_T + h["toffoli"]
        print(
            f"R{R}B{B}C{C}: heurT={h['toffoli']} "
            f"(outer={h['outer_state_prep_toffoli']}, "
            f"inner={h['inner_state_prep_toffoli']}, "
            f"givens={h['givens_rotations_toffoli']}) "
            f"persist={h['persistent_qubits']} itemp={h['temporary_qubits']} "
            f"Q={Q} T={T} TQ={T * Q} score@lambda_base={LAM_BASE * T * Q:.3f}"
        )
    h = heuristic_costs(76, 5, 129, 68, 8)
    Q = h["persistent_qubits"] + 40 + max(90, h["temporary_qubits"])
    print(f"(5,129,68) break-even lambda with current loaders: "
          f"{SCORE_BASE / ((ANGLES_T + h['toffoli']) * Q):.9f}")
    angles_linear = ANGLES_T * (76 + 5 * 129) / 1220
    T_linear = h["toffoli"] + angles_linear
    print(f"(5,129,68) linear loader projection: angles={angles_linear:.3f} "
          f"T={T_linear:.3f} Q={Q} score={LAM_BASE * T_linear * Q:.3f} "
          f"break-even lambda={SCORE_BASE / (T_linear * Q):.9f}")


if __name__ == "__main__":
    main()
