"""Null-splice round-trip test on the DQI tape: proves the surgery toolchain before any change.

Self-contained (Kaggle script kernels only carry one file, so the splice helpers are inline).

Reads 575b043f, splices several ranges with their own content, writes, and compares sha256 with
the source. Also reports the condition-stack depth at every candidate cut and the .kmb's named
registers (the authoritative word layout - q//12 is only a guess).

CPU only, static IR only. Deletes the 479 MB tape before exiting so the output fetch is small.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
PACKETS = ("qqq0", "qqq1", "qqq2", "qq0", "qq1", "q0", "b0", "bc", "angles")


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
    """Replace instructions [a, b) of c with the Circuit `new`."""
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


xz = find("dqi_575b043f.kmb.xz")
RAW = WORK / "dqi.kmb"
say("decompress", xz)
with lzma.open(xz, "rb") as fi, open(RAW, "wb") as fo:
    while True:
        b = fi.read(1 << 23)
        if not b:
            break
        fo.write(b)
say("bytes", RAW.stat().st_size)

c = ir.Circuit.read(str(RAW))
SHA = c.sha256()
OUT = {"src_sha256": SHA, "num_ops": c.num_ops, "qubits": c.num_qubits, "bits": c.num_bits,
       "registers": len(c.registers), "tags": int(len(c.tag_ends))}
say("read", c.num_ops, "sha", SHA[:16], "regs", len(c.registers), "tags", len(c.tag_ends))

# The .kmb carries named registers: that is the authoritative word layout.
regs = []
for nm, ids in c.registers:
    ids = ids.astype(np.int64)
    isq = bool(len(ids) and (ids[0] & (1 << 31)))
    v = [int(x) & 0x7FFFFFFF for x in ids]
    regs.append({"name": nm, "n": len(ids), "qubit": isq,
                 "ids": v[:24], "min": (min(v) if v else None), "max": (max(v) if v else None)})
OUT["register_count"] = len(regs)
OUT["register_names_head"] = [r["name"] for r in regs[:14]]
OUT["registers"] = regs[:110]

cuts = {
    "fwd_cluster": (19_508_954, 21_385_877),
    "rev_cluster": (46_230_185, 52_842_219),
    "chien_start": (30_335_416, 30_336_416),
    "mid": (30_000_000, 30_001_000),
}
OUT["cut_depth"] = {nm: {"a": c.depth(a), "b": c.depth(b)} for nm, (a, b) in cuts.items()}

tests = {}
for nm, (a, b) in cuts.items():
    t = time.time()
    out = splice(c, a, b, c.slice(a, b, allow_open=True))
    dst = WORK / f"null_{nm}.kmb"
    sha = out.write(str(dst))
    tests[nm] = {"ops": b - a, "identical": sha == SHA, "seconds": round(time.time() - t, 1)}
    say("null splice", nm, tests[nm])
    dst.unlink()
OUT["null_splice"] = tests
OUT["all_identical"] = all(t["identical"] for t in tests.values())

a = 30_335_416
if c.depth(a) == 0 and c.depth(a + 1) == 0:
    new = ir.Circuit.from_ops([("X", [0], []), ("X", [0], [])], registers=[])
    out2 = splice(c, a, a, new)
    OUT["from_ops_insert"] = {"n_new": new.num_ops, "ops_delta": out2.num_ops - c.num_ops,
                              "touches_q": out2.num_qubits, "max_q": int(out2._max_id(True))}
    out2.write(str(WORK / "ins.kmb"))
    (WORK / "ins.kmb").unlink()
    say("from_ops insert ok", OUT["from_ops_insert"])

with open(WORK / "null_splice.json", "w") as f:
    json.dump(OUT, f, indent=1)
print(json.dumps({k: v for k, v in OUT.items() if k not in ("registers",)}, indent=1))
RAW.unlink()
say("done; tape removed")
