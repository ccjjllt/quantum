"""889Q census: same caliber as 20261110_e9diff/stage_census.py + decoder_struct checklist.

Read-only: dumps 889q kmb to kmx once, runs stage census (INFO_TAG stack,
paid=CCX/CCZ/CSWAP/CCX_CARRY, unread_ccx_before_hmr), then checklist pass:
extract inverse24/multiply-v counts, scan guard blocks, unextract narrow return.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, deque
from pathlib import Path

import kickmix as km

KMB = Path("artifacts/20261110_e9diff_889/dqi_889q_993c7038.kmb")
OUT = Path("artifacts/20261110_e9diff_889/stage_census_889q.json")
TMPDIR = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff")

PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_kmx(kmb: Path, tmpdir: Path) -> Path:
    out = tmpdir / (kmb.stem + ".kmx")
    if out.exists() and out.stat().st_size > 0:
        return out
    c = km.Circuit.from_file(str(kmb))
    c.to_file(str(out), format="kmx")
    return out


def stage_census_kmx(kmx_path: Path, kmb_path: Path) -> dict:
    stage_paid: dict[str, Counter] = {}
    stage_ops: Counter = Counter()
    total_ops = 0
    unread_ccx_before_hmr = 0
    stack: list[str] = []
    window: deque[str] = deque(maxlen=61)
    num_qubits = 0
    try:
        c = km.Circuit.from_file(str(kmb_path))
        num_qubits = int(c.num_qubits)
    except Exception:
        pass
    with kmx_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("INFO_TAG "):
                try:
                    tag = line.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                if line:
                    window.append(line)
                continue
            if not line or line.startswith(SKIP_PREFIX):
                continue
            stage = stack[0] if stack else "header"
            total_ops += 1
            stage_ops[stage] += 1
            op = line.split()[0]
            if op in PAID:
                if stage not in stage_paid:
                    stage_paid[stage] = Counter()
                stage_paid[stage][op] += 1
            if op in ("HMR", "R"):
                p = line.split()
                q = p[1] if len(p) > 1 else ""
                hist = list(window)[-60:]
                for past in reversed(hist):
                    p2 = past.split()
                    if not p2:
                        continue
                    if p2[0] in ("PUSH_CONDITION", "POP_CONDITION"):
                        continue
                    if q not in p2:
                        continue
                    if p2[0] == "CCX" and len(p2) > 3 and p2[3] == q and (" if " not in past):
                        unread_ccx_before_hmr += 1
                    break
            window.append(line)
    stages_out = {}
    total_paid = 0
    for st, cnt in stage_paid.items():
        st_tot = sum(cnt.values())
        total_paid += st_tot
        stages_out[st] = {
            "ops": stage_ops[st],
            "toffoli_like": st_tot,
            "CCX": int(cnt.get("CCX", 0)),
            "CSWAP": int(cnt.get("CSWAP", 0)),
            "CCZ": int(cnt.get("CCZ", 0)),
            "CCX_CARRY": int(cnt.get("CCX_CARRY", 0)),
        }
    return {
        "kmb": str(kmb_path),
        "sha256": sha256_file(kmb_path),
        "num_qubits": num_qubits,
        "total_ops": total_ops,
        "total_toffoli_like": total_paid,
        "unread_ccx_before_hmr": unread_ccx_before_hmr,
        "stages": stages_out,
    }


def main() -> None:
    TMPDIR.mkdir(parents=True, exist_ok=True)
    print("dumping 889q kmx...", flush=True)
    kmx = dump_kmx(KMB, TMPDIR)
    import os
    print(f"kmx size: {os.path.getsize(kmx)}", flush=True)
    print("census 889q...", flush=True)
    res = stage_census_kmx(kmx, KMB)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
