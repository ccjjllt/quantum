"""收尾聚合（前向单遍）：每线首写/末读/读写计数.

供 Q-1 打孔精确定价：团区间 [2858014,57907640] 单块 55M ops，
打孔成本 ≈ 2 × 团内读数 × producer_paid（≥2×读数）vs 887。
只读静态。
"""
from __future__ import annotations

import json
from pathlib import Path

E_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
OUT = Path("artifacts/20261110_qpebble/q_reads.json")

SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
CLIQUE = (2858014, 57907640)


def qtoks(parts: list[str]) -> list[str]:
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def main() -> None:
    fw: dict[str, int] = {}
    lr: dict[str, int] = {}
    nr: dict[str, int] = {}
    nw: dict[str, int] = {}
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
                w = {0}; r = set()
            elif op == "CX":
                w = {1}; r = {0}
            elif op in ("CCX", "CCX_CARRY"):
                w = {2}; r = {0, 1}
            elif op in ("CSWAP", "SWAP"):
                w = set(range(len(qs))); r = set(range(len(qs)))
            elif op == "R":
                w = {0}; r = set()
            else:
                w = set(); r = set(range(len(qs)))
            for k, q in enumerate(qs):
                if k in w:
                    if q not in fw:
                        fw[q] = i
                    nw[q] = nw.get(q, 0) + 1
                if k in r:
                    lr[q] = i
                    nr[q] = nr.get(q, 0) + 1
    rows = []
    for qi in range(892):
        q = f"q{qi}"
        rows.append({"q": q, "fw": fw.get(q, -1), "lr": lr.get(q, -1),
                     "n_reads": nr.get(q, 0), "n_writes": nw.get(q, 0)})
    by_reads = sorted(rows, key=lambda d: d["n_reads"])
    out = {"total_ops": op_idx, "rows": rows,
           "fewest_reads_10": by_reads[:10],
           "min_reads": by_reads[0]["n_reads"],
           "min_reads_wire": by_reads[0]["q"]}
    OUT.write_text(json.dumps(out) + "\n")
    print(json.dumps({"total_ops": op_idx, "fewest_reads_10": by_reads[:10]}, indent=1))
    # 打孔下界：min_reads 读 → ≥2×min_reads paid vs 887
    m = by_reads[0]
    print(f"punch lower bound best wire {m['q']}: >= {2*m['n_reads']} paid vs break-even 887 "
          f"=> ratio {2*m['n_reads']/887:.1f}x over")


if __name__ == "__main__":
    main()
