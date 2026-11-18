"""Pass 2: the exact EEA -> relayout -> Chien -> rev transitions.

Pass 1 (k_map) found that the forward EEA's last Toffoli is at op 30,151,420, i.e. 184,000 ops
before the first Chien anchor at 30,335,416, and that the 184k ops in between contain **zero**
Toffolis. This pass dumps that segment, the true boundaries, and the tape's own ends.

Outputs: out/survey2.json plus resolved op listings. The tape is deleted before exit.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)
T0 = time.time()


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

EEA_END = 30_151_421          # first op after the last EEA multiplication CCX
CHI_ANCHOR = 30_335_416       # first Chien anchor (12 x BIT_STORE1_IF)
CHI_END = 35_627_261          # last Chien anchor
REV = (35_627_262, 57_520_821)

xz = find("dqi_575b043f.kmb.xz")
RAW = WORK / "dqi.kmb"
with lzma.open(xz, "rb") as fi, open(RAW, "wb") as fo:
    while True:
        blk = fi.read(1 << 23)
        if not blk:
            break
        fo.write(blk)
c = ir.Circuit.read(str(RAW))
sha = c.sha256()
say("read", c.num_ops, "sha", sha[:16])

NAMES = [ir.name(x) if ir.VALID[x] else "?" for x in range(256)]
base = lambda t: (t & 0x7F)
qn = lambda q: f"S{q // 12}[{q % 12}]" if q < 840 else f"Q{q}"
bn = lambda b: f"E{b // 12}[{b % 12}]" if b < 12 * 4095 else f"B{b}"


def window(a, b):
    out = []
    for i, nm, qs, tb, cb in c.decode(a, b):
        out.append(f"{i}\t{nm}\t{','.join(qn(q) for q in qs)}\t"
                   f"{'' if tb is None else bn(tb)}\t{'' if cb is None else bn(cb)}")
    return out


R = {"kmb_sha256": sha, "num_ops": c.num_ops}

# ---- the Toffoli-free segment between the EEA and the Chien ----------------------------------
SEG = (EEA_END, CHI_ANCHOR)
t = c.types[SEG[0]:SEG[1]]
bs = base(t)
cens = {}
for k in np.unique(bs):
    cens[NAMES[int(k)]] = int((bs == k).sum())
cond = {}
for k in np.unique(bs[ir.LCOND[t]]):
    cond[NAMES[int(k)]] = int(((bs == k) & ir.LCOND[t]).sum())
R["segment"] = {"range": list(SEG), "n_ops": int(SEG[1] - SEG[0]),
                "toffoli": int(ir.LTOF[t].sum()), "census": cens, "with_cond": cond}

# per-1k-op word histogram across the segment (which words it moves)
rows = []
step = 20_000
for lo in range(SEG[0], SEG[1], step):
    hi = min(SEG[1], lo + step)
    w = {}
    for i, nm, qs, tb, cb in c.decode(lo, hi):
        for q in qs:
            w[q // 12] = w.get(q // 12, 0) + 1
    rows.append({"lo": lo, "hi": hi, "q_words": {int(k): int(v) for k, v in sorted(w.items())}})
R["segment_profile"] = rows
say("segment census done", R["segment"]["toffoli"], "toffoli in", SEG[1] - SEG[0], "ops")

# ---- resolved windows ------------------------------------------------------------------------
WINDOWS = {
    "eea_last_mult": (EEA_END - 400, EEA_END + 700),
    "pre_chien_5k": (CHI_ANCHOR - 5_416, CHI_ANCHOR),
    "chien_block1": (CHI_ANCHOR - 700, CHI_ANCHOR + 800),
    "chien_block_mid": (33_000_000, 33_001_600),
    "chien_to_rev": (CHI_END - 800, CHI_END + 1_200),
    "tape_head": (0, 400),
    "tape_tail": (c.num_ops - 400, c.num_ops),
}
for nm, (a, b) in WINDOWS.items():
    (OUT / f"win2_{nm}.txt").write_text("\n".join(window(a, b)) + "\n")
    say("wrote", nm, b - a)
R["windows"] = {k: list(v) for k, v in WINDOWS.items()}

# ---- exact per-qubit handoff at the three real cuts (±40k window) ----------------------------
def handoff(cut, half=40_000):
    lo, hi = max(0, cut - half), min(c.num_ops, cut + half)
    last = {}
    first = {}
    for i, nm, qs, tb, cb in c.decode(lo, hi):
        for q in qs:
            last[q] = i
            first.setdefault(q, i)
    carry = {q: (last[q], first[q]) for q in last if last[q] < cut <= first[q]}
    by_word = {}
    for q, (lb, fa) in carry.items():
        by_word.setdefault(q // 12, []).append((q % 12, lb, fa))
    return {"cut": cut, "window": [lo, hi], "depth": c.depth(cut),
            "n_carry": len(carry),
            "carry_words": {int(k): sorted(v[0] for v in vs) for k, vs in sorted(by_word.items())},
            "carry_examples": [[qn(q), lb, fa] for q, (lb, fa) in
                               sorted(carry.items())[:20]]}


for nm, cut in (("eea_end", EEA_END), ("chien_start", CHI_ANCHOR),
                ("chien_end", REV[0]), ("tape_end", REV[1])):
    R[f"handoff_{nm}"] = handoff(cut, 20_000 if cut == REV[1] else 40_000)
    say("handoff", nm, R[f"handoff_{nm}"]["n_carry"], "carried")

# ---- the three Chien blocks: which registers each one touches --------------------------------
def block_regs(a, b):
    q = {}
    bits = {}
    for i, nm, qs, tb, cb in c.decode(a, b):
        for x in qs:
            q.setdefault(x // 12, set()).add(x % 12)
        for x in (tb, cb):
            if x is not None:
                bits.setdefault(x // 12, set()).add(x % 12)
    return {"qubit_words": {int(k): sorted(v) for k, v in sorted(q.items())},
            "bit_regs": {int(k): sorted(v) for k, v in sorted(bits.items())}}


R["chien_blocks"] = {
    "first": block_regs(CHI_ANCHOR - 620, CHI_ANCHOR + 620),
    "mid": block_regs(32_999_400, 33_000_600),
    "last": block_regs(CHI_END - 620, CHI_END + 620),
}

# ---- per-position op template: opcode sequence of the first block, run-length encoded ---------
a, b = CHI_ANCHOR - 620, CHI_ANCHOR + 620
seq = [NAMES[int(x)] for x in base(c.types[a:b])]
rle = []
for nm in seq:
    if rle and rle[-1][0] == nm:
        rle[-1][1] += 1
    else:
        rle.append([nm, 1])
R["template_rle"] = rle
R["template_n_ops"] = len(seq)

(OUT / "survey2.json").write_text(json.dumps(R, indent=1))
say("wrote survey2.json", (OUT / "survey2.json").stat().st_size)
RAW.unlink()
say("deleted tape; exists", RAW.exists())
say("done")
