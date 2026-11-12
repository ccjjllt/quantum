"""eae396ba: 用 INFO_TAG 里的 gadget 名字标定乘法 kernel 的"操作数指纹"。

对每个 tag 实例统计：paid、CCX、以及 CCX 三个操作数位上出现的寄存器集合与
"最低位"分布。已知标签（tag_census.json）里有 multiply v(99)、head_phase(42)、
full_head_product(126/168/210)、inverse24 products(70) 等，可用来判断某个
未标注的 186/178 块是"一个 186 项 kernel"还是"若干 kernel 拼起来"。

只读，不建电路。一次流式扫描。
"""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID = {"CCX", "CSWAP", "CCZ", "CCX_CARRY"}
SKIP = ("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")


def main():
    q2r = {}
    rname = {}
    stack = []
    agg = defaultdict(lambda: {"n": 0, "paid": 0, "ccx": 0,
                              "x": Counter(), "y": Counter(), "z": Counter(),
                              "zreg": Counter(), "yreg": Counter()})
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
            elif tag.startswith("@exit:") and stack:
                stack.pop()
            continue
        if not stack:
            continue
        ops = l.split()
        op = ops[0]
        if op not in PAID:
            continue
        key = stack[-1]          # 最内层 tag
        a = agg[key]
        a["paid"] += 1
        if op == "CCX":
            a["ccx"] += 1
            qs = [int(x[1:]) for x in ops[1:4]]
            for slot, q in zip(("x", "y", "z"), qs):
                a[slot][rname.get(q2r.get(q), "?")] += 1
            a["yreg"][rname.get(q2r.get(qs[1]), "?")] += 1
            a["zreg"][rname.get(q2r.get(qs[2]), "?")] += 1
    for k, a in sorted(agg.items(), key=lambda kv: -kv[1]["paid"]):
        if a["paid"] < 60:
            continue
        print(f"{k:26s} n={a['n']:3d} paid={a['paid']:7d} ccx={a['ccx']:6d} "
              f"|x|={len(a['x'])} |y|={len(a['y'])} |z|={len(a['z'])}")
        print(f"     x={dict(sorted(a['x'].items()))}")
        print(f"     y={dict(sorted(a['y'].items()))}")
        print(f"     z={dict(sorted(a['z'].items()))}")


if __name__ == "__main__":
    main()
