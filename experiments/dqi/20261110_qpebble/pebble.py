"""跨阶段 pebbling 交换表（unextract 重算对盘点 + 死区载体门控）.

问题：unextract 96,881 paid（24.5%）。Bennett 视角下两类重算：
  (H) hold-instead-of-recompute：同一 CCX 字面出现 ≥2 次（算—反算—重算），
      若跨度内持有则省 1~2 paid/组，需载体（某线在该跨度内全死）。
  (R) recompute-instead-of-hold：长跨度持有值提前反算、用时重算，
      花 paid 换峰值 occupancy 下降（供任务 1 Q-1 用；本脚本只输出跨峰值候选）。
读取 q_live.json 的死区 инвентарь 做载体门控；1% unextract = 969 门为标尺。
只读静态，不构建候选、不跑验证器。
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
Q_LIVE = Path("artifacts/20261110_qpebble/q_live.json")
OUT = Path("artifacts/20261110_qpebble/pebble.json")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")


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
    op_idx = 0
    # unextract 内 CCX 字面 -> positions
    pos: dict[tuple, list[int]] = defaultdict(list)
    n_unextract_ops = 0
    n_unextract_ccx = 0
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
            n_unextract_ops += 1
            parts = l.split()
            if parts[0] != "CCX" or " if " in l:
                continue
            qs = qtoks(parts)
            if len(qs) != 3:
                continue
            a, b, t = qs
            key = (min(a, b), max(a, b), t)
            pos[key].append(i)
            n_unextract_ccx += 1

    groups = {k: v for k, v in pos.items() if len(v) >= 2}
    # 每组 k 次出现：跨全跨度持有则省 (k-1) paid（跳过后续每次重算；含反算对时
    # 同量级，取上界 k-1，门控与精确语义在 q_fuse/README 中收敛）。
    pairs = []
    gross_save = 0
    for k, v in groups.items():
        gross_save += len(v) - 1
        for j in range(len(v) - 1):
            span = v[j + 1] - v[j]
            pairs.append({"lit": f"CCX {k[0]} {k[1]} {k[2]}",
                          "p0": v[j], "p1": v[j + 1], "span": span})
    pairs.sort(key=lambda d: -d["span"])
    n_pair_windows = len(pairs)

    # 载体门控：读死区，对每对 (p0,p1) 找是否存在他线死区 ⊇ [p0,p1]
    gated = None
    if Q_LIVE.exists():
        ql = json.loads(Q_LIVE.read_text())
        gaps = [(g["wire"], g["start"], g["end"]) for g in
                json.loads(json.dumps(ql.get("top_gaps_30", [])))]
        # top_gaps 只有 30 个不够做门控：重建需要全量 gaps。q_live.json 未存全量，
        # 此处置 ungated 上界 + 用 top30 试门控（诚实标注覆盖度）。
        gated = {"note": "q_live.json 仅存 top30 死区，全量门控需 q_fuse 阶段重建；"
                         "此处为上界估计，见 README",
                 "n_pair_windows": n_pair_windows, "gross_save": gross_save}
    out = {
        "unextract_ops": n_unextract_ops,
        "unextract_ccx_uncond": n_unextract_ccx,
        "n_literal_groups_ge2": len(groups),
        "n_pair_windows": n_pair_windows,
        "gross_save_upper_bound": gross_save,
        "one_percent_unextract": 968,
        "ratio_gross_over_1pct": gross_save / 968 if pairs else 0,
        "top_spans_30": pairs[:30],
        "gate_note": (gated or {}).get("note", "q_live.json 缺失，未门控"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "top_spans_30"}, indent=1))
    for p in pairs[:15]:
        print(f"{p['lit']}: [{p['p0']},{p['p1']}] span={p['span']}")


if __name__ == "__main__":
    main()
