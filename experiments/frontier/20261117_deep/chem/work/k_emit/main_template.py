"""Emit cheaper k2/k3 chemistry loaders with the repo's own planner port (inlined), then verify.

Kaggle CPU only. The compiler port (`chem/code2`, 45 files) is carried as a base64 zip in
CODE2_B64 because a Kaggle *script* kernel only uploads main.py.

Steps
  1. unzip the port to /tmp/work, read the shipped submission.npz (angle_words + 15 loaders)
  2. plan k=2 and k=3 against the shipped 8-bit word table (STOP_AT=145 cuts -> 190 products)
  3. emit .kmx, convert to .kmb with kickmix, report per-loader Toffoli
  4. if both are cheaper than shipped (269), assemble dfthcsos = npz + 13 shipped + 2 new
     and run the UNCHANGED official dfthcsos verifier (78,080 shots)
"""
from __future__ import annotations

import base64
import io
import json
import os
import pathlib
import shutil
import sys
import time
import zipfile

CODE2_B64 = "__CODE2_B64__"

WORK = pathlib.Path("/tmp/work")
OUT = pathlib.Path("/tmp/out")
COMP = None
for p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    if (p.parents[1] / "kickmix").is_dir():
        COMP = p.parents[1]
        break


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def unzip_port() -> pathlib.Path:
    WORK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(CODE2_B64))) as z:
        z.extractall(WORK)
    p = WORK / "code2"
    sys.path.insert(0, str(p))
    sys.path.insert(0, str(p / "compiler"))
    log("port at", p, "files", len(list(p.rglob('*.py'))))
    return p


def shipped_zip() -> pathlib.Path:
    for z in sorted(pathlib.Path("/kaggle/input").rglob("submission.zip")):
        if "v27" in str(z) or "chemistry" in str(z) or "4-022" in str(z):
            return z
    for z in sorted(pathlib.Path("/kaggle/input").rglob("submission.zip")):
        return z
    raise SystemExit("no submission.zip")


def main() -> None:
    log("competition:", COMP)
    port = unzip_port()
    os.environ["LS_SECONDS"] = "120"
    import compile_basis as CB
    from planner import complete_words, cross_tensor
    from emit_from_basis import build
    import numpy as np

    CB.STOP_AT = 145
    CB.LS_SECONDS = 120

    zpath = shipped_zip()
    log("shipped zip:", zpath)
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(OUT / "src")
    src = OUT / "src"
    npz = next(src.rglob("submission.npz"))
    z = np.load(npz, allow_pickle=False)
    W = np.asarray(z["angle_words"], np.uint8)
    log("angle_words", W.shape, "npz", npz)
    Wc = complete_words(W)

    results = {}
    for k in (2, 3):
        t0 = time.time()
        target = cross_tensor(Wc, k)
        best = CB.plan_one(target, seeds=(7, 8, 9), trials=60, time_limit=900, verbose=True)
        if best is None:
            log(f"k{k}: planner found nothing")
            results[k] = None
            continue
        state = {"k": k, "parts": CB.PARTS5, "cuts": best["cuts"], "rows": best["rows"],
                 "F": best["F"], "sum_cuts": int(best["sum_c"])}
        sp = OUT / f"plan_k{k}.json"
        sp.write_text(json.dumps(state))
        rep, s = build(k, sp, OUT / f"k{k}")
        log(f"k{k}: cuts={best['sum_c']} products={rep['product_count']} toffoli={rep['toffoli_count']} "
            f"qubits={rep['num_qubits']} [{time.time()-t0:.0f}s]")
        results[k] = rep

    # convert kmx -> kmb
    import kickmix as km
    conv = {}
    for k in (2, 3):
        src_kmx = OUT / f"k{k}" / f"angle_k_{k}.kmx"
        if not src_kmx.exists():
            continue
        dst = OUT / f"k{k}" / f"angle_k_{k}.kmb"
        km.Circuit.from_file(str(src_kmx), format="kmx").to_file(str(dst), format="kmb")
        conv[k] = dst
        log(f"k{k} kmb {dst.stat().st_size} B")

    shipped_angles = {p.name: p for p in src.rglob("angle_k_*.kmb")}
    log("shipped loaders found:", len(shipped_angles))
    if len(conv) == 2 and all(results[k] and results[k]["toffoli_count"] < 269 for k in (2, 3)):
        run = OUT / "run"
        (run / "dfthcsos").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(npz, run / "dfthcsos" / "submission.npz")
        for name, p in shipped_angles.items():
            shutil.copyfile(p, run / "dfthcsos" / name)
        for k in (2, 3):
            shutil.copyfile(conv[k], run / "dfthcsos" / f"angle_k_{k}.kmb")
        log("assembled", len(list((run / 'dfthcsos').iterdir())), "dfthcsos members")
        import subprocess
        env = dict(os.environ, JAX_PLATFORMS="cpu", OMP_NUM_THREADS="4",
                   PYTHONPATH=f"{COMP / 'kickmix'}:{COMP / 'verifiers'}")
        r = subprocess.run([sys.executable, str(COMP / "verifiers/dfthcsos/verify.py"), str(run / "dfthcsos")],
                           capture_output=True, text=True, env=env, cwd=str(COMP / "verifiers"))
        log("official chemistry verifier rc =", r.returncode)
        print(r.stdout[-4000:], flush=True)
        print(r.stderr[-1500:], flush=True)
    else:
        log("no cheaper pair -> nothing to verify")
    print("SUMMARY " + json.dumps({str(k): (None if v is None else
          {"products": v["product_count"], "toffoli": v["toffoli_count"], "qubits": v["num_qubits"]})
          for k, v in results.items()}), flush=True)
    log("DONE")


if __name__ == "__main__":
    main()
