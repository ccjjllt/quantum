"""Build a pinned 18-member manifest from a staged candidate directory.

    python3 make_members.py --stage DIR --out members.json --label "..." \
        [--invsqrt-sha SHA --dqi-sha SHA]   # keep existing legs' shas from a base manifest

The staged directory must contain `invsqrt.kmb`, `dqi.kmb`, `dfthcsos/submission.npz`
and `dfthcsos/angle_k_0..K-1.kmb`. Members keep the manifest format used by
`make_main.py`: `{"members": {name: {sha256, size, source}}}`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--source", default="")
    a = ap.parse_args()
    root = pathlib.Path(a.stage)
    members = {}
    for rel in ["invsqrt.kmb", "dqi.kmb", "dfthcsos/submission.npz"]:
        p = root / rel
        if not p.is_file():
            raise SystemExit(f"missing {p}")
        members[rel] = {"sha256": sha256(p), "size": p.stat().st_size, "source": a.source or a.label}
    angles = sorted(
        (p for p in (root / "dfthcsos").glob("angle_k_*") if p.suffix in (".kmb", ".kmx")),
        key=lambda p: int(p.stem.split("_")[-1]),
    )
    if not angles:
        raise SystemExit("no dfthcsos/angle_k_*")
    for p in angles:
        rel = f"dfthcsos/{p.name}"
        members[rel] = {"sha256": sha256(p), "size": p.stat().st_size, "source": a.source or a.label}
    out = {"candidate": a.label, "members": members}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {a.out}: {len(members)} members ({len(angles)} loaders)")


if __name__ == "__main__":
    main()
