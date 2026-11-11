"""Q-1 判决性覆盖分析（前向聚合）：真活区间重叠扫描.

真活区间（保守上界）：[首写，末读]；无读线视为空（永不持有活值）。
  写：X / CX目标 / CCX目标 / R / CSWAP / SWAP（交换读写皆计）；
  读：CCZ/CZ/Z/控制端/H/HMR（测量）/未知含q op（保守按读）。
max重叠 M≤891 ⟹ 区间图 891-可着色 ⟹ 零paid重命名 Q-1（充分条件，sound 方向）；
M=892 ⟹ 输出团见证区间/成员 + 各成员被团区间穿越数 C（打孔下界 ≥2C paid，
与 887 break-even 比）。
另输出 read_bins（打孔精确定价用）与空活线（潜在零成本消除）。
只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT = Path("artifacts/20261110_qpebble/q_cover.json")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
BINW = 500_000


def qtoks(parts: list[str]) -> list[str]:
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def main() -> None:
    first_write: dict[str, int] = {}
    last_read: dict[str, int] = {}
    read_bins: dict[str, Counter] = {}
    op_idx = 0
    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if l.startswith("INFO_TAG ") or not l or l.startswith(SKIP_PREFIX):
                continue
            i = op_idx
            op_idx += 1
            parts = l.split()
            op = parts[0]
            qs = qtoks(parts)
            if not qs:
                continue
            if op == "X":
                w = {0}
                r = set()
            elif op == "CX":
                w = {1}
                r = {0}
            elif op in ("CCX", "CCX_CARRY"):
                w = {2}
                r = {0, 1}
            elif op in ("CSWAP", "SWAP"):
                w = set(range(len(qs)))
                r = set(range(len(qs)))
            elif op == "R":
                w = {0}
                r = set()
            else:  # CCZ/CZ/Z/HMR/未知：全按读（sound 方向）
                w = set()
                r = set(range(len(qs)))
            for k, q in enumerate(qs):
                if k in w and q not in first_write:
                    first_write[q] = i
                if k in r:
                    last_read[q] = i
                    rb = read_bins.get(q)
                    if rb is None:
                        rb = read_bins[q] = Counter()
                    rb[i // BINW] += 1
            # CSWAP/SWAP 写端已在 w 中；X/CX/CCX/R 写端首写已记。
            # 纯写 op 的目标若同时是读？不计（上界方向取小 live？不——
            # 首写取小、末读取大才是上界；写端不计入读，live 可能偏小？
            # 写后若无人读则值死，[首写,末读] 仍是上界（末读<该写则区间为空/更小，
            # sound：真活值必在某读处存活，真区间 ⊆ [首写,末读] ✓）。

    wires = set(first_write) | set(last_read)
    intervals = []
    empty = []
    for q in wires:
        fw = first_write.get(q, 10**18)
        lr = last_read.get(q, -1)
        if lr < fw:
            empty.append(q)
        else:
            intervals.append((fw, lr, q))
    # 扫描 max 重叠
    events: list[tuple[int, int]] = []
    for (fw, lr, q) in intervals:
        events.append((fw, 1))
        events.append((lr + 1, -1))
    events.sort()
    cur = 0
    M = 0
    M_at = -1
    for pos, d in events:
        cur += d
        if cur > M:
            M = cur
            M_at = pos
    # 团区间（overlap==M 的极大范围，仅 M==892 时精细输出；否则给 M 与见证点）
    # 二次扫描得覆盖成员（892 区间全量判定， cheap）
    clique_ranges = []
    if M == 892:
        # 事件扫出 overlap==892 的极大区间
        cur = 0
        start = -1
        prev = -1
        for pos, d in events:
            if cur == 892 and pos != prev and start >= 0:
                pass
            # 先结算 [prev, pos)：若 cur==892 则记录
            if prev >= 0 and pos > prev and cur == 892:
                if clique_ranges and clique_ranges[-1][1] == prev:
                    clique_ranges[-1][1] = pos
                else:
                    clique_ranges.append([prev, pos])
            cur += d
            prev = pos
    members = []
    punch = []
    if M == 892 and M_at >= 0:
        members = sorted([q for (fw, lr, q) in intervals if fw <= M_at <= lr],
                         key=lambda x: int(x[1:]))
        for q in members:
            fw = first_write[q]
            lr = last_read[q]
            c = sum(1 for (a, b) in clique_ranges if not (lr < a or fw >= b))
            punch.append({"q": q, "clique_ranges_crossed": c,
                          "punch_lower_paid": 2 * c,
                          "feasible_by_break_even": 2 * c < 887})
    out = {
        "total_ops": op_idx,
        "n_wires": len(wires),
        "n_nonempty_intervals": len(intervals),
        "n_empty_live": len(empty),
        "empty_wires": sorted(empty, key=lambda x: int(x[1:])),
        "M_coarse": M,
        "M_at": M_at,
        "n_clique_ranges": len(clique_ranges),
        "clique_ranges": clique_ranges[:20],
        "clique_members_at_witness": members,
        "punch_bounds": punch,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("punch_bounds", "clique_members_at_witness")}, indent=1))
    print("members:", len(members), members[:10])
    feas = [p for p in punch if p["feasible_by_break_even"]]
    print("members with 2C<887:", len(feas), [p["q"] for p in feas[:10]])


if __name__ == "__main__":
    main()
