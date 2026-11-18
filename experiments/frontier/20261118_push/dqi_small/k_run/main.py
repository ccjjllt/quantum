"""Build the small fast decoder with the competition kickmix (/usr/bin/python3) and verify.

The kernel's default python (3.13) carries a different kickmix than the competition;
the verifier and the reference generator both run under /usr/bin/python3. So the build
script is written out and executed with that interpreter.
"""
import json, os, shutil, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path("/kaggle/working")
BUILD_SRC = HERE / "build_fast.py"
COMP = "/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation"
M, N, D, SHOTS = 63, 6, 4, 25600

print("interpreter", sys.executable, flush=True)
p = subprocess.run(["/usr/bin/python3", "-c", "import kickmix as km; print(km.__file__); print(hasattr(km,'CircuitBuilder'))"],
                   capture_output=True, text=True)
print("competition kickmix:", p.stdout.strip(), p.stderr.strip()[-300:], flush=True)
for it in (None,):
    kmb = WORK / ("fast_%d_%d_%d.kmb" % (M, N, D))
    args = ["/usr/bin/python3", str(BUILD_SRC), str(kmb), "--m", str(M), "--n", str(N), "--degree", str(D)]
    r = subprocess.run(args, capture_output=True, text=True)
    print("build rc", r.returncode, flush=True)
    print(r.stdout[-2000:], flush=True)
    print(r.stderr[-3000:], flush=True)
    if r.returncode != 0:
        continue
    cmd = ["/usr/bin/python3", COMP + "/verifiers/dqi/verify_submission_dqi.py", str(kmb),
           "--m", str(M), "--n", str(N), "--degree", str(D), "--num-shots", str(SHOTS)]
    v = subprocess.run(cmd, capture_output=True, text=True)
    print("verify rc", v.returncode, flush=True)
    print(v.stdout[-4000:], flush=True)
    print(v.stderr[-2000:], flush=True)
