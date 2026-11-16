"""Delete chosen op lines from a .kmx/.kmb and write the result (no renumbering).

Usage:
  python prune.py <base.kmb> <out.kmx> <op_index> [<op_index> ...] [--keep N1,N2]

Op indices are 0-based indices into the filtered kmx line list (same convention as the
analysis scripts).  Optional --keep lists extra indices that must be preserved.
"""
import sys
from pathlib import Path

import kickmix


def load_lines(path: Path):
    if path.suffix == ".kmb":
        c = kickmix.Circuit.from_file(path, format="auto")
        tmp = Path("/tmp/_prune_base.kmx")
        c.to_file(tmp)
        return tmp.read_text().splitlines()
    return path.read_text().splitlines()


def main() -> None:
    base = Path(sys.argv[1])
    out = Path(sys.argv[2])
    rest = sys.argv[3:]
    keep = set()
    if "--keep" in rest:
        k = rest.index("--keep")
        keep = {int(x) for x in rest[k + 1].split(",")}
        rest = rest[:k] + rest[k + 2:]
    drop = {int(x) for x in rest} - keep
    lines = [l for l in load_lines(base) if l.strip()]
    print(f"lines {len(lines)}  dropping {len(drop)}")
    for i in sorted(drop):
        print(f"  drop {i}: {lines[i]}")
    kept = [l for i, l in enumerate(lines) if i not in drop]
    out.write_text("\n".join(kept) + "\n")
    print("wrote", out, len(kept), "lines")


if __name__ == "__main__":
    main()
