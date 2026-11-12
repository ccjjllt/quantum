"""Each top-level stage's paid gate count from a kickmix .kmx tag stream. Read-only."""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")


def main(path: Path) -> None:
    stack: list[str] = []
    top = None
    stage_paid: dict[str, Counter] = defaultdict(Counter)
    stage_ops: dict[str, Counter] = defaultdict(Counter)
    sub_paid: dict[tuple[str, str], int] = defaultdict(int)
    sub_count: dict[tuple[str, str], int] = defaultdict(int)
    cur_sub = None
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INFO_TAG "):
                try:
                    tag = line.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    name = tag[7:]
                    if top is None:
                        top = name
                    elif len(stack) == 1:
                        cur_sub = name
                    stack.append(name)
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    if len(stack) == 0:
                        top = None
                    elif len(stack) == 1:
                        cur_sub = None
                continue
            if not line or line.startswith(SKIP_PREFIX):
                continue
            op = line.split()[0]
            stage_ops[top][op] += 1
            if op in PAID:
                stage_paid[top][op] += 1
                if cur_sub is not None:
                    sub_paid[(top, cur_sub)] += 1
                    sub_count[(top, cur_sub)] += 1
    total = 0
    for st in ("initial", "mask_projection", "extract", "synthesis", "convert", "scan",
               "unconvert", "unsynthesis", "unextract"):
        paid = sum(stage_paid[st].values())
        total += paid
        print(f"=== {st}: paid={paid} {dict(stage_paid[st])}")
        print("    ops:", dict(sorted(stage_ops[st].items(), key=lambda kv: -kv[1])[:12]))
        subs = sorted(((n, sub_paid[(st, n)]) for (s, n) in sub_paid if s == st), key=lambda kv: -kv[1])
        for name, count in subs[:8]:
            print(f"      {name:28s} x{sub_count[(st, name)]:<5d} paid={count}")
    print("TOTAL", total)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
