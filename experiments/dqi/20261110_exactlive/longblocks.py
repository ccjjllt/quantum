"""长块（span>1000，238 个）免费打孔普查：单遍前向到最大 RR.

对每长块报告 free punch（punch_ub==0）是否存在及最便宜 3 线。
punch_ub 定义同 blocks_check（reads_inblock*(paid_since+块paid)，持有穿越修正）。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

E_KMX = Path("/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT_DIR = Path("experiments/dqi/20261110_exactlive")
OUT = OUT_DIR / "longblocks.json"

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}
N_Q = 892


def qtoks(parts, op):
    if op in ("X", "R", "HMR", "Z"):
        return [parts[1]]
    if op in ("CX", "CZ", "SWAP"):
        return [parts[1], parts[2]]
    if op in ("CCX", "CCX_CARRY", "CCZ", "CSWAP"):
        return [parts[1], parts[2], parts[3]]
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def main() -> None:
    ex = json.load(open(OUT_DIR / "exact_live.json"))
    runs = sorted(ex["full_runs"])
    longs = [r for r in runs if r[1] - r[0] > 1000]
    print(f"long blocks: {len(longs)}", flush=True)
    max_rr = max(r[1] for r in longs)
    # per-block per-wire counters（稀疏 Counter）
    in_touch = [Counter() for _ in longs]
    in_read = [Counter() for _ in longs]
    in_paid = [Counter() for _ in longs]
    Ls = [r[0] for r in longs]
    RRs = [r[1] for r in longs]
    # 快照：L 处 last_birth/touch/paid
    snaps_lb = [None] * len(longs)
    snaps_ts = [None] * len(longs)
    snaps_ps = [None] * len(longs)
    # 双指针：blocks 有序，维护候选下标（L 未到 / 进行中）
    import bisect
    Ls_sorted = Ls  # runs 已排序，longs 保持有序
    ptr = 0  # 下一个 L
    active = set()  # 进行中块下标
    # 为 O(1) 判定 op 是否在某块内：块不重叠，用指针推进
    # 预处理：按 L 排序（已序）
    last_birth = [-1] * N_Q
    touch_since = [0] * N_Q
    paid_since = [0] * N_Q
    op_idx = -1
    li = 0  # longs 下标指针（按 L）
    # 进行中块：由于块不重叠，同时至多 1 个块包含当前 op（块互斥），用单指针即可
    cur = -1  # 当前所在块下标（若 op 在块内）
    # 为快照，需在 op_idx==L 时拷贝；用 li 推进
    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if not l or l.startswith(SKIP_PREFIX):
                continue
            op_idx += 1
            if op_idx > max_rr:
                break
            # 推进 li 到覆盖 op_idx 的块（或下一个 L）
            while li < len(longs) and op_idx > RRs[li]:
                li += 1
            # 快照：op_idx 恰为某块 L（可能多个块同 L？runs 互斥不重叠，L 唯一）
            # 用二分找 L==op_idx（块数少，直接查 li 附近）
            # 简化：若 op_idx 等于 longs[li] 的 L（li 未越界），快照
            if li < len(longs) and op_idx == Ls[li]:
                snaps_lb[li] = list(last_birth)
                snaps_ts[li] = list(touch_since)
                snaps_ps[li] = list(paid_since)
            parts = l.split()
            op = parts[0]
            if op in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                      "PUSH_CONDITION", "POP_CONDITION"):
                continue
            qs_raw = qtoks(parts, op)
            qs = [int(x[1:]) for x in qs_raw if x.startswith("q") and x[1:].isdigit()]
            if not qs:
                continue
            if op == "X":
                w = {0}; r = set()
            elif op == "CX":
                w = {1}; r = {0}
            elif op in ("CCX", "CCX_CARRY"):
                w = {2}; r = {0, 1}
            elif op in ("CSWAP", "SWAP"):
                w = set(range(len(qs))); r = set(range(len(qs)))
            elif op == "R":
                w = {0}; r = set()
            elif op == "HMR":
                w = set(); r = {0}
            else:
                w = set(); r = set(range(len(qs)))
            in_block = (li < len(longs) and Ls[li] <= op_idx <= RRs[li])
            # 注意：快照在 L 处取（L 之前状态），块内计数含 L 本身；全局触碰累计
            # 对 L 本身是否计入 touch_since？snap 已取 L 前状态，L 本身触碰不应计入
            # snap（已拷贝），全局累计含 L 无妨（snap 不受影响）。
            if in_block:
                for k, q in enumerate(qs):
                    if q < 0 or q >= N_Q:
                        continue
                    in_touch[li][q] += 1
                    if (k in r) or (op in ("CSWAP", "SWAP")):
                        in_read[li][q] += 1
                    if op in PAID:
                        in_paid[li][q] += 1
            for q in qs:
                if q < 0 or q >= N_Q:
                    continue
                touch_since[q] += 1
                if op in PAID:
                    paid_since[q] += 1
            if op in ("R", "HMR"):
                q = qs[0]
                if 0 <= q < N_Q:
                    last_birth[q] = op_idx
                    touch_since[q] = 0
                    paid_since[q] = 0
    res = []
    n_free = 0
    for i, (L, RR) in enumerate(longs):
        lb, ts, ps = snaps_lb[i], snaps_ts[i], snaps_ps[i]
        if lb is None:
            res.append({"L": L, "R": RR, "span": RR - L, "error": "no snapshot"})
            continue
        best = None
        n_zero = 0
        for q in range(N_Q):
            cone = ps[q] + in_paid[i].get(q, 0)
            punch = in_read[i].get(q, 0) * cone
            if in_touch[i].get(q, 0) == 0 and (ts[q] > 0 or ps[q] > 0):
                punch = ps[q]
            if punch == 0:
                n_zero += 1
            if best is None or punch < best[0]:
                best = (punch, cone, in_read[i].get(q, 0), ts[q], ps[q], q)
        if n_zero > 0:
            n_free += 1
        res.append({"L": L, "R": RR, "span": RR - L,
                    "distinct": len(in_touch[i]), "n_free_punch": n_zero,
                    "best": {"q": f"q{best[5]}", "punch_ub": best[0], "cone_paid": best[1],
                             "reads_inblock": best[2], "touch_since": best[3],
                             "paid_since": best[4]}})
    OUT.write_text(json.dumps({"n_long": len(longs), "n_free": n_free, "rows": res}) + "\n")
    print(f"long blocks free punch: {n_free}/{len(longs)}")
    for r in res[:10]:
        print(r)
    bad = [r for r in res if r.get("n_free_punch", 0) == 0]
    print(f"non-free long blocks: {len(bad)}")
    for r in bad[:10]:
        print(r)


if __name__ == "__main__":
    main()
