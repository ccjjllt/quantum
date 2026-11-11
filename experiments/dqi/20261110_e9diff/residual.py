"""e9 残余空间扫描 + 分阶段 qubit 触及画像（单遍流式读 e9.kmx）。

(a) CSWAP-双目标测量模板残余：CSWAP(c,x,y) 后 80 行内出现 HMR x 与 HMR y，
    且其间无其他门触碰 x/y（付费或免费皆计）→ 未改写位点。
(b) 相位回踢 sandwich 残余：CCX(a,b,t) 后 15 个 op 内出现 CZ(c,t)，
    随后出现第二处同归一化 CCX(a,b,t)，其间 t 无其他触碰 → 未改写位点。
(c) 分阶段 distinct-qubit / max-index 画像（892Q 宽度冗余判断输入）。
只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT = Path("artifacts/20261110_e9diff/residual_e9.json")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
PAID_OPS = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
QTOK = re.compile(r"^q(\d+)$")


def qtoks(text: str) -> list[str]:
    return [p for p in text.split()[1:] if p.startswith("q") and p[1:].split()[0].isdigit()]


def main() -> None:
    stack: list[str] = []
    stage_of_line: list = []  # not stored; streaming
    # --- width stats ---
    stage_qubits: dict[str, set] = {}
    stage_maxidx: dict[str, int] = {}
    # --- (a) pending CSWAPs ---
    pending_sw: list[dict] = []
    sw_hits: list[dict] = []
    # --- (b) pending CCX sandwiches ---
    pending_cx: list[dict] = []
    sw_sandwich_hits: list[dict] = []
    lineno = 0
    n_ops = 0
    opcount_since: int = 0  # counts non-skip lines for expiry (approx)

    with E_KMX.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            lineno += 1
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
            n_ops += 1
            stage = stack[0] if stack else "header"
            parts = l.split()
            op = parts[0]
            qs = set(qtoks(l))
            idxs = [int(q[1:]) for q in qs]
            s = stage_qubits.setdefault(stage, set())
            s.update(qs)
            for i in idxs:
                if i > stage_maxidx.get(stage, -1):
                    stage_maxidx[stage] = i
            # expire pendings by op count
            # (a) update pending CSWAPs
            still = []
            for p in pending_sw:
                if n_ops - p["opidx"] > 80:
                    continue
                if p["x"] in qs or p["y"] in qs:
                    if op == "HMR" and len(parts) > 1:
                        if parts[1] == p["x"]:
                            p["hx"] = lineno
                        if parts[1] == p["y"]:
                            p["hy"] = lineno
                    else:
                        # 其他触碰（CSWAP 自身已过，只看之后的）→ 若在 hx,hy 齐全前触碰则失效
                        if not (p["hx"] and p["hy"]):
                            # HMR 行本身已处理；其他任何含 x/y 的行使模板失效
                            if not (op == "HMR"):
                                p["dead"] = True
                if p["hx"] and p["hy"] and not p.get("dead"):
                    sw_hits.append({"stage": p["stage"], "csw": p["text"],
                                    "csw_lineno": p["lineno"], "hmr_x": p["hx"], "hmr_y": p["hy"]})
                    continue
                if not p.get("dead"):
                    still.append(p)
            pending_sw = still
            if len(pending_sw) < 5000 and op == "CSWAP" and len(parts) >= 4:
                pending_sw.append({"stage": stage, "text": l, "lineno": lineno,
                                   "opidx": n_ops, "c": parts[1], "x": parts[2], "y": parts[3],
                                   "hx": 0, "hy": 0})
            # (b) update pending CCX sandwiches
            still2 = []
            for p in pending_cx:
                if n_ops - p["opidx"] > 15:
                    continue
                if p["t"] in qs:
                    if op == "CZ" and len(parts) >= 3 and p["t"] in (parts[1], parts[2]):
                        # CZ(c,t)（对称，任一序皆可）；其间只允许恰好一个
                        if p["cz"]:
                            p["dead"] = True
                        else:
                            other = parts[2] if parts[1] == p["t"] else parts[1]
                            p["cz"] = (lineno, other)
                    elif op == "CCX" and len(parts) >= 4:
                        a, b, t = parts[1], parts[2], parts[3]
                        if t == p["t"] and {a, b} == {p["a"], p["b"]} and p["cz"]:
                            sw_sandwich_hits.append({
                                "stage": p["stage"], "ccx": p["text"], "ccx_lineno": p["lineno"],
                                "cz_lineno": p["cz"][0], "cz_c": p["cz"][1],
                                "ccx2_lineno": lineno, "would_add": f"CCZ {p['a']} {p['b']} {p['cz'][1]}",
                                "would_del": 2, "would_add_n": 1})
                            continue
                        else:
                            p["dead"] = True
                    else:
                        # t 被其他门触碰（HMR/R/CX/...）→ 模板要求 t 仅被 CZ 触碰，失效
                        # 注意：CCX 自身对 (a,b) 的触碰不影响（只跟踪 t）
                        p["dead"] = True
                if not p.get("dead"):
                    still2.append(p)
            pending_cx = still2
            if len(pending_cx) < 5000 and op == "CCX" and len(parts) >= 4 and " if " not in l:
                pending_cx.append({"stage": stage, "text": l, "lineno": lineno, "opidx": n_ops,
                                   "a": parts[1], "b": parts[2], "t": parts[3], "cz": None})

    width = {st: {"distinct_qubits": len(v), "max_index": stage_maxidx.get(st, -1)}
             for st, v in stage_qubits.items()}
    # 按阶段汇总残余
    from collections import Counter
    sw_by = Counter(h["stage"] for h in sw_hits)
    sd_by = Counter(h["stage"] for h in sw_sandwich_hits)
    out = {
        "n_ops_scanned": n_ops,
        "width_e9": width,
        "cswap_hmr_residual_total": len(sw_hits),
        "cswap_hmr_residual_by_stage": dict(sw_by),
        "cswap_hmr_examples": sw_hits[:15],
        "sandwich_residual_total": len(sw_sandwich_hits),
        "sandwich_residual_by_stage": dict(sd_by),
        "sandwich_examples": sw_sandwich_hits[:15],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if not k.endswith("examples")}, indent=2))
    print("--- cswap examples ---")
    for h in sw_hits[:10]:
        print(f"[{h['stage']}] {h['csw_lineno']}: {h['csw']} hmr_x={h['hmr_x']} hmr_y={h['hmr_y']}")
    print("--- sandwich examples ---")
    for h in sw_sandwich_hits[:10]:
        print(f"[{h['stage']}] {h['ccx_lineno']}: {h['ccx']} +CZ@{h['cz_lineno']} +CCX@{h['ccx2_lineno']} => {h['would_add']}")


if __name__ == "__main__":
    main()
