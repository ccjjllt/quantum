import pathlib
import subprocess
import sys

HDR = "\n".join([f"APPEND_TO_REGISTER q{i} r0" for i in range(6)] + ['REGISTER r0 "x"']) + "\n"
CASES = {
    "one_cz": "CCX q0 q1 q2\nCZ q3 q2\nCCX q0 q1 q2\n",
    "value_read": "CCX q0 q1 q2\nCZ q3 q2\nCX q2 q4\nCCX q0 q1 q2\n",
    "z_read": "CCX q0 q1 q2\nZ q2\nCCX q0 q1 q2\n",
    "two_cz": "CCX q0 q1 q2\nCZ q3 q2\nCZ q4 q2\nCCX q0 q1 q2\n",
    "dirty_target": "X q2\nCCX q0 q1 q2\nCZ q3 q2\nCCX q0 q1 q2\n",
    "no_cancel": "CCX q0 q1 q2\nCX q0 q4\nCZ q3 q2\nCCX q0 q1 q2\n",
}
tmp = pathlib.Path("/tmp/foldtest")
tmp.mkdir(exist_ok=True)
for name, body in CASES.items():
    p = tmp / f"{name}.kmx"
    p.write_text(HDR + body)
    out = subprocess.run([sys.executable, "experiments/frontier/20261118_push/invsqrt/fold_atoms.py", str(p)],
                         capture_output=True, text=True, cwd="/Users/zhaohuaxiang/ccjjllt/quantum")
    keep = [l for l in out.stdout.splitlines() if "fold sites" in l or "total Toffoli" in l or l.startswith("  ops")]
    print(name, "->", " | ".join(keep) if keep else out.stdout[-300:] + out.stderr[-300:])
