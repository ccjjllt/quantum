"""Norm triples + multiply-v singles exact deletion. Read-only; no verifier."""
import itertools
import json
import sys
import time
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T")
OUT = Path("artifacts/20261106_eeakernel_rewrite/template_triples_norm.json")
CAP = 600000


def anf_for(ops, wires, idx):
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
        else:
            return None
    return poly


def check_deletions(ops, wires, idx, sizes):
    base = anf_for(ops, wires, idx)
    assert base is not None
    ccx = [i for i, p in enumerate(ops) if p[0] == "CCX"]
    out = {}
    import math
    for k in sizes:
        found = []
        total = 0
        for combo in itertools.combinations(ccx, k):
            total += 1
            drop = set(combo)
            m = anf_for([p for i, p in enumerate(ops) if i not in drop], wires, idx)
            if m is not None and all(m[w] == base[w] for w in wires):
                found.append(list(combo))
        out[k] = {"tested": total, "redundant": found}
        print(json.dumps({"k": k, "tested": total, "found": len(found)}), flush=True)
    return out


def main():
    t0 = time.monotonic()
    res = {}
    d = json.load(open(TMP / "norm_template.json"))
    ops = [tuple(p) for p in d["ops"]]
    wires = d["wires"]
    idx = {w: i for i, w in enumerate(wires)}
    print(json.dumps({"template": "norm", "n_ccx": sum(1 for p in ops if p[0] == "CCX")}), flush=True)
    res["norm"] = check_deletions(ops, wires, idx, [3])
    # multiply-v template single deletion (interface 20->7; ANF may blow up -> recorded, not fatal)
    try:
        d2 = json.load(open(TMP / "prod_template.json"))
    except FileNotFoundError:
        d2 = None
    if d2 is not None:
        ops2 = [tuple(p) for p in d2["ops"]]
        wires2 = d2["wires"]
        idx2 = {w: i for i, w in enumerate(wires2)}
        base2 = anf_for(ops2, wires2, idx2)
        if base2 is None:
            res["multiply_v"] = {"note": "ANF blowup at baseline; left for targeted follow-up"}
            print(json.dumps({"multiply_v": "baseline ANF blowup"}), flush=True)
        else:
            ccx2 = [i for i, p in enumerate(ops2) if p[0] == "CCX"]
            red = []
            for k in ccx2:
                m = anf_for([p for i, p in enumerate(ops2) if i != k], wires2, idx2)
                if m is not None and all(m[w] == base2[w] for w in wires2):
                    red.append(k)
            res["multiply_v"] = {"n_ccx": len(ccx2), "redundant_single": red}
            print(json.dumps({"multiply_v_singles": red}), flush=True)
    res["wall_seconds"] = round(time.monotonic() - t0, 1)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({"done": True, "wall": res["wall_seconds"]}))


if __name__ == "__main__":
    main()
