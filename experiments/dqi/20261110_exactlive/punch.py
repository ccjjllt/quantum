"""最小见证区间打孔真实代价上界（前向扫描到见证点）.

见证 [L,Rr]=[16391916,16391920]（exact_live 最小跨度 892 块）。
- 宿主：块内 live==892 处处成立（exact_live runs 定义），故无真死线可借（0 候选）。
- 重算：对 892 线中每一线 v，计算其在 L 点的值的扇入锥上界：
  上界取“自上次出生（R/HMR）以来触碰 v 的全部 op 数（总门数）及其中的 paid 门数
  （CCX/CCZ/CSWAP，与 q_live total_paid 口径一致）”。侧输入一律按持有计（块内全活，
  故可用），不展开侧输入锥——此为重算 v 在 L 点值的充分代价上界（回放自出生以来
  v 链全部触碰即可恢复，实际最小锥只会更小；sound 上界方向）。
  打孔穿越整块 [L,Rr] 的上界 = 块内读数(v) × 锥paid(v)（每次块内读前重算；出生恢复
  R/HMR 按免费计，R/HMR 本身 0 paid）。若 <887 则为可行切口。
- 另输出块内触碰明细与最便宜候选链。

只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

E_KMX = Path("/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT_DIR = Path("experiments/dqi/20261110_exactlive")
OUT = OUT_DIR / "punch.json"

L = 16391916
RR = 16391920
N_Q = 892
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}


def qtoks(parts, op):
    # 已知 op 固定位置取 q；未知则扫到 if 为止
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
    last_birth = [-1] * N_Q  # R/HMR op_idx；-1 表初始 |0>
    touch_since = [0] * N_Q
    paid_since = [0] * N_Q
    n_reads_total = [0] * N_Q  # 粗读（控制/CCZ/CZ/Z/HMR）计数，仅参考
    n_writes_total = [0] * N_Q  # X/CX-t/CCX-t/R/SWAP/CSWAP
    inblock_touch = Counter()
    inblock_reads = Counter()
    inblock_paid = Counter()
    inblock_ops = []
    op_idx = -1
    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if not l or l.startswith(SKIP_PREFIX):
                continue
            op_idx += 1
            if op_idx > RR:
                break
            parts = l.split()
            op = parts[0]
            if op in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                      "PUSH_CONDITION", "POP_CONDITION"):
                continue
            qs_raw = qtoks(parts, op)
            qs = [int(x[1:]) for x in qs_raw if x.startswith("q") and x[1:].isdigit()]
            if not qs:
                continue
            # 读写分类（同 q_cover/q_live）
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
            for k, q in enumerate(qs):
                if q < 0 or q >= N_Q:
                    continue
                is_read = (k in r) or (op in ("CSWAP", "SWAP"))
                # SWAP/CSWAP 读写皆计：读侧按 read 计入 uses
                if op_idx >= L and op_idx <= RR:
                    inblock_touch[q] += 1
                    if is_read:
                        inblock_reads[q] += 1
                    if op in PAID:
                        inblock_paid[q] += 1
                if op_idx < L:
                    # 出生前触碰累计（上界用）
                    touch_since[q] += 1
                    if op in PAID:
                        paid_since[q] += 1
                    if k in r:
                        n_reads_total[q] += 1
                    if k in w:
                        n_writes_total[q] += 1
                elif op_idx == L and False:
                    pass
            if op in ("R", "HMR") and op_idx < L:
                q = qs[0]
                if 0 <= q < N_Q:
                    last_birth[q] = op_idx
                    touch_since[q] = 0
                    paid_since[q] = 0
            if L <= op_idx <= RR:
                inblock_ops.append((op_idx, l[:160]))
    # L 点锥上界 = 出生以来触碰（若无出生则为自起点以来全部触碰）
    rows = []
    for q in range(N_Q):
        lb = last_birth[q]
        dist = L - lb if lb >= 0 else L + 1
        rows.append({"q": f"q{q}", "last_birth": lb, "dist_since_birth": dist,
                     "cone_touch_ub": touch_since[q], "cone_paid_ub": paid_since[q],
                     "reads_before_L": n_reads_total[q], "writes_before_L": n_writes_total[q],
                     "uses_in_block": inblock_touch.get(q, 0)})
    # 打孔整块上界：块内读数×锥paid。其中块内读数按触碰计（保守，写也计需恢复），
    # 锥 paid 上界 = 出生以来 paid + 块内 paid（回放出生到读点的全部 paid 触碰即可恢复，
    # 实际最小锥只会更小；sound 上界方向）。若 <887 则为可行切口。
    for d in rows:
        q = int(d["q"][1:])
        cone_paid = d["cone_paid_ub"] + inblock_paid.get(q, 0)
        d["cone_paid_ub_incl_block"] = cone_paid
        d["reads_in_block"] = inblock_reads.get(q, 0)
        d["uses_in_block"] = inblock_touch.get(q, 0)
        punch = d["reads_in_block"] * cone_paid
        # 块内零触碰但 L 前有触碰（持有穿越整块）：块后恢复一次，上界为 cone
        #（L 前零触碰的闲置 |0> 恢复免费，上式读 0 得 0，已一致）。
        if d["uses_in_block"] == 0 and (d["cone_touch_ub"] > 0 or d["cone_paid_ub"] > 0):
            punch = d["cone_paid_ub"]
        d["punch_paid_ub"] = punch
    rows_by_cost = sorted(rows, key=lambda d: (d["punch_paid_ub"], d["cone_paid_ub"], d["cone_touch_ub"]))
    out = {"L": L, "R": RR, "span": RR - L,
           "n_members": N_Q,
           "host_candidates": [],
           "host_note": "exact_live runs 定义块内 live_before==892 处处成立，故块内无真死线可借",
           "cheapest_10": rows_by_cost[:10],
           "most_expensive_5": sorted(rows, key=lambda d: -d["cone_paid_ub"])[:5],
           "table": sorted(rows, key=lambda d: int(d["q"][1:])),
           "inblock_ops": inblock_ops,
           "inblock_distinct": len(inblock_touch),
           }
    OUT.write_text(json.dumps(out) + "\n")
    print(f"L={L} R={RR} span={RR-L} distinct_inblock={len(inblock_touch)}")
    print("inblock ops:")
    for i, s in inblock_ops:
        print(f"  {i} {s}")
    print("cheapest 15 by uses*cone_paid:")
    for d in rows_by_cost[:15]:
        print(f"  {d['q']}: uses_in_block={d['uses_in_block']} cone_paid_ub={d['cone_paid_ub']} "
              f"cone_touch_ub={d['cone_touch_ub']} last_birth={d['last_birth']} punch_ub={d['punch_paid_ub']} "
              f"reads_before={d['reads_before_L']} writes_before={d['writes_before_L']}")
    # 块内被写线精确小链（人工核对窗口模式 R;CCX;CX;CX）
    print("window ancilla check (q22/q95/q143/q143 chain):")
    for q in [22, 95, 143, 18, 17, 84, 24]:
        d = rows[q]
        print(f"  q{q}: {d}")


if __name__ == "__main__":
    main()
