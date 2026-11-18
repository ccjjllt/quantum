"""DQI BM feasibility: static attribution of the EEA-forward Toffoli budget per round.

CPU-only Kaggle kernel.  **No simulation.**  Reads the instruction stream of tape
575b043f and answers three questions that decide whether a <=890-qubit decoder can
reach T <= 264,691:

  Q1  how many 12-bit words does the EEA working set actually occupy at each round
      (i.e. is the "1nb packing" real, and is sigma/omega materialised inside the
      syndrome array)?
  Q2  is the per-round Toffoli cost  T(w) = a + b*w  with b ~ 43 (control is
      per-ROUND) or b ~ 99 (control is per-POSITION)?
  Q3  same decomposition for the reverse pass, as a cross-check.

Method: the tape runs a +1 ladder of division rounds with window w = 4..34 (measured
by the dqi_algo line).  We anchor each round on its 42-CCX field-multiply blocks,
cut round boundaries at the first multiply of the next round, and regress the
Toffoli count of each round on its window size.  The intercept is the per-round
fixed cost; the slope is the marginal cost of one more multiply position.

Output: rounds.json  (also printed).
"""
import hashlib
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
OUT = {}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def find_inputs():
    xz = irp = None
    for p in pathlib.Path("/kaggle/input").rglob("dqi_575b043f.kmb.xz"):
        xz = p
        break
    for p in pathlib.Path("/kaggle/input").rglob("vqcc_ir.py"):
        irp = p
        break
    if not (xz and irp):
        raise SystemExit("inputs not found")
    return xz, irp


if pathlib.Path("/kaggle/input").is_dir():
    XZ, IRPY = find_inputs()
else:
    XZ = pathlib.Path("/private/tmp/dqid/dqi_575b043f.kmb.xz")
    IRPY = pathlib.Path("artifacts/20261118_push_dqi/ds/vqcc_ir.py").resolve()
WORK.mkdir(parents=True, exist_ok=True)
raw = WORK / "dqi_575b043f.kmb"
if not raw.exists():
    say("decompress", XZ)
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)
OUT["kmb_sha256"] = sha256(raw)
OUT["kmb_bytes"] = raw.stat().st_size
OUT["ir_py_sha256"] = sha256(IRPY)

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
t = c.types
N = c.num_ops
OUT["num_ops"] = N
OUT["num_qubits"] = c.num_qubits
OUT["static_toffoli"] = int(c.toffoli_like())
say("ops", N, "Q", c.num_qubits, "T", OUT["static_toffoli"])

cfun3 = np.zeros(N + 1, dtype=np.int32); cfun3[1:] = np.cumsum(ir.L3Q[t])
cfuncc = np.zeros(N + 1, dtype=np.int32); cfuncc[1:] = np.cumsum(ir.LCOND[t])

tof = np.flatnonzero(ir.LTOF[t])
is_ccx_op = (t[tof] & 0x7F) == 0x31
ccxp = tof[is_ccx_op]
q3 = cfun3[ccxp + 1] - 1
CRA = c.qqq0[q3].astype(np.int64) // 12
CRB = c.qqq1[q3].astype(np.int64) // 12
CRT = c.qqq2[q3].astype(np.int64) // 12
del q3
OUT["ccx"] = int(len(ccxp))

# ------------------------------------------------ Chien anchor -> regions A|B|C
pos = np.flatnonzero(t == 0xC1)
cond = c.bc[cfuncc[pos + 1] - 1].astype(np.int64)
cn = cond.tolist()
found = []
i = 0
while i + 11 < len(cn):
    c0 = cn[i]
    if (c0 % 12 == 0 and cn[i + 11] == c0 + 11
            and all(cn[i + k] == c0 + k for k in range(12))):
        found.append(int(pos[i]))
        i += 12
    else:
        i += 1
A = min(found)
B = max(found)
OUT["region_A_end"] = A
OUT["region_B_end"] = B
OUT["chien_positions"] = len(found)
reg_of = np.zeros(N, dtype=np.int8)
reg_of[A:B + 1] = 1
reg_of[B + 1:] = 2
say("regions", A, B, len(found))


