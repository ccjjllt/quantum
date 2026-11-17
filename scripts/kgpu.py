#!/usr/bin/env python3
"""Kaggle CPU-only kernel runner (push / status / fetch / logs / new).

Every research line runs its circuits on Kaggle CPU kernels: never locally, never on GPU.

Usage
-----
    python scripts/kgpu.py new    --dir DIR --slug NAME --account zhuating \
                                  [--dataset O/S ...] [--kernel O/S ...] \
                                  [--competition] [--title "..."]
    python scripts/kgpu.py push   --dir DIR --account zhuating [--wait SECONDS]
    python scripts/kgpu.py status --kernel O/S --account zhuating
    python scripts/kgpu.py fetch  --kernel O/S --account zhuating --out DIR
    python scripts/kgpu.py logs   --kernel O/S --account zhuating [-n 80]

`new` writes a CPU-only `kernel-metadata.json` (enable_gpu / enable_tpu false) and a
main.py skeleton if absent. `push` immediately pushes the folder; the folder must
contain `kernel-metadata.json`. Accounts map to token files `~/.kaggle/access_token_<account>`.

Rules encoded here so they cannot be forgotten:
  * enable_gpu = false, enable_tpu = false, machine_shape = ""
  * internet off by default (the competition data + datasets are enough)
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

KAGGLE = os.path.expanduser("~/.local/bin/kaggle")
SKELETON = '''"""Kaggle CPU experiment. CPU only; no GPU, no TPU, no local simulation."""
print("hello from {slug}", flush=True)
'''


def token(account: str) -> str:
    path = pathlib.Path.home() / ".kaggle" / f"access_token_{account}"
    if not path.exists():
        sys.exit(f"missing token file {path}")
    return path.read_text().strip()


def kaggle(args: list[str], account: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["KAGGLE_API_TOKEN"] = token(account)
    env["KAGGLE_CONFIG_DIR"] = str(pathlib.Path.home() / ".kaggle")
    return subprocess.run([KAGGLE, *args], env=env, capture_output=True, text=True, check=False)


def cmd_new(a: argparse.Namespace) -> None:
    d = pathlib.Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": f"{a.account}/{a.slug}",
        # Kaggle resolves a pushed kernel by the slug of its title, so the title must be
        # exactly the slug words or `kernels status <owner/slug>` looks at nothing.
        "title": a.slug.replace("-", " ").title(),
        "code_file": "main.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": bool(a.internet),
        "machine_shape": "",
        "dataset_sources": a.dataset or [],
        "competition_sources": ["google-verifiable-quantum-circuit-compilation"] if a.competition else [],
        "kernel_sources": a.kernel or [],
        "model_sources": [],
    }
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    if not (d / "main.py").exists():
        (d / "main.py").write_text(SKELETON.format(slug=a.slug))
    print(f"wrote {d/'kernel-metadata.json'} (id {meta['id']}, gpu={meta['enable_gpu']})")


def cmd_push(a: argparse.Namespace) -> None:
    d = pathlib.Path(a.dir)
    meta = json.loads((d / "kernel-metadata.json").read_text())
    assert meta.get("enable_gpu") is False and meta.get("enable_tpu") is False, "CPU only"
    print(f"pushing {meta['id']} from {d} ...", flush=True)
    r = kaggle(["kernels", "push", "-p", str(d)], a.account)
    print(r.stdout[-4000:])
    if r.returncode != 0:
        print(r.stderr[-4000:], file=sys.stderr)
        sys.exit(r.returncode)
    if a.wait:
        cmd_status(argparse.Namespace(kernel=meta["id"], account=a.account, wait=a.wait))


def status_once(kernel: str, account: str) -> tuple[str, str]:
    r = kaggle(["kernels", "status", kernel], account)
    out = (r.stdout or "") + (r.stderr or "")
    return out.strip(), out


def cmd_status(a: argparse.Namespace) -> None:
    deadline = time.time() + (a.wait or 0)
    while True:
        out, _ = status_once(a.kernel, a.account)
        print(out.replace("\n", " "), flush=True)
        if a.wait and ("COMPLETE" in out or "ERROR" in out or "CANCEL" in out or "FAILED" in out):
            return
        if time.time() > deadline:
            return
        time.sleep(30)


def cmd_fetch(a: argparse.Namespace) -> None:
    out_dir = pathlib.Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    r = kaggle(["kernels", "output", a.kernel, "-p", str(out_dir)], a.account)
    print(r.stdout[-3000:] or r.stderr[-3000:])
    if r.returncode != 0:
        sys.exit(r.returncode)


def cmd_logs(a: argparse.Namespace) -> None:
    r = kaggle(["kernels", "output", a.kernel, "-p", f"/tmp/kgpu_logs_{int(time.time())}"], a.account)
    print(r.stdout[-2000:] or r.stderr[-2000:])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new")
    n.add_argument("--dir", required=True)
    n.add_argument("--slug", required=True)
    n.add_argument("--account", required=True)
    n.add_argument("--title")
    n.add_argument("--dataset", action="append")
    n.add_argument("--kernel", action="append")
    n.add_argument("--competition", action="store_true")
    n.add_argument("--internet", action="store_true")
    n.set_defaults(func=cmd_new)

    for name, fn in (("push", cmd_push), ("status", cmd_status), ("fetch", cmd_fetch), ("logs", cmd_logs)):
        s = sub.add_parser(name)
        if name == "push":
            s.add_argument("--dir", required=True)
            s.add_argument("--wait", type=int, default=0)
        else:
            s.add_argument("--kernel", required=True)
            if name == "status":
                s.add_argument("--wait", type=int, default=0)
            if name == "fetch":
                s.add_argument("--out", required=True)
            if name == "logs":
                s.add_argument("-n", type=int, default=80)
        s.add_argument("--account", required=True)
        s.set_defaults(func=fn)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
