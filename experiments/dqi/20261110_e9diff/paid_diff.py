"""e9f54be3 vs 4432ec5f 付费门对齐差分 + 小窗口形态分类 + e9 残余扫描.

输入：/tmp 下两份 kmx（stage_census.py 已落盘）。
方法：
  1. 流式抽取付费门序列 (CCX/CCZ/CSWAP/CCX_CARRY)，记录 kmx 全局行号、阶段、字节偏移。
  2. 按阶段对付费序列做贪心对齐（lookahead 重同步，编辑量小，O(N)），定位差分 hunk。
  3. 每个 hunk 回跳 kmx 取全门类上下文（±25 行，含 CX/CZ/HMR/R/CONDITION），做形态启发式分类：
     - 测量窥孔（Kirill 谱系）：被删 CCX 目标线在 ±15 行内有 HMR/R，且新侧出现条件 CZ/HMR；
     - 字面复用（Ozer/Isabe 谱系）：被删 CCX(a,b,t) 在窗口内有字面双胞胎（控制可交换）；
     - 规范对匹配（Syed V10 谱系候选）：同目标不同控制的 CCX 对（仅记候选，不做仿射断言）；
     - 新模板：以上皆非，逐 hunk 描述。
  4. e9 残余扫描：字面重复对滑窗计数 + 窥孔残余（census 值复用）+ 新模板原模式剩余实例 grep。
只读静态审计，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff")
F_KMX = TMP / "dqi.kmx"
E_KMX = TMP / "e9.kmx"
OUT = Path("artifacts/20261110_e9diff/paid_diff.json")

PAID_OPS = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
QRE = re.compile(r"q(\d+)")


def norm_paid(text: str) -> str:
    """付费门归一化 token：CCX 控制可交换；其余直写。"""
    p = text.split()
    op = p[0]
    if op == "CCX" and len(p) >= 4:
        a, b, t = p[1], p[2], p[3]
        if a > b:
            a, b = b, a
        return f"CCX {a} {b} {t}"
    return text


def extract_paid(kmx: Path):
    """返回 {stage: [dict(lineno, off, text, tok)]}, 以及行号->行内容索引按需回读。"""
    per_stage: dict[str, list] = {}
    stack: list[str] = []
    lineno = 0
    with kmx.open("rb") as f:
        while True:
            off = f.tell()
            raw = f.readline()
            if not raw:
                break
            lineno += 1
            try:
                l = raw.decode("utf-8", errors="replace").rstrip("\n")
            except Exception:
                continue
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
            op = l.split()[0]
            if op in PAID_OPS:
                stage = stack[0] if stack else "header"
                per_stage.setdefault(stage, []).append(
                    {"lineno": lineno, "off": off, "text": l, "tok": norm_paid(l)}
                )
    return per_stage


def align_paid(a_list, b_list, lookahead=500):
    """贪心对齐：返回 hunk 列表，每个 hunk = {a_del:[...], b_add:[...], a_start, b_start}。
    a=frontier, b=e9。匹配以 tok 相等为准。"""
    hunks = []
    i = j = 0
    na, nb = len(a_list), len(b_list)
    cur = None
    while i < na and j < nb:
        if a_list[i]["tok"] == b_list[j]["tok"]:
            if cur is not None:
                hunks.append(cur)
                cur = None
            i += 1
            j += 1
            continue
        # 失配：在 lookahead 内找重同步点
        found = None
        # 优先找 a[i] 在 b[j+1..]，或 b[j] 在 a[i+1..]
        for k in range(1, lookahead + 1):
            if j + k < nb and b_list[j + k]["tok"] == a_list[i]["tok"]:
                found = ("b_skip", k)
                break
            if i + k < na and a_list[i + k]["tok"] == b_list[j]["tok"]:
                found = ("a_skip", k)
                break
        if cur is None:
            cur = {"a_del": [], "b_add": [], "a_start": i, "b_start": j,
                   "a_lines": [], "b_lines": []}
        if found is None:
            cur["a_del"].append(a_list[i])
            cur["b_add"].append(b_list[j])
            i += 1
            j += 1
        elif found[0] == "b_skip":
            k = found[1]
            for t in range(k):
                cur["b_add"].append(b_list[j + t])
            j += k
        else:
            k = found[1]
            for t in range(k):
                cur["a_del"].append(a_list[i + t])
            i += k
    # 尾部
    if i < na or j < nb:
        if cur is None:
            cur = {"a_del": [], "b_add": [], "a_start": i, "b_start": j,
                   "a_lines": [], "b_lines": []}
        while i < na:
            cur["a_del"].append(a_list[i])
            i += 1
        while j < nb:
            cur["b_add"].append(b_list[j])
            j += 1
    if cur is not None:
        hunks.append(cur)
    return hunks


def read_window(kmx: Path, center_offs: list[int], before=25, after=25, max_lines=61):
    """按字节偏移取上下文窗口：找到最接近的偏移行，取前后行。简化实现：
    二次扫描目标行号区间。调用方传入行号区间即可。"""
    return []


def get_lines_multi(kmx: Path, intervals: list[tuple[int, int]]):
    """单遍扫描取多个行号区间（先合并重叠区间，一次扫描后切片）。返回 {(lo,hi): [...] }。"""
    ivs = sorted(set(intervals))
    out: dict[tuple[int, int], list] = {}
    if not ivs:
        return out
    merged: list[list[int]] = [[ivs[0][0], ivs[0][1]]]
    for lo, hi in ivs[1:]:
        if lo <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    store: dict[int, str] = {}
    max_hi = merged[-1][1]
    mi = 0
    with kmx.open("r", encoding="utf-8", errors="replace") as f:
        for n, l in enumerate(f, start=1):
            if n > max_hi:
                break
            while mi < len(merged) and n > merged[mi][1]:
                mi += 1
            if mi < len(merged) and merged[mi][0] <= n <= merged[mi][1]:
                store[n] = l.rstrip("\n")
    for lo, hi in ivs:
        out[(lo, hi)] = [(n, store[n]) for n in range(lo, hi + 1) if n in store]
    return out


def classify_hunk(f_win, e_win, a_del, b_add):
    """启发式形态分类，返回 (label, evidence)。"""
    f_text = "\n".join(t for _, t in f_win)
    e_text = "\n".join(t for _, t in e_win)
    del_ccx = [d for d in a_del if d["text"].startswith("CCX")]
    # 1. 测量窥孔：被删 CCX 目标在旧窗口 ±15 行内有 HMR/R 同线，且新侧有条件 CZ 或 HMR
    peep_ev = []
    for d in del_ccx:
        p = d["text"].split()
        t = p[3] if len(p) > 3 else ""
        # 在旧窗口中找 HMR/R t
        for n, tline in f_win:
            pp = tline.split()
            if pp and pp[0] in ("HMR", "R") and len(pp) > 1 and pp[1] == t:
                peep_ev.append(f"F:{n}:{tline.strip()} <- {d['text']} (L{d['lineno']})")
    new_cond_cz = [t for _, t in e_win if t.startswith("CZ") and " if " in t]
    new_hmr = [t for _, t in e_win if t.startswith("HMR")]
    if peep_ev and (new_cond_cz or new_hmr):
        return ("测量窥孔", f"del-CCX目标被HMR/R紧跟 {len(peep_ev)}处; 新侧条件CZ={len(new_cond_cz)}, HMR={len(new_hmr)}; e.g. {peep_ev[0]}")
    # 2. 字面复用：被删 CCX 的归一化 token 在旧窗口保留侧仍存在（窗口内双胞胎）
    if del_ccx:
        f_toks = Counter(t.split(" if ")[0] for _, t in f_win if t.startswith("CCX"))
        # 归一化比较
        twin = []
        for d in del_ccx:
            c = Counter()
            if f_toks.get(norm_paid(d["text"]), 0) >= 1:
                # 确认双胞胎不是被删自身（窗口包含被删行，需 >=2 或新侧仍有）
                e_toks = Counter(norm_paid(t.split(" if ")[0]) for _, t in e_win if t.startswith("CCX"))
                if f_toks.get(norm_paid(d["text"]), 0) + e_toks.get(norm_paid(d["text"]), 0) >= 2 or e_toks.get(norm_paid(d["text"]), 0) >= 1:
                    twin.append(d["text"])
        if twin:
            return ("字面复用", f"{len(twin)}个被删CCX在窗口内有字面双胞胎; e.g. {twin[0]}")
    # 3. 规范对匹配候选：被删 CCX 与窗口内另一 CCX 同目标、控制不同
    if del_ccx:
        win_ccx_f = [t.split(" if ")[0].split() for _, t in f_win if t.startswith("CCX")]
        cand = []
        for d in del_ccx:
            dp = d["text"].split()
            if len(dp) < 4:
                continue
            da, db, dt = dp[1], dp[2], dp[3]
            for wp in win_ccx_f:
                if len(wp) < 4:
                    continue
                if wp[3] == dt and {wp[1], wp[2]} != {da, db}:
                    cand.append(f"del {d['text']} vs win {' '.join(wp)}")
                    break
        if cand:
            return ("规范对匹配候选", f"{len(cand)}处同目标异控制; e.g. {cand[0]}（需仿射确认，本轮不断言）")
    # 4. 新模板
    ops_f = Counter(t.split()[0] for _, t in f_win if t and not t.startswith("INFO_TAG"))
    ops_e = Counter(t.split()[0] for _, t in e_win if t and not t.startswith("INFO_TAG"))
    return ("新模板", f"旧侧门类 {dict(ops_f)}; 新侧门类 {dict(ops_e)}; del={len(a_del)} add={len(b_add)}")


def main() -> None:
    print("extract frontier paid...", flush=True)
    f_paid = extract_paid(F_KMX)
    print("extract e9 paid...", flush=True)
    e_paid = extract_paid(E_KMX)
    total_f = sum(len(v) for v in f_paid.values())
    total_e = sum(len(v) for v in e_paid.values())
    print(f"paid totals: frontier={total_f} e9={total_e} delta={total_e - total_f}", flush=True)
    all_hunks = []
    for stage in sorted(set(f_paid) | set(e_paid)):
        a_list = f_paid.get(stage, [])
        b_list = e_paid.get(stage, [])
        hunks = align_paid(a_list, b_list)
        # 合并邻近 hunk（付费索引差距 <= 20 视为同一窗口）
        merged = []
        for h in hunks:
            if merged and (h["a_start"] - (merged[-1]["a_start"] + len(merged[-1]["a_del"])) <= 20):
                prev = merged[-1]
                prev["a_del"].extend(h["a_del"])
                prev["b_add"].extend(h["b_add"])
            else:
                merged.append(h)
        for h in merged:
            # 锚点：hunk 在双方 paid 序列中的起始下标（纯删/纯增时即重同步点）
            a_sync = a_list[h["a_start"] + len(h["a_del"])]["lineno"] if h["a_start"] + len(h["a_del"]) < len(a_list) else None
            b_sync = b_list[h["b_start"] + len(h["b_add"])]["lineno"] if h["b_start"] + len(h["b_add"]) < len(b_list) else None
            h["a_start_idx"] = h["a_start"]
            h["b_start_idx"] = h["b_start"]
            h["a_sync_lineno"] = a_sync
            h["b_sync_lineno"] = b_sync
            a_los = [d["lineno"] for d in h["a_del"]]
            b_los = [d["lineno"] for d in h["b_add"]]
            h["f_iv"] = (max(1, min(a_los) - 25), max(a_los) + 25) if a_los else None
            if b_los:
                h["e_iv"] = (max(1, min(b_los) - 25), max(b_los) + 25)
            elif h["b_sync_lineno"] is not None:
                # 纯删除：新侧锚点取重同步 paid 门行号，窗口放宽到 ±40
                h["e_iv"] = (max(1, h["b_sync_lineno"] - 40), h["b_sync_lineno"] + 40)
            else:
                h["e_iv"] = None
            h["_a_los"] = a_los
            h["_b_los"] = b_los
        # 批量取窗口（每文件单遍扫描）
        f_ivs = [h["f_iv"] for h in merged if h["f_iv"]]
        e_ivs = [h["e_iv"] for h in merged if h["e_iv"]]
        f_winmap = get_lines_multi(F_KMX, f_ivs)
        e_winmap = get_lines_multi(E_KMX, e_ivs)
        for h in merged:
            f_win = f_winmap.get(h["f_iv"], [])
            e_win = e_winmap.get(h["e_iv"], [])
            label, ev = classify_hunk(f_win, e_win, h["a_del"], h["b_add"])
            all_hunks.append({
                "stage": stage,
                "label": label,
                "evidence": ev,
                "n_del": len(h["a_del"]),
                "n_add": len(h["b_add"]),
                "del_texts": [d["text"] for d in h["a_del"][:12]],
                "add_texts": [d["text"] for d in h["b_add"][:12]],
                "f_range": list(h["f_iv"]) if h["f_iv"] else None,
                "e_range": list(h["e_iv"]) if h["e_iv"] else None,
                "a_start_idx": h["a_start_idx"],
                "b_start_idx": h["b_start_idx"],
                "a_sync_lineno": h["a_sync_lineno"],
                "b_sync_lineno": h["b_sync_lineno"],
            })
        print(f"stage {stage}: paid f={len(a_list)} e={len(b_list)} hunks={len(merged)}", flush=True)
    by_label = Counter(h["label"] for h in all_hunks)
    out = {
        "paid_totals": {"frontier": total_f, "e9": total_e, "delta": total_e - total_f},
        "per_stage_paid": {s: {"frontier": len(f_paid.get(s, [])), "e9": len(e_paid.get(s, []))} for s in sorted(set(f_paid) | set(e_paid))},
        "n_hunks": len(all_hunks),
        "by_label": dict(by_label),
        "hunks": all_hunks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"paid_totals": out["paid_totals"], "per_stage": out["per_stage_paid"],
                      "n_hunks": len(all_hunks), "by_label": dict(by_label)}, indent=2))
    for h in all_hunks[:40]:
        print(f"[{h['stage']}/{h['label']}] del={h['n_del']} add={h['n_add']} F{h['f_range']} E{h['e_range']}")
        print(f"   ev: {h['evidence']}")


if __name__ == "__main__":
    main()
