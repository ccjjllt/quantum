"""Assemble and grade the 2026-11-17 28.15083 candidate on a Kaggle CPU kernel.

Candidate (all public, credited by the publishers):
  invsqrt.kmb          maoxin123/atakan 0af21cb8 44Q, cost 74,797.37 (embedded below, zlib/base64)
  dqi.kmb              61c8348d 890Q (grantprater merged-closings: 66b4f18b+d54d3387 parents),
                       clean-draw cost 346,413,579,540.50 (verified PASS 0/0 salt-8ad413d9;
                       default-salt draw loses one shot: 348,004,440,260.46, still PASS)
  dfthcsos/*           a73b25d2 chem-shape move (maoxin123 v27 02:04 kernel, sibling-identical
                       loaders 02:16 kernel): submission.npz + 15 SMALL angle loaders
                       (T=14706, depth 177, cost 294,643,137.73; 3/3 salt-invariant PASS).
                       The SMALL loader family MUST pair with this npz, not the standard
                       415169...362314 set.

Every member is located by SHA-256 under /kaggle/input, its hash is asserted, and the
UNCHANGED official competition verifiers are run with their default salts and shot counts:

    verifiers/dfthcsos/verify.py <dir>              78,080 shots
    verifiers/invsqrt/verify_submission_invsqrt.py  200,540,928 shots
    verifiers/dqi/verify_submission_dqi.py          102,400 shots

The kernel writes /kaggle/working/submission.zip plus receipt.json and verifier logs.
Kaggle CPU only; no GPU, no TPU, no local simulation.
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
from datetime import datetime, timezone

# --------------------------------------------------------------------------------------
# Candidate manifest. Keep this in sync with members.json.
# --------------------------------------------------------------------------------------
MEMBERS = {
    "invsqrt.kmb": {
        "sha256": "0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b",
        "size": 180382,
        "source": "embedded zlib/base64, maoxin123/atakan 0af21cb8",
    },
    "dqi.kmb": {
        "sha256": "61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de",
        "size": 479128630,
        "source": "grantprater/vqcc-dqi-61c8348d-merged-closings dqi.kmb (grantprater 23:45 kernel byte-identical; parents 66b4f18b+d54d3387 shipped)",
    },
    "dfthcsos/submission.npz": {
        "sha256": "a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3",
        "size": 1847552,
        "source": "maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier submission.zip (sibling-identical to qcc-28-14-4-022-toffoli-chemistry-loaders 02:16 kernel; T14706 chem-shape move)",
    },
}
for _i, _h in enumerate([
    "ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538",
    "8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd",
    "e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f",
    "b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e",
    "ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d",
    "21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856",
    "1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1",
    "8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0",
    "0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563",
    "b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71",
    "41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6",
    "76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca",
    "e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f",
    "9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8",
    "fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f",
]):
    MEMBERS[f"dfthcsos/angle_k_{_i}.kmb"] = {
        "sha256": _h,
        "size": [
            180436, 151084, 135545, 134697, 130825, 130454, 129631, 130875,
            130222, 130054, 131074, 130646, 129613, 130455, 130774,
        ][_i],
        "source": "maoxin123/qcc-v27 sibling submission.zip angle_k_%d.kmb (SMALL family; must pair with a73b25d2)" % _i,
    }

INV_B64 = "__INV_B64__"

EXPECTED = {
    "invsqrt": 74797.37,
    "dqi": 346413579540.50,
    "chem": 294643137.73,
    "gm": 28.15082863,
    "dqi_draw": 348004440260.46,
    "gm_draw": 28.10786705,
}
REFERENCE = {
    "invsqrt": 2076774.233715,
    "dqi": 24439463583672.93,
    "chem": 3355599588.3155375,
}
CURRENT_PUBLIC = 28.09486
# 2026-11-16 final correction: the 28.09486 plateau has grown to 185 teams
# (ranks 93-277); the silver cutoff rank 156 is inside it. Exactly one team at
# 28.09487 (rank 92) sits above the cutoff, but a new tie entry is ordered last
# and would worsen our position. The bdae chemistry's measured GM is 28.0948754,
# which is still below the only worth-submitting gate: >= 28.09490.
TIE_PLATEAU_GM = 28.09486
NEXT_PUBLIC_GM = 28.09498
MIN_GM = 28.09490
OFFICIAL_VERIFIERS = {
    "verifiers/dfthcsos/verify.py": "0775be7a528922367caebe9e4d051d6199811f1aefeaa4b793eaaa4621b8ec9d",
    "verifiers/dqi/verify_submission_dqi.py": "f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65",
    "verifiers/invsqrt/verify_submission_invsqrt.py": "ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a",
}

INPUT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
STAGE = WORK / "stage"
LOGS = WORK / "logs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: pathlib.Path, buf: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(buf), b""):
            h.update(block)
    return h.hexdigest()


def sha256_stream(f, buf: int = 1 << 24) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: f.read(buf), b""):
        h.update(block)
    return h.hexdigest()


def parse_official_json(stdout: str):
    start, end = stdout.find("{"), stdout.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(stdout[start:end + 1])
    except json.JSONDecodeError:
        return None


def find_competition_root() -> pathlib.Path:
    for p in INPUT.rglob("verify_submission_invsqrt.py"):
        comp = p.parents[2]
        if (comp / "kickmix").is_dir() and (comp / "verifiers/dfthcsos/verify.py").is_file():
            return comp
    for p in INPUT.rglob("FeMoCo76o113e.fcidump"):
        comp = p.parents[2]
        if (comp / "kickmix").is_dir():
            return comp
    raise RuntimeError("official competition data (kickmix + verifiers) not found under /kaggle/input")


def stage_embedded_invsqrt() -> str:
    raw = zlib.decompress(base64.b64decode(INV_B64))
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == MEMBERS["invsqrt.kmb"]["sha256"], digest
    assert len(raw) == MEMBERS["invsqrt.kmb"]["size"], len(raw)
    (STAGE / "invsqrt.kmb").write_bytes(raw)
    return "embedded zlib/base64"


def stage_members() -> dict[str, str]:
    STAGE.mkdir(parents=True, exist_ok=True)
    found: dict[str, str] = {}
    found["invsqrt.kmb"] = stage_embedded_invsqrt()

    by_sha = {m["sha256"]: name for name, m in MEMBERS.items()}
    remaining_sizes = {m["size"] for name, m in MEMBERS.items() if name not in found}
    files = sorted(p for p in INPUT.rglob("*") if p.is_file() and not p.name.startswith("._"))

    # Diagnostic trail: `kaggle kernels logs` is retrievable even on failure,
    # so record every size-matching candidate and every unreadable file.
    size_hits: list[str] = []
    unreadable: list[str] = []
    for p in files:
        if len(found) == len(MEMBERS):
            break
        suffix = p.suffix.lower()
        try:
            if suffix in (".kmb", ".npz"):
                try:
                    size = p.stat().st_size
                except OSError as e:
                    unreadable.append(f"{p}: stat failed: {e}")
                    continue
                if size not in remaining_sizes:
                    continue
                digest = None
                last_err = ""
                for _ in range(4):
                    try:
                        digest = sha256_file(p)
                        break
                    except OSError as e:
                        last_err = str(e)
                        time.sleep(10)
                if digest is None:
                    unreadable.append(f"{p}: hash failed 4x, last: {last_err}")
                    continue
                name = by_sha.get(digest)
                size_hits.append(f"{size} {digest[:16]} -> {name}  {p}")
                if name is None or name in found:
                    continue
                dst = STAGE / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dst)
                found[name] = str(p)
            elif suffix == ".xz":
                if "dqi.kmb" in found:
                    continue
                with lzma.open(p, "rb") as f:
                    digest = sha256_stream(f)
                if digest != MEMBERS["dqi.kmb"]["sha256"]:
                    continue
                dst = STAGE / "dqi.kmb"
                with lzma.open(p, "rb") as f, open(dst, "wb") as g:
                    shutil.copyfileobj(f, g, 1 << 24)
                found["dqi.kmb"] = str(p)
            elif suffix == ".zip":
                try:
                    z = zipfile.ZipFile(p)
                except zipfile.BadZipFile:
                    continue
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    base = info.filename.rsplit("/", 1)[-1]
                    if base.startswith("._") or info.file_size not in remaining_sizes:
                        continue
                    with z.open(info) as f:
                        digest = sha256_stream(f)
                    name = by_sha.get(digest)
                    if name is None or name in found:
                        continue
                    dst = STAGE / name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as f, open(dst, "wb") as g:
                        shutil.copyfileobj(f, g, 1 << 24)
                    found[name] = f"{p}:{info.filename}"
        except (OSError, lzma.LZMAError):
            continue

    missing = sorted(set(MEMBERS) - set(found))
    print(f"\nSIZE-HIT CANDIDATES ({len(size_hits)}):", flush=True)
    for h in size_hits:
        print(f"  {h}", flush=True)
    if unreadable:
        print(f"\nUNREADABLE ({len(unreadable)}):", flush=True)
        for u in unreadable:
            print(f"  {u}", flush=True)
    assert not missing, f"not found under /kaggle/input: {missing}"
    for name, meta in MEMBERS.items():
        path = STAGE / name
        assert path.stat().st_size == meta["size"], (name, path.stat().st_size, meta["size"])
        assert sha256_file(path) == meta["sha256"], name
    return found


def run_official(task: str, cmd: list[str], cwd: pathlib.Path, timeout: int) -> dict:
    env = dict(
        os.environ,
        JAX_PLATFORMS="cpu",
        OMP_NUM_THREADS="4",
        PYTHONPATH=f"{COMP / 'kickmix'}:{COMP / 'verifiers'}",
    )
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=str(cwd))
    seconds = round(time.time() - t0, 2)
    (LOGS / f"{task}.stdout.txt").write_text(proc.stdout)
    (LOGS / f"{task}.stderr.txt").write_text(proc.stderr)
    parsed = parse_official_json(proc.stdout)
    if parsed is not None:
        (LOGS / f"{task}.json").write_text(json.dumps(parsed, indent=2) + "\n")
    print(f"\n===== {task.upper()} rc={proc.returncode} seconds={seconds} =====", flush=True)
    print(proc.stdout, flush=True)
    if proc.stderr:
        print("----- stderr -----", flush=True)
        print(proc.stderr, flush=True)
    return {
        "command": cmd,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "seconds": seconds,
        "json": parsed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
    }


def package_zip() -> dict:
    out = WORK / "submission.zip"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for name in sorted(MEMBERS):
            z.write(STAGE / name, name)
    with zipfile.ZipFile(out) as z:
        names = sorted(z.namelist())
        assert names == sorted(MEMBERS), names
        for name, meta in MEMBERS.items():
            with z.open(name) as f:
                assert sha256_stream(f) == meta["sha256"], name
    return {"path": str(out), "size": out.stat().st_size, "sha256": sha256_file(out), "members": len(names)}


def main() -> None:
    started = utc_now()
    print(f"START {started}", flush=True)
    WORK.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(STAGE, ignore_errors=True)

    global COMP
    COMP = find_competition_root()
    print(f"competition root: {COMP}", flush=True)

    official = {}
    for rel, want in OFFICIAL_VERIFIERS.items():
        got = sha256_file(COMP / rel)
        official[rel] = got
        assert got == want, f"official verifier changed: {rel}: {got} != {want}"
    kickmix_sha = sha256_file(COMP / "kickmix/kickmix.so")
    print(f"official verifier hashes OK; kickmix.so {kickmix_sha}", flush=True)

    found = stage_members()
    print(f"\nSTAGED {len(found)}/{len(MEMBERS)} members", flush=True)
    for name in sorted(MEMBERS):
        meta = MEMBERS[name]
        print(f"{name:32s} {meta['size']:>12d} {meta['sha256'][:16]} <- {found[name]}", flush=True)

    py = sys.executable
    verifiers = {}
    verifiers["chem"] = run_official(
        "chem",
        [py, str(COMP / "verifiers/dfthcsos/verify.py"), str(STAGE / "dfthcsos")],
        COMP / "verifiers/dfthcsos",
        21600,
    )
    verifiers["dqi"] = run_official(
        "dqi",
        [py, str(COMP / "verifiers/dqi/verify_submission_dqi.py"), str(STAGE / "dqi.kmb")],
        COMP / "verifiers/dqi",
        36000,
    )
    verifiers["invsqrt"] = run_official(
        "invsqrt",
        [py, str(COMP / "verifiers/invsqrt/verify_submission_invsqrt.py"), str(STAGE / "invsqrt.kmb")],
        COMP / "verifiers/invsqrt",
        36000,
    )

    all_pass = all(
        v["returncode"] == 0 and isinstance(v["json"], dict) and v["json"].get("status") == "PASS"
        for v in verifiers.values()
    )
    scores = None
    gm = None
    ratios = None
    if all_pass:
        scores = {task: float(v["json"]["score"]) for task, v in verifiers.items()}
        ratios = {task: REFERENCE[task] / scores[task] for task in REFERENCE}
        gm = float(math.prod(ratios.values()) ** (1.0 / 3.0))

        q = verifiers["invsqrt"]["json"].get("num_qubits")
        dq = verifiers["dqi"]["json"].get("num_qubits")
        cq = verifiers["chem"]["json"].get("num_qubits")
        assert q == 44, q
        assert dq == 890, dq
        assert cq == 427, cq

        print("\n===== OFFICIAL SCORES =====", flush=True)
        for task in ("invsqrt", "dqi", "chem"):
            r = verifiers[task]["json"]
            print(f"{task:8s} score={r['score']!r} Q={r.get('num_qubits')} "
                  f"T={r.get('toffoli_count')} lambda_eff={r.get('lambda_eff')} "
                  f"worst/tol={r.get('worst_error_over_tolerance')} "
                  f"errors={r.get('value_errors')}/{r.get('phase_errors')}", flush=True)
        print(f"GM {gm:.9f}  expected {EXPECTED['gm']:.9f}  current public {CURRENT_PUBLIC:.5f}  "
              f"tie plateau {TIE_PLATEAU_GM:.5f}  next public {NEXT_PUBLIC_GM:.5f}  "
              f"min {MIN_GM:.5f}", flush=True)

    if not all_pass:
        decision = "DO_NOT_SUBMIT"
    elif gm is not None and gm >= MIN_GM:
        decision = "SUBMIT"
    elif gm is not None and gm >= 28.0930:
        decision = "HOLD_TIE"
    else:
        decision = "DO_NOT_SUBMIT"
    zip_info = package_zip() if all_pass else None
    if zip_info:
        print(f"ZIP {zip_info['path']} {zip_info['size']} {zip_info['sha256']} members={zip_info['members']}", flush=True)

    receipt = {
        "generated_utc": utc_now(),
        "started_utc": started,
        "candidate": "0af-61c8348d-a73b25d2-2815083",
        "description": (
            "invsqrt 0af21cb8 (44Q) + DQI 61c8348d (890Q, grantprater merged-closings) + "
            "chemistry a73b25d2 chem-shape move with 15 SMALL loaders (427Q, T=14706, "
            "depth 177, cost 294643137.73); official default salts"
        ),
        "decision": decision,
        "gm": gm,
        "expected_gm": EXPECTED["gm"],
        "current_public": CURRENT_PUBLIC,
        "tie_plateau_gm": TIE_PLATEAU_GM,
        "next_public_gm": NEXT_PUBLIC_GM,
        "min_gm": MIN_GM,
        "policy": "Submit only when all official verifiers PASS and GM >= 28.09490. "
                  "28.09486 is a 185-team plateau (ranks 93-277) and is held; "
                  "28.09487 is also below the gate. Do not replace our existing tie entry "
                  "with a later submission that would worsen the in-tie rank.",
        "scores": scores,
        "ratios": ratios,
        "members": {
            name: {
                **meta,
                "found_at": found.get(name),
                "staged_sha256": sha256_file(STAGE / name) if (STAGE / name).exists() else None,
            }
            for name, meta in MEMBERS.items()
        },
        "official_verifiers": official,
        "kickmix_sha256": kickmix_sha,
        "verifiers": verifiers,
        "zip": zip_info,
        "apache_2_0_attribution": (
            "Submission description and notes credit Syed Asad Ali (Apache-2.0 invsqrt/DQI generator "
            "lineage), Ali Haydar Ozdag (64-row table), Ertugrul Ozer, Asterios Panoras, James Barlow, "
            "Leo Tang, Hayato Hikawa (C8 milestone), maoxin, grantprater, boristown (merge patches), "
            "ratnachand (verified public floor), Lera/marculera and the "
            "c44 chemistry lineage, and Google Quantum AI / Qualtran for kickmix and the verifiers."
        ),
    }
    (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (WORK / "RUN_SUMMARY.json").write_text(json.dumps({
        "decision": decision,
        "gm": gm,
        "expected_gm": EXPECTED["gm"],
        "scores": scores,
        "zip": zip_info,
        "verifier_status": {k: (v["json"] or {}).get("status") for k, v in verifiers.items()},
        "verifier_seconds": {k: v["seconds"] for k, v in verifiers.items()},
    }, indent=2) + "\n")
    # Keep the Kaggle output small: the receipt and logs are the evidence, not the 487 MB stage.
    shutil.rmtree(STAGE, ignore_errors=True)
    print(f"\nDECISION {decision}", flush=True)
    if decision == "HOLD_TIE":
        print(f"HELD: GM {gm:.9f} is inside the 28.09486 plateau; do not spend a submission slot.", flush=True)
    print("DONE", flush=True)
    if decision == "DO_NOT_SUBMIT":
        sys.exit(2)


if __name__ == "__main__":
    main()
