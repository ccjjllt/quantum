"""pebbling 全量门控 v2：宿主覆盖（阶段1）+ 控制值等价扫（阶段2）.

窗：unextract 同字面 CCX(a,b,t) 连续对 [p0,p1]，持有改写=删 p1、窗内 t 触碰更名至宿主。
阶段 1（内存）：字面位置表 + 宿主死区覆盖 [p0,ext]（ext=p1 后 t 下次写；
  宿主须 |0>-确定：死区起点 HMR 或 s==0，不依赖 R-force）。
阶段 2（流式）：按 p0 排序的活跃窗扫——窗内 (p0,p1) 若 a/b 被写/杀（X/CX-t/
  CCX-t/CSWAP/SWAP/R/HMR）则值已变 ⟹ 不可持有；t 被中间写 ⟹ 链断裂。
  纯读触碰允许。端点 p0/p1 自身不触发。
幸存窗才计可行（省 ≥1 paid/窗；ext==p2 链式另标省 2，需复核宿主到 p3）。
宿主复用冲突（重叠持有窗同宿主）在幸存者上做着色检查——本轮幸存 0，无需此步。
价值谓词说明（诚实边界）：`a/b 窗内零写`是充分非必要条件；同值重写情形受
deepfix 函数级结论约束（见 README §2）。
只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import bisect
import json
from collections import defaultdict
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
GAPS = Path("artifacts/20261110_qpebble/gaps.jsonl")
OUT = Path("artifacts/20261110_qpebble/q_gate.json")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")


def qtoks(parts: list[str]) -> list[str]:
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def op_class(op: str, qs: list[str]):
    """返回 (write_idx, kill_all_flag)。write_idx：写位；其余含 q 触碰按读。
    HMR/R 视为 kill（值变）。"""
    if op == "X":
        return {0}, False
    if op == "CX":
        return {1}, False
    if op in ("CCX", "CCX_CARRY"):
        return {2}, False
    if op in ("CSWAP", "SWAP"):
        return set(range(len(qs))), False
    if op in ("HMR", "R"):
        return set(), True
    return set(), False  # CCZ/CZ/Z/控制端/未知：纯读


def main() -> None:
    by_host: dict[str, list] = defaultdict(list)
    with GAPS.open(encoding="utf-8") as gf:
        for line in gf:
            w, s, e, sk, ek = json.loads(line)
            if ek != "SWAP":
                by_host[w].append((s, e, sk, ek))
    for v in by_host.values():
        v.sort()

    def hosts_cover(wires: set, p0: int, ext: int, need_tail: bool, total: int):
        hs = []
        for h, ivs in by_host.items():
            if h in wires:
                continue
            k = bisect.bisect_right(ivs, (p0, 10**18, "", "")) - 1
            for kk in (k, k + 1):
                if 0 <= kk < len(ivs) and ivs[kk][0] <= p0 and ivs[kk][1] >= ext:
                    if need_tail and ivs[kk][1] != total:
                        continue
                    sk = ivs[kk][2]
                    if ivs[kk][0] == 0 or sk == "HMR":
                        hs.append(h)
                        break
            if len(hs) >= 3:
                break
        return hs

    # ---- 阶段 1 ----
    stack: list[str] = []
    op_idx = 0
    pos: dict[tuple, list[int]] = defaultdict(list)
    twrites: dict[str, list[int]] = defaultdict(list)
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
            stage = stack[0] if stack else "header"
            i = op_idx
            op_idx += 1
            if stage != "unextract":
                continue
            parts = l.split()
            if parts[0] != "CCX" or " if " in l:
                continue
            qs = qtoks(parts)
            if len(qs) != 3:
                continue
            a, b, t = qs
            pos[(min(a, b), max(a, b), t)].append(i)
            twrites[t].append(i)
    for v in twrites.values():
        v.sort()

    windows = []
    wid = 0
    for (a, b, t), v in pos.items():
        wires = {a, b, t}
        for j in range(len(v) - 1):
            p0, p1 = v[j], v[j + 1]
            k = bisect.bisect_right(twrites[t], p1)
            no_next = k >= len(twrites[t])
            ext = twrites[t][k] if not no_next else p1
            hs = hosts_cover(wires, p0, ext, need_tail=no_next, total=op_idx)
            if hs:
                p2 = v[j + 2] if j + 2 < len(v) else None
                windows.append({"id": wid, "a": a, "b": b, "t": t, "p0": p0,
                                "p1": p1, "ext": ext, "p2": p2,
                                "chain": (p2 is not None and ext == p2),
                                "hosts": hs})
                wid += 1
    print(f"phase1: host-covered windows = {len(windows)}", flush=True)

    # ---- 阶段 2：价值等价扫 ----
    windows.sort(key=lambda d: d["p0"])
    by_id = {w["id"]: w for w in windows}
    alive: dict[int, dict] = {}
    wire_index: dict[str, set] = defaultdict(set)
    ptr = 0
    n_fail_ab = 0
    n_fail_t = 0
    survivors = []
    op_idx = 0

    def close_window(wid_: int, survived: bool):
        w = by_id[wid_]
        for x in (w["a"], w["b"], w["t"]):
            s = wire_index.get(x)
            if s is not None:
                s.discard(wid_)
        del alive[wid_]
        if survived:
            survivors.append(wid_)

    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if l.startswith("INFO_TAG ") or not l or l.startswith(SKIP_PREFIX):
                continue
            i = op_idx
            op_idx += 1
            # 关闭到达 p1 的窗（先关，后处理本 op，避免端点自触发）
            done = [wid_ for wid_, w in alive.items() if w["p1"] == i]
            for wid_ in done:
                close_window(wid_, True)
            # 开启 p0==i 的窗（本 op 为 compute 端点，不触发自身检查）
            while ptr < len(windows) and windows[ptr]["p0"] == i:
                w = windows[ptr]
                alive[w["id"]] = w
                wire_index[w["a"]].add(w["id"])
                wire_index[w["b"]].add(w["id"])
                wire_index[w["t"]].add(w["id"])
                ptr += 1
            if not alive:
                continue
            parts = l.split()
            op = parts[0]
            qs = qtoks(parts)
            if not qs:
                continue
            wset, kill = op_class(op, qs)
            if op in ("CCX", "CCX_CARRY", "CX", "X", "CSWAP", "SWAP",
                      "HMR", "R", "CCZ", "CZ", "Z"):
                pass  # 全量分类已由 op_class 覆盖
            for k, q in enumerate(qs):
                ids = wire_index.get(q)
                if not ids:
                    continue
                is_write = (k in wset) or kill
                for wid_ in list(ids):
                    w = alive.get(wid_)
                    if w is None or not (w["p0"] < i < w["p1"]):
                        continue
                    if q == w["t"]:
                        if is_write:
                            close_window(wid_, False)
                            n_fail_t += 1
                        # t 的纯读允许（更名后由宿主服务）
                    else:  # a/b：任何写/杀都改变值
                        if is_write:
                            close_window(wid_, False)
                            n_fail_ab += 1
    # 收尾：仍 alive 的（p1 超出文件？不可能，p1 皆有效）全按幸存计
    for wid_ in list(alive):
        close_window(wid_, True)

    surv = [by_id[i] for i in survivors]
    chains = [w for w in surv if w["chain"]]
    out = {"n_host_covered": len(windows),
           "n_fail_ab_rewrite": n_fail_ab, "n_fail_t_write": n_fail_t,
           "n_survivors": len(surv),
           "survivor_save_lower": len(surv),
           "n_chain": len(chains),
           "survivors": surv[:50], "chains": chains[:20]}
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("survivors", "chains")}, indent=1))
    for w in surv[:15]:
        print("SURV", w["a"], w["b"], w["t"], w["p0"], w["p1"], w["ext"],
              "chain=" + str(w["chain"]), w["hosts"])


if __name__ == "__main__":
    main()
