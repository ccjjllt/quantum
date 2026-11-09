"""s1_blocks.py: per-subblock paid-gate census for extract/scan/unextract + conditionals.

Single streaming pass over the kmx cache. Records for every L2 block
(tag + entry/exit line): counts of CCX/CCZ/CSWAP/CX + conditional depth usage.
Also collects PUSH_CONDITION bit ids used per top-level stage.

Writes artifacts/20261109_dqi_decoder_struct/s1_blocks.json
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_decoder_struct/s1_blocks.json")

PAID = ("CCX", "CCZ", "CSWAP")


def main() -> None:
    stack: list[str] = []
    # current L2 block accumulator
    cur = None  # dict(tag, top, entry, ops Counter, cond_ops Counter, cond_bits set)
    blocks: list[dict] = []
    top_cond_bits: dict[str, Counter] = {}
    top_cond_ops: dict[str, int] = Counter()
    top_ops: dict[str, Counter] = {}
    depth = 0
    cur_cond_stack: list[str] = []

    def flush():
        nonlocal cur
        if cur is not None:
            cur["ops"] = dict(cur["ops"])
            cur["cond_ops"] = dict(cur["cond_ops"])
            cur["cond_bits"] = sorted(cur["cond_bits"])
            blocks.append(cur)
            cur = None

    with open(KMX) as f:
        for idx, raw in enumerate(f):
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                    if len(stack) == 2:
                        flush()
                        cur = {"tag": stack[1], "top": stack[0], "entry": idx,
                               "ops": Counter(), "cond_ops": Counter(), "cond_bits": set()}
                elif tag.startswith("@exit:") and stack:
                    if len(stack) == 2:
                        if cur is not None:
                            cur["exit"] = idx
                            flush()
                    name = tag[6:]
                    if stack and stack[-1] == name:
                        stack.pop()
                    else:
                        for k in range(len(stack) - 1, -1, -1):
                            if stack[k] == name:
                                del stack[k]
                                break
                continue
            if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION", "BIT_")):
                continue
            if l.startswith("PUSH_CONDITION"):
                parts = l.split()
                bit = parts[1] if len(parts) > 1 else "?"
                cur_cond_stack.append(bit)
                depth += 1
                if stack:
                    top_cond_bits.setdefault(stack[0], Counter())[bit] += 1
                continue
            if l.startswith("POP_CONDITION"):
                if cur_cond_stack:
                    cur_cond_stack.pop()
                depth -= 1
                continue
            parts = l.split()
            op = parts[0]
            inline = None
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]
            top = stack[0] if stack else "header"
            top_ops.setdefault(top, Counter())[op] += 1
            if depth > 0 or inline is not None:
                top_cond_ops[top] += 1
            if cur is not None and len(stack) >= 2:
                cur["ops"][op] += 1
                if depth > 0 or inline is not None:
                    cur["cond_ops"][op] += 1
                    for b in cur_cond_stack:
                        cur["cond_bits"].add(b)
                    if inline is not None:
                        cur["cond_bits"].add(inline)
    flush()
    # summaries per (top, tag-head)
    summ: dict[str, dict] = {}
    for b in blocks:
        key = f"{b['top']}/{b['tag'].split()[0]}"
        s = summ.setdefault(key, {"n": 0, "paid": [], "cx": [], "lines": []})
        paid = sum(b["ops"].get(k, 0) for k in PAID)
        s["n"] += 1
        s["paid"].append(paid)
        s["cx"].append(b["ops"].get("CX", 0))
        s["lines"].append(b["exit"] - b["entry"] + 1)
    summary = {}
    for k, s in summ.items():
        import statistics as st
        summary[k] = {"n": s["n"], "paid_min": min(s["paid"]), "paid_max": max(s["paid"]),
                      "paid_mean": sum(s["paid"]) / len(s["paid"]),
                      "cx_mean": sum(s["cx"]) / len(s["cx"]),
                      "lines_mean": sum(s["lines"]) / len(s["lines"])}
    out = {
        "top_ops": {k: dict(v) for k, v in top_ops.items()},
        "top_cond_ops": dict(top_cond_ops),
        "top_cond_bits_distinct": {k: len(v) for k, v in top_cond_bits.items()},
        "block_summary": summary,
        "n_blocks": len(blocks),
    }
    # keep full block list separately (large) - store compact rows
    out["blocks_compact"] = [
        {"tag": b["tag"], "top": b["top"], "entry": b["entry"], "exit": b["exit"],
         "paid": sum(b["ops"].get(k, 0) for k in PAID),
         "CCX": b["ops"].get("CCX", 0), "CCZ": b["ops"].get("CCZ", 0),
         "CSWAP": b["ops"].get("CSWAP", 0), "CX": b["ops"].get("CX", 0),
         "cond": dict(b["cond_ops"]), "cond_bits": b["cond_bits"][:8]}
        for b in blocks
    ]
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"blocks={len(blocks)}")
    for k in sorted(summary):
        s = summary[k]
        print(f"{k}: n={s['n']} paid_mean={s['paid_mean']:.1f} [{s['paid_min']},{s['paid_max']}] cx_mean={s['cx_mean']:.1f}")
    print("top_cond_ops:", dict(top_cond_ops))
    print("top_cond_bits_distinct:", {k: len(v) for k, v in top_cond_bits.items()})
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
