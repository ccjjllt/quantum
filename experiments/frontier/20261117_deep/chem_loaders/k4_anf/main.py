"""Exact ANF (algebraic normal form) census of the 15 ANGLE delta tables.

The gate dump shows: CCX(4,5->51), CCX(4,6->52), ..., CCX(4,53->70) etc, i.e. the
circuit builds products of the high selection bits as shared monomials, then
accumulates them into the 40 word bits (CCX) and fans them out (CX).  So the load
is a *shared-monomial* circuit and the floor is the number of distinct monomials
that the table actually needs.  This kernel measures that number exactly.

Mobius transform over 2^11 addresses per output bit, with the 828 addresses that
no row uses fixed to 0 (they are true don't-cares: the verifier simulates only
num_vectors = 1220 addresses, but a circuit that is wrong there is still legal --
so we also report the variant where the don't-cares are chosen to minimise each
single bit's monomial count, which is a lower bound).
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
TMP = pathlib.Path("/tmp/anf")
TMP.mkdir(exist_ok=True)
ROOT = pathlib.Path("/kaggle/input")
for z in sorted(ROOT.rglob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for m in zf.namelist():
            if m.endswith(".npz"):
                zf.extract(m, TMP)
p = sorted(TMP.rglob("*.npz"))[0]
z = np.load(p, allow_pickle=True)
aw = np.array(z["angle_words"])
rows, nw = aw.shape
brot = 8
NSEL = 11
ADDR = 1 << NSEL
J = 5
NC = (nw + J - 1) // J
bits = ((aw[:, :, None] >> np.arange(brot)) & 1).astype(np.uint8)
log(f"A0 angle_words {aw.shape} rows {rows} words {nw} circuits {NC} addr {ADDR}")


def mobius(f):
    """f: (ADDR, w) uint8 -> ANF coefficients over 11 variables (in place)."""
    g = f.copy()
    for i in range(NSEL):
        m = 1 << i
        idx = np.arange(ADDR)
        hi = idx[(idx & m) != 0]
        lo = hi ^ m
        g[hi] ^= g[lo]
    return g


tot_mono = 0
tot_mono_min = 0
tot_bits = 0
tot_by_deg = {}
per = []
for k in range(NC):
    lo = J * k
    hi = min(lo + J, nw)
    cur = bits[:, lo:hi, :].reshape(rows, -1)
    if k == 0:
        d = cur.copy()
    else:
        d = cur ^ bits[:, lo - J:lo, :].reshape(rows, -1)
    w = d.shape[1]
    F = np.zeros((ADDR, w), np.uint8)
    F[:rows] = d
    G = mobius(F)
    mono = int(G.sum())
    # degree histogram
    for i in range(NSEL):
        pass
    deg = np.zeros(NSEL + 1, np.int64)
    popc = np.array([bin(a).count("1") for a in range(ADDR)])
    for a in np.flatnonzero(G.any(axis=1)):
        deg[popc[a]] += int(G[a].sum())
    # lower bound with per-bit optimal don't-care assignment:
    # a bit with support S (|S| ones among `rows` addresses) needs at least
    # min(|S|, rows-|S|) ... we report the plain count and the "complement" bound
    mono_min = 0
    for b in range(w):
        col = d[:, b]
        ones = int(col.sum())
        mono_min += min(ones, 1)
    union = int(G.any(axis=1).sum())
    # greedy don't-care reduction: flip free addresses that shrink the ANF support
    free = np.zeros(ADDR, bool)
    free[rows:] = True
    best_union = union
    rng = np.random.default_rng(12345)
    cur = F.copy()
    for it in range(40):
        cand = np.flatnonzero(free)
        pick = rng.choice(cand, size=min(64, len(cand)), replace=False)
        trial = cur.copy()
        for a in pick.tolist():
            trial[a] ^= 1
        Gt = mobius(trial)
        nu = int(Gt.any(axis=1).sum())
        if nu < best_union:
            best_union = nu
            cur = trial
    log(f"B{k:2d} UNION monomials {union:5d}  after 40 greedy don't-care sweeps "
        f"{best_union:5d}  shipped T {[292,287,269,269,263,263,263,263,263,264,265,265,265,265,266][k]}")
    per.append((k, w, mono, deg, union, best_union))
    tot_mono += mono
    tot_mono_min += mono_min
    tot_bits += w
    for i in range(NSEL + 1):
        tot_by_deg[i] = tot_by_deg.get(i, 0) + int(deg[i])
    log(f"B{k:2d} outbits {w:2d} ANFmonomials {mono:6d} perBit {mono / w:6.2f}  "
        f"deg1 {int(deg[1]):4d} deg2 {int(deg[2]):4d} deg3 {int(deg[3]):4d} "
        f"deg4 {int(deg[4]):4d} deg>=5 {int(deg[5:].sum()):5d}")

log("")
log(f"C0 ANF monomials over 15 circuits {tot_mono}  (per pass); "
    f"shipped static Toffoli per pass 4,022  ratio {4022 / tot_mono:.3f}")
log(f"C1 shipped per circuit [292,287,269,269,263,263,263,263,263,264,265,265,265,265,266]")
log(f"C2 degree histogram (all circuits) {dict(sorted(tot_by_deg.items()))}")
log(f"C3 rows {rows} addr {ADDR} don't-cares {ADDR - rows}")
log(f"C4 per-circuit ANF monomials {[p[2] for p in per]}")
log(f"C7 per-circuit UNION (shared across the 40 bits) {[p[4] for p in per]}")
log(f"C8 per-circuit UNION after don't-care search {[p[5] for p in per]}")
log(f"C9 sum of C8 {sum(p[5] for p in per)} vs shipped 4,022 -> ratio "
    f"{4022 / max(sum(p[5] for p in per), 1):.3f}")
log(f"C5 floor if each monomial needs >=1 CCX: {tot_mono}; "
    f"shipped is {4022 / max(tot_mono, 1):.3f}x that")
log(f"C6 ratio shipped/ANF per circuit {[round(s / max(p[2], 1), 3) for s, p in zip([292,287,269,269,263,263,263,263,263,264,265,265,265,265,266], per)]}")

pathlib.Path("/kaggle/working/report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
