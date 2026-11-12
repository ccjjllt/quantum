"""eae396ba kmx 标签树普查：每个 tag 实例的 paid 门数、行号范围、子树。只读。"""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")

def main():
    stack = []
    instances = []
    path = []
    line_no = 0
    with KMX.open("r", encoding="utf-8", errors="replace") as f:
        for l in f:
            line_no += 1
            if l.startswith("INFO_TAG "):
                try:
                    tag = l.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    name = tag[7:]
                    stack.append({"name": name, "start": line_no, "paid": Counter(), "path": path + [name]})
                    path.append(name)
                elif tag.startswith("@exit:") and stack:
                    inst = stack.pop()
                    path.pop()
                    inst["end"] = line_no
                    instances.append(inst)
                    if stack:
                        parent = stack[-1]
                        for k, v in inst["paid"].items():
                            parent["paid"][k] += v
                continue
            if not l or l.startswith(SKIP_PREFIX):
                continue
            op = l.split()[0]
            if op in PAID and stack:
                stack[-1]["paid"][op] += 1
    if stack:
        print("UNCLOSED", [s["name"] for s in stack], file=sys.stderr)
    by_name = defaultdict(lambda: {"count": 0, "paid_total": 0, "paid_hist": Counter(), "sizes": []})
    for inst in instances:
        d = by_name[inst["name"]]
        d["count"] += 1
        tot = sum(inst["paid"].values())
        d["paid_total"] += tot
        d["sizes"].append(tot)
        d["paid_hist"].update(inst["paid"])
    out = {}
    for name, d in sorted(by_name.items(), key=lambda kv: -kv[1]["paid_total"]):
        sizes = d["sizes"]
        out[name] = {
            "count": d["count"], "paid_total": d["paid_total"],
            "CCX": d["paid_hist"].get("CCX", 0), "CSWAP": d["paid_hist"].get("CSWAP", 0),
            "CCZ": d["paid_hist"].get("CCZ", 0),
            "size_min": min(sizes), "size_max": max(sizes),
            "sizes_top": Counter(sizes).most_common(5),
        }
    top = sorted([i for i in instances if len(i["path"]) == 1], key=lambda i: i["start"])
    total = 0
    print(f"{'tag':34s} {'count':>6s} {'paid_tot':>9s} {'CCX':>8s} {'CSWAP':>7s} {'CCZ':>6s}  size[min..max] common")
    for name, d in sorted(out.items(), key=lambda kv: -kv[1]["paid_total"]):
        print(f"{name:34s} {d['count']:6d} {d['paid_total']:9d} {d['CCX']:8d} {d['CSWAP']:7d} {d['CCZ']:6d}  [{d['size_min']}..{d['size_max']}] {d['sizes_top']}")
    print("\nTOP-LEVEL:")
    for i in top:
        tot = sum(i["paid"].values())
        total += tot
        print(f"  {i['name']:20s} lines {i['start']:>10d}-{i['end']:<10d} paid {tot:7d}  CCX {i['paid'].get('CCX',0)} CSWAP {i['paid'].get('CSWAP',0)} CCZ {i['paid'].get('CCZ',0)}")
    print("TOTAL paid", total)
    outpath = Path("artifacts/20261112_branch_recovery/tag_census.json")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps({"by_name": out, "top_level": [{"name": i["name"], "start": i["start"], "end": i["end"], "paid": sum(i["paid"].values())} for i in top]}, indent=2))

if __name__ == "__main__":
    main()
