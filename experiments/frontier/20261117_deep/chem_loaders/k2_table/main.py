"""Chemistry ANGLE loader: measure the angle_words table and the information floor.

Read-only. Loads `angle_words` out of the shipped submission.npz, rebuilds the 15
delta tables exactly as `angle_k_reference_circuit.py` documents
(delta[0] = batch[0], delta[k] = batch[k] ^ batch[k-1], 5 words per circuit,
brot = 8 bits per word), and counts the things any QROM implementation must pay:
  * active addresses  (delta[k][a] != 0)          -> each needs address selectance
  * distinct nonzero values / maximal bit runs    -> CX-only work, free
  * the pruned segment-tree cost of the zero subtrees
Then compares with the measured static Toffoli of each shipped loader.
"""
import pathlib
import zipfile

import numpy as np

REPORT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s)
    print(s, flush=True)


WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/chemtab")
TMP.mkdir(exist_ok=True)
ROOT = pathlib.Path("/kaggle/input")

zips = [p for p in sorted(ROOT.rglob("*.zip"))]
for z in zips:
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        log(f"A0 {z.name} members {len(names)}: {[n for n in names if n.endswith('.npz')][:5]}")
        for m in names:
            if m.endswith(".npz"):
                zf.extract(m, TMP)
npzs = sorted(TMP.rglob("*.npz"))
log(f"A1 npz {[(p.name, p.stat().st_size) for p in npzs]}")
best = None
for p in npzs:
    try:
        z = np.load(p, allow_pickle=True)
        ks = list(z.keys())
        log(f"A2 {p.name} keys {ks}")
        if "angle_words" in ks:
            best = (p, z)
            break
    except Exception as e:
        log(f"A2 {p.name} FAILED {e!r}")
if best is None:
    (WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
    raise SystemExit("no angle_words")

p, z = best
aw = np.array(z["angle_words"])
log(f"A3 angle_words shape {aw.shape} dtype {aw.dtype} min {aw.min()} max {aw.max()}")
rows, nw = aw.shape
brot = 8
assert int(aw.max()) < (1 << brot), "brot != 8?"
# bits: (rows, nw, 8) little-endian
bits = ((aw[:, :, None] >> np.arange(brot)) & 1).astype(np.uint8)
log(f"A4 bits {bits.shape}")

NSEL = 11
ADDR = 1 << NSEL
J = 5                      # words per circuit (persistent 40 bits / 8)
NC = (nw + J - 1) // J
log(f"A5 rows {rows} words {nw} circuits {NC} (J={J})  addr space {ADDR}")

tot_active = 0
tot_nonzero_bits = 0
tot_runs = 0
tot_mono = 0
tot_tree = 0
per = []
for k in range(NC):
    lo = J * k
    hi = min(lo + J, nw)
    cur = bits[:, lo:hi, :].reshape(rows, -1)          # (rows, J*8)
    if k == 0:
        d = cur.copy()
    else:
        prev = bits[:, lo - J:lo, :].reshape(rows, -1)
        d = cur ^ prev
    w = d.shape[1]
    nz_rows = int((d.any(axis=1)).sum())
    nz_bits = int(d.sum())
    runs = 0
    for b in range(w):
        col = d[:, b]
        runs += int(1 + np.count_nonzero(col[1:] != col[:-1]))
    # pruned segment tree over the ADDR space: a leaf with d==0 can be cut
    # cost of a unary iteration that prunes zero subtrees, per output bit, is
    # shared across bits; we report the shared chain length for the union support
    sup = np.zeros(ADDR, bool)
    sup[:rows] = d.any(axis=1)
    # number of internal nodes of a binary tree that contain >=1 active leaf
    nodes = 0
    idx = np.flatnonzero(sup)
    # count distinct prefixes of active addresses
    pref = set()
    for a in idx.tolist():
        for L in range(1, NSEL + 1):
            pref.add((L, a >> (NSEL - L)))
    nodes = len(pref)
    tree = max(nodes - 1, 0)
    tot_active += nz_rows
    tot_nonzero_bits += nz_bits
    tot_runs += runs
    tot_tree += tree
    per.append((k, w, nz_rows, nz_bits, runs, nodes, tree))
    log(f"B{k:2d} words {lo}..{hi - 1} outbits {w:2d} activeRows {nz_rows:5d} "
        f"nonzeroBits {nz_bits:5d} runs {runs:6d} treeNodes {nodes:6d} treeCost {tree:6d}")

log("")
log(f"C0 totals over {NC} circuits: activeRows {tot_active} nonzeroBits {tot_nonzero_bits} "
    f"runs {tot_runs} treeNodes {tot_tree + NC}")
log(f"C1 shipped static T measured per kernel = 263..292 (sum 4,022 per pass)")
shipped = [292, 287, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]
log(f"C2 shipped per circuit {shipped} sum {sum(shipped)}  (2 passes -> {2 * sum(shipped)})")
log(f"C3 ratio shipped/nonzeroBits {sum(shipped) / max(tot_nonzero_bits, 1):.3f} ; "
    f"shipped/activeRows {sum(shipped) / max(tot_active, 1):.3f} ; "
    f"shipped/treeCost {sum(shipped) / max(tot_tree, 1):.3f}")
log(f"C4 L-2 reference floor per circuit {rows - 2} ; total {NC * (rows - 2)}")

# how many bits are constant zero in a whole circuit, and how many rows share values
log("")
consec = (aw[:, 1:] ^ aw[:, :-1])
log(f"D0 consecutive-word XOR table shape {consec.shape} nonzero frac "
    f"{float((consec != 0).mean()):.4f}")
log(f"D1 per-word-column variance: distinct values per column "
    f"min {int(min(len(np.unique(aw[:, j])) for j in range(nw)))} "
    f"max {int(max(len(np.unique(aw[:, j])) for j in range(nw)))}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
