"""每个 top-level stage 内的 sub-tag 序列与门类计数。只读。"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")

def main():
    stack = []      # (name, paid counter)
    top = None
    seq = []        # (stage, subname, paid)
    stage_paid = defaultdict(Counter)
    stage_ops = defaultdict(Counter)
    cur_sub = None
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
                    if top is None:
                        top = name
                    elif len(stack) == 1:
                        cur_sub = {"name": name, "start": line_no, "paid": Counter()}
                    stack.append(name)
                elif tag.startswith("@exit:") and stack:
                    name = stack.pop()
                    if len(stack) == 1 and cur_sub is not None:
                        cur_sub["end"] = line_no
                        seq.append((top, cur_sub["name"], sum(cur_sub["paid"].values())))
                        cur_sub = None
                    elif not stack:
                        top = None
                continue
            if not l or l.startswith(SKIP_PREFIX):
                continue
            op = l.split()[0]
            stage_ops[top][op] += 1
            if op in PAID:
                stage_paid[top][op] += 1
                if cur_sub is not None:
                    cur_sub["paid"][op] += 1
    for st in ("extract","synthesis","convert","scan","unconvert","unsynthesis","unextract","mask_projection","initial"):
        print(f"=== {st}: paid={sum(stage_paid[st].values())} {dict(stage_paid[st])}")
        print("    ops:", dict(sorted(stage_ops[st].items(), key=lambda kv:-kv[1])[:14]))
        subs = [s for s in seq if s[0]==st]
        if subs:
            # compress consecutive repeats
            print(f"    subtags ({len(subs)}):")
            i=0
            while i < len(subs):
                j=i
                while j+1<len(subs) and subs[j+1][1]==subs[i][1] and subs[j+1][2]==subs[i][2]:
                    j+=1
                n=j-i+1
                print(f"      {subs[i][1]:28s} x{n:<4d} paid={subs[i][2]}")
                i=j+1

if __name__ == "__main__":
    main()
