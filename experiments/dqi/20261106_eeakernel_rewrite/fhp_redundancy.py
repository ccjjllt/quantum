"""full_head_product 3 templates: exact single + pair deletion via ANF."""
import itertools
import json
import re
import sys
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T")
OUT = Path("artifacts/20261106_eeakernel_rewrite/fhp_redundancy.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
KMX = TMP / "dqi891.kmx"
SPANS = {"fhp126": (13924713, 13929128), "fhp168": (13948965, 13955942),
         "fhp210": (13978497, 13988431)}
CAP = 800000


def load(s, e):
    ops = []
    wires = []
    seen = set()
    with open(KMX) as f:
        for ln, line in enumerate(f, 1):
            if s <= ln <= e and not line.startswith(("APPEND", "REGISTER", "INFO_TAG")):
                p = tuple(line.split())
                if p[0] not in ("CX", "CCX", "SWAP"):
                    raise ValueError(f"unexpected op: {p}")
                ops.append(p)
                for t in p[1:]:
                    if t.startswith("q") and t not in seen:
                        seen.add(t)
                        wires.append(t)
    return ops, wires


def anf_for(ops, wires, limit_combos=None):
    idx = {w: i for i, w in enumerate(wires)}
    poly = {w: set([frozenset([idx[w]])]) for w in wires}
    for p in ops:
        if p[0] == "CX":
            a, b = p[1], p[2]
            s = set(poly[b]) ^ set(poly[a])
            if len(s) > CAP:
                return None
            poly[b] = s
        elif p[0] == "CCX":
            a, b, t = p[1], p[2], p[3]
            prod = set()
            for x in poly[a]:
                for y in poly[b]:
                    prod.add(x | y)
                    if len(prod) > CAP:
                        return None
            s = set(poly[t]) ^ prod
            if len(s) > CAP:
                return None
            poly[t] = s
        elif p[0] == "SWAP":
            a, b = p[1], p[2]
            poly[a], poly[b] = poly[b], poly[a]
    return poly


def main():
    import time
    t0 = time.monotonic()
    out = {}
    for name, (s, e) in SPANS.items():
        ops, wires = load(s, e)
        base = anf_for(ops, wires)
        assert base is not None, name
        ccx = [i for i, p in enumerate(ops) if p[0] == "CCX"]
        red1 = []
        for k in ccx:
            m = anf_for([p for i, p in enumerate(ops) if i != k], wires)
            if m is not None and all(m[w] == base[w] for w in wires):
                red1.append(k)
        print({"template": name, "n_ccx": len(ccx), "singles": red1,
               "elapsed": round(time.monotonic() - t0, 1)}, flush=True)
        out[name] = {"n_ccx": len(ccx), "redundant_single": red1}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SINGLES DONE", flush=True)


if __name__ == "__main__":
    main()
