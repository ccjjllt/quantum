"""Static liveness + stage width analysis for width_opt62 (manual, not a test).

Run manually:
    uv run python experiments/invsqrt/20261102_generator_v2/width_liveness.py

Outputs (in experiments/... dir):
    liveness_gen2.json, width_report.md
Does NOT run official verifier, does NOT fit tables.
"""
import json
import re
import sys
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import width_opt62 as W

OUT_JSON = HERE / "liveness_gen2.json"
OUT_MD = HERE / "width_report.md"

QRE = re.compile(r"\bq(\d+)\b")
STAGE_RE = re.compile(r'INFO_TAG "STAGE:([^"]+)"')

# ---- allocation tracking via monkey-patch ----
stage_alloc = []  # (stage, num_allocated)
max_alloc = {"v": 0}
orig_info_tag = km.CircuitBuilder.info_tag
orig_alloc = km.CircuitBuilder.alloc_qubits
orig_free = km.CircuitBuilder.free

def patched_info_tag(self, text):
    r = orig_info_tag(self, text)
    m = re.search(r"STAGE:([^\"\s]+)", text)
    if m:
        try:
            na = self.num_allocated_qubits
        except Exception:
            na = -1
        stage_alloc.append((m.group(1), int(na)))
        if int(na) > max_alloc["v"]:
            max_alloc["v"] = int(na)
    return r

def patched_alloc(self, n):
    r = orig_alloc(self, n)
    try:
        na = self.num_allocated_qubits
        if int(na) > max_alloc["v"]:
            max_alloc["v"] = int(na)
    except Exception:
        pass
    return r

km.CircuitBuilder.info_tag = patched_info_tag
km.CircuitBuilder.alloc_qubits = patched_alloc

tables = W.load_tables()
circ = W.build_circuit(tables)
text = str(circ)
lines = text.splitlines()
nq = circ.num_qubits

# restore
km.CircuitBuilder.info_tag = orig_info_tag
km.CircuitBuilder.alloc_qubits = orig_alloc

# ---- stage boundaries from INFO_TAG lines ----
markers = []  # (line_idx, stage)
for i, ln in enumerate(lines):
    m = STAGE_RE.search(ln)
    if m:
        markers.append((i, m.group(1)))

# Pair ENTER/EXIT by name convention: F_X_ENTER ... F_X_EXIT.
# Build stage intervals: for each ENTER, find matching EXIT (same prefix).
stages = []
stack = {}
for idx, name in markers:
    if name.endswith("_ENTER"):
        prefix = name[: -len("_ENTER")]
        stack[prefix] = idx
    elif name.endswith("_EXIT"):
        prefix = name[: -len("_EXIT")]
        if prefix in stack:
            stages.append({"name": prefix, "start": stack.pop(prefix), "end": idx})
# Any unclosed (should be none)
for prefix, s in stack.items():
    stages.append({"name": prefix, "start": s, "end": len(lines) - 1})
stages.sort(key=lambda d: d["start"])

def count_ops(slice_lines):
    ops = {}
    for ln in slice_lines:
        s = ln.strip()
        if not s or s.startswith("APPEND") or s.startswith("REGISTER") or s.startswith("INFO_TAG"):
            continue
        op = s.split()[0]
        ops[op] = ops.get(op, 0) + 1
    toff = ops.get("CCX", 0) + ops.get("CSWAP", 0)
    qs = set()
    for ln in slice_lines:
        for m in QRE.finditer(ln):
            # exclude APPEND/REGISTER lines? keep them: they indicate allocation
            qs.add(int(m.group(1)))
    return ops, toff, len(qs), sorted(qs)[:8]

for st in stages:
    sl = lines[st["start"]: st["end"] + 1]
    ops, toff, ndist, _ = count_ops(sl)
    st["num_lines"] = len(sl)
    st["ops"] = ops
    st["toffoli_like"] = toff
    st["distinct_qubits"] = ndist
    st["num_instructions_ops"] = sum(ops.values())

# ---- global per-qubit first-last liveness ----
first, last = {}, {}
for i, ln in enumerate(lines):
    if ln.strip().startswith("REGISTER"):
        continue
    for m in QRE.finditer(ln):
        q = int(m.group(1))
        if q not in first:
            first[q] = i
        last[q] = i
# sweep line for peak
events = []
for q in first:
    events.append((first[q], 1))
    events.append((last[q] + 1, -1))
events.sort()
cur = peak = peak_line = 0
for pos, d in events:
    cur += d
    if cur > peak:
        peak = cur
        peak_line = pos
# peak composition at peak_line: which qubits live
live_at_peak = [q for q in first if first[q] <= peak_line <= last[q]]
# classify by known allocation order: x 0..21, lz 22..26, coef 27..59, v 60..114, rest temp
def cls(q):
    if 0 <= q <= 21:
        return "x"
    if 22 <= q <= 26:
        return "lz"
    if 27 <= q <= 59:
        return "coef"
    if 60 <= q <= 114:
        return "v"
    return "temp"
from collections import Counter
comp = Counter(cls(q) for q in live_at_peak)

