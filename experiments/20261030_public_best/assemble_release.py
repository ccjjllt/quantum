"""Reconstruct the pinned public portfolio from its downloaded release files.

This copies published circuits; it is not their algorithmic generator.
No simulation, official verification, packaging or submission is performed.
"""

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.release / "QCC_RELEASE_MANIFEST.json").read_text())
    if manifest["portfolio"] != "v45_oz":
        raise ValueError("Expected heliosli/qcc-circuits-live dataset v24, portfolio v45_oz")
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for item in manifest["files"]:
        name, stored = Path(item["file"]), Path(item["stored_as"])
        if any(p.is_absolute() or ".." in p.parts for p in (name, stored)):
            raise ValueError("Release paths must stay inside their directories")
        src, dst = args.release / stored, args.output / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        opener = lzma.open if src.suffix == ".xz" else open
        with opener(src, "rb") as incoming, dst.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1 << 22)
        with dst.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        size = dst.stat().st_size
        if digest != item["sha256"] or size != item["bytes"]:
            raise ValueError(f"Release hash or size mismatch: {name}")
        rows.append({"file": name.as_posix(), "bytes": size, "sha256": digest})
    print(json.dumps({"portfolio": manifest["portfolio"], "files": rows}, indent=2))


if __name__ == "__main__":
    main()
