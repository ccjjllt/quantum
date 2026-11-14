import os, pathlib, shutil, subprocess, sys, urllib.request, zipfile

# Rounding-cost calibration for the (8,143,44) DF-THC family, on Kaggle GPU only.
#
# Question the public docs leave open: upstream says rounding "has cost 6-8 mHa on merged
# shapes", but never measures it for this exact (8,143,44) coded-word table. Two numbers
# settle whether B<143 can ever survive 8-bit rounding:
#
#   e2_c(143)  continuous full-U floor of the SAME family (no pruning)
#   e2_q(143)  the same fit after quantize.py --brot 8
#   rounding_cost = e2_q(143) - e2_c(143)
#
# Then, for the pruned shapes:
#   e2_c(129) from shrink.py  = 19.830 mHa (already measured, qcc-chem-b129-full v1)
#   e2_q(129) quantized with the same schedule
#
# If e2_q(129) <= 20 mHa the B=129 lever is ALIVE and worth 15 loaders + the official
# 78,080-shot verifier. Otherwise it is closed by direct measurement, not inference.
URLS = json_urls  # noqa: F821  (filled by the launcher)

W = pathlib.Path("/kaggle/working/roundcal")
shutil.rmtree(W, ignore_errors=True)
W.mkdir(parents=True)
for n, u in URLS.items():
    p = W / (n + ".npz") if n == "seed" else W / (n + ".zip")
    urllib.request.urlretrieve(u, p)
    print("dl", n, p.stat().st_size, flush=True)
for n in ("starter", "pipe"):
    d = W / n
    d.mkdir(exist_ok=True)
    with zipfile.ZipFile(W / (n + ".zip")) as z:
        z.extractall(d)
starter_root = W / "starter" / "starter_kit"
pipe_root = W / "pipe" / "dfthc_refit"
comp = W / "comp"
(comp / "verifiers" / "dfthcsos").mkdir(parents=True)
for f in ("FeMoCo76o113e.fcidump", "FeMoCo76o113e.fixed_shifts.npz"):
    shutil.copyfile(W / "starter" / f, comp / "verifiers" / "dfthcsos" / f)
env = dict(
    os.environ,
    DFTHC_DATA=str(comp),
    DFTHC_STARTER=str(starter_root),
    PYTHONPATH=str(pipe_root) + ":" + str(starter_root),
    OMP_NUM_THREADS="4",
    XLA_PYTHON_CLIENT_PREALLOCATE="false",
)
print("roots", comp, starter_root, pipe_root, flush=True)


def run(tag, cmd):
    print("==", tag, " ".join(map(str, cmd)), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=str(pipe_root / "experiments"),
                       env=env, capture_output=True, text=True)
    print("--", tag, "rc", r.returncode, flush=True)
    print("--", tag, "OUT", r.stdout[-5000:], flush=True)
    if r.returncode:
        print("--", tag, "ERR", r.stderr[-3000:], flush=True)
    return r.returncode


PY = sys.executable
OUT = W / "out"
OUT.mkdir(exist_ok=True)
FREE = "1.0,0.9,0.7,0.5,0.35,0.2,0.1,0.04,0.0"

# 1) continuous full-U refit at B=143 (control: this family's floor, no pruning)
run("shrink143", [PY, "-u", str(pipe_root / "experiments" / "shrink.py"), str(W / "seed.npz"),
                  str(OUT), "143x44", "--merge", "1", "--pre", "0", "--fade", "500", "--fit", "2500",
                  "--final", "8000", "--save", "143x44", "--select", "impact", "--device", "--f32",
                  "--kappa", "5e-5"])

# 2) quantize that continuous fit at 8 bits -> the family's true rounding cost
run("quant143", [PY, "-u", str(pipe_root / "quantize.py"), str(OUT / "8x143x44.npz"),
                 str(OUT / "q143.npz"), "--brot", "8", "--stage-steps", "300",
                 "--final-steps", "600", "--fit-steps", "1200", "--kappa", "5e-5", "--free", FREE])

# 3) pruned shape: continuous 129 (known ~19.83) then the same quantization
run("shrink129", [PY, "-u", str(pipe_root / "experiments" / "shrink.py"), str(W / "seed.npz"),
                  str(OUT), "129x44", "--merge", "1", "--pre", "0", "--fade", "500", "--fit", "2500",
                  "--final", "8000", "--save", "129x44", "--select", "impact", "--device", "--f32",
                  "--kappa", "5e-5"])
run("quant129", [PY, "-u", str(pipe_root / "quantize.py"), str(OUT / "8x129x44.npz"),
                 str(OUT / "q129.npz"), "--brot", "8", "--stage-steps", "300",
                 "--final-steps", "600", "--fit-steps", "1200", "--kappa", "5e-5", "--free", FREE])

print("out files", sorted((p.name, p.stat().st_size) for p in OUT.glob("*.npz")), flush=True)
