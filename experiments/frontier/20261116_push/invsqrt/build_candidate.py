"""Build a width-reduced invsqrt candidate from a base .kmx plus retirement spec.

  python build_candidate.py <base.kmb> <spec.json> <out.kmx> [--no-renumber]

spec.json:
  {"retire": [{"wire": 22, "lo": 430, "hi": 6610,
               "zero": [26, 28],      # V = XOR of these wires at op `lo`
               "rebuild": [26, 28]}]} # V = XOR of these wires at op `hi`+1

Transformation per entry: at line `lo` insert  CX s q{w} for s in zero, then R q{w};
at line `hi+1` insert CX s q{w} for s in rebuild.

Then a physical-wire assignment is computed from the modified op list:
occupied(w) = dirty(w) union live(w); intervals of different logical wires that
overlap must get different physical wires; greedy interval colouring.
The x register keeps its first-segment colour also for its last segment.
"""
import json
import sys
from pathlib import Path

import kickmix


def parse_lines(path: Path):
    if path.suffix == ".kmb":
        c = kickmix.Circuit.from_file(path, format="auto")
        tmp = Path("/tmp/_build_base.kmx")
        c.to_file(tmp)
        text = tmp.read_text()
    else:
        text = path.read_text()
    return [l for l in text.splitlines() if l.strip()]


def op_args(parts):
    q = []
    for tok in parts[1:]:
        if tok.startswith("q"):
            q.append(int(tok[1:]))
    return q


def effects(kind, q):
    if kind == "CX":
        return [q[0]], [q[1]]
    if kind == "CCX":
        return [q[0], q[1]], [q[2]]
    if kind in ("CZ", "CCZ", "Z", "Z_POW"):
        return list(q), []
    if kind in ("X", "R"):
        return [], list(q)
    if kind in ("HMR", "SWAP"):
        return list(q), list(q)
    return [], []


