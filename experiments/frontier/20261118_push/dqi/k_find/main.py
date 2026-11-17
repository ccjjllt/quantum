"""DQI 575b043f: a finder for product-retention pairs INSIDE condition blocks.

grantprater's shipped `find(retain=True)` pairs only `depth == 0 and own is None` CCX gates, so
every CCX inside a PUSH_CONDITION block is invisible to it.  The shipped prover
(`pair_window.py`) does handle conditioned pairs (both gates in one block instance); it just has
no finder.  This kernel supplies one and then uses the shipped prover per pair and the shipped
`apply(..., allow_open=True)` for the proven ones.

Also counted, and never applied before: (a) plain cancels -- CCX(a,b,t) twice with a, b, t and
every condition bit untouched in between, in one block instance: both gates are deleted, 2 Toffoli
each, no wire needed; (b) void CCX -- a control holds the constant 0, so the gate does nothing.

Read-only until the last step; the last step writes a candidate .kmb that a separate kernel
verifies with the unmodified official verifier.  Nothing is submitted.
"""
from __future__ import annotations

import json
import lzma
import os
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
if DS is None:
    raise SystemExit("tools dataset not found")

WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqi")
TMP.mkdir(parents=True, exist_ok=True)
TOOLS = pathlib.Path("/tmp/tools")

(TOOLS / "qc" / "passes").mkdir(parents=True, exist_ok=True)
(TOOLS / "analysis" / "dqi").mkdir(parents=True, exist_ok=True)
for p in (TOOLS / "qc" / "__init__.py", TOOLS / "qc" / "passes" / "__init__.py",
          TOOLS / "analysis" / "__init__.py", TOOLS / "analysis" / "dqi" / "__init__.py"):
    p.write_text("")
for src, dst in (("vqcc_ir.py", "qc/ir.py"),
                 ("vqcc_bitsim.py", "qc/bitsim.py"),
                 ("vqcc_measure_out.py", "qc/passes/measure_out.py"),
                 ("vqcc_pair_window.py", "analysis/dqi/pair_window.py")):
    shutil.copyfile(DS / src, TOOLS / dst)
sys.path.insert(0, str(TOOLS))
from qc import ir                                        # noqa: E402
from qc.passes import measure_out as MO                   # noqa: E402
from analysis.dqi import pair_window as PW                # noqa: E402

log("tools:", sorted(str(p.relative_to(TOOLS)) for p in TOOLS.rglob("*.py")))


