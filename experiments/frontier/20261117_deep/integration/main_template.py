"""Generic integrator: stage a three-leg candidate, run the UNCHANGED official verifiers,
compute the leaderboard GM, and package the submission.zip.

Kaggle CPU only (`enable_gpu=false`, `enable_tpu=false`). No local simulation.

LEGS is a JSON literal substituted by make_main.py:
    {"zipname": {"sha256": ..., "size": ...,
                 "b64": "<zlib+base64>"        # embedded bytes
                 "path": "/kaggle/input/.../x" # explicit file
                 "src": "<human note>"}}
A member without b64/path is located by (size, sha256) anywhere under /kaggle/input
after extracting any .zip / .xz whose size is below a cap.
"""
from __future__ import annotations

import base64
import hashlib
import json
import lzma
import math
import os
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile
import zlib

REFERENCE = {
    "invsqrt": 2076774.233715,
    "dqi": 24439463583672.93,
    "chem": 3355599588.3155375,
}
LEGS = __LEGS__
EXPECTED_GM = __EXPECTED_GM__
LABEL = __LABEL__
MIN_GM = __MIN_GM__
ZIP_CAP = 200 * 1024 * 1024  # do not extract archives larger than this

WORK = pathlib.Path("/kaggle/working")
STAGE = WORK / "stage"
INPUT = pathlib.Path("/kaggle/input")


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_stream(f) -> str:
    h = hashlib.sha256()
    for chunk in iter(lambda: f.read(1 << 24), b""):
        h.update(chunk)
    return h.hexdigest()


def find_competition() -> pathlib.Path:
    for p in INPUT.rglob("verify_submission_invsqrt.py"):
        comp = p.parents[2]
        if (comp / "kickmix").is_dir() and (comp / "verifiers/dfthcsos/verify.py").is_file():
            return comp
    for p in INPUT.rglob("FeMoCo76o113e.fcidump"):
        comp = p.parents[2]
        if (comp / "kickmix").is_dir():
            return comp
    listing = "\n".join(str(p) for p in sorted(INPUT.rglob("*"))[:80])
    raise SystemExit("competition data not found under /kaggle/input\n" + listing)


def unpack_archives() -> None:
    out = WORK / "unz"
    out.mkdir(parents=True, exist_ok=True)
    for p in sorted(INPUT.rglob("*")):
        if not p.is_file() or p.name.startswith("._"):
            continue
        cap = p.stat().st_size
        if cap > ZIP_CAP:
            continue
        d = out / p.parent.name
        if p.suffix == ".zip":
            marker = d / ".done"
            if marker.exists():
                continue
            d.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(p) as zf:
                    zf.extractall(d)
                marker.touch()
                print(f"  extracted {p}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  zip extract failed {p}: {e}", flush=True)
        elif p.suffix == ".xz":
            marker = d / ".done"
            if marker.exists():
                continue
            d.mkdir(parents=True, exist_ok=True)
            try:
                with lzma.open(p, "rb") as f, open(d / p.stem, "wb") as g:
                    shutil.copyfileobj(f, g, 1 << 24)
                marker.touch()
                print(f"  unpacked {p}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  xz failed {p}: {e}", flush=True)


