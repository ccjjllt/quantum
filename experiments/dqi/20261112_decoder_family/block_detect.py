"""Detect zero-workspace rank-one multiplication blocks in a .kmx stream.

The kernels `field.mul_xor0` and `noscratch.tensor_xor_noscratch` emit, once
per tensor term, a locally recognizable motif:

    CX x[i] x[p] ...            fan-in on the first input pivot
    CX y[i] y[p] ...            fan-in on the second input pivot
    CX z[t] z[j] ...            fan-out on the output pivot (may be empty)
    CCX x[p] y[p] z[t]
    (mirror CX undo)

We count CCX events that are immediately followed by a CX reading the same
target and that have a CX write into each control within a short lookback.
Consecutive counted CCX with the same (a,b,t) triple form a *term*; terms with
identical triples within a short window form a *block*; the block length is the
tensor rank (3/6/15/42/99/105).

Read-only; used to attribute eae396ba's paid T to multiplication rank blocks.

Usage: python block_detect.py IN.kmx OUT.json [--stages]
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
QRE = re.compile(r"q(\d+)")


def main(path, out, stages=False):
    stack = []
    top = None
    per_stage = defaultdict(Counter)
    # rolling lookback of (op, qargs)
    hist = []
    pending = None  # (a,b,t,stage) awaiting "next op is CX with control t"
    blocks = defaultdict(Counter)  # stage -> rank -> count
    cur = None  # (a,b,t,stage,length)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
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
                    stack.append(name)
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    if not stack:
                        top = None
                continue
            if not line or line[:1].isspace():
                continue
            op = line.split(None, 1)[0]
            if op in SKIP:
                continue
            qs = [int(x) for x in QRE.findall(line.split(" if ")[0])]
            # resolve pending with this event
            if pending is not None:
                a, b, t, st = pending
                ok_out = op == "CX" and len(qs) == 2 and qs[0] == t
                if ok_out:
                    # term = consecutive same triple
                    if cur is not None and cur[:4] == (a, b, t, st):
                        cur = (a, b, t, st, cur[4] + 1)
                    else:
                        if cur is not None:
                            blocks[cur[3]][cur[4]] += 1
                        cur = (a, b, t, st, 1)
                else:
                    if cur is not None:
                        blocks[cur[3]][cur[4]] += 1
                        cur = None
                pending = None
            if op == "CCX" and len(qs) == 3:
                a, b, t = qs
                # lookback up to 8 events for a CX writing a and one writing b
                ha = hb = False
                for hop, hq in reversed(hist[-24:]):
                    if hop == "CX" and len(hq) == 2:
                        if hq[1] == a and hq[0] != b:
                            ha = True
                        if hq[1] == b and hq[0] != a:
                            hb = True
                if ha and hb:
                    pending = (a, b, t, top)
            # update stats
            if op in PAID:
                per_stage[top][op] += 1
            hist.append((op, qs))
            if len(hist) > 28:
                del hist[0]
    if cur is not None:
        blocks[cur[3]][cur[4]] += 1
    result = {
        "stages": {st: dict(c) for st, c in per_stage.items()},
        "rank_blocks": {st: {str(k): v for k, v in sorted(c.items())} for st, c in blocks.items()},
    }
    Path(out).write_text(json.dumps(result, indent=1))
    ranks = sorted({k for c in blocks.values() for k in c})
    print("rank", *[f"{r:>6d}" for r in ranks])
    for st in ("extract", "synthesis", "convert", "scan", "unconvert", "unsynthesis", "unextract"):
        print(f"{st[:12]:12s}", *[f"{blocks[st].get(r,0):6d}" for r in ranks])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
