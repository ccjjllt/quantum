"""Build circuit variants from the baseline kmx text with simple edits.

Edits are given on the command line:
  drop=START:END      delete flat op indices [START, END)
  zpow=K:VALUE        replace the K-th rotation Z_POW exponent with VALUE

Op indices are 0-based over instructions (APPEND_TO_REGISTER / REGISTER lines
excluded), matching kmx_parse.Op.index.
"""

from __future__ import annotations

import argparse
import io
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def load_lines(path: Path) -> list[str]:
    import kickmix as km

    c = km.Circuit.from_file(str(path), format="auto")
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return buf.getvalue().splitlines()


def op_line_map(lines: list[str]) -> list[int]:
    out = []
    for i, line in enumerate(lines):
        if not line:
            continue
        head = line.split()[0]
        if head in ("APPEND_TO_REGISTER", "REGISTER"):
            continue
        out.append(i)
    return out


def rotation_lines(lines: list[str]) -> list[int]:
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
    ap.add_argument("out", type=Path)
    ap.add_argument("edit", nargs="*", default=[])
    args = ap.parse_args()

    lines = load_lines(args.circuit)
    omap = op_line_map(lines)
    rot = rotation_lines(lines)
    drop_lines: set[int] = set()
    zpow_new: dict[int, str] = {}
    for e in args.edit:
        if e.startswith("drop="):
            a, b = e[5:].split(":")
            for op in range(int(a), int(b)):
                drop_lines.add(omap[op])
        elif e.startswith("zpow="):
            k, v = e[5:].split(":")
            line = rot[int(k)]
            p = lines[line].split()
            lines[line] = f"Z_POW {p[1]} {v}"
            zpow_new[int(k)] = v
        else:
            raise SystemExit(f"bad edit {e}")
    out = [l for i, l in enumerate(lines) if i not in drop_lines]
    args.out.write_text("\n".join(out) + "\n")
    print(f"wrote {args.out} ({len(out)} lines, dropped {len(drop_lines)} lines, "
          f"zpow edits {sorted(zpow_new)})")


if __name__ == "__main__":
    main()
