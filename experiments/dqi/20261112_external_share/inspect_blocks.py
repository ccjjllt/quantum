"""eae396ba 的 unextract/extract 复合块解剖：186/178 T 块里到底有几个乘法、操作数是谁。

只读 797 MB 的 .kmx（由 main 的 artifacts/20261112_eae_candidate/dqi.kmb 生成，
见 20261112_branch_recovery/dump_kmx.py）。不做电路构建。

一次流式扫描，随后在内存里做：
  * 块签名直方图（按 paid 与 CCX 簇大小）
  * 指定 paid 的块的逐簇、逐操作数寄存器明细

用法：python inspect_blocks.py [cluster_gap]
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID = {"CCX", "CSWAP", "CCZ", "CCX_CARRY"}
SKIP = ("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")


def main(CL_GAP=150, SEG_GAP=200):
    q2r = {}
    rname = {}
    stages = []          # (name, enter_line, exit_line)
    segs = {"extract": [], "unextract": []}
    stack = []
    inside = None
    cur = None
    run = 0
    ln = 0
    for l in open(KMX, "r", encoding="utf-8", errors="replace"):
        ln += 1
        if l.startswith("APPEND_TO_REGISTER"):
            _, q, r = l.split()
            q2r[int(q[1:])] = int(r[1:])
            continue
        if l.startswith("REGISTER "):
            _, r, nm = l.split()
            rname[int(r[1:])] = nm.strip('"')
            continue
        if l.startswith(SKIP) or not l.strip():
            continue
        if l.startswith("INFO_TAG "):
            tag = l.strip().split('"', 2)[1]
            if tag.startswith("@enter:"):
                stack.append(tag[7:])
                if len(stack) == 1:
                    stages.append([tag[7:], ln, None])
            elif tag.startswith("@exit:") and stack:
                if len(stack) == 1:
                    stages[-1][2] = ln
                stack.pop()
            inside = stack[0] if stack else None
            continue
        if inside not in segs:
            continue
        ops = l.split()
        op = ops[0]
        if op in PAID:
            if cur is None:
                cur = {"start": ln, "paid": Counter(), "ccx": []}
            cur["paid"][op] += 1
            if op == "CCX":
                cur["ccx"].append((int(ops[1][1:]), int(ops[2][1:]), int(ops[3][1:]),
                                   min(run, 255)))
            run = 0
        else:
            run += 1
            if run >= SEG_GAP and cur is not None:
                cur["end"] = ln
                segs[inside].append(cur)
                cur = None
    if cur is not None:
        cur["end"] = ln
        segs[inside].append(cur)

    qn = {q: rname.get(r, f"r{r}") for q, r in q2r.items()}

    def clusters(seg):
        out = []
        for q1, q2, q3, r in seg["ccx"]:
            if out and r <= CL_GAP:
                out[-1].append((q1, q2, q3))
            else:
                out.append([(q1, q2, q3)])
        return out

    for stage in ("extract", "unextract"):
        ss = segs[stage]
        h = Counter()
        for s in ss:
            sig = tuple(len(c) for c in clusters(s))
            h[(sum(s["paid"].values()), sig, s["paid"]["CCZ"], s["paid"]["CSWAP"])] += 1
        tot = sum(k[0] * v for k, v in h.items())
        print(f"\n== {stage}: segments={len(ss)} paid={tot} cluster_gap={CL_GAP}")
        for k, v in sorted(h.items(), key=lambda kv: -kv[0][0] * kv[1])[:14]:
            print(f"   paid={k[0]:5d} cl={k[1]} ccz={k[2]} cs={k[3]} x{v} -> {k[0]*v}")

    # 明细：unextract 里 paid ∈ {186,178} 的前几个，逐簇寄存器
    for want in (186, 178, 99, 84, 42):
        shown = 0
        for s in segs["unextract"]:
            if sum(s["paid"].values()) != want:
                continue
            shown += 1
            if shown > 2:
                break
            cls = clusters(s)
            print(f"\n--- unextract paid={want} lines {s['start']}..{s['end']} "
                  f"clusters={[len(c) for c in cls]}")
            for cl in cls:
                slots = []
                for i in range(3):
                    c = Counter(qn[q] for q in [t[i] for t in cl])
                    slots.append(" ".join(f"{r}x{n}" for r, n in sorted(c.items())))
                print(f"   {len(cl):4d} T : [{slots[0]}] x [{slots[1]}] -> [{slots[2]}]")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 150)
