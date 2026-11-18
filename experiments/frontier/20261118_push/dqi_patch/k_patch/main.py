"""Patch harness for the DQI tape: splice a replacement into 575b043f and verify it officially.

Self-contained (Kaggle script kernels only carry one file). The replacement instruction list is
the SPEC constant below; empty ops means a null splice (the tape must come out identical and
still PASS, which proves the rewrite is faithful).

Steps: decompress -> read -> splice -> write -> sha -> run the unmodified official verifier once
per salt (102,400 shots each, ~160 s) -> report value/phase errors, mean Toffoli, score -> expected
GM. CPU only; static IR + the official verifier only; no local simulation.
"""
import importlib.util
import json
import lzma
import math
import os
import pathlib
import subprocess
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
COMP = pathlib.Path("/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation")
REF = {"invsqrt": 2076774.233715, "dqi": 24439463583672.93, "chem": 3355599588.3155375}
CUR = {"invsqrt": 74560.90687312803, "dqi": 346409762292.7187, "chem": 294643137.73357135}
T_OLD = 367116.05721679685
VERIFIER_PY = "/usr/bin/python3"  # the interpreter that carries kickmix (as in the receipt)

SPEC = {
    "range": [19508954, 21385877],
    "ops": [],
    "salts": ["", "nullcheck"],
}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def find(pattern):
    for p in pathlib.Path("/kaggle/input").rglob(pattern):
        return p
    raise SystemExit(f"missing {pattern}")


ir = load("vqcc_ir", str(find("vqcc_ir.py")))


def splice(c, a, b, new):
    if not (0 <= a <= b <= c.num_ops):
        raise ValueError(f"bad range [{a}, {b}) of {c.num_ops}")
    d_new = np.cumsum(ir.LPUSH[new.types].astype(np.int64) - ir.LPOP[new.types].astype(np.int64))
    if len(d_new) and d_new.min() < 0:
        raise ValueError("replacement pops an empty condition stack")
    depth_new = int(d_new[-1]) if len(d_new) else 0
    if c.depth(a) + depth_new != c.depth(b):
        raise ValueError(f"depth {c.depth(a)} + {depth_new} != {c.depth(b)}")
    if new._max_id(True) >= c.num_qubits or new._max_id(False) >= c.num_bits:
        raise ValueError("replacement touches qubits/bits outside the tape's width")
    parts = []
    if a:
        parts.append(c.slice(0, a, allow_open=True))
    parts.append(new)
    if b < c.num_ops:
        parts.append(c.slice(b, c.num_ops, allow_open=True))
    out = ir.Circuit.concat(parts)
    out.registers = c.registers
    out._check()
    return out


def gm(costs):
    return math.prod(REF[k] / costs[k] for k in REF) ** (1 / 3)


xz = find("dqi_575b043f.kmb.xz")
RAW = WORK / "dqi.kmb"
say("decompress", xz)
with lzma.open(xz, "rb") as fi, open(RAW, "wb") as fo:
    while True:
        blk = fi.read(1 << 23)
        if not blk:
            break
        fo.write(blk)

c = ir.Circuit.read(str(RAW))
base_sha = c.sha256()
a, b = SPEC["range"]
ops = SPEC.get("ops") or []
say("read", c.num_ops, "ops", c.num_qubits, "q sha", base_sha[:16], "depth", c.depth(a), c.depth(b))

if ops:
    new = ir.Circuit.from_ops([(o[0], o[1], o[2]) for o in ops], registers=[])
    out = splice(c, a, b, new)
    say("spliced", b - a, "->", new.num_ops, "ops; total", out.num_ops)
else:
    out = splice(c, a, b, c.slice(a, b, allow_open=True))
    say("null splice")

PAT = WORK / "dqi_patched.kmb"
sha = out.write(str(PAT))
REPORT = {"src_sha256": base_sha, "patched_sha256": sha, "changed": sha != base_sha,
          "range": [a, b], "ops_in": len(ops), "num_ops": out.num_ops,
          "qubits": out.num_qubits, "bits": out.num_bits, "salts": {}}
say("wrote", PAT.stat().st_size, "bytes sha", sha[:16])
live = c.liveness()
REPORT["distinct_qubits"] = len(live) if live is not None else None
used = np.zeros(c.num_qubits, bool)
for arr, lut in (("qqq0", ir.L3Q), ("qqq1", ir.L3Q), ("qqq2", ir.L3Q),
                 ("qq0", ir.L2Q), ("qq1", ir.L2Q), ("q0", ir.L1Q)):
    a = getattr(c, arr)[lut[c.types]]
    used[a.astype(np.int64)] = True
REPORT["qubits_used"] = int(used.sum())
REPORT["qubit_gaps"] = int(c.num_qubits - used.sum())
say("qubits used", REPORT["qubits_used"], "of", c.num_qubits)

env = dict(os.environ)
for salt in SPEC.get("salts") or [""]:
    cmd = [VERIFIER_PY, str(COMP / "verifiers/dqi/verify_submission_dqi.py"), str(PAT)]
    if salt:
        cmd += ["--salt", salt]
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    key = salt or "(default)"
    entry = {"rc": r.returncode, "seconds": round(time.time() - t, 1)}
    try:
        entry.update(json.loads(r.stdout))
    except Exception:
        entry["stdout_tail"] = r.stdout[-1500:]
        entry["stderr_tail"] = r.stderr[-1500:]
    REPORT["salts"][key] = entry
    say("salt", key, "rc", r.returncode, "value", entry.get("value_errors"),
        "phase", entry.get("phase_errors"), "T", entry.get("toffoli_count"))

ok = all(v.get("rc") == 0 and v.get("value_errors") == 0 and v.get("phase_errors") == 0
         for v in REPORT["salts"].values())
REPORT["all_pass"] = ok
if ok:
    t_new = REPORT["salts"][list(REPORT["salts"])[0]].get("toffoli_count", T_OLD)
    costs = dict(CUR)
    costs["dqi"] = CUR["dqi"] * t_new / T_OLD
    REPORT["mean_toffoli"] = t_new
    REPORT["delta_T"] = t_new - T_OLD
    REPORT["expected_gm"] = gm(costs)
    say("GM", REPORT["expected_gm"], "deltaT", REPORT["delta_T"])

with open(WORK / "patch_report.json", "w") as f:
    json.dump(REPORT, f, indent=1)
print(json.dumps({k: v for k, v in REPORT.items() if k != "salts"}, indent=1))

if ok and sha != base_sha:
  with open(PAT, "rb") as fi, lzma.open(WORK / "dqi_patched.kmb.xz", "wb", preset=6) as fo:
    while True:
        blk = fi.read(1 << 23)
        if not blk:
            break
        fo.write(blk)
  say("wrote dqi_patched.kmb.xz", (WORK / "dqi_patched.kmb.xz").stat().st_size)
RAW.unlink()
PAT.unlink()
say("done")
