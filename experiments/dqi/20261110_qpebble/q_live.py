"""Q 高水位 + 死区盘点（pass 1，流式单遍读 e9.kmx）.

方法（occ/活性）：
- 按 op 序号（跳过 APPEND/REGISTER/INFO_TAG/SEMANTIC/ANNOTATION 空行，与
  stage_census 口径一致）遍历全部 ops。
- 读写分类（保守：未知含 q 操作数 op 按读处理，只漏记、不误记）：
  写：X(q) / CX(t) / CCX(t) / CSWAP(三线) / R(q, 先闭后开)；
  杀死旧值并开启死区：HMR(q) / R(q)；
  读（使已开死区作废）：其余一切含 q 触碰（CCZ/CZ/H/CX-控制/CCX-控制/...）。
- 死区 = (kill_pos, 下次写_pos) 零触碰区间，全部记录（熔接候选）；
  另记 head [0, 首写)、tail (末触碰, T] 死区。
- R 分段只用于分段计数（R 分段平铺全线，occupancy 恒 892，无信息量，
  故高水位用死区反推 + 首末跨度 + bin 画像）。
- 输出供 q_fuse.py（短线精查）与 pebble.py（unextract 交换表）复用。

只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT = Path("artifacts/20261110_qpebble/q_live.json")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
BINW = 500_000

READ_OPS = frozenset({
    "CCZ", "CZ", "H", "Z", "Y", "S", "T", "RX", "RY", "RZ",
    "PUSH_CONDITION", "POP_CONDITION",
})


def classify(op: str, qs: list[str]):
    """返回 (kind, write_idx_set, read_idx_set)。
    kind ∈ {"write", "read", "killrk"}:
      write: 含写（含 CSWAP 全写；HMR/R 另行处理）；
      read: 纯读/未知；
      killrk: R（先闭死区再开新死区）；HMR 由调用方处理。
    """
    if op == "X":
        return ("write", {0}, set())
    if op == "CX":
        return ("write", {1}, {0})
    if op == "CCX":
        return ("write", {2}, {0, 1})
    if op == "CSWAP":
        return ("write", {0, 1, 2}, set())
    if op == "SWAP":
        # 交换：结束死区（记 end_kind=SWAP 供人工复核伙伴线），死后不另开死区
        return ("swap", {0, 1}, set())
    if op == "HMR":
        return ("hmr", set(), set(range(len(qs))))
    if op == "R":
        return ("reset", {0}, set())
    if op in ("CCX_CARRY",):
        return ("write", {2}, {0, 1})
    return ("read", set(), set(range(len(qs))))


def qtoks(parts: list[str]) -> list[str]:
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def main() -> None:
    stack: list[str] = []
    stage_enter_op: dict[str, int] = {}
    stage_exit_op: dict[str, int] = {}
    op_idx = 0  # 0-based op 序号
    max_q = -1

    first: dict[str, int] = {}
    last: dict[str, int] = {}
    cnt: Counter = Counter()
    n_hmr: Counter = Counter()
    n_r: Counter = Counter()
    stage_first: dict[str, dict[str, int]] = {}
    stage_last: dict[str, dict[str, int]] = {}
    bins_touch: dict[str, Counter] = {}
    bin_paid: Counter = Counter()
    bin_distinct: dict[int, set] = {}
    bin_stage: dict[int, Counter] = {}
    total_paid = 0

    gap_open: dict[str, int] = {}       # wire -> kill op_idx
    gap_open_kind: dict[str, str] = {}  # HMR/R
    gaps: list[tuple] = []              # (wire, start, end, start_kind, end_kind)
    unknown_ops: Counter = Counter()

    def touch_wire(q: str, i: int, stage: str):
        nonlocal max_q
        if q not in first:
            first[q] = i
        last[q] = i
        cnt[q] += 1
        b = i // BINW
        bc = bins_touch.get(q)
        if bc is None:
            bc = bins_touch[q] = Counter()
        bc[b] += 1
        s = bin_distinct.get(b)
        if s is None:
            s = bin_distinct[b] = set()
        s.add(q)
        sf = stage_first.get(stage)
        if sf is None:
            sf = stage_first[stage] = {}
        if q not in sf:
            sf[q] = i
        sl = stage_last.get(stage)
        if sl is None:
            sl = stage_last[stage] = {}
        sl[q] = i

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
                    if len(stack) == 1:
                        stage_enter_op[tag[7:]] = op_idx
                elif tag.startswith("@exit:") and stack:
                    if len(stack) == 1:
                        stage_exit_op[stack[-1]] = op_idx
                    stack.pop()
                continue
            if not l or l.startswith(SKIP_PREFIX):
                continue
            stage = stack[0] if stack else "header"
            i = op_idx
            op_idx += 1
            parts = l.split()
            op = parts[0]
            if op in ("CCX", "CCZ", "CSWAP", "CCX_CARRY"):
                total_paid += 1
                bin_paid[i // BINW] += 1
            bin_stage.setdefault(i // BINW, Counter())[stage] += 1
            qs = qtoks(parts)
            if not qs:
                if op not in READ_OPS and op not in (
                    "X", "CX", "CCX", "CSWAP", "SWAP", "HMR", "R", "CCX_CARRY",
                    "BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                    "PUSH_CONDITION", "POP_CONDITION",
                ):
                    unknown_ops[op] += 1
                continue
            kind, wset, rset = classify(op, qs)
            if kind == "read" and op not in READ_OPS:
                unknown_ops[op] += 1
            # 先登记触碰（head 死区需要首写位置；R/HMR 本身也是触碰）
            for q in qs:
                touch_wire(q, i, stage)
            if q := max((int(x[1:]) for x in qs), default=-1):
                if q > max_q:
                    max_q = q
            if kind == "hmr":
                q = qs[0]
                n_hmr[q] += 1
                if q in gap_open:
                    # HMR 读当前值：已开死区作废（保守），再开新死区
                    del gap_open[q]
                    del gap_open_kind[q]
                gap_open[q] = i
                gap_open_kind[q] = "HMR"
            elif kind == "reset":
                q = qs[0]
                n_r[q] += 1
                if q in gap_open:
                    gaps.append((q, gap_open[q], i, gap_open_kind[q], "R"))
                    del gap_open[q]
                    del gap_open_kind[q]
                gap_open[q] = i
                gap_open_kind[q] = "R"
            elif kind in ("write", "swap"):
                for k, q in enumerate(qs):
                    if k in wset:
                        if q in gap_open:
                            gaps.append((q, gap_open[q], i, gap_open_kind[q], op))
                            del gap_open[q]
                            del gap_open_kind[q]
                    else:  # 读端（CX/CCX 控制）
                        if q in gap_open:
                            del gap_open[q]
                            del gap_open_kind[q]
            else:  # read：作废所涉线死区
                for q in qs:
                    if q in gap_open:
                        del gap_open[q]
                        del gap_open_kind[q]

    total_ops = op_idx
    # tail 死区：仍开着的死区延续到末尾（零触碰到结尾）
    for q, s in gap_open.items():
        gaps.append((q, s, total_ops, gap_open_kind[q], "TAIL"))
    # head 死区：[0, 首触碰) —— 首触碰若是写则全死，若是读则值无关紧要仍可死？
    # 保守：只记首触碰本身（head 本质是 |0> 未用窗，记作窗供参考，不作熔接依据）
    wires = sorted(first, key=lambda x: int(x[1:]))

    wire_stats = []
    for q in wires:
        wire_stats.append({
            "q": q,
            "qi": int(q[1:]),
            "first": first[q],
            "last": last[q],
            "span": last[q] - first[q],
            "touches": cnt[q],
            "n_hmr": n_hmr.get(q, 0),
            "n_r": n_r.get(q, 0),
        })
    by_span = sorted(wire_stats, key=lambda d: d["span"])
    gap_lens = sorted(
        ((e - s, w, s, e, sk, ek) for (w, s, e, sk, ek) in gaps),
        reverse=True,
    )
    out = {
        "e9_kmx": str(E_KMX),
        "total_ops": total_ops,
        "total_paid": total_paid,
        "n_qubits_touched": len(wires),
        "max_q_index": max_q,
        "stage_enter_op": stage_enter_op,
        "stage_exit_op": stage_exit_op,
        "bin_width": BINW,
        "n_bins": (total_ops + BINW - 1) // BINW,
        "bin_paid": {str(k): v for k, v in sorted(bin_paid.items())},
        "bin_distinct_count": {str(k): len(v) for k, v in sorted(bin_distinct.items())},
        "bin_top_stage": {str(k): c.most_common(1)[0] for k, c in sorted(bin_stage.items())},
        "wire_stats": wire_stats,
        "shortest_20": [
            {k: d[k] for k in ("q", "first", "last", "span", "touches", "n_hmr", "n_r")}
            for d in by_span[:20]
        ],
        "longest_5": [
            {k: d[k] for k in ("q", "first", "last", "span", "touches", "n_hmr", "n_r")}
            for d in by_span[-5:]
        ],
        "n_gaps": len(gaps),
        "top_gaps_30": [
            {"wire": w, "start": s, "end": e, "len": L, "start_kind": sk, "end_kind": ek}
            for (L, w, s, e, sk, ek) in gap_lens[:30]
        ],
        "gap_len_hist": Counter(min(999999999, L) // 1000 for (L, *_r) in gap_lens[:0]) or {},
        "unknown_ops": dict(unknown_ops),
    }
    # 死区长度分布（全量，分桶）
    buckets: Counter = Counter()
    for (L, *_r) in gap_lens:
        buckets[L // 1000] += 1
    out["gap_len_buckets_k"] = {str(k): v for k, v in sorted(buckets.items())}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out) + "\n", encoding="utf-8")
    print(json.dumps({
        "total_ops": total_ops, "total_paid": total_paid,
        "n_qubits": len(wires), "max_q": max_q,
        "n_gaps": len(gaps),
        "shortest_5": out["shortest_20"][:5],
        "top_gaps_5": out["top_gaps_30"][:5],
        "unknown_ops": dict(unknown_ops),
        "stage_enter_op": stage_enter_op,
    }, indent=1))


if __name__ == "__main__":
    main()
