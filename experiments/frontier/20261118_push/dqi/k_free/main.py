"""DQI 575b043f: close the last free-Toffoli mechanisms, and measure the extra-wire curve.

The shipped `free_gates` tests three no-Toffoli classes on UNCONDITIONED gates only (0 found in
317,590 gates):
  void   the product symbol is 0 (a control holds the constant 0) -> the gate does nothing
  zero   the target already holds exactly the product -> the gate clears it -> HMR(t), CZ(a,b) if m
  held   another wire already holds exactly the product -> CX(w, t)
This kernel tests all three on EVERY CCX, conditioned or not, in the shipped 64-bit symbol
algebra (qc.passes.measure_out.step_symbols), keeping a symbol -> wire count so `held` is O(1).

It also records every retention pair (with its exact list of clean wires over the span) so the
"add k wires, buy K retentions" exchange is measured on the FULL population -- the earlier
measurement was on the unconditioned population only.

Read-only. Nothing is written except reports.
"""
from __future__ import annotations

import json
import lzma
import pathlib
import random
import shutil
import sys
import time

import numpy as np

T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)


DS = None
for p in sorted(pathlib.Path("/kaggle/input").rglob("vqcc_measure_out.py")):
    DS = p.parent
    break
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqi")
TMP.mkdir(parents=True, exist_ok=True)
TOOLS = pathlib.Path("/tmp/tools")
(TOOLS / "qc" / "passes").mkdir(parents=True, exist_ok=True)
for p in (TOOLS / "qc" / "__init__.py", TOOLS / "qc" / "passes" / "__init__.py"):
    p.write_text("")
for src, dst in (("vqcc_ir.py", "qc/ir.py"), ("vqcc_measure_out.py", "qc/passes/measure_out.py")):
    shutil.copyfile(DS / src, TOOLS / dst)
sys.path.insert(0, str(TOOLS))
from qc import ir                                        # noqa: E402
from qc.passes import measure_out as MO                   # noqa: E402

TAPE = TMP / "dqi_575b043f.kmb"
if not TAPE.exists():
    with lzma.open(DS / "dqi_575b043f.kmb.xz", "rb") as f, open(TAPE, "wb") as g:
        shutil.copyfileobj(f, g, 1 << 24)
c = ir.Circuit.read(TAPE)
log(f"tape ops {c.num_ops:,} Q {c.num_qubits} staticT {c.toffoli_like():,} sha {c.sha256()[:16]}")

rnd = random.Random(7)
reg = {int(x) for _, ids in c.registers for x in (ids[ids >> 31 == 1] & 0x7FFFFFFF)}
regbits = {int(x) for _, ids in c.registers for x in ids[ids >> 31 == 0]}
nq = c.num_qubits
one = rnd.getrandbits(64)
fp = [rnd.getrandbits(64) if q in reg else 0 for q in range(nq)]
bs = {b: rnd.getrandbits(64) for b in regbits}
loc = {}
for s in fp:
    loc[s] = loc.get(s, 0) + 1

stack, sid, bit_at = [], [], []
last_touch = np.full(nq, -1, np.int64)
res_flag = np.array([q not in reg for q in range(nq)], bool)
res_stack = [() if q not in reg else None for q in range(nq)]
last_bit_write = {}
opened = {}
pairs = []            # (pos, j, a0,b0,t0, a,b,t, ws, depth)
ctr = {}


def bump(k, d):
    ctr[f"{k}@{d}"] = ctr.get(f"{k}@{d}", 0) + 1


