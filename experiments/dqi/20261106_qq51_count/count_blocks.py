"""Histogram CCX per span for every INFO_TAG block type (nesting-aware)."""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1])


def main():
    stack = []  # [tag, ccx]
    hist = {}
    counts = {}
    total = 0
    with open(KMX) as f:
        for line in f:
            total += 1
            if line.startswith("INFO_TAG"):
                parts = line.split(None, 1)
                tag = parts[1].strip().strip('"') if len(parts) > 1 else ""
                if tag.startswith("@enter:"):
                    name = tag[len("@enter:"):]
                    stack.append([name, 0])
                    counts[name] = counts.get(name, 0) + 1
                elif tag.startswith("@exit:"):
                    name = tag[len("@exit:"):]
                    if stack and stack[-1][0] == name:
                        _, c = stack.pop()
                        h = hist.setdefault(name, {})
                        h[c] = h.get(c, 0) + 1
                    else:
                        hist.setdefault("MISMATCH_" + name, {}).__setitem__("x", 1)
            elif line.startswith("CCX"):
                for s in stack:
                    s[1] += 1
    out = {"total_lines": total, "block_calls": counts,
           "ccx_per_span": {k: dict(sorted(v.items())) for k, v in sorted(hist.items())}}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