# ---------------------------------------------------------------- block census
def blocks_in(reg: int, size_min: int = 12, gapmax: int = 80):
    """maximal same-triple CCX runs of size >= size_min inside region `reg`."""
    sel = np.flatnonzero(reg_of[ccxp] == reg)
    P, a, b, d = ccxp[sel], CRA[sel], CRB[sel], CRT[sel]
    out_p, out_size = [], []
    i = 0
    while i < len(P):
        j = i
        while (j + 1 < len(P) and P[j + 1] - P[j] <= gapmax
               and a[j + 1] == a[j] and b[j + 1] == b[j] and d[j + 1] == d[j]):
            j += 1
        if j - i + 1 >= size_min:
            out_p.append(int(P[i]))
            out_size.append(int(j - i + 1))
        i = j + 1
    return np.array(out_p, dtype=np.int64), np.array(out_size, dtype=np.int64)


ccx_block_start = {}
ccx_block_size = {}
for reg in (0, 2):
    # every CCX block (size >= 1) so that we can classify each Toffoli
    sel = np.flatnonzero(reg_of[ccxp] == reg)
    P, a, b, d = ccxp[sel], CRA[sel], CRB[sel], CRT[sel]
    size_at = np.zeros(len(P), dtype=np.int64)
    i = 0
    while i < len(P):
        j = i
        while (j + 1 < len(P) and P[j + 1] - P[j] <= 80
               and a[j + 1] == a[j] and b[j + 1] == b[j] and d[j + 1] == d[j]):
            j += 1
        size_at[i:j + 1] = j - i + 1
        i = j + 1
    ccx_block_start[reg] = P
    ccx_block_size[reg] = size_at


def rounds_for(reg: int, gap_cluster: int = 6000):
    """group the 42-blocks of a pass into rounds, then locate the 4..34 ladder."""
    p42, s42 = blocks_in(reg, size_min=40)
    keep = p42[s42 == 42]
    if len(keep) == 0:
        return None
    sel = np.flatnonzero(reg_of[ccxp] == reg)      # CCX of this pass, stream order
    # cluster the 42-blocks
    cuts = [0]
    for k in range(1, len(keep)):
        if keep[k] - keep[k - 1] > gap_cluster:
            cuts.append(k)
    cuts.append(len(keep))
    clusters = []
    for k in range(len(cuts) - 1):
        lo, hi = cuts[k], cuts[k + 1]
        clusters.append({"first": int(keep[lo]), "last": int(keep[hi - 1]),
                         "n42": int(hi - lo)})
    # longest strictly +1 ladder starting at 4
    best = (0, -1, 0)          # (length, start, w0)
    for start in range(len(clusters)):
        w = clusters[start]["n42"]
        if w < 3:
            continue
        L = 1
        while (start + L < len(clusters)
               and clusters[start + L]["n42"] == w + L):
            L += 1
        if L > best[0]:
            best = (L, start, w)
    L, start, w0 = best
    Preg = ccx_block_start[reg]        # global op index of each CCX of this pass
    Sreg = ccx_block_size[reg]         # its enclosing block size
    rounds = []
    for k in range(L):
        cl = clusters[start + k]
        nxt = (clusters[start + k + 1]["first"] if start + k + 1 < len(clusters)
               else (A if reg == 0 else N))
        lo = cl["first"]
        hi = nxt
        m = (Preg >= lo) & (Preg < hi)
        sizes = Sreg[m]
        words = np.concatenate([CRA[sel][m], CRB[sel][m], CRT[sel][m]])
        rounds.append({
            "w": int(cl["n42"]),
            "op_lo": lo, "op_hi": hi,
            "toffoli": int(((tof >= lo) & (tof < hi)).sum()),
            "ccx": int(m.sum()),
            "ccx_in_block42": int((sizes == 42).sum()),
            "ccx_in_block_12_41": int(((sizes >= 12) & (sizes < 42)).sum()),
            "ccx_in_block_lt12": int((sizes < 12).sum()),
            "words_touched": sorted(set(int(x) for x in np.unique(words))),
        })
    return {"gap_cluster": gap_cluster, "ladder_start_cluster": int(start),
            "ladder_len": int(L), "w0": int(w0),
            "n_clusters": len(clusters), "n42_blocks": int(len(keep)),
            "clusters": clusters,
            "rounds": rounds}


