"""s3_broadcast.py: analyze literal-top (120,859) reuse chain in unextract.

Finds all unconditional CCX with controls {120,859} in unextract:
lines, targets, span; checks control-line stability across [L1,Lk]
(any write to q120/q859 between); checks target/control aliasing;
reports gap distribution for sub-interval options.

Writes artifacts/20261109_dqi_decoder_struct/s3_broadcast.json
"""
from __future__ import annotations
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_decoder_struct/s3_broadcast.json")
UNEXTRACT_ENTRY = 52196517  # 0-based index of @enter:unextract (see s1)


def main() -> None:
    stack: list[str] = []
    depth = 0
    occ: list[dict] = []  # {line, target}
    # touch log for q120/q859 within unextract: line -> op
    touches: list[dict] = []
    targets_counter: dict[int, int] = {}
    with open(KMX) as f:
        for idx, raw in enumerate(f):
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                elif tag.startswith("@exit:"):
                    if stack and stack[-1] == tag[6:]:
                        stack.pop()
                continue
            if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
                continue
            if l.startswith("PUSH_CONDITION"):
                depth += 1
                continue
            if l.startswith("POP_CONDITION"):
                depth -= 1
                continue
            parts = l.split()
            op = parts[0]
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]
                args = parts[1:-2]
            else:
                inline = None
                args = parts[1:]
            top = stack[0] if stack else "header"
            if top != "unextract":
                continue
            if op == "CCX" and depth == 0 and inline is None:
                a, b, t = (int(x[1:]) for x in args[:3])
                if {a, b} == {120, 859}:
                    occ.append({"line": idx, "a": a, "b": b, "t": t})
                    targets_counter[t] = targets_counter.get(t, 0) + 1
            # any write to q120/q859 (as target of CCX/CX, or X/SWAP/HMR/R/CSWAP...)
            if op in ("CCX", "CX", "X", "HMR", "R", "SWAP", "CSWAP"):
                # written wires: CCX->args[2], CX->args[1], X/HMR/R->args[0],
                # SWAP->both, CSWAP->args[1],args[2]
                if op == "CCX":
                    written = args[2:3]
                elif op == "CX":
                    written = args[1:2]
                elif op in ("X", "HMR", "R"):
                    written = args[0:1]
                elif op == "SWAP":
                    written = args[0:2]
                elif op == "CSWAP":
                    written = args[1:3]
                else:
                    written = []
                for w in written:
                    if w in ("q120", "q859"):
                        touches.append({"line": idx, "op": l[:60]})
    occ.sort(key=lambda o: o["line"])
    L1 = occ[0]["line"]
    Lk = occ[-1]["line"]
    mid = [t for t in touches if L1 < t["line"] < Lk]
    # target aliasing: target == 120 or 859?
    alias = [o for o in occ if o["t"] in (120, 859)]
    # distinct targets
    gaps = [occ[i + 1]["line"] - occ[i]["line"] for i in range(len(occ) - 1)]
    out = {
        "k": len(occ),
        "L1": L1, "Lk": Lk, "span": Lk - L1,
        "distinct_targets": len(targets_counter),
        "top_targets": sorted(targets_counter.items(), key=lambda kv: -kv[1])[:10],
        "control_midspan_writes": len(mid),
        "control_midspan_examples": mid[:20],
        "target_control_alias": len(alias),
        "gap_min": min(gaps), "gap_max": max(gaps),
        "gap_sorted": sorted(gaps)[:20],
        "first5": occ[:5], "last5": occ[-5:],
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("first5", "last5", "gap_sorted")}, indent=1))
    print("first5:", occ[:5])
    print("last5:", occ[-5:])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
