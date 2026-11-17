"""Find more Toffoli reductions in DQI 575b043f with grantprater's own tools.

Kaggle CPU only. Reads the 479 MB tape from the attached dataset, lays out the tool
package the way the dataset README says, runs

    python -m qc.passes.measure_out free  575b043f.kmb            (no-Toffoli gates)
    python -m qc.passes.measure_out count 575b043f.kmb --retain --symclean
    python -m qc.passes.measure_out count 575b043f.kmb            (baseline count)

and, if anything is found, writes the rewritten tape and runs the UNCHANGED official
DQI verifier (102,400 shots) on it. Nothing is submitted from here.
"""
from __future__ import annotations

import lzma
import os
import pathlib
import shutil
import subprocess
import sys
import time

def find_ds() -> pathlib.Path:
    hits = sorted(pathlib.Path("/kaggle/input").rglob("vqcc_measure_out.py"))
    if not hits:
        raise SystemExit("dataset tools not found")
    return hits[0].parent


DS = find_ds()
DATA = pathlib.Path("/tmp/dqi")
TOOLS = pathlib.Path("/tmp/tools")
COMP = None
for p in pathlib.Path("/kaggle/input").rglob("verify_submission_dqi.py"):
    if (p.parents[2] / "kickmix").is_dir():
        COMP = p.parents[2]
        break


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def setup_tools() -> None:
    (TOOLS / "qc" / "passes").mkdir(parents=True, exist_ok=True)
    (TOOLS / "qc" / "__init__.py").write_text("")
    (TOOLS / "qc" / "passes" / "__init__.py").write_text("")
    shutil.copyfile(DS / "vqcc_ir.py", TOOLS / "qc" / "ir.py")
    for src, dst in (("vqcc_bitsim.py", "bitsim.py"), ("vqcc_measure_out.py", "passes/measure_out.py")):
        p = DS / src
        if p.exists():
            shutil.copyfile(p, TOOLS / "qc" / dst)
    log("tools laid out:", sorted(str(p.relative_to(TOOLS)) for p in TOOLS.rglob("*.py")))


def run(args: list[str], timeout: int = 5400) -> tuple[int, str]:
    t0 = time.time()
    p = subprocess.run([sys.executable, "-m", *args], cwd=str(TOOLS), capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (("\n[stderr] " + p.stderr[-1500:]) if p.stderr else "")
    log(f"$ {' '.join(args)}  rc={p.returncode}  {time.time()-t0:.0f}s")
    print(out[-4000:], flush=True)
    return p.returncode, out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tape = DATA / "dqi.kmb"
    if not tape.exists():
        log("decompressing 575b043f ...")
        with lzma.open(DS / "dqi_575b043f.kmb.xz", "rb") as f, open(tape, "wb") as g:
            shutil.copyfileobj(f, g, 1 << 24)
    log("tape bytes:", tape.stat().st_size)
    setup_tools()

    # how many pairs would K EXTRA clean wires serve?  (--extra K)
    for extra in ("1", "2", "4", "8", "12", "16"):
        run(["qc.passes.measure_out", "count", str(tape), "--retain", "--extra", extra])
    log("DONE")


if __name__ == "__main__":
    main()