chunk, nops = 1 << 20, c.num_ops
for a0 in range(0, nops, chunk):
    for i, nm, qs, tb, cb in c.decode(a0, min(a0 + chunk, nops)):
        if nm == "PUSH_CONDITION":
            stack.append(bs.get(int(cb), 0))
            sid.append(i)
            bit_at.append(int(cb))
            continue
        if nm == "POP_CONDITION":
            if stack:
                stack.pop()
                sid.pop()
                bit_at.pop()
            continue
        base = nm[:-3] if nm.endswith("_IF") else nm
        own = int(cb) if nm.endswith("_IF") else None
        cond = bool(stack) or own is not None
        depth = len(sid)
        sig = (tuple(sid), own)
        if cond:
            ks = stack + ([bs.get(own, 0)] if own is not None else [])
            if all(ks):
                k = ks[0]
                for x in ks[1:]:
                    k = MO._mixw(*sorted((k, x)), 64)
            else:
                k = 0
        else:
            k = None
        if base == "CCX":
            a_, b_, t_ = int(qs[0]), int(qs[1]), int(qs[2])
            bump("ccx", depth)
            if k == 0:
                bump("free_dead_condition", depth)
            elif not fp[a_] or not fp[b_]:
                bump("free_void", depth)
            else:
                prod = MO._mixw(*sorted((fp[a_], fp[b_])), 64)
                sym = prod if k is None else MO._mixw(*sorted((k, prod)), 64)
                if fp[t_] == sym:
                    bump("free_zero", depth)
                elif loc.get(sym, 0) > 0:
                    bump("free_held", depth)
            if fp[a_] and fp[b_] and fp[a_] != fp[b_]:
                key = (sig, tuple(sorted((fp[a_], fp[b_]))))
                g = opened.pop(key, None)
                if g is None:
                    opened[key] = (i, a_, b_, t_)
                else:
                    pos, a0_, b0_, t0_ = g
                    bits = list(bit_at) + ([own] if own is not None else [])
                    if all(last_bit_write.get(b, -1) < pos for b in bits):
                        S = tuple(sid)
                        free = np.flatnonzero((last_touch < pos) & res_flag)
                        ws = [w for w in free.tolist()
                              if w not in (a_, b_, t_)
                              and res_stack[w] is not None and S[:len(res_stack[w])] == res_stack[w]]
                        pairs.append((pos, i, a0_, b0_, t0_, a_, b_, t_, ws, depth))
        QS = [int(q) & 0x7FFFFFFF for q in qs]
        old = [fp[q] for q in QS]
        MO.step_symbols(fp, base, qs, cond, rnd, one, k=k)
        for q, o in zip(QS, old):
            n = fp[q]
            if n != o:
                loc[o] -= 1
                if not loc[o]:
                    loc.pop(o, None)
                loc[n] = loc.get(n, 0) + 1
        if base == "HMR":
            bs[int(tb)] = rnd.getrandbits(64)
        elif base in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            if not cond:
                bs[int(tb)] = (0 if base == "BIT_STORE0" else one if base == "BIT_STORE1"
                               else bs.get(int(tb), 0) ^ one)
            elif base == "BIT_INVERT":
                bs[int(tb)] = bs.get(int(tb), 0) ^ (k or 0)
            else:
                bs[int(tb)] = rnd.getrandbits(64)
        elif tb is not None:
            bs[int(tb)] = rnd.getrandbits(64)
        is_res = base in ("R", "HMR")
        S = tuple(sid)
        for q in QS:
            last_touch[q] = i
            res_flag[q] = is_res
            res_stack[q] = S if is_res else None
        if tb is not None and base in ("HMR", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            last_bit_write[int(tb)] = i
    if (a0 // chunk) % 10 == 0:
        log(f"  scan {a0:,}/{nops:,} pairs {len(pairs):,}")

log("counts:", json.dumps({k: v for k, v in sorted(ctr.items())}, indent=1))

# --------------- extra-wire curve: k virtual clean wires + every wire that is genuinely free
curve = {}
rows = sorted(pairs, key=lambda r: r[1])
for k in (0, 1, 2, 3, 4, 6, 8, 12, 14, 16, 24):
    virt = list(range(nq, nq + k))
    held, served = {}, 0
    for pos, j, a0_, b0_, t0_, a_, b_, t_, ws, depth in rows:
        slot = None
        for x in virt:
            if held.get(x, -1) < pos:
                slot = x
                break
        if slot is None:
            for x in ws:
                if held.get(x, -1) < pos:
                    slot = x
                    break
        if slot is not None:
            held[slot] = j
            served += 1
    curve[k] = served
    log(f"  extra {k:2d}: served {served:,} retentions   (+{k} wires costs {k*825.4:,.0f} T at Q=890)")

byw = {str(n): sum(1 for p in pairs if len(p[8]) == n) for n in range(8)}
SUMMARY = {"counts": {k: v for k, v in sorted(ctr.items())}, "n_pairs": len(pairs),
           "pairs_by_free_wires": byw, "extra_wire_curve": curve}
(WORK / "free_summary.json").write_text(json.dumps(SUMMARY, indent=1))
log("summary:", json.dumps(SUMMARY))
log("DONE")