def main() -> None:
    base = Path(sys.argv[1])
    spec = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {"retire": []}
    out = Path(sys.argv[3])
    renumber = "--no-renumber" not in sys.argv

    lines = parse_lines(base)
    nq = max(max(op_args(l.split()) or [-1]) for l in lines) + 1
    XW = 22

    ins_at = {}
    for r in spec.get("retire", []):
        w = r["wire"]
        ins_at.setdefault(r["lo"], []).extend(("CX", [s, w]) for s in r["zero"])
        ins_at[r["lo"]].append(("R", [w]))
        ins_at.setdefault(r["hi"] + 1, []).extend(("CX", [s, w]) for s in r["rebuild"])

    new_lines = []
    seq = []  # (kind, qargs) for analysis
    for i, l in enumerate(lines):
        for (k, q) in ins_at.get(i, []):
            new_lines.append(f"{k} " + " ".join(f"q{x}" for x in q))
            seq.append((k, q))
        new_lines.append(l)
        parts = l.split()
        seq.append((parts[0], op_args(parts)))
    for (k, q) in ins_at.get(len(lines), []):
        new_lines.append(f"{k} " + " ".join(f"q{x}" for x in q))
        seq.append((k, q))
    print(f"ops {len(lines)} -> {len(seq)} (+{len(seq) - len(lines)})")

    # liveness
    live_mask = [0] * len(seq)
    live = set()
    for i in range(len(seq) - 1, -1, -1):
        kind, q = seq[i]
        rd, wr = effects(kind, q)
        live = (live - set(wr)) | set(rd)
        live_mask[i] = sum(1 << w for w in live)

    # dirty intervals
    clean = [w >= XW for w in range(nq)]
    start = [0 if w < XW else None for w in range(nq)]
    iv = [[] for _ in range(nq)]
    for i, (kind, q) in enumerate(seq):
        for w in q:
            if clean[w]:
                clean[w] = False
                start[w] = i
        if kind == "HMR":
            w = q[0]
            if start[w] is not None:
                iv[w].append((start[w], i))
                start[w] = None
            clean[w] = True
    for w in range(nq):
        if start[w] is not None:
            iv[w].append((start[w], len(seq) - 1))

    def runs(mask_fn):
        return mask_fn()

    occ = [[] for _ in range(nq)]
    for w in range(nq):
        segs = list(iv[w])
        # live runs become intervals too
        i = 0
        while i < len(seq):
            if live_mask[i] >> w & 1:
                j = i
                while j + 1 < len(seq) and live_mask[j + 1] >> w & 1:
                    j += 1
                segs.append((i, j))
                i = j + 1
            else:
                i += 1
        segs.sort()
        merged = []
        for (a, b) in segs:
            if merged and a <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        occ[w] = merged

    cnt = [0] * len(seq)
    for w in range(nq):
        for (a, b) in occ[w]:
            for i in range(a, b + 1):
                cnt[i] += 1
    print("peak occupied", max(cnt), "at", [i for i, c in enumerate(cnt) if c == max(cnt)][:5])

    if not renumber:
        out.write_text("\n".join(new_lines) + "\n")
        print("wrote", out, "(no renumber)")
        return

    # colour
    intervals = []
    for w in range(nq):
        for k, (a, b) in enumerate(occ[w]):
            intervals.append((a, b, w, k))
    intervals.sort()
    parent = {(w, k): (w, k) for w in range(nq) for k in range(len(occ[w]))}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for w in range(XW):
        if len(occ[w]) >= 2:
            union((w, 0), (w, len(occ[w]) - 1))

    colour = {}
    active = {}
    ncol = 0
    for (a, b, w, k) in intervals:
        root = find((w, k))
        if root in colour:
            c = colour[root]
        else:
            used = {cc for cc, e in active.items() if e >= a}
            c = 0
            while c in used:
                c += 1
            ncol = max(ncol, c + 1)
            colour[root] = c
        colour[(w, k)] = colour[root]
        active[c] = max(active.get(c, -1), b)
    print("colouring ->", ncol, "physical wires")

    # per line colour lookup
    def colour_at(w, t):
        for k, (a, b) in enumerate(occ[w]):
            if a <= t <= b:
                return colour[(w, k)]
        raise KeyError((w, t))

    finals = []
    for i, l in enumerate(new_lines):
        pass
    # rewrite: need sequence index aligned with new_lines
    seq_pos = []
    j = 0
    for i, l in enumerate(lines):
        for _ in ins_at.get(i, []):
            seq_pos.append(j)
            j += 1
        seq_pos.append(j)
        j += 1
    pos_of_line = seq_pos  # not used directly

    # simpler: rebuild with an explicit walk
    res = []
    k = 0
    for i, l in enumerate(lines):
        for (kind, q) in ins_at.get(i, []):
            res.append(f"{kind} " + " ".join(f"q{colour_at(w, k)}" for w in q))
            k += 1
        parts = l.split()
        qa = op_args(parts)
        if parts[0] in ("APPEND_TO_REGISTER", "REGISTER"):
            res.append(l)
            k += 1
            continue
        newq = [colour_at(w, k) for w in qa]
        rest = [t for t in parts[1:] if not t.startswith("q")]
        res.append(" ".join([parts[0]] + [f"q{x}" for x in newq] + rest))
        k += 1
    for (kind, q) in ins_at.get(len(lines), []):
        res.append(f"{kind} " + " ".join(f"q{colour_at(w, k)}" for w in q))
        k += 1

    # register lines: colour of x_i first segment
    reg_colour = [colour[(w, 0)] for w in range(XW)]
    final = []
    for l in res:
        parts = l.split()
        if parts[0] == "APPEND_TO_REGISTER":
            idx = int(parts[1][1:])
            final.append(f"APPEND_TO_REGISTER q{reg_colour[idx]} {parts[2]}")
        else:
            final.append(l)
    out.write_text("\n".join(final) + "\n")
    print("register colours", reg_colour)
    print("wrote", out)


if __name__ == "__main__":
    main()
