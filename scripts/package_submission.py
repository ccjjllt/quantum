"""Package candidate files as a submission ZIP; does not verify or submit them."""

import argparse
from pathlib import Path
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory containing invsqrt, dqi, and dfthcsos/.")
    parser.add_argument("--output", type=Path, required=True, help="New ZIP path; existing files are never overwritten.")
    args = parser.parse_args()
    root = args.input_dir.resolve()
    files = []
    for stem in ("invsqrt", "dqi"):
        matches = [root / f"{stem}.{suffix}" for suffix in ("kmb", "kmx") if (root / f"{stem}.{suffix}").is_file()]
        if len(matches) != 1:
            parser.error(f"Expected one {stem}.kmb or {stem}.kmx in {root}.")
        files.extend(matches)
    factorization = root / "dfthcsos" / "submission.npz"
    if not factorization.is_file():
        parser.error(f"Missing {factorization}.")
    angles = sorted(p for p in (root / "dfthcsos").glob("angle_k_*") if p.is_file() and p.suffix in (".kmb", ".kmx"))
    if not angles:
        parser.error("No dfthcsos/angle_k_*.kmb or .kmx files found.")
    files += [factorization, *angles]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(args.output, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for path in files:
                archive.write(path, path.relative_to(root).as_posix())
    except FileExistsError:
        parser.error(f"Output already exists: {args.output}")
    print(f"Packaged {len(files)} files into {args.output.resolve()}")


if __name__ == "__main__":
    main()
