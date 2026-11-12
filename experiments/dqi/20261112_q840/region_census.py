"""Per-stage census of the two qubit regions: syndrome (q<840) and bank (q>=840).

For each top-level stage: how many distinct syndrome qubits are touched, how
many ops touch them, and how many distinct bank qubits. If the syndrome were
idle during a stage, that stage could in principle borrow its wires.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION", "PUSH", "POP")
QRE = re.compile(r"q(\d+)")
STAGES = ["mask_projection", "initial", "extract", "synthesis", "convert", "scan",
          "unconvert", "unsynthesis", "unextract", "uninitial", "restore_masks"]
BASE = 840


def main(path: Path) -> None:
    stack: list[str] = []
    stage = None
    syn: dict[str, set] = defaultdict(set)
    bank: dict[str, set] = defaultdict(set)
    syn_ops: Counter = Counter()
    bank_ops: Counter = Counter()
    syn_uses: Counter = Counter()
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INFO_TAG "):
                try:
                    tag = line.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    if stage is None:
                        stage = tag[7:]
                    stack.append(tag[7:])
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    if not stack:
                        stage = None
                continue
            if not line or line.startswith(SKIP):
                continue
            qs = [int(m.group(1)) for m in QRE.finditer(line)]
            s = [q for q in qs if q < BASE]
            b = [q for q in qs if q >= BASE]
            if s:
                syn[stage].update(s)
                syn_ops[stage] += 1
                for q in s:
                    syn_uses[q] += 1
            if b:
                bank[stage].update(b)
                bank_ops[stage] += 1
    print(f"{'stage':16s} {'distinct_S':>10s} {'ops_touching_S':>15s} {'distinct_bank':>13s} {'ops_touching_bank':>18s}")
    for st in STAGES:
        print(f"{st:16s} {len(syn[st]):10d} {syn_ops[st]:15d} {len(bank[st]):13d} {bank_ops[st]:18d}")
    never = [q for q in range(BASE) if q not in syn_uses]
    least = sorted(range(BASE), key=lambda q: syn_uses[q])[:20]
    print(f"\nsyndrome qubits never touched: {len(never)}")
    print("least-used syndrome qubits:", [(q, syn_uses[q]) for q in least])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
