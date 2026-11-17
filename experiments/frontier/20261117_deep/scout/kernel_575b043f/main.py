"""Scout check: new DQI byte dqi_575b043f (grantprater dataset v4).

CPU-only Kaggle kernel. Decompresses the candidate from the mounted dataset,
hashes it, and runs the UNCHANGED official DQI verifier at full shots for the
default salt plus two extra salts. No submission, no GPU/TPU, no internet.
"""
import hashlib
import json
import lzma
import os
import pathlib
import subprocess
import sys

WORK = pathlib.Path("/kaggle/working")
STAGE = WORK / "stage"
STAGE.mkdir(parents=True, exist_ok=True)


def find_competition_root() -> pathlib.Path:
    for base in pathlib.Path("/kaggle/input").rglob("verifiers/dqi/verify_submission_dqi.py"):
        return base.parents[2]
    raise SystemExit("competition root not found")


def find_candidate() -> pathlib.Path:
    for p in pathlib.Path("/kaggle/input").rglob("dqi_575b043f.kmb.xz"):
        return p
    raise SystemExit("candidate not found")


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def run_verifier(root: pathlib.Path, circuit: pathlib.Path, salt: str):
    cmd = [sys.executable, str(root / "verifiers/dqi/verify_submission_dqi.py"), str(circuit)]
    if salt:
        cmd += ["--salt", salt]
    env = dict(os.environ)
    # The competition ships kickmix as a bare extension module (kickmix/kickmix.so,
    # no __init__.py). Putting the root on sys.path makes `kickmix` a namespace
    # package that shadows the .so; the .so's own directory must be the path entry.
    env["PYTHONPATH"] = str(root / "kickmix") + os.pathsep + env.get("PYTHONPATH", "")
    env["JAX_PLATFORMS"] = "cpu"
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, env=env)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    payload = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                payload = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return {"salt": salt or "<default>", "rc": proc.returncode,
            "json": payload, "stdout_tail": out[-4000:], "stderr_tail": err[-2000:]}


def main() -> None:
    root = find_competition_root()
    preflight = subprocess.run(
        [sys.executable, "-c", "import kickmix as km; print(km.__file__, hasattr(km, 'Circuit'))"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(root / "kickmix")},
    )
    print(json.dumps({"kickmix_preflight": (preflight.stdout or "").strip(),
                      "preflight_err": (preflight.stderr or "").strip()[-500:]}), flush=True)
    pins = {}
    for rel in ("verifiers/dqi/verify_submission_dqi.py", "kickmix/kickmix.so"):
        p = root / rel
        pins[rel] = sha256(p) if p.exists() else "MISSING"
    print(json.dumps({"competition_root": str(root), "pins": pins}, indent=2), flush=True)

    src = find_candidate()
    dst = STAGE / "dqi_575b043f.kmb"
    with lzma.open(src, "rb") as fin, dst.open("wb") as fout:
        while True:
            chunk = fin.read(1 << 22)
            if not chunk:
                break
            fout.write(chunk)
    cand = {"source": str(src), "bytes": dst.stat().st_size, "sha256": sha256(dst)}
    print(json.dumps({"candidate": cand}, indent=2), flush=True)

    results = [run_verifier(root, dst, s) for s in ("", "scout575a", "scout575b")]
    summary = {"candidate": cand, "pins": pins, "runs": results}
    (WORK / "verify_results.json").write_text(json.dumps(summary, indent=2) + "\n")
    for r in results:
        print(json.dumps({"salt": r["salt"], "rc": r["rc"], "json": r["json"],
                          "stderr_tail": r["stderr_tail"]}), flush=True)


if __name__ == "__main__":
    main()
