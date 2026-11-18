"""Compact anatomy of one multiply block: the 42 CCX triples, and per-CCX the CX
prep/unprep pairs (which carriers get built), plus the block's outside traffic.
Read-only, no simulation."""
import collections
import importlib.util
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum")
spec = importlib.util.spec_from_file_location("vqcc_ir", ROOT / "artifacts/20261118_push_dqi/ds/vqcc_ir.py")
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read("/private/tmp/dqid/dqi_575b043f.kmb")


def word(q):
    return f"w{q // 12}.{q % 12}"


def anatomy(a, b, pad=0, nm=""):
    ops = c.decode(a - pad, b + pad)
    print(f"\n===== block {nm} [{a},{b})  {len(ops)} ops with pad {pad}")
    ccx = [(i, qs, tb, cb) for (i, name, qs, tb, cb) in ops if name.startswith("CCX")]
    print(f"-- {len(ccx)} CCX")
    for i, qs, cb, _ in [(x[0], x[1], x[3], 0) for x in ccx]:
        print(f"   {i:>9} CCX {tuple(word(q) for q in qs)}  cond={cb}")
    # everything that is not CX/CCX
    other = [(i, name, qs, tb, cb) for (i, name, qs, tb, cb) in ops if not name.startswith("CX") and not name.startswith("CCX")]
    print(f"-- {len(other)} non-CX/CCX ops:", collections.Counter(x[1] for x in other))
    for i, name, qs, tb, cb in other[:40]:
        print(f"   {i:>9} {name:<14} {qs} tbit={tb} cond={cb}")
    # CX per word pair
    cnt = collections.Counter()
    for (i, name, qs, tb, cb) in ops:
        if name == "CX":
            cnt[(qs[0] // 12, qs[1] // 12)] += 1
        elif name == "CX_IF":
            cnt[("IF", qs[0] // 12, qs[1] // 12)] += 1
    print("-- CX by (src-word, dst-word):", dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:24]))


anatomy(17576206, 17577498, 0, "fwd0")
anatomy(17576206, 17577498, 400, "fwd0+pad400")
anatomy(17579104, 17580396, 0, "fwd1")
anatomy(36295669, 36296961, 0, "rev0")
