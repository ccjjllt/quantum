"""Dump the full instruction window around chosen multiply blocks. Read-only."""
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
t = c.types

BLOCKS = [(17576206, 17577498, "fwd0"), (17579104, 17580396, "fwd1"), (36295669, 36296961, "rev0")]
PAD = 60
for a, b, nm in BLOCKS:
    lo, hi = a - PAD, b + PAD
    ops = c.decode(lo, hi)
    print(f"\n########## {nm}  block [{a},{b}) window [{lo},{hi})  {len(ops)} ops")
    for (i, name, qs, tb, cb) in ops:
        mark = " <<<" if i in (a, b - 1) else ""
        extra = f" tbit={tb}" if tb is not None else ""
        ex2 = f" cond={cb}" if cb is not None else ""
        print(f"{i:>9} {name:<16} {str(qs):<22}{extra}{ex2}{mark}")
