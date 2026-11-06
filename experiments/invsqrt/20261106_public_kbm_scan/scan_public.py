"""Inspect the public invsqrt KMB mirror (anonymous Kaggle dataset API).

Usage:
  .venv/bin/python experiments/invsqrt/20261106_public_kbm_scan/scan_public.py --list
  .venv/bin/python experiments/invsqrt/20261106_public_kbm_scan/scan_public.py --download
  .venv/bin/python experiments/invsqrt/20261106_public_kbm_scan/scan_public.py --inspect

No credentials are used. The list endpoint returns 100 files per page; the mirror
has 52 invsqrt files. Downloads go to artifacts/20261106_public_scan/.
"""
from __future__ import annotations

import argparse
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261106_public_scan"
DATASET = "manwithacat/vqcc-apache-public-circuits"
LIST_URL = f"https://www.kaggle.com/api/v1/datasets/list/{DATASET}?pageSize=100"
FILE_URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET}?fileName="


def fetch_list():
    OUT.mkdir(parents=True, exist_ok=True)
    token = None
    files = []
    while True:
        url = LIST_URL + (f"&pageToken={urllib.parse.quote(token)}" if token else "")
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
        for f in d.get("datasetFiles", []):
            if "invsqrt" in f.get("name", "").lower():
                files.append({"name": f["name"], "bytes": f.get("totalBytes")})
        token = d.get("nextPageToken")
        if not token:
            break
    (OUT / "public_invsqrt_list.json").write_text(json.dumps(files, indent=2) + "\n")
    print(f"invsqrt files: {len(files)}")
    return files


def download(files):
    OUT.mkdir(parents=True, exist_ok=True)
    for f in files:
        name = f["name"]
        target = OUT / Path(name).name
        if target.exists() and target.stat().st_size == f["bytes"]:
            continue
        url = FILE_URL + urllib.parse.quote(name)
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
        target.write_bytes(data)
        print(target.name, len(data))


def inspect():
    rows = []
    for p in sorted(OUT.glob("*.kmb")):
        c = km.Circuit.from_file(p)
        s = c.operation_statistics()
        rows.append({"hash": p.stem, "Q": c.num_qubits, "ops": len(c),
                     "static_paid": s.num_toffoli_like, "static_t": s.num_t_like})
    (OUT / "public_invsqrt_inspect.json").write_text(json.dumps(rows, indent=2) + "\n")
    for r in sorted(rows, key=lambda x: (x["Q"], x["static_paid"])):
        print(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--inspect", action="store_true")
    args = ap.parse_args()
    files = fetch_list() if (args.list or args.download) else []
    if args.download:
        download(files)
    if args.inspect:
        inspect()


if __name__ == "__main__":
    main()
