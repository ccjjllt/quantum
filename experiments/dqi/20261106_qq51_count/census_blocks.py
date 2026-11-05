"""Single-pass per-block wire/op census for named INFO_TAG spans."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

KMX = Path(sys.argv[1])
NAMES = sys.argv[2:]

spans = {t: [] for t in NAMES}
acc = {}
stack = []
with open(KMX) as f:
    for line in f:
        if line.startswith("INFO_TAG"):
            m = re.search(r"@(enter|exit):(.*)", line)
            if not m:
                continue
            kind, name = m.group(1), m.group(2).strip().strip("\"")
            if kind == "enter":
                if name in NAMES:
                    idx = len(spans[name])
                    acc[(name, idx)] = [set(), set(), False, 0, 0]
                stack.append(name)
            elif stack and stack[-1] == name:
                stack.pop()
                if name in NAMES:
                    spans[name].append(1)
        else:
            if stack and stack[-1] in NAMES:
                nm = stack[-1]
                idx = len(spans[nm])
                a = acc.get((nm, idx))
                if a is None:
                    continue
                p = line.split()
                if p[0] == "HMR":
                    a[2] = True
                if p[0] == "CCX":
                    a[3] += 1
                if p[0] == "CX":
                    a[4] += 1
                for t in p[1:]:
                    if t.startswith("q"):
                        a[0].add(int(t[1:]))
                        if p[0] in ("CX", "CCX") and t == p[-1]:
                            a[1].add(int(t[1:]))

out = {}
for nm in NAMES:
    sig = Counter()
    ex = None
    for idx in range(len(spans[nm])):
        a = acc.get((nm, idx))
        if a:
            sig[(len(a[0]), a[3], a[4], a[2])] += 1
            if ex is None:
                ex = {"wires": sorted(a[0]), "written": sorted(a[1]),
                      "read_only": sorted(a[0] - a[1])}
    out[nm] = {"calls": len(spans[nm]), "signatures": {str(k): v for k, v in sig.items()},
               "example": ex}
print(json.dumps(out, indent=2))
