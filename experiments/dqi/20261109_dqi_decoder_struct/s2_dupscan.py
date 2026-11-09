"""s2_dupscan.py: search structural (non-cache) rewrite candidates.

A. Adjacent duplicate CZ pairs (same args + same condition): CCX-free phase
   fixups; a pair cancels exactly (CZ^2=I). Counts per top-level stage.
B. R qX ... HMR qX with no qX touch between (provision-measure pairs),
   plus whether the HMR outcome bit is ever read later.
C. Unextract PUSH_CONDITION region map (count/sizes/bits).
D. Multiply-v x6 block identity check: identical wire lists?

Writes artifacts/20261109_dqi_decoder_struct/s2_dupscan.json
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_decoder_struct/s2_dupscan.json")


def norm_cond(args, inline, depth_bits):
    if inline is not None:
        return ("inline", inline)
    if depth_bits:
        return ("stack", tuple(depth_bits))
    return ("none",)


def main() -> None:
    stack: list[str] = []
    depth = 0
    cstack: list[str] = []
    prev_cz = {}   # per stage: last CZ descriptor (for adjacency)
    dup_cz: dict[str, list] = {}
    # R/HMR tracking per qubit: last R line with no intervening touch
    last_R: dict[str, int] = {}
    touched_since_R: dict[str, bool] = {}
    r_hmr_pairs: list = []
    # HMR outcome bit uses
    hmr_bit: dict[str, int] = {}   # bit -> producing line
    bit_reads: Counter = Counter()
    push_regions: dict[str, list] = {}
    region_start = None
    pending_bit = None
    mult_blocks: list = []
    cur_mult = None

    with open(KMX) as f:
        for idx, raw in enumerate(f):
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                    if len(stack) == 2 and stack[1].startswith("multiply"):
                        cur_mult = {"entry": idx, "tag": stack[1], "ops": []}
                elif tag.startswith("@exit:"):
                    if cur_mult is not None and len(stack) == 2 and stack[1].startswith("multiply"):
                        cur_mult["exit"] = idx
                        mult_blocks.append(cur_mult)
                        cur_mult = None
                    name = tag[6:]
                    if stack and stack[-1] == name:
                        stack.pop()
                continue
            if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
                continue
            if l.startswith("PUSH_CONDITION"):
                bit = l.split()[-1]
                cstack.append(bit)
                depth += 1
                if depth == 1 and stack:
                    region_start = idx
                    pending_bit = bit
                continue
            if l.startswith("POP_CONDITION"):
                if cstack:
                    cstack.pop()
                depth -= 1
                if depth == 0 and region_start is not None and stack:
                    push_regions.setdefault(stack[0], []).append(
                        {"bit": pending_bit, "start": region_start, "end": idx,
                         "len": idx - region_start})
                    region_start = None
                continue
            parts = l.split()
            op = parts[0]
            if op in ("BIT_INVERT", "BIT_STORE0", "BIT_STORE1"):
                # BIT_INVERT dst if src... / BIT_STORE1 dst if src
                if len(parts) >= 4 and parts[-2] == "if":
                    bit_reads[parts[-1]] += 1
                continue
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]
                args = parts[1:-2]
                bit_reads[inline] += 1
            else:
                inline = None
                args = parts[1:]
            top = stack[0] if stack else "header"
            cond = norm_cond(args, inline, cstack if depth else [])
            if op == "CZ":
                desc = (tuple(args), cond)
                if top in prev_cz and prev_cz[top] == desc:
                    dup_cz.setdefault(top, []).append({"line": idx, "desc": [list(args), list(cond)]})
                    prev_cz[top] = None  # avoid triple-count overlap
                else:
                    prev_cz[top] = desc
            else:
                # any non-CZ line breaks adjacency (conservative: only immediate adjacency)
                if top in prev_cz:
                    # keep prev only if this line is also CZ-handled above; else reset
                    prev_cz[top] = None
            if cur_mult is not None and op in ("CCX", "CX", "HMR", "R", "CZ", "X"):
                cur_mult["ops"].append(l)
            # R/HMR pair tracking (qubit-indexed, global)
            if op == "R" and not inline and depth == 0:
                q = args[0]
                last_R[q] = idx
                touched_since_R[q] = False
            elif op == "HMR" and not inline and depth == 0:
                q = args[0]
                bit = args[1] if len(args) > 1 else None
                if q in last_R and not touched_since_R.get(q, True):
                    r_hmr_pairs.append({"R": last_R[q], "HMR": idx, "q": q, "bit": bit,
                                        "top": top})
                if bit:
                    hmr_bit[bit] = idx
                last_R.pop(q, None)
            else:
                # mark touched qubits
                for a in args:
                    if a.startswith("q") and a[1:].isdigit():
                        if a in last_R:
                            touched_since_R[a] = True
    # outcome-bit liveness for R-HMR pairs
    live = 0
    for p in r_hmr_pairs:
        p["bit_used_later"] = bit_reads.get(p["bit"], 0)
        if p["bit_used_later"]:
            live += 1
    # multiply identity
    mult_sig = Counter()
    for m in mult_blocks:
        sig = "\n".join(m["ops"])
        mult_sig[sig] += 1
    out = {
        "dup_cz_counts": {k: len(v) for k, v in dup_cz.items()},
        "dup_cz_examples": {k: v[:5] for k, v in dup_cz.items()},
        "r_hmr_pairs": len(r_hmr_pairs),
        "r_hmr_bit_live": live,
        "r_hmr_examples": r_hmr_pairs[:10],
        "push_regions": {k: {"n": len(v),
                             "len_hist": Counter([r["len"] for r in v]),
                             "bits": Counter([r["bit"] for r in v]).most_common(8),
                             "examples": v[:5]} for k, v in push_regions.items()},
        "multiply_blocks": len(mult_blocks),
        "multiply_distinct_bodies": len(mult_sig),
        "multiply_body_counts": list(mult_sig.values()),
        "multiply_paid": [sum(1 for o in m["ops"] if o.startswith(("CCX", "CCZ", "CSWAP"))) for m in mult_blocks],
        "multiply_spans": [[m["entry"], m["exit"]] for m in mult_blocks],
    }
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "r_hmr_examples"}, indent=1, default=str)[:3000])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
