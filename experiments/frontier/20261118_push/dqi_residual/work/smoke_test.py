"""Local functional smoke test for the dqi_residual analysis kernel.

Builds a SMALL synthetic .kmb (pure construction, no simulation, no .kmb of the
competition is read) whose structure contains one instance of every redundancy class
the kernel is supposed to find, runs the unmodified kernel source against it, and
checks the findings:

  * a 42-CCX multiply-like block, emitted twice on the same (A,B,C) word triple with
    the operands untouched in between        -> E4 must report it
  * R t; CCX(a,b,t); R t (result never read)  -> E2 must report exactly 1 dead target
  * R t; CCX(a,b,t); CX(t,o)                  -> must NOT be reported dead
  * a 200+ token segment repeated verbatim    -> E3 must report it
  * HMR whose bit is overwritten by an unconditional BIT_STORE0 -> dead bit
  * CCZ(x,x,y)                                -> E1 repeated operand
  * a 12-CCX word-AND block                   -> B/C must put it in the "12" bucket
  * a PUSH/POP gated CCX                      -> depth_gt0 branch exercised

Run:  .venv/bin/python experiments/frontier/20261118_push/dqi_residual/work/smoke_test.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
KERNEL = HERE.parent / "k_res" / "main.py"
IRPY = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261118_push_dqi/ds/vqcc_ir.py")
sys.path.insert(0, str(IRPY.parent))
import vqcc_ir as ir  # noqa: E402

NQ = 60          # 5 words of 12
NB = 40
ops = []


def ccx(a, b, t):
    ops.append(("CCX", (a, b, t), ()))


def cx(a, b):
    ops.append(("CX", (a, b), ()))


def h(x):
    ops.append(("HMR", (x,), (0,)))


def r(x):
    ops.append(("R", (x,), ()))


def hmr(x, bit):
    ops.append(("HMR", (x,), (bit,)))


def bs0(bit):
    ops.append(("BIT_STORE0", (), (bit,)))


def push(bit):
    ops.append(("PUSH_CONDITION", (), (bit,)))


def pop():
    ops.append(("POP_CONDITION", (), ()))


# --- a "multiply" block on word triple (1,2,3): 42 CCX with CX scaffolding
def mult_block(a0=12, b0=24, t0=36):
    for k in range(42):
        cx(a0 + k % 12, b0 + k % 12)
        for j in range(3):
            cx(t0 + j, a0 + k % 12)
        ccx(a0 + k % 12, b0 + (k * 5) % 12, t0 + k % 12)
        for j in range(3):
            cx(t0 + j, a0 + k % 12)


mult_block()
# something in between that does NOT touch words 1,2,3
for k in range(30):
    cx(48 + k % 6, 54 + k % 6)
mult_block()          # identical block, same operands -> E4 target

# --- 12-bit word AND on words (0,1,4)
for k in range(12):
    ccx(k, 12 + k, 48 + k % 12)

# --- dead CCX: result reset before any read
r(6)
ccx(0, 1, 6)
for k in range(5):
    cx(50, 51)
r(6)

# --- live CCX: product consumed by CX
r(7)
ccx(0, 1, 7)
cx(7, 8)

# --- HMR whose bit is discarded
hmr(9, 3)
bs0(3)
# --- HMR whose bit is used as a condition
hmr(10, 4)
push(4)
ccx(2, 3, 11)
pop()

# --- CCZ with a repeated operand
ops.append(("CCZ", (5, 5, 13), ()))

# --- a 200+ token segment, emitted twice verbatim
seg = []
for k in range(120):
    seg.append(("CX", (52 + (k % 4), 56 + (k % 3)), ()))
    seg.append(("SWAP", (52 + (k % 5), 57 + (k % 2)), ()))
ops.extend(seg)
ops.extend([("CX", (0, 1), ())])
ops.extend(seg)

# --- condition-gated CCX (depth > 0) + a conditional bit write
push(5)
ccx(3, 4, 14)
pop()

regs = [("S0", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]),
        ("S1", [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]),
        ("E0", [0, 1, 2, 3, 4, 5])]
c = ir.Circuit.from_ops(ops, regs)
tmp = pathlib.Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/dqi_smoke")
tmp.mkdir(parents=True, exist_ok=True)
kmb = tmp / "smoke.kmb"
sha = c.write(str(kmb))
print("synthetic tape", kmb, sha[:16], "ops", c.num_ops, "T", c.toffoli_like())

env = dict(os.environ)
env["DQI_TAPE"] = str(kmb)
env["DQI_IR"] = str(IRPY)
env["DQI_OUT"] = str(tmp)
p = subprocess.run([sys.executable, str(KERNEL)], env=env, capture_output=True, text=True)
print(p.stdout[-6000:])
if p.returncode != 0:
    print(p.stderr[-6000:])
    raise SystemExit("kernel failed")

res = json.loads((pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum")
                  / "experiments/frontier/20261118_push/dqi_residual/k_res"
                  / "residual.json").read_text()) if False else json.loads(
    (tmp / "residual.json").read_text())

fail = []


def chk(name, cond, got=None):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  got={got}"))
    if not cond:
        fail.append(name)


chk("static T = 100 CCX + 1 CCZ", res["static_toffoli"] == 101, res["static_toffoli"])
chk("ccx = 42+42+12+1+1+1+1 = 100", sum(v["ccx"] for v in res["regions"].values()) == 100,
    {k: v["ccx"] for k, v in res["regions"].items()})
chk("two 42-blocks merged into one 84 word-run (as on the real tape)",
    json.dumps(res["word_runs"]["per_region"]).count('"84"') >= 1,
    res["word_runs"]["per_region"])
chk("12-CCX word run counted", res["word_runs"]["n_blocks_12"] == 1,
    res["word_runs"]["n_blocks_12"])
chk("E2 dead target found == 1", res["dce"]["dead_R_A"] == 1, res["dce"])
chk("E2 dead with dead-HMR == 1", res["dce"]["dead_R_B"] == 1, res["dce"])
chk("E2 the consumed product is NOT dead (only 1 dead overall)",
    res["dce"]["dead_R_A"] == 1, res["dce"])
chk("dead bit found", res["dead_bits"]["n_dead"] >= 1, res["dead_bits"])
chk("E1 CCZ repeated operand == 1", res["degeneracy"]["ccz_repeated_operand"] == 1,
    res["degeneracy"])
chk("E1 CCX repeated operand == 0", res["degeneracy"]["ccx_repeated_operand"] == 0,
    res["degeneracy"])
chk("E3 duplicated 240-op segment found (L64 verified)",
    res["dup_segments"]["L64"]["n_verified"] >= 1, res["dup_segments"]["L64"])
chk("E4 duplicated 42-CCX window found", res["mult_dups"]["n_rows"] >= 1,
    res["mult_dups"])
chk("E4 reports a semantic-gap verdict per pair",
    any(r["gap_ops_net"] <= 0 for r in res["mult_dups"]["rows"]),
    res["mult_dups"]["rows"][:2])
chk("and/uncompute counts present", res["and_uncompute"]["R_before_target"] >= 2,
    res["and_uncompute"])
chk("idiom rows cover every CCX", sum(r["n"] for r in res["idioms"]["rows"]) == 100,
    [(r["n"], r["wrun"]) for r in res["idioms"]["rows"]])
chk("depth_gt0 idiom present", any(r["depth_gt0"] for r in res["idioms"]["rows"]),
    [(r["n"], r["depth_gt0"]) for r in res["idioms"]["rows"]])
chk("words table has 5 rows", len(res["words"]) == 5, len(res["words"]))
chk("plumbing errors empty", not res.get("errors"), res.get("errors"))
chk("mean sampling ran", res["mean_sampling"]["mean"] is not None,
    res["mean_sampling"])

print("\n== sample window ==")
print(res["idioms"]["rows"][0].get("example_window", "")[:1200])
print("\nFAILED:", fail if fail else "none")
