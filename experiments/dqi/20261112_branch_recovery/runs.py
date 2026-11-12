"""把某一 stage 的 kmx 行压缩成 run 视图（同 op 连续合并），用于识别 gadget 边界。"""
from __future__ import annotations
import sys
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")

def main(stage, lo_off, n_lines):
    stage = stage
    inside = False
    start = None
    lines = []
    with KMX.open("r", encoding="utf-8", errors="replace") as f:
        for ln, l in enumerate(f, 1):
            if l.startswith("INFO_TAG "):
                tag = l.strip().split('"',2)[1]
                if tag == f"@enter:{stage}": inside=True; start=ln
                elif tag == f"@exit:{stage}": inside=False
                continue
            if inside:
                lines.append((ln, l.rstrip("\n")))
    print(f"stage {stage} lines={len(lines)} start={start}")
    sel = lines[lo_off:lo_off+n_lines]
    # runs
    i = 0
    while i < len(sel):
        j = i
        op = sel[i][1].split()[0]
        while j+1 < len(sel) and sel[j+1][1].split()[0] == op:
            j += 1
        chunk = [t for _, t in sel[i:j+1]]
        paid = sum(1 for t in chunk if t.split()[0] in ("CCX","CSWAP","CCZ","CCX_CARRY"))
        def brief(t):
            p=t.split()
            return p[0]+" "+" ".join(p[1:4]) if len(p)>3 else t
        head = brief(chunk[0]); tail = brief(chunk[-1]) if len(chunk)>1 else ""
        print(f"  L{sel[i][0]}: {op:12s} x{j-i+1:6d} paid={paid:6d} | {head}" + (f" ... {tail}" if tail and tail!=head else ""))
        i = j+1

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
