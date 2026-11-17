"""DQI public-candidate verification sweep (CPU only, unmodified official verifier).

For every .kmb / .kmb.xz in the grantprater DQI dataset, decompress to /kaggle/working
(one at a time), read the header (Q, static Toffoli cap), then run the official
verifiers/dqi/verify_submission_dqi.py at the default salt plus two fresh salts.
"""
import json
import lzma
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

COMP = None
for p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for up in (p.parents[1], p.parents[2], p.parents[3]):
        if (up / "kickmix").is_dir():
            COMP = up
            break
    if COMP:
        break
print(json.dumps({"competition_root": str(COMP)}), flush=True)

DS = pathlib.Path("/kaggle/input/datasets/grantprater/vqcc-dqi-61c8348d-merged-closings")
WORK = pathlib.Path("/kaggle/working")
SALTS = ["<default>", "dqi-push-18x", "dqi-push-18y"]

env = dict(os.environ, PYTHONPATH=f"{COMP/'kickmix'}:{COMP/'verifiers'}")
VER = COMP / "verifiers/dqi/verify_submission_dqi.py"


def header(path):
    """Read the text header line of a .kmb and extract Q / static T if present."""
    with open(path, "rb") as f:
        head = f.read(4096)
    try:
        txt = head.split(b"\x00")[0].decode("utf-8", "replace")
    except Exception:
        txt = ""
    out = {"header_tail": txt[-300:]}
    m = re.search(r"Q=(\d+)", txt)
    if m:
        out["Q_header"] = int(m.group(1))
    m = re.search(r"(?:staticT|T)=(\d+)", txt)
    if m:
        out["static_header"] = int(m.group(1))
    return out


def run(path, salt):
    args = [sys.executable, str(VER), str(path)]
    if salt != "<default>":
        args += ["--salt", salt]
    t0 = time.time()
    r = subprocess.run(args, env=env, cwd=str(COMP / "verifiers"),
                       capture_output=True, text=True)
    tail = r.stdout[-4000:] + "\n--stderr--\n" + r.stderr[-1500:]
    rec = {"salt": salt, "rc": r.returncode, "secs": round(time.time() - t0, 1)}
    try:
        s = r.stdout
        i = s.index("{")
        # last JSON object in stdout
        j = s.rindex("}")
        rec["json"] = json.loads(s[i:j + 1])
    except Exception as e:
        rec["parse_error"] = repr(e)
        rec["stdout_tail"] = tail
    return rec


def main():
    files = sorted([p for p in DS.iterdir() if p.name.endswith(".kmb") or p.name.endswith(".kmb.xz")])
    print(json.dumps({"n_files": len(files), "names": [p.name for p in files]}), flush=True)
    results = {"competition_root": str(COMP), "salts": SALTS, "candidates": []}
    for src in files:
        name = re.sub(r"\.kmb(\.xz)?$", "", src.name)
        dst = WORK / (src.name if src.name.endswith(".kmb") else src.name[:-3])
        t0 = time.time()
        if src.name.endswith(".xz"):
            with lzma.open(src, "rb") as fi, open(dst, "wb") as fo:
                shutil.copyfileobj(fi, fo, 1 << 23)
        else:
            shutil.copyfile(src, dst)
        hdr = header(dst)
        cand = {"name": name, "source": str(src), "bytes": dst.stat().st_size,
                "decompress_secs": round(time.time() - t0, 1), **hdr, "runs": []}
        print(json.dumps({"candidate": cand["name"], "bytes": cand["bytes"], **hdr}), flush=True)
        for salt in SALTS:
            rec = run(dst, salt)
            j = rec.get("json") or {}
            cand["runs"].append(rec)
            print(json.dumps({
                "candidate": cand["name"], "salt": salt, "rc": rec["rc"], "secs": rec["secs"],
                "status": j.get("status"), "score": j.get("score"),
                "toffoli_mean": j.get("toffoli_count"),
                "toffoli_static": j.get("max_toffoli_count"),
                "num_qubits": j.get("num_qubits"),
                "value_errors": j.get("value_errors"), "phase_errors": j.get("phase_errors"),
                "repetition_factor": j.get("repetition_factor"),
            }), flush=True)
        results["candidates"].append(cand)
        dst.unlink()
    (WORK / "dqi_verify_sweep.json").write_text(json.dumps(results, indent=1))
    print("DONE", flush=True)


main()