# ---8<--- condfind: a retention-pair finder that accepts conditioned gates
class Finder:
    def __init__(self, c, MO, seed=1, chunk=1 << 20):
        self.c, self.MO, self.seed, self.chunk = c, MO, seed, chunk
        self.rnd = random.Random(seed)
        self.reg = {int(x) for _, ids in c.registers for x in (ids[ids >> 31 == 1] & 0x7FFFFFFF)}
        self.regbits = {int(x) for _, ids in c.registers for x in ids[ids >> 31 == 0]}
        self.nq = c.num_qubits
        self.one = self.rnd.getrandbits(64)

    def run(self, log=print):
        MO = self.MO
        rnd, one, nq = self.rnd, self.one, self.nq
        fp = [rnd.getrandbits(64) if q in self.reg else 0 for q in range(nq)]
        bs = {b: rnd.getrandbits(64) for b in self.regbits}
        stack, sid, bit_at = [], [], []
        last_touch = np.full(nq, -1, np.int64)
        res_flag = np.array([q not in self.reg for q in range(nq)], bool)
        res_stack = [() if q not in self.reg else None for q in range(nq)]
        last_bit_write = {}
        opened, opened_w, cancels, pairs = {}, {}, [], []
        ctr = {"ccx_total": 0, "ccx_keyable": 0, "pairs": 0, "pairs_no_wire": 0,
               "pairs_bit_write_between": 0, "cond_pairs": 0, "cond_pairs_no_wire": 0,
               "ccx_void": 0, "cancels": 0, "cond_cancels": 0}
        nops, chunk = self.c.num_ops, self.chunk
        for a0 in range(0, nops, chunk):
            for i, nm, qs, tb, cb in self.c.decode(a0, min(a0 + chunk, nops)):
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
                sig = (tuple(sid), own)
                if base == "CCX":
                    ctr["ccx_total"] += 1
                    s0, s1, tt = int(qs[0]), int(qs[1]), int(qs[2])
                    if not fp[s0] or not fp[s1]:
                        ctr["ccx_void"] += 1      # a control holds the constant 0: nothing happens
                    if fp[s0] and fp[s1] and fp[s0] != fp[s1]:
                        ctr["ccx_keyable"] += 1
                        bits = list(bit_at) + ([own] if own is not None else [])
                        nobit = all(last_bit_write.get(b, -1) < 0 for b in bits)
                        # ---- a plain cancel: same three wires, same block, nothing touched between
                        wk = (sig, s0, s1, tt)
                        gw = opened_w.pop(wk, None)
                        if (gw is not None and last_touch[s0] == gw and last_touch[s1] == gw
                                and last_touch[tt] == gw
                                and all(last_bit_write.get(b, -1) < gw for b in bits)):
                            cancels.append([gw, i, s0, s1, tt, len(sid)])
                            ctr["cancels"] += 1
                            if cond:
                                ctr["cond_cancels"] += 1
                        else:
                            opened_w[wk] = i
                        # ---- a retention pair: same control functions, one block instance
                        key = (sig, tuple(sorted((fp[s0], fp[s1]))))
                        g = opened.pop(key, None)
                        if g is None:
                            opened[key] = (i, s0, s1, tt)
                        else:
                            pos, a0_, b0_, t0_ = g
                            if any(last_bit_write.get(b, -1) >= pos for b in bits):
                                ctr["pairs_bit_write_between"] += 1
                            else:
                                S = tuple(sid)
                                free = np.flatnonzero((last_touch < pos) & res_flag)
                                ws = [w for w in free.tolist()
                                      if w not in (s0, s1, tt)
                                      and res_stack[w] is not None
                                      and S[:len(res_stack[w])] == res_stack[w]]
                                if ws:
                                    pairs.append((pos, i, a0_, b0_, t0_, s0, s1, tt, len(sid), ws))
                                else:
                                    ctr["pairs_no_wire"] += 1
                                    if cond:
                                        ctr["cond_pairs_no_wire"] += 1
                                if cond:
                                    ctr["cond_pairs"] += 1
                # symbols exactly as qc.passes.measure_out.find(condsym=True)
                if cond:
                    ks = stack + ([bs.get(own, 0)] if own is not None else [])
                    if not all(ks):
                        k = 0
                    else:
                        k = ks[0]
                        for x in ks[1:]:
                            k = MO._mixw(*sorted((k, x)), 64)
                else:
                    k = None
                MO.step_symbols(fp, base, qs, cond, rnd, one, k=k)
                if base == "HMR":
                    bs[int(tb)] = rnd.getrandbits(64)
                elif base in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
                    if not cond:
                        bs[int(tb)] = (0 if base == "BIT_STORE0" else
                                       one if base == "BIT_STORE1" else
                                       bs.get(int(tb), 0) ^ one)
                    elif base == "BIT_INVERT":
                        bs[int(tb)] = bs.get(int(tb), 0) ^ (k or 0)
                    else:
                        bs[int(tb)] = rnd.getrandbits(64)
                elif tb is not None:
                    bs[int(tb)] = rnd.getrandbits(64)
                is_res = base in ("R", "HMR")
                S = tuple(sid)
                for q in qs:
                    q = int(q) & 0x7FFFFFFF
                    last_touch[q] = i
                    res_flag[q] = is_res
                    res_stack[q] = S if is_res else None
                if tb is not None and base in ("HMR", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
                    last_bit_write[int(tb)] = i
            if (a0 // chunk) % 10 == 0:
                log(f"  scan {a0:,}/{nops:,}  pairs {len(pairs):,}  opened {len(opened):,}")
        ctr["pairs"] = len(pairs)
        return pairs, ctr, cancels


def assign(pairs):
    """Greedy joint assignment by span end: one wire serves disjoint spans."""
    rows = sorted(pairs, key=lambda r: r[1])
    held, out = {}, []
    for pos, j, a0_, b0_, t0_, s0, s1, tt, d, ws in rows:
        best = [w for w in ws if held.get(w, -1) < pos]
        if best:
            w = max(best, key=lambda x: held.get(x, -1))
            held[w] = j
            out.append([pos, j, a0_, b0_, t0_, w, s0, s1, tt, d, j - pos])
    return out
# ---8<--- end condfind


# ---------------------------------------------------------------- pool-wire census (840..889)
def pool_census(c, lo=840, hi=890):
    """Per-wire touches / reads / writes / Toffoli writes / resets / windows for the scratch pool."""
    parts = []
    for arr, kind in ((c.qqq0, 0), (c.qqq1, 0), (c.qqq2, 1), (c.qq0, 0), (c.qq1, 1), (c.q0, 1)):
        a = np.asarray(arr)
        for s in range(0, len(a), 1 << 23):
            blk = a[s:s + (1 << 23)]
            k = np.flatnonzero((blk >= lo) & (blk < hi))
            if len(k):
                parts.append(np.stack([blk[k].astype(np.int64), (k + s).astype(np.int64),
                                       np.full(len(k), kind, np.int64)], 1))
    tab = np.concatenate(parts)
    del parts
    base = np.asarray(c.types)[tab[:, 1]] & 0x7F
    tab[(base == 0x30) & (tab[:, 2] == 1), 2] = 0            # CCZ: diagonal
    tab[(base == 0x20) & (tab[:, 2] == 1), 2] = 0            # CZ: diagonal
    tab[np.isin(base, [0x31, 0x32]) & (tab[:, 2] == 1), 2] = 2
    tab[np.isin(base, [0x12, 0x50]) & (tab[:, 2] >= 1), 2] = 3
    o = np.lexsort((tab[:, 1], tab[:, 0]))
    tab = tab[o]
    del o
    out = {}
    for w in range(lo, hi):
        a, b = np.searchsorted(tab[:, 0], [w, w + 1])
        seg = tab[a:b]
        k, pos = seg[:, 2], seg[:, 1]
        rst = pos[k == 3]
        win = int(len(rst) + (1 if len(pos) and (not len(rst) or pos.min() < rst.min()) else 0))
        out[w] = {"touches": int(len(seg)), "reads": int((k == 0).sum()),
                  "writes": int((k >= 1).sum()), "toffoli_writes": int((k == 2).sum()),
                  "resets": int((k == 3).sum()), "windows": win}
    return out


# ---------------------------------------------------------------- run
TAPE = TMP / "dqi_575b043f.kmb"
if not TAPE.exists():
    log("decompressing 575b043f ...")
    with lzma.open(DS / "dqi_575b043f.kmb.xz", "rb") as f, open(TAPE, "wb") as g:
        shutil.copyfileobj(f, g, 1 << 24)
c = ir.Circuit.read(TAPE)
log(f"tape {TAPE.stat().st_size:,} B  sha {c.sha256()[:16]}  ops {c.num_ops:,}  Q {c.num_qubits}  "
    f"bits {c.num_bits}  staticT {c.toffoli_like():,}")

t = np.asarray(c.types)
d_after = np.cumsum((t == 0x81).astype(np.int64) - (t == 0x01).astype(np.int64), dtype=np.int64)
before = np.empty_like(d_after)
before[0] = 0
before[1:] = d_after[:-1]
tof = np.isin(t & 0x7F, [0x30, 0x31, 0x32])
ccx = (t & 0x7F) == 0x31
CSX = {"toffoli_like": int(tof.sum()), "ccx": int(ccx.sum()),
       "toffoli_at_depth0": int((tof & (before == 0)).sum()),
       "toffoli_at_depth_gt0": int((tof & (before > 0)).sum()),
       "ccx_at_depth0": int((ccx & (before == 0)).sum()),
       "ccx_at_depth_gt0": int((ccx & (before > 0)).sum()),
       "max_depth": int(d_after.max()), "push": int((t == 0x81).sum()),
       "if_suffixed_nonpush": int(((t & 0x80) != 0).sum() - (t == 0x81).sum())}
del t, before
log("depth census:", json.dumps(CSX))

PC = pool_census(c)
tot = {k: sum(PC[w][k] for w in PC) for k in ("touches", "reads", "writes", "toffoli_writes",
                                              "resets", "windows")}
log("pool census totals (wires 840-889):", json.dumps(tot))
(WORK / "pool_census.json").write_text(json.dumps({str(k): v for k, v in PC.items()}, indent=0))

log("=== conditioned retain-pair scan ===")
pairs, CCOUNT, cancels = Finder(c, MO).run(log=log)
log("scan counts:", json.dumps(CCOUNT))
byd = {}
for p in pairs:
    byd[p[8]] = byd.get(p[8], 0) + 1
log("pairs with a wire, by condition depth:", json.dumps({str(k): v for k, v in sorted(byd.items())}))

assign = assign(pairs)
log(f"joint assignment: {len(assign)} retention pairs (of {len(pairs)} with a wire)")
assign.sort(key=lambda r: r[10])
(WORK / "assign_cond.json").write_text(json.dumps(assign))
(WORK / "cancels.json").write_text(json.dumps({"cancels": cancels[:20000],
                                                "n": len(cancels)}))

SUMMARY = {"depth_census": CSX, "pool_totals": tot, "scan": CCOUNT, "n_pairs": len(pairs),
           "pairs_by_depth": {str(k): v for k, v in sorted(byd.items())},
           "n_cancels": len(cancels), "assigned": len(assign),
           "assigned_by_depth": {str(d): sum(1 for r in assign if r[9] == d) for d in sorted(byd)},
           "span_median": int(np.median([r[10] for r in assign])) if assign else 0,
           "span_max": int(max(r[10] for r in assign)) if assign else 0}
(WORK / "cond_pairs_summary.json").write_text(json.dumps(SUMMARY, indent=1))
log("summary:", json.dumps(SUMMARY))

# ---------------------------------------------------------------- prove + apply
BUDGET = float(os.environ.get("PROVE_BUDGET_S", "5400"))
SPAN_CAP = int(os.environ.get("SPAN_CAP", "120000"))
cancel_ops = {x for cn in cancels for x in cn[:2]}
take, proved, undecided, failed, wirefail, toolong, iscancel = [], 0, 0, 0, 0, 0, 0
for row in assign:
    pos, j, a0_, b0_, t0_, w, s0, s1, tt, d, span = row
    if time.time() - T0 > BUDGET:
        log(f"prove budget spent after {proved} taken")
        break
    if pos in cancel_ops or j in cancel_ops:
        iscancel += 1
        continue
    if span > SPAN_CAP:
        toolong += 1
        continue
    d0 = int(d_after[pos - 1]) if pos else 0
    if int(d_after[j - 1]) != d0 or int(d_after[pos - 1:j].min()) < d0:
        failed += 1
        continue
    ok, note, stats = PW.prove(c.decode(pos, j + 1), c.num_qubits, 4_000_000, True)
    if ok is None:
        undecided += 1
        continue
    if not ok:
        failed += 1
        continue
    clean, touched = PW.wire_free(c, w, pos, j)
    if not (clean and not touched):
        wirefail += 1
        continue
    (_, n1, q1, _, _), (_, n2, q2, _, _) = c.decode(pos, pos + 1)[0], c.decode(j, j + 1)[0]
    q1 = [int(x) & 0x7FFFFFFF for x in q1]
    q2 = [int(x) & 0x7FFFFFFF for x in q2]
    assert n1 == "CCX" and n2 == "CCX", (n1, n2)
    take.append((pos, j, q1[0], q1[1], q1[2], w, q2[0], q2[1], q2[2]))
    proved += 1
    if proved % 100 == 0:
        log(f"  proved {proved} (failed {failed}, undecided {undecided}, wirefail {wirefail}, "
            f"elapsed {time.time()-T0:.0f}s)")
log(f"PROVE: {proved} proven+clean, {failed} not proven, {undecided} undecided, {wirefail} wire rejected, "
    f"{toolong} over the span cap {SPAN_CAP}, {iscancel} also-plain-cancels")

res = dict(SUMMARY, proved=proved, failed=failed, undecided=undecided, wirefail=wirefail,
           toolong=toolong, iscancel=iscancel, take=take)
(WORK / "prove_result.json").write_text(json.dumps(res, indent=1))

if take:
    log("applying ...")
    new = MO.apply(c, take, allow_open=True)
    OUT = WORK / "dqi_cond.kmb"
    new.write(OUT)
    after = ir.Circuit.read(OUT)
    log(f"OUT {OUT.stat().st_size:,} B sha {after.sha256()[:16]} ops {after.num_ops:,} "
        f"Q {after.num_qubits} bits {after.num_bits} staticT {after.toffoli_like():,} "
        f"(was {c.toffoli_like():,}; cut {c.toffoli_like()-after.toffoli_like()})")
    (WORK / "candidate.json").write_text(json.dumps({
        "file": "dqi_cond.kmb", "sha256": after.sha256(), "qubits": after.num_qubits,
        "static_toffoli": after.toffoli_like(), "parent_static_toffoli": c.toffoli_like(),
        "cuts": c.toffoli_like() - after.toffoli_like(), "num_ops": after.num_ops,
        "num_bits": after.num_bits, "applied_pairs": len(take)}, indent=1))
log("DONE")
