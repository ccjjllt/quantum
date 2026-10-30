"""Manually run one official verifier, leaving its output and exit status intact."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "invsqrt": "invsqrt.verify_submission_invsqrt",
    "dqi": "dqi.verify_submission_dqi",
    "dfthcsos": "dfthcsos.verify",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Extra arguments after -- go directly to the official verifier. Defaults run full verification.",
    )
    parser.add_argument("task", choices=MODULES)
    parser.add_argument("path", type=Path, help="Circuit file, or dfthcsos submission directory.")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "competition")
    parser.add_argument("--salt", default=None, help="A reproducible local salt; this is not the leaderboard salt.")
    parser.add_argument("--seed", type=int, default=None, help="Explicit simulator seed, overriding salt.")
    argv = sys.argv[1:]
    separator = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:separator])
    extra = argv[separator + 1:]

    verifier_dir = (args.data_dir / "verifiers").resolve()
    if not verifier_dir.is_dir():
        parser.error(f"Official verifiers are missing at {verifier_dir}; download competition data first.")
    command = [sys.executable, "-m", MODULES[args.task], str(args.path.resolve())]
    if args.salt is not None:
        command += ["--salt", args.salt]
    if args.seed is not None:
        command += ["--seed", str(args.seed)]
    command += extra
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(verifier_dir), env.get("PYTHONPATH")]))
    # Use the installed native kickmix package, never the Kaggle Linux .so.
    return subprocess.call(command, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