for reg, name in ((0, "eea_forward"), (2, "eea_reverse")):
    try:
        r = rounds_for(reg)
        OUT[name] = r
        if r:
            rows = r["rounds"]
            w = np.array([x["w"] for x in rows], dtype=float)
            y = np.array([x["toffoli"] for x in rows], dtype=float)
            M = np.stack([np.ones_like(w), w], 1)
            (a, b), *_ = np.linalg.lstsq(M, y, rcond=None)
            resid = y - (a + b * w)
            ss_res = float((resid ** 2).sum())
            ss_tot = float(((y - y.mean()) ** 2).sum())
            OUT[name + "_fit"] = {"intercept_per_round": float(a),
                                 "slope_per_position": float(b),
                                 "r2": 1.0 - ss_res / ss_tot if ss_tot else None,
                                 "n_rounds": int(len(w)),
                                 "sum_toffoli": float(y.sum()),
                                 "implied_per_round_ctrl": float(a),
                                 "implied_per_multiply_total": float(b)}
            say(name, "ladder", r["ladder_len"], "fit a=%.1f b=%.2f"
                % (a, b), "r2", OUT[name + "_fit"]["r2"])
    except Exception as ex:                       # never fail the whole kernel
        OUT[name + "_error"] = repr(ex)
        say(name, "ERROR", repr(ex))


# --------------------------------------- every cluster, no ladder assumption
def dump_clusters(reg: int, gap_cluster: int = 6000):
    p42, s42 = blocks_in(reg, size_min=40)
    keep = p42[s42 == 42]
    if len(keep) == 0:
        return []
    Preg = ccx_block_start[reg]
    Sreg = ccx_block_size[reg]
    sel = np.flatnonzero(reg_of[ccxp] == reg)
    cuts = [0]
    for k in range(1, len(keep)):
        if keep[k] - keep[k - 1] > gap_cluster:
            cuts.append(k)
    cuts.append(len(keep))
    rows = []
    for k in range(len(cuts) - 1):
        lo = int(keep[cuts[k]])
        hi = int(keep[cuts[k + 1]]) if k + 1 < len(cuts) - 1 else (A if reg == 0 else N)
        m = (Preg >= lo) & (Preg < hi)
        sizes = Sreg[m]
        words = np.concatenate([CRA[sel][m], CRB[sel][m], CRT[sel][m]])
        u = np.unique(words)
        rows.append({"op_lo": lo, "op_hi": hi,
                     "w": int(cuts[k + 1] - cuts[k]),
                     "toffoli": int(((tof >= lo) & (tof < hi)).sum()),
                     "ccx": int(m.sum()),
                     "b42": int((sizes == 42).sum()),
                     "b12_41": int(((sizes >= 12) & (sizes < 42)).sum()),
                     "blt12": int((sizes < 12).sum()),
                     "wmin": int(u.min()), "wmax": int(u.max()), "nw": int(len(u))})
    return rows


for reg, name in ((0, "eea_forward"), (2, "eea_reverse")):
    try:
        OUT[name + "_clusters"] = dump_clusters(reg)
        say(name, "clusters dumped", len(OUT[name + "_clusters"]))
    except Exception as ex:
        OUT[name + "_cluster_error"] = repr(ex)
        say(name, "cluster dump ERROR", repr(ex))

# global word census of the forward pass: which 12-bit words does the EEA touch?
sel0 = np.flatnonzero(reg_of[ccxp] == 0)
OUT["forward_words_targets"] = sorted(set(int(x) for x in np.unique(CRT[sel0])))
OUT["forward_n_target_words"] = len(OUT["forward_words_targets"])
OUT["forward_target_words_ge70"] = [int(x) for x in sorted(set(int(x) for x in np.unique(CRT[sel0]))) if x >= 70]
OUT["forward_max_target_word"] = int(CRT[sel0].max())

with open(WORK / "rounds.json", "w") as f:
    json.dump(OUT, f, indent=1, default=str)
print(json.dumps({k: v for k, v in OUT.items() if k not in ("eea_forward", "eea_reverse")},
                 indent=1, default=str))
for name in ("eea_forward", "eea_reverse"):
    r = OUT.get(name)
    if not r:
        continue
    print(f"\n{name}: ladder {r['ladder_len']} rounds from w={r['w0']}, "
          f"{r['n_clusters']} clusters, {r['n42_blocks']} 42-blocks")
    print("  clusters (first_op, n42):")
    print("   " + " ".join(f"{c['first']}:{c['n42']}" for c in r["clusters"]))
    print(f"{'w':>3} {'T':>8} {'ccx':>7} {'blk42':>7} {'24-41':>7} {'<12':>7}  words")
    for x in r["rounds"]:
        wd = x["words_touched"]
        print(f"{x['w']:>3} {x['toffoli']:>8} {x['ccx']:>7} {x['ccx_in_block42']:>7} "
              f"{x['ccx_in_block_12_41']:>7} {x['ccx_in_block_lt12']:>7}  "
              f"{wd[0]}..{wd[-1]} ({len(wd)})")
say("done")
