"""Windowed op-type profiles of the submission (58.3M) and reference (86M) DQI circuits."""
import json
import sys
from collections import Counter
from pathlib import Path

SUB = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx")
REF = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dqi.kmb")
OUT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify")
WIN = 500_000


def profile(path, fmt, tag):
    import io
    import kickmix as km
    c = km.Circuit.from_file(path, format=fmt)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    counts = []
    cur = Counter()
    n = 0
    total = Counter()
    for line in buf.getvalue().splitlines():
        if line.startswith(("APPEND", "REGISTER")):
            continue
        tag_op = line.split()[0]
        cur[tag_op] += 1
        total[tag_op] += 1
        n += 1
        if n % WIN == 0:
            counts.append(dict(cur))
            cur = Counter()
    if cur:
        counts.append(dict(cur))
    print("=== %s ops %d windows %d" % (tag, n, len(counts)), flush=True)
    print("total", dict(total), flush=True)
    json.dump({"total": dict(total), "windows": counts, "win": WIN},
              open(OUT / ("profile_%s.json" % tag), "w"))
    for i, w in enumerate(counts):
        print("win %3d  CX %7d CCX %6d CZ %6d HMR %5d R %5d X %5d %s" % (
            i, w.get("CX", 0), w.get("CCX", 0), w.get("CZ", 0), w.get("HMR", 0),
            w.get("R", 0), w.get("X", 0),
            "".join("%s:%d " % (k, v) for k, v in sorted(w.items()) if k not in
                    ("CX", "CCX", "CZ", "HMR", "R", "X", "APPEND_TO_REGISTER"))[:60]),
            flush=True)


if __name__ == "__main__":
    profile(SUB, "kmx", "submission")
    profile(REF, "kmb", "reference")
