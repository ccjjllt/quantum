"""DQI 精确后向活性（流式单遍逆序）：真活集合 dataflow.

语义（与 q_cover.py 读写一致，精确到操作级）：
- 活集 = 其当前值未来仍会被读的 q 线集合；终点 live-out = 空（终态垃圾可弃，
  尾部为 CX + 经典 BIT，无末端观测；此假设对 Q-1 是最有利的——若此下 M=892，
  则任何 live-out 下皆不可 Q-1）。
- 逆向 transfer（live = after 状态，求 before）：
  X q            : before = after（可逆，t_before=t_after；计数不变）→ 跳过
  CX c t         : t_before=t_after；c_before=c_after|t_after（t 活才需 c）
  CCX c0 c1 t    : t 保留；t 活则 +=c0,c1
  SWAP a b       : 置换成员（计数不变）
  CSWAP c a b    : a/b 任一活 → before 需 {c,a,b} 全活；否则不变
  R q (reset)    : before = after - {q}（唯一可降计数的 op；新 |0> 与旧值无关）
  HMR q b        : before = after ∪ {q}（测量读旧值 + reset；保守设测量结果恒被用）
  CZ/CCZ/Z/未知读: before = after ∪ {全部 q}（相位/未知按读，无 kill）
  条件 CX/CZ/Z (if b)：条件为假则空操作，故 kill 不成立；但本电路 kill 仅 R（无条件），
    CX 本就不降计数，故条件/无条件 transfer 相同（纯加）。实现上统一按上表。
  BIT_*/NEG/PUSH/POP：无 q，计入 op 序号但活集不变。
- 桶：前向 op 序号（跳过 APPEND/REGISTER/INFO_TAG/SEMANTIC/ANNOTATION 空行，
  与 q_cover/q_live 口径一致）按 500k 分桶，记每桶真活 max；全局 M_exact 与见证点。
- 流式逆序：二进制分块从尾向前，不全载入；活集用 Python int 位集（892 位），
  计数增量维护（避免每步 popcount）。

只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

E_KMX = Path("/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT_DIR = Path("experiments/dqi/20261110_exactlive")
OUT_JSON = OUT_DIR / "exact_live.json"
OUT_BINS = OUT_DIR / "buckets.csv"

TOTAL = 58269417  # 前向 counted ops（q_cover/census 一致）；逆序后校验
BINW = 500_000
N_Q = 892

SKIP_PREFIX = (b"APPEND", b"REGISTER", b"INFO_TAG", b"SEMANTIC", b"ANNOTATION")


def main() -> None:
    masks = [1 << i for i in range(N_Q)]
    n_bins = (TOTAL + BINW - 1) // BINW
    bucket_max = [0] * n_bins

    t0 = time.time()
    size = E_KMX.stat().st_size
    print(f"kmx size={size} total_assumed={TOTAL} nbins={n_bins}", flush=True)

    live = 0
    live_n = 0
    max_live = 0
    max_at = -1
    rev_count = 0  # 已处理的 counted ops 数
    # 892 runs（前向序号）：逆序遇到，先见大端
    runs: list[list[int]] = []
    cur_end = -1  # 当前 892 块的大端（前向序号），-1 表不在块内

    CHUNK = 8 * 1024 * 1024
    pos = size
    leftover = b""
    # 本地绑定加速
    m = masks

    # 为避免每行 Python 分支爆炸，按首字节快速分流
    while pos > 0:
        n = CHUNK if pos >= CHUNK else pos
        pos -= n
        with E_KMX.open("rb") as f:
            f.seek(pos)
            data = f.read(n)
        buf = data + leftover
        # 切行；首段为跨块残行留待下轮
        lines = buf.split(b"\n")
        if pos > 0:
            leftover = lines[0]
            work = lines[1:]
        else:
            leftover = b""
            work = lines
        # 逆序处理
        for raw in reversed(work):
            # 去行尾 \r（kmx 应无，但保险）；空行跳过（不计数）
            if not raw or raw == b"\r":
                continue
            if raw.endswith(b"\r"):
                raw = raw[:-1]
                if not raw:
                    continue
            c0 = raw[0:1]
            # 快跳：Axxx / Ixxx / SExxx
            if c0 == b"A" or c0 == b"I":
                # APPEND*/ANNOTATION*/INFO_TAG* 均跳过（不计数）
                continue
            if c0 == b"S":
                if raw.startswith(b"SEMANTIC"):
                    continue
                # 否则 SWAP（S 开头仅 SWAP；SEMANTIC 已除）
                # fallthrough 到通用解析（op=SWAP）
                pass
            elif c0 == b"R":
                if raw.startswith(b"REGISTER"):
                    continue
                # 否则 R（R 开头仅 R；REGISTER 已除）
                pass
            # 计数 op（所有非 skip 行均计数，与前向一致）
            # 先判定无 q 的经典 op：BIT_*/NEG/PUSH_/POP_（活集不变，仅记桶）
            # 注意：ANNOTATION/APPEND/INFO_TAG/SEMANTIC/REGISTER 已跳过不计数
            if c0 == b"B" or c0 == b"N" or c0 == b"P":
                # BIT_STORE0/BIT_STORE1/BIT_INVERT/NEG/PUSH_CONDITION/POP_CONDITION
                i = TOTAL - 1 - rev_count
                rev_count += 1
                b = i // BINW
                if live_n > bucket_max[b]:
                    bucket_max[b] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                # 892 run 跟踪（live 不变）
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            # 含 q 的 op：split（C 实现）后按 op 分发
            parts = raw.split(b" ")
            # parts[0] 为 op；可能含空串（多空格？kmx 单空格为主，仍过滤？）
            # 为速度，假设单空格；若首 token 为空则回退
            op = parts[0]
            if not op:
                # 罕见：前导空格，过滤空串
                parts = [p for p in parts if p]
                if not parts:
                    continue
                op = parts[0]
            # X：活集不变，仅计数+桶
            if op == b"X":
                i = TOTAL - 1 - rev_count
                rev_count += 1
                b = i // BINW
                if live_n > bucket_max[b]:
                    bucket_max[b] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"CX":
                # parts: CX qc qt [if ...]
                c = int(parts[1][1:])
                t = int(parts[2][1:])
                if live & m[t]:
                    if not (live & m[c]):
                        live |= m[c]
                        live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                b = i // BINW
                if live_n > bucket_max[b]:
                    bucket_max[b] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"CCX" or op == b"CCX_CARRY":
                c0 = int(parts[1][1:])
                c1 = int(parts[2][1:])
                t = int(parts[3][1:])
                if live & m[t]:
                    if not (live & m[c0]):
                        live |= m[c0]
                        live_n += 1
                    if not (live & m[c1]):
                        live |= m[c1]
                        live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                b = i // BINW
                if live_n > bucket_max[b]:
                    bucket_max[b] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"R":
                q = int(parts[1][1:])
                mm = m[q]
                if live & mm:
                    live ^= mm
                    live_n -= 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                b = i // BINW
                if live_n > bucket_max[b]:
                    bucket_max[b] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"HMR":
                q = int(parts[1][1:])
                mm = m[q]
                if not (live & mm):
                    live |= mm
                    live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                b = i // BINW
                if live_n > bucket_max[b]:
                    bucket_max[b] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"SWAP":
                a = int(parts[1][1:])
                bq = int(parts[2][1:])
                ha = 1 if (live & m[a]) else 0
                hb = 1 if (live & m[bq]) else 0
                if ha != hb:
                    live ^= (m[a] | m[bq])
                i = TOTAL - 1 - rev_count
                rev_count += 1
                bb = i // BINW
                if live_n > bucket_max[bb]:
                    bucket_max[bb] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"CSWAP":
                c = int(parts[1][1:])
                a = int(parts[2][1:])
                bq = int(parts[3][1:])
                if (live & m[a]) or (live & m[bq]):
                    if not (live & m[c]):
                        live |= m[c]
                        live_n += 1
                    if not (live & m[a]):
                        live |= m[a]
                        live_n += 1
                    if not (live & m[bq]):
                        live |= m[bq]
                        live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                bb = i // BINW
                if live_n > bucket_max[bb]:
                    bucket_max[bb] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"CZ":
                a = int(parts[1][1:])
                bq = int(parts[2][1:])
                if not (live & m[a]):
                    live |= m[a]
                    live_n += 1
                if not (live & m[bq]):
                    live |= m[bq]
                    live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                bb = i // BINW
                if live_n > bucket_max[bb]:
                    bucket_max[bb] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"Z":
                q = int(parts[1][1:])
                mm = m[q]
                if not (live & mm):
                    live |= mm
                    live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                bb = i // BINW
                if live_n > bucket_max[bb]:
                    bucket_max[bb] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            if op == b"CCZ":
                a = int(parts[1][1:])
                bq = int(parts[2][1:])
                cq = int(parts[3][1:])
                if not (live & m[a]):
                    live |= m[a]
                    live_n += 1
                if not (live & m[bq]):
                    live |= m[bq]
                    live_n += 1
                if not (live & m[cq]):
                    live |= m[cq]
                    live_n += 1
                i = TOTAL - 1 - rev_count
                rev_count += 1
                bb = i // BINW
                if live_n > bucket_max[bb]:
                    bucket_max[bb] = live_n
                    if live_n > max_live:
                        max_live = live_n
                        max_at = i
                if live_n == N_Q:
                    if cur_end < 0:
                        cur_end = i
                else:
                    if cur_end >= 0:
                        runs.append([i + 1, cur_end])
                        cur_end = -1
                continue
            # 未知含 q op：保守按全读
            qs = []
            for p in parts[1:]:
                if p == b"if":
                    break
                if p[:1] == b"q":
                    try:
                        qs.append(int(p[1:]))
                    except ValueError:
                        pass
            for q in qs:
                if 0 <= q < N_Q:
                    if not (live & m[q]):
                        live |= m[q]
                        live_n += 1
            i = TOTAL - 1 - rev_count
            rev_count += 1
            bb = i // BINW
            if live_n > bucket_max[bb]:
                bucket_max[bb] = live_n
                if live_n > max_live:
                    max_live = live_n
                    max_at = i
            if live_n == N_Q:
                if cur_end < 0:
                    cur_end = i
            else:
                if cur_end >= 0:
                    runs.append([i + 1, cur_end])
                    cur_end = -1
        if rev_count % 10000000 == 0:
            print(f"  rev {rev_count} live={live_n} max={max_live}@{max_at} t={time.time()-t0:.1f}s", flush=True)
    if cur_end >= 0:
        runs.append([0, cur_end])
    # leftover 首行（文件头）：若为 counted op 需处理？文件头为 APPEND/REGISTER/INFO_TAG，
    # 均为 skip；但保险起见若 leftover 非空非 skip 则告警（应不影响总数）。
    if leftover.strip():
        lb = leftover.strip()
        if not (lb.startswith(SKIP_PREFIX) or lb == b""):
            print(f"WARN leftover head: {lb[:80]!r}", flush=True)
    t1 = time.time()
    print(f"done rev_count={rev_count} (assumed {TOTAL}) live_end={live_n} max={max_live}@{max_at} t={t1-t0:.1f}s", flush=True)
    runs.sort()
    # 最小跨度 892 块
    min_run = None
    if runs:
        min_run = min(runs, key=lambda r: (r[1] - r[0], r[0]))
    out = {
        "e9_kmx": str(E_KMX),
        "total_assumed": TOTAL,
        "rev_count": rev_count,
        "count_match": rev_count == TOTAL,
        "M_exact": max_live,
        "M_at": max_at,
        "n_bins": n_bins,
        "bin_width": BINW,
        "bucket_max": bucket_max,
        "n_full_runs": len(runs),
        "full_runs": runs,
        "min_span_run": min_run,
        "live_at_start": live_n,
        "seconds": round(t1 - t0, 1),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out) + "\n")
    with OUT_BINS.open("w") as f:
        f.write("bin,start_op,end_op,live_max\n")
        for bi, vm in enumerate(bucket_max):
            f.write(f"{bi},{bi*BINW},{min((bi+1)*BINW-1, TOTAL-1)},{vm}\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("bucket_max", "full_runs")}, indent=1))
    print("buckets:", bucket_max)


if __name__ == "__main__":
    main()
