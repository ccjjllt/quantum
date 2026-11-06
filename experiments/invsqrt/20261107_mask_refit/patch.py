"""Patch the baseline KMB: modify fine-rotation angles, insert mask gates.

The circuit is manipulated as kmx text (the only stable serialization API
kickmix exposes).  Rotation angles are exact binary fractions of a half turn,
so they are written as exact finite decimals.
"""
from __future__ import annotations

import io
from fractions import Fraction
from pathlib import Path

import kickmix as km

import model as M

BASE = M.BASE_KMB


def fmt_half_turns(units: int) -> str:
    """Exact decimal for a half-turn angle given in units of 2^-64 turns."""
    u = int(units) % (1 << 64)      # half turns mod 2 == phase mod 1 turn
    fr = Fraction(u, 1 << 63)
    n, d = fr.numerator, fr.denominator
    k = d.bit_length() - 1          # d == 2**k
    scaled = n * 5**k
    s = str(scaled).rjust(k + 1, "0")
    return s[:-k] + "." + s[-k:] if k else s


def is_rotation(theta: Fraction) -> bool:
    return theta % Fraction(1, 2) != 0 and theta % Fraction(1, 4) != 0


def load_lines(path: Path = BASE) -> tuple[list[str], list[str]]:
    c = km.Circuit.from_file(path)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    all_lines = buf.getvalue().splitlines()
    header = [l for l in all_lines if l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    body = [l for l in all_lines if not l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    return header, body


def rotation_indices(body: list[str]) -> list[int]:
    out = []
    for i, line in enumerate(body):
        p = line.split()
        if p[0] == "Z_POW" and is_rotation(Fraction(p[2])):
            out.append(i)
    return out


def build(theta_units, inserts: dict[int, list[str]] | None = None,
          path: Path = BASE) -> km.Circuit:
    """Return a Circuit with new angles and optional gate lines inserted.

    theta_units: length-41 int64 angles (units 2^-64 turns, half-turn scale).
    inserts: {rotation_index: [kmx gate lines]} placed immediately before the
             Z_POW of that rotation.
    """
    header, body = load_lines(path)
    rot_idx = rotation_indices(body)
    assert len(rot_idx) == 41, len(rot_idx)
    new_body: list[str] = []
    rot = 0
    inserts = inserts or {}
    for i, line in enumerate(body):
        if i in rot_idx:
            if rot in inserts:
                new_body.extend(inserts[rot])
            p = line.split()
            assert p[0] == "Z_POW"
            new_body.append(f"Z_POW q{p[1][1:]} {fmt_half_turns(theta_units[rot])}")
            rot += 1
        else:
            new_body.append(line)
    text = "\n".join(header + new_body) + "\n"
    return km.Circuit.from_file(io.StringIO(text), format="kmx")


def write(circuit: km.Circuit, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        circuit.to_file(f, format="kmb")
