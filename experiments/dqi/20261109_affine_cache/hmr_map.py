"""Map HMR (flag-carry) sites per stage with local paid-gate context."""
from __future__ import annotations

import sys
from collections import Counter

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"

stage = "header"
stack: list[str] = []
hmr_by_stage: dict[str, list[tuple[int, str]]] = {}
window: list[tuple[int, str]] = []  # (idx, line) ring buffer

PAID = ("CCX", "CCZ", "CSWAP")


def ctx(lines_window, idx):
    out = []
    for i, l in lines_window:
        if abs(i - idx) <= 12 and l.split()[0] in PAID + ("HMR", "R", "CZ", "CX",
                                                           "PUSH_CONDITION", "POP_CONDITION"):
            out.append((i, l))
    return out


with open(KMX) as f:
    for idx, raw in enumerate(f):
        l = raw.strip()
        if not l:
            continue
        if l.startswith("INFO_TAG"):
            tag = l.split('"', 2)[1]
            if tag.startswith("@enter:"):
                stack.append(tag[7:])
                stage = stack[0]
            elif tag.startswith("@exit:") and stack:
                stack.pop()
                stage = stack[0] if stack else "header"
            continue
        window.append((idx, l))
        if len(window) > 400:
            window.pop(0)
        if l.startswith("HMR"):
            hmr_by_stage.setdefault(stage, []).append((idx, l))

for st, evs in hmr_by_stage.items():
    print(f"{st}: {len(evs)} HMR")
if "--detail" in sys.argv:
    want = sys.argv[sys.argv.index("--detail") + 1]
    evs = hmr_by_stage.get(want, [])
    print(f"--- first 8 and last 8 HMR in {want} ---")
    for idx, l in (evs[:8] + evs[-8:]):
        print(f"@{idx}: {l}")
    # per-qubit HMR counts
    ct = Counter(l.split()[1] for _, l in evs)
    print("top measured qubits:", ct.most_common(15))
    # distinct HMR bits
    cb = Counter(l.split()[2] for _, l in evs)
    print("n distinct bits:", len(cb))
