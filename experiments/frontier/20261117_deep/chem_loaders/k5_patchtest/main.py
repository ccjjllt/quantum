"""Can the ANGLE loader's data layer be rewritten with CX-only changes (0 extra Toffoli)?

Method.  The tape is classical-reversible (X/CX/CCX/SWAP + R/HMR resets + phase):
every wire holds a definite function of the 11-bit address `a`, so the circuit can be
evaluated *symbolically* over all 2^11 addresses instead of simulated.

1. Evaluate every wire's value function V[w][a] by replaying the tape.
   Self-check: the word registers at the end must equal the shipped delta table.
2. Decompose the 292 Toffolis into
     - product/address CCX  (target is a temporary wire)      -> data independent
     - data CCX             (target is a word bit)            -> data dependent
3. Reachability of a new table.  A word bit's final value is
     (XOR of its data-CCX contributions)  XOR  (XOR of the CX slots we keep, each
     contributing the *time-of-gate* value of its control)  XOR  (X X-gates).
   The CCX part is fixed (we are not allowed to add Toffoli), the CX slots are free
   to keep or delete.  So bit b can realise the new table iff
     new_b XOR ccx_part_b  is in  span{ V[c] at each CX slot into b }.
   That is an exact GF(2) membership test.
4. If all 40 bits pass, build the patched .kmb (delete the unneeded CX) and run the
   UNMODIFIED official contract check `recover_words_from_circuits` on the 15-circuit
   family, comparing the recovered words with the patched table.
"""
import itertools
import pathlib
import struct
import zipfile

import numpy as np

REPORT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s)
    print(s, flush=True)


MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
TMP = pathlib.Path("/tmp/patchcx")
TMP.mkdir(exist_ok=True)
WORK = pathlib.Path("/kaggle/working")
ROOT = pathlib.Path("/kaggle/input")
for z in sorted(ROOT.rglob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for m in zf.namelist():
            if m.endswith(".npz") or "angle_k_" in m:
                zf.extract(m, TMP)
npz = sorted(TMP.rglob("*.npz"))[0]
z = np.load(npz, allow_pickle=True)
aw = np.array(z["angle_words"])
rows, nw = aw.shape
brot, NSEL, J = 8, 11, 5
ADDR = 1 << NSEL
NC = (nw + J - 1) // J
bits = ((aw[:, :, None] >> np.arange(brot)) & 1).astype(np.uint8)
log(f"A0 table {aw.shape} addr {ADDR} circuits {NC}")


def deltas(k):
    lo = J * k
    hi = min(lo + J, nw)
    cur = bits[:, lo:hi, :].reshape(rows, -1)
    if k == 0:
        return cur.copy()
    return cur ^ bits[:, lo - J:lo, :].reshape(rows, -1)


def parse(path):
    raw = path.read_bytes()
    h = list(struct.unpack_from("<4I9Q", raw, 16))
    pos, secs = 104, {}
    while pos < len(raw):
        idx, size = struct.unpack_from("<QQ", raw, pos)
        if 1 <= idx <= 9:
            secs[idx] = np.frombuffer(raw[pos + 16:pos + 16 + size],
                                      dtype=np.uint8 if idx == 1 else np.uint32).copy()
        pos += 16 + size
    ops = secs[1]
    n = len(ops)
    base = ops & 127
    cb = (ops & 128) != 0
    i3 = np.isin(base, [0x30, 0x31, 0x32])
    i2 = np.isin(base, [0x20, 0x21, 0x22])
    i1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
    A = np.full(n, -1, np.int64); B = np.full(n, -1, np.int64); C = np.full(n, -1, np.int64)
    p3, p2, p1 = (np.cumsum(x) for x in (i3, i2, i1))
    q3, q2, q1 = (np.flatnonzero(x) for x in (i3, i2, i1))
    A[q3] = secs[2][p3[q3] - 1]; B[q3] = secs[3][p3[q3] - 1]; C[q3] = secs[4][p3[q3] - 1]
    A[q2] = secs[5][p2[q2] - 1]; C[q2] = secs[6][p2[q2] - 1]
    A[q1] = secs[7][p1[q1] - 1]
    return h, secs, ops, base, cb, A, B, C


k0 = sorted(p for p in TMP.rglob("angle_k_0.kmb"))[0]
H, SECS, ops, base, cb, A, B, C = parse(k0)
n = len(ops)
Q = int(max(A.max(), B.max(), C.max())) + 1
log(f"A1 {k0.name} Q {Q} n {n} staticT {int(np.isin(base, [0x30, 0x31, 0x32]).sum())}")


def wire(x, flag=None):
    """decode an operand: bit8 = anti-control (negation)."""
    neg = (int(x) & 0x100) != 0
    w = int(x) & 0x7F
    return w, neg


# symbolic evaluation over all addresses
V = np.zeros((Q, ADDR), np.uint8)
for i in range(NSEL):
    V[i] = ((np.arange(ADDR) >> i) & 1).astype(np.uint8)
slices = []          # per CX-into-word snapshot: (op, target, control, neg)

for k in range(n):
    b = int(base[k])
    if b == 0x10:      # X
        w, neg = wire(A[k]); V[w] ^= 1
    elif b == 0x21:    # CX
        c, cneg = wire(A[k]); t, tneg = wire(C[k])
        val = (1 - V[c]) if cneg else V[c]
        if t < 51:
            slices.append((k, t, c, cneg))
        V[t] ^= val
    elif b == 0x22:    # SWAP
        a1, _ = wire(A[k]); c1, _ = wire(C[k])
        V[[a1, c1]] = V[[c1, a1]]
    elif b in (0x12, 0x50):   # R / HMR -> |0>
        w, _ = wire(A[k]); V[w] = 0
    elif b in (0x30, 0x31, 0x32):
        c1, n1 = wire(A[k]); c2, n2 = wire(B[k]); t, _ = wire(C[k])
        v1 = (1 - V[c1]) if n1 else V[c1]
        v2 = (1 - V[c2]) if n2 else V[c2]
        V[t] ^= (v1 & v2)
    # CZ / Z : phase only

tab = deltas(0)
def replay(flagbit, revaddr, hmr_reset=True, mask=0x7F):
    V = np.zeros((Q, ADDR), np.uint8)
    for i in range(NSEL):
        V[i] = ((np.arange(ADDR) >> (NSEL - 1 - i if revaddr else i)) & 1).astype(np.uint8)
    def dec(x):
        return int(x) & mask, (int(x) & flagbit) != 0
    for k in range(n):
        b = int(base[k])
        if b == 0x10:
            w, _ = dec(A[k]); V[w] ^= 1
        elif b == 0x21:
            c, cn = dec(A[k]); t, _ = dec(C[k])
            V[t] ^= (1 - V[c]) if cn else V[c]
        elif b == 0x22:
            a1, _ = dec(A[k]); c1, _ = dec(C[k]); V[[a1, c1]] = V[[c1, a1]]
        elif b == 0x12 or (b == 0x50 and hmr_reset):
            w, _ = dec(A[k]); V[w] = 0
        elif b == 0x50:
            pass
        elif b == 0x31:
            c1, n1 = dec(A[k]); c2, n2 = dec(B[k]); t, _ = dec(C[k])
            v1 = (1 - V[c1]) if n1 else V[c1]
            v2 = (1 - V[c2]) if n2 else V[c2]
            V[t] ^= (v1 & v2)
    return V[11:51].T

best = None
for flagbit in (0x100, 0x200, 0x400):
    for revaddr in (False, True):
        for hmr in (True, False):
            g = replay(flagbit, revaddr, hmr)
            mism = int((g[:rows] != tab).sum())
            agree = 1.0 - mism / tab.size
            log(f"A3 flag=0x{flagbit:x} revaddr={revaddr} hmr_reset={hmr}: "
                f"mismatches {mism}/{tab.size} agreement {100 * agree:.2f}%")
            if best is None or mism < best[0]:
                best = (mism, flagbit, revaddr, hmr)
log(f"A4 best {best}")
# per-bit agreement for the best variant
g = replay(best[1], best[2], best[3])
per = [(j, float((g[:rows, j] == tab[:, j]).mean())) for j in range(g.shape[1])]
log(f"A5 per-bit agreement: {[round(x[1], 3) for x in per]}")
# row-block agreement: first 5 blocks vs the rest
log(f"A6 agreement rows 0..75 {float((g[:76] == tab[:76]).mean()):.4f} ; "
    f"rows 80..1219 {float((g[80:rows] == tab[80:rows]).mean()):.4f}")
(pathlib.Path("/kaggle/working/report.txt")).write_text("\n".join(REPORT) + "\n")
log("done")