def stage_all(comp: pathlib.Path) -> dict[str, str]:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    wanted = {name: m for leg in LEGS.values() for name, m in leg.items()}
    found: dict[str, str] = {}
    for name, m in wanted.items():
        dst = STAGE / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if "b64" in m:
            raw = zlib.decompress(base64.b64decode(m["b64"]))
            assert hashlib.sha256(raw).hexdigest() == m["sha256"], f"embedded {name} sha mismatch"
            dst.write_bytes(raw)
            found[name] = "embedded"
            print(f"  staged {name} (embedded)", flush=True)
            continue
        if "path" in m:
            src = pathlib.Path(m["path"])
            if not src.exists():
                raise SystemExit(f"{name}: path missing {src}")
            shutil.copyfile(src, dst)
            assert sha256_file(dst) == m["sha256"], f"{name}: sha mismatch at {src}"
            found[name] = str(src)
            print(f"  staged {name} from {src}", flush=True)
            continue
        found[name] = ""  # resolved by scan below
    todo = {n: m for n, m in wanted.items() if found.get(n) == ""}
    if todo:
        sizes = {m["size"] for m in todo.values()}
        by_sha = {m["sha256"]: n for n, m in todo.items()}
        scanned = 0
        for root in (WORK / "unz", INPUT):
            if not todo:
                break
            for p in sorted(root.rglob("*")):
                if not todo or not p.is_file() or p.name.startswith("._"):
                    continue
                try:
                    if p.stat().st_size not in sizes:
                        continue
                except OSError:
                    continue
                scanned += 1
                try:
                    d = sha256_file(p)
                except OSError:
                    continue
                n = by_sha.get(d)
                if n is None or n not in todo:
                    continue
                dst = STAGE / n
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dst)
                found[n] = str(p)
                del todo[n]
                print(f"  staged {n} from {p}", flush=True)
        print(f"  scanned {scanned} size-matching files", flush=True)
    missing = [n for n in wanted if not found.get(n)]
    if missing:
        raise SystemExit(f"missing members: {missing}")
    return found


def run(cmd: list[str]) -> dict:
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "").strip()
    payload = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return {
        "cmd": " ".join(cmd),
        "returncode": p.returncode,
        "seconds": round(time.time() - t0, 1),
        "json": payload,
        "stdout_tail": out[-3000:],
        "stderr_tail": (p.stderr or "")[-3000:],
    }


def main() -> None:
    print(f"candidate {LABEL}", flush=True)
    comp = find_competition()
    print("competition:", comp, flush=True)
    unpack_archives()
    print("staging", flush=True)
    found = stage_all(comp)
    py = sys.executable
    print("running unchanged official verifiers (full default shots)", flush=True)
    verifiers = {
        "chem": run([py, str(comp / "verifiers/dfthcsos/verify.py"), str(STAGE / "dfthcsos")]),
        "dqi": run([py, str(comp / "verifiers/dqi/verify_submission_dqi.py"), str(STAGE / "dqi.kmb")]),
        "invsqrt": run([py, str(comp / "verifiers/invsqrt/verify_submission_invsqrt.py"), str(STAGE / "invsqrt.kmb")]),
    }
    scores, status, gm = {}, {}, None
    for k, v in verifiers.items():
        j = v["json"] or {}
        status[k] = j.get("status")
        if j.get("status") == "PASS" and "score" in j:
            scores[k] = float(j["score"])
        print(f"{k}: {status[k]} score={scores.get(k)} {v['seconds']}s", flush=True)
    if len(scores) == 3:
        ratios = {k: REFERENCE[k] / scores[k] for k in REFERENCE}
        gm = float(math.prod(ratios.values()) ** (1.0 / 3.0))
        print(f"GM {gm:.9f} (expected {EXPECTED_GM:.9f})", flush=True)
    zip_info = None
    if gm is not None and all(s == "PASS" for s in status.values()):
        out_zip = WORK / "submission.zip"
        files = sorted(p for p in STAGE.rglob("*") if p.is_file())
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            for p in files:
                zf.write(p, p.relative_to(STAGE).as_posix())
        zip_info = {
            "path": str(out_zip),
            "bytes": out_zip.stat().st_size,
            "sha256": sha256_file(out_zip),
            "members": {p.relative_to(STAGE).as_posix(): sha256_file(p) for p in files},
        }
        print(f"zip {zip_info['bytes']} bytes sha256 {zip_info['sha256']}", flush=True)
    receipt = {
        "label": LABEL,
        "expected_gm": EXPECTED_GM,
        "gm": gm,
        "scores": scores,
        "ratios": {k: REFERENCE[k] / scores[k] for k in scores} if len(scores) == 3 else None,
        "status": status,
        "verifiers": verifiers,
        "found": found,
        "zip": zip_info,
        "min_gm_to_submit": MIN_GM,
        "decision": "SUBMIT" if (gm is not None and gm > MIN_GM) else "DO_NOT_SUBMIT",
    }
    (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"gm": gm, "status": status, "scores": scores,
                      "zip": (zip_info or {}).get("sha256"),
                      "decision": receipt["decision"]}), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