# which stage contains peak_line?
peak_stage = None
for st in stages:
    if st["start"] <= peak_line <= st["end"]:
        # innermost: smallest interval containing peak
        if peak_stage is None or (st["end"] - st["start"]) < (peak_stage["end"] - peak_stage["start"]):
            peak_stage = st

stats = W.resource_stats(circ)
result = {
    "qubits": nq,
    "num_lines_text": len(lines),
    "max_allocated_tracked": max_alloc["v"],
    "stage_alloc_track": [{"stage": s, "num_allocated": n} for s, n in stage_alloc],
    "stages": stages,
    "liveness": {
        "peak_first_last": peak,
        "peak_line": peak_line,
        "peak_stage": peak_stage["name"] if peak_stage else None,
        "peak_composition": dict(comp),
        "num_qubits_tracked": len(first),
        "note": "first-last static; qubit-index reuse after free merges ranges (overestimates during free gaps); allocation track is ground truth for width",
    },
    "resource_stats": {k: v for k, v in stats.items() if k != "ops"},
    "ops_total": stats.get("ops"),
}
OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

# ---- markdown ----
L = []
L.append("# width_report.md：gen2 寿命实测（静态）")
L.append("")
L.append(f"- 电路 qubits={nq}，文本行 {len(lines)}，tracker max_allocated={max_alloc['v']}。")
L.append(f"- 全局 first-last 峰值 {peak} @line {peak_line}（阶段 {peak_stage['name'] if peak_stage else '?'}），构成 {dict(comp)}。")
L.append("- first-last 为静态近似（qubit 索引复用会合并 free 间隙，高估）；宽度真值以 alloc tracker 与 circuit.num_qubits 为准。")
L.append("- 本电路为 width_opt62 加 STAGE 标记版（INFO_TAG 只增指令数，不占线、不改语义；SHA 与基线不同，见下）。")
L.append(f"- instrumented SHA={stats.get('sha256')}，基线 REC_SHA=4fe00ee7…（差值来自 INFO_TAG 标记行，门数差见 ops）。")
L.append("")
L.append("## 阶段表（含 STAGE 标记区间行数 / distinct qubits / toffoli-like=CCX+CSWAP）")
L.append("")
L.append("| 阶段 | 行区间 | 行数 | distinctQ | toff | 主要 ops |")
L.append("|---|---|---|---|---|---|")
for st in stages:
    ops = st["ops"]
    top = ",".join(f"{k}:{v}" for k, v in sorted(ops.items(), key=lambda kv: -kv[1])[:4])
    L.append(f"| {st['name']} | {st['start']}..{st['end']} | {st['num_lines']} | {st['distinct_qubits']} | {st['toffoli_like']} | {top} |")
L.append("")
L.append("## alloc tracker（每 STAGE 标记点 num_allocated_qubits）")
L.append("")
L.append("| 标记 | allocated |")
L.append("|---|---|")
for s, n in stage_alloc:
    L.append(f"| {s} | {n} |")
L.append("")
L.append("## 峰值构成（实测，以 first-last @peak 为准）")
L.append("")
L.append(f"- peak_line {peak_line} 落在 `{peak_stage['name'] if peak_stage else '?'}`；live 构成 x/lz/coef/v/temp = {[comp.get(k,0) for k in ['x','lz','coef','v','temp']]}。")
L.append("- 预期 `ripple暂存~45 + coef33 + V55 + x22 (+lz5)` = 160；以本实测为准，见阶段表 R1_J0 行。")
L.append("- R1 各行 distinctQ 与 toff（定位最宽调用点）：")
R1rows = [st for st in stages if st["name"].startswith("F_R1_EXIT") or st["name"].startswith("R1_J")]
# actually nested row stages are named R1_J{j}
rows = [st for st in stages if st["name"].startswith("R1_J") and not st["name"].startswith("R1R")]
rows = sorted(rows, key=lambda d: d["name"])
for st in rows:
    L.append(f"  - {st['name']}: distinctQ={st['distinct_qubits']} toff={st['toffoli_like']} lines={st['num_lines']}")
A1rows = [st for st in stages if st["name"].startswith("A1_J") and "R_" not in st["name"] and "R1" not in st["name"]]
A1rows = sorted([st for st in stages if st["name"].startswith("A1_J")], key=lambda d: d["name"])[:16]
for st in A1rows:
    L.append(f"  - {st['name']}: distinctQ={st['distinct_qubits']} toff={st['toffoli_like']} lines={st['num_lines']}")
L.append("")
L.append("## 逆向各段恢复成本（toffoli-like，逆序段）")
L.append("")
for st in stages:
    if st["name"].startswith("R_"):
        L.append(f"- {st['name']}: toff={st['toffoli_like']} lines={st['num_lines']} distinctQ={st['distinct_qubits']}")
L.append("")
OUT_MD.write_text("\n".join(L) + "\n")
print(f"qubits={nq} peak_firstlast={peak} @{peak_line} stage={peak_stage['name'] if peak_stage else '?'} comp={dict(comp)}")
print(f"wrote {OUT_JSON} and {OUT_MD}")
