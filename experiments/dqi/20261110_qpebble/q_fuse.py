"""Q 熔接精查（pass 2）：短跨度线全时间线 + 全量死区 + 载体门控.

输入：artifacts/20261110_qpebble/q_live.json（短线名单、阶段边界）、
      pebble.json（top 跨度窗）。
全量重扫 e9.kmx 一遍：
  (a) 候选线（最短 8 线 + top 窗的 t 线）全触碰时间线（op 序号 + 读写角色码），
      定精确 birth（首写）/death（末读）；
  (b) 全量死区落盘 gaps.jsonl，供熔接拟合与 pebble 门控；
  (c) 对 top 跨度窗做死区载体门控（他线死区是否全覆盖窗）。
只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import bisect
import json
from collections import defaultdict
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
Q_LIVE = Path("artifacts/20261110_qpebble/q_live.json")
PEBBLE = Path("artifacts/20261110_qpebble/pebble.json")
OUT = Path("artifacts/20261110_qpebble/q_fuse.json")
GAPS = Path("artifacts/20261110_qpebble/gaps.jsonl")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
N_SHORT = 8


def qtoks(parts: list[str]) -> list[str]:
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def main() -> None:
    ql = json.loads(Q_LIVE.read_text())
    short_qs = [d["q"] for d in ql["shortest_20"][:N_SHORT]]
    peb = json.loads(PEBBLE.read_text()) if PEBBLE.exists() else {"top_spans_30": []}
    t_qs = set()
    for w in peb.get("top_spans_30", [])[:10]:
        lit = w["lit"].split()
        t_qs.add(lit[3])
    cand = sorted(set(short_qs) | t_qs, key=lambda x: int(x[1:]))
    candset = set(cand)
    print("candidates:", cand)

    stack: list[str] = []
    op_idx = 0
    timelines: dict[str, list] = {q: [] for q in cand}
    gap_open: dict[str, int] = {}
    gap_open_kind: dict[str, str] = {}
    gaps: list[tuple] = []

    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if l.startswith("INFO_TAG "):
                try:
                    tag = l.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                continue
            if not l or l.startswith(SKIP_PREFIX):
                continue
            i = op_idx
            op_idx += 1
            parts = l.split()
            op = parts[0]
            qs = qtoks(parts)
            if not qs:
                continue
            qset = set(qs)
            # (b) 全量死区（与 q_live.py 同谓词）
            if op == "HMR":
                q = qs[0]
                if q in gap_open:
                    del gap_open[q]
                    del gap_open_kind[q]
                gap_open[q] = i
                gap_open_kind[q] = "HMR"
            elif op == "R":
                q = qs[0]
                if q in gap_open:
                    gaps.append((q, gap_open[q], i, gap_open_kind[q], "R"))
                    del gap_open[q]
                    del gap_open_kind[q]
                gap_open[q] = i
                gap_open_kind[q] = "R"
            elif op in ("X", "CX", "CCX", "CSWAP", "SWAP", "CCX_CARRY"):
                if op == "X":
                    wset = {0}
                elif op == "CX":
                    wset = {1}
                elif op in ("CCX", "CCX_CARRY"):
                    wset = {2}
                else:
                    wset = set(range(len(qs)))
                for k, q in enumerate(qs):
                    if q in gap_open and (k in wset or op == "SWAP"):
                        gaps.append((q, gap_open[q], i, gap_open_kind[q], op))
                        del gap_open[q]
                        del gap_open_kind[q]
                    elif q in gap_open:
                        del gap_open[q]
                        del gap_open_kind[q]
            else:
                for q in qs:
                    if q in gap_open:
                        del gap_open[q]
                        del gap_open_kind[q]
            # (a) 候选线时间线
            hit = qset & candset
            if hit:
                if op == "HMR":
                    code = "K_hmr"
                elif op == "R":
                    code = "W_r"
                elif op == "X":
                    code = "W_x"
                elif op == "CX":
                    code = "W_cx" if qs[1] in hit else "r"
                elif op in ("CCX", "CCX_CARRY"):
                    code = "W_ccx" if qs[2] in hit else "r"
                elif op in ("CSWAP", "SWAP"):
                    code = "W_swap"
                else:
                    code = "r"
                for q in hit:
                    # 控制/目标角色细化（多候选同行时以该线为准重算）
                    c = code
                    if op == "CX" and qs[1] != q:
                        c = "r"
                    if op in ("CCX", "CCX_CARRY") and qs[2] != q:
                        c = "r"
                    timelines[q].append((i, c))

    total_ops = op_idx
    for q, s in gap_open.items():
        gaps.append((q, s, total_ops, gap_open_kind[q], "TAIL"))

    # 精确 birth/death：birth=首写（W_*），death=末读（含读；若末触碰是写且后无读，
    # 则 death=该写——值无人读，死于写处）
    fuse = []
    for q in cand:
        tl = timelines[q]
        writes = [i for (i, c) in tl if c.startswith("W")]
        birth = writes[0] if writes else (tl[0][0] if tl else -1)
        death = tl[-1][0] if tl else -1
        fuse.append({"q": q, "touches": len(tl), "birth": birth, "death": death,
                     "live_span": (death - birth) if death >= 0 else -1,
                     "n_writes": len(writes),
                     "first_events": tl[:12], "last_events": tl[-12:]})

    # (c) 门控：top 窗是否被他线死区全覆盖（host≠窗内三线任一；端 kind 非 SWAP）
    by_host: dict[str, list] = defaultdict(list)
    for (w, s, e, sk, ek) in gaps:
        by_host[w].append((s, e, ek))
    for v in by_host.values():
        v.sort()
    gated = []
    for w in peb.get("top_spans_30", [])[:30]:
        lit = w["lit"].split()
        wires = set(lit[1:4])
        p0, p1 = w["p0"], w["p1"]
        hosts = []
        for h, ivs in by_host.items():
            if h in wires:
                continue
            # 二分找覆盖 [p0,p1] 的区间
            k = bisect.bisect_right(ivs, (p0, 10**18, "")) - 1
            for kk in (k, k + 1):
                if 0 <= kk < len(ivs) and ivs[kk][0] <= p0 and ivs[kk][1] >= p1:
                    if ivs[kk][2] != "SWAP":
                        hosts.append([h, ivs[kk][0], ivs[kk][1], ivs[kk][2]])
                        break
            if len(hosts) >= 5:
                break
        gated.append({"lit": w["lit"], "p0": p0, "p1": p1, "span": w["span"],
                      "n_hosts": len(hosts), "hosts": hosts[:5]})

    with GAPS.open("w", encoding="utf-8") as gf:
        for (w, s, e, sk, ek) in gaps:
            gf.write(json.dumps([w, s, e, sk, ek]) + "\n")

    out = {"total_ops": total_ops, "n_gaps": len(gaps),
           "candidates": cand, "fuse": fuse, "gated_windows": gated}
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps({"total_ops": total_ops, "n_gaps": len(gaps),
                      "fuse": [{k: d[k] for k in ("q", "touches", "birth", "death", "live_span", "n_writes")} for d in fuse],
                      "gated": [{k: d[k] for k in ("lit", "span", "n_hosts")} for d in gated]}, indent=1))


if __name__ == "__main__":
    main()
