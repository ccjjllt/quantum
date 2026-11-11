"""多见证块闲置 |0> 抽查（单遍前向到最大 RR，一次收集多块）.

抽查块（exact_live runs 代表）：
- 最早块 runs[0]
- 中位块 runs[len//2]
- 最末块 runs[-1]（含 M_at）
- 最小跨度块 min_span
- 另含 M_at 的块（即最末块）已覆盖；再加 runs[100] 早段、runs[8000] 晚段。
对每块报告：跨度、块内 distinct、闲置 |0> 线数（出生后零触碰且块内零触碰，
cone_paid==0，可免费打孔），最便宜 5 线明细。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

E_KMX = Path("/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT_DIR = Path("experiments/dqi/20261110_exactlive")
OUT = OUT_DIR / "blocks_check.json"

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
    runs = ex["full_runs"]
    blocks = {
        "earliest": runs[0],
        "early100": runs[100],
        "minspan": ex["min_span_run"],
        "mid": runs[len(runs) // 2],
        "late8000": runs[8000],
        "latest": runs[-1],
    }
    print("blocks:", blocks)
    max_rr = max(r[1] for r in blocks.values())
    # per-block counters
    names = list(blocks.keys())
    idx_of = {n: i for i, n in enumerate(names)}
    Ls = {n: blocks[n][0] for n in names}
    RRs = {n: blocks[n][1] for n in names}
    in_touch = {n: Counter() for n in names}
    in_read = {n: Counter() for n in names}
    in_paid = {n: Counter() for n in names}
    in_ops_sample = {n: [] for n in names}

    last_birth = [-1] * N_Q
    touch_since = [0] * N_Q
    paid_since = [0] * N_Q
    snap = {}  # name -> (last_birth copy, touch copy, paid copy)

    op_idx = -1
    pending = set(names)
    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if not l or l.startswith(SKIP_PREFIX):
                continue
            op_idx += 1
            if op_idx > max_rr:
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
            # 快照：到达 L 时拷贝（L 之前的状态，即出生/触碰均不含 L 本身）
            for n in list(pending):
                if op_idx == Ls[n]:
                    snap[n] = (list(last_birth), list(touch_since), list(paid_since))
                    pending.discard(n)
            # 块内计数
            for n in names:
                if Ls[n] <= op_idx <= RRs[n]:
                    for k, q in enumerate(qs):
                        if q < 0 or q >= N_Q:
                            continue
                        in_touch[n][q] += 1
                        is_read = (k in r) or (op in ("CSWAP", "SWAP"))
                        if is_read:
                            in_read[n][q] += 1
                        if op in PAID:
                            in_paid[n][q] += 1
                    if len(in_ops_sample[n]) < 8:
                        in_ops_sample[n].append((op_idx, l[:120]))
            # 全局出生/触碰（用于快照；块内 op 也正常计入全局，但快照已在 L 处取，
            # 故块内计数不影响快照；出生在块内的线，其 snap 出生为块前，需注意：
            # 若线出生在块内（R/HMR 在 [L,RR]），则其在 L 点值并非 |0>（出生在后），
            # 闲置判定需排除此类（以上 touch_since 快照为 L 前状态，正确）。
            for k, q in enumerate(qs):
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
    res = {}
    for n in names:
        L, RR = blocks[n]
        lb, ts, ps = snap[n]
        free_idle = []
        for q in range(N_Q):
            if ts[q] == 0 and ps[q] == 0 and in_touch[n].get(q, 0) == 0:
                # 出生后零触碰（L 前）且块内零触碰：在块内全程 |0> 闲置，可免费打孔
                free_idle.append(q)
        # 最便宜 5（含块内读×锥）：读为 0 的免费线 punch=0；否则 reads*(ps+块paid)
        costs = []
        for q in range(N_Q):
            cone = ps[q] + in_paid[n].get(q, 0)
            punch = in_read[n].get(q, 0) * cone
            # 块内零触碰但块后仍需恢复：若 ts==0 且块内零触碰，恢复免费（R），punch 应为 0
            # （上式读 0 得 0，已一致）；若 ts>0 且块内零触碰（持有穿越），恢复需 cone，
            # 上式得 0 会低估——修正为 cone（块后恢复一次）。
            if in_touch[n].get(q, 0) == 0 and (ts[q] > 0 or ps[q] > 0):
                punch = ps[q]  # 持有穿越整块：块后恢复一次（上界）
            costs.append((punch, cone, in_read[n].get(q, 0), ts[q], ps[q], lb[q], q))
        costs.sort()
        res[n] = {"L": L, "R": RR, "span": RR - L,
                  "distinct_inblock": len(in_touch[n]),
                  "n_free_idle": len(free_idle),
                  "free_idle_sample": free_idle[:20],
                  "cheapest_5": [{"q": f"q{c[6]}", "punch_ub": c[0], "cone_paid": c[1],
                                  "reads_inblock": c[2], "touch_since": c[3],
                                  "paid_since": c[4], "last_birth": c[5]} for c in costs[:5]],
                  "ops_sample": in_ops_sample[n]}
    OUT.write_text(json.dumps(res) + "\n")
    for n in names:
        r = res[n]
        print(f"{n} [{r['L']},{r['R']}] span={r['span']} distinct={r['distinct_inblock']} free_idle={r['n_free_idle']} sample={r['free_idle_sample'][:10]}")
        for c in r["cheapest_5"]:
            print(f"   {c}")
        print(f"   ops: {r['ops_sample'][:5]}")


if __name__ == "__main__":
    main()
