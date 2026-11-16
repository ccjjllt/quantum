"""Q-reduction planner: retire wires by XOR identities, then interval-colour to a physical width.

Usage:
  python plan_q.py <circuit.kmb> [--retire w=R:B:s1,s2,... ...] [--pinx] [--verbose]

--retire q22=7400:20510:q26,q28   means: at line 7400 zero q22 with CX s q22 for s in {q26,q28};
                                  at line 20510 rebuild with the same CXs.
The identity must be supplied by the caller (found by the Kaggle probe); this script only
validates the structural side: interval structure, occupancy, colouring, register pinning.
"""
import sys
from pathlib import Path

from analyze_live import effect, load_ops


def parse_retire(args):
    out = []
    for a in args:
        if "=" not in a or a.count(":") != 2:
            continue
        w, rest = a.split("=")
        lo, hi, srcs = rest.split(":")
        srcs = [s for s in srcs.replace("q", "").split(",") if s]
        out.append((int(w.replace("q", "")), int(lo), int(hi), [int(s) for s in srcs]))
    return out


def main() -> None:
    path = Path(sys.argv[1])
    retires = parse_retire(sys.argv[2:])
    ops = load_ops(path)
    n = max(max(o["q"]) for o in ops if o["q"]) + 1
    XW = 22
    nlines = len(ops)

    # build modified op sequence with inserted CXs (only affects line indices)
    insert_zero = {}
    insert_rebuild = {}
    for (w, lo, hi, srcs) in retires:
        insert_zero.setdefault(lo, []).extend((s, w) for s in srcs)
        insert_rebuild.setdefault(hi + 1, []).extend((s, w) for s in srcs)

    seq = []  # (op, qargs) with qargs possibly empty for inserted CX
    for i, o in enumerate(ops):
        for (s, t) in insert_zero.get(i, []):
            seq.append(("CX", [s, t]))
        for (s, t) in insert_rebuild.get(i, []):
            seq.append(("CX", [s, t]))
        seq.append((o["op"], list(o["q"])))
    print(f"ops {len(ops)} -> {len(seq)} (+{len(seq) - len(ops)} inserted CX)")

    # liveness on modified sequence
    live_mask = [0] * len(seq)
    live = set()
    for i in range(len(seq) - 1, -1, -1):
        m, q = seq[i]
        if m in ("CX",):
            rd, wr = [q[0]], [q[1]]
        elif m == "CCX":
            rd, wr = [q[0], q[1]], [q[2]]
        elif m in ("CZ", "CCZ", "Z", "Z_POW"):
            rd, wr = list(q), []
        elif m == "X":
            rd, wr = [], list(q)
        elif m in ("HMR", "SWAP"):
            rd, wr = list(q), list(q)
        else:
            rd, wr = [], []
        live = (live - set(wr)) | set(rd)
        live_mask[i] = sum(1 << w for w in live)

    # dirty intervals
    clean = [w >= XW for w in range(n)]
    start = [0 if w < XW else None for w in range(n)]
    iv = [[] for _ in range(n)]
    for i, (m, q) in enumerate(seq):
        for w in q:
            if clean[w]:
                clean[w] = False
                start[w] = i
        if m == "HMR":
            w = q[0]
            if start[w] is not None:
                iv[w].append((start[w], i))
                start[w] = None
            clean[w] = True
    for w in range(n):
        if start[w] is not None:
            iv[w].append((start[w], len(seq) - 1))

    # forced-clean windows from the retire specs: the wire is |0> between zero and rebuild
    for (w, lo, hi, srcs) in retires:
        newiv = []
        for (a, b) in iv[w]:
            if b < lo or a > hi:
                newiv.append((a, b))
                continue
            if a < lo:
                newiv.append((a, lo - 1))
            if b > hi:
                newiv.append((hi + 1, b))
        iv[w] = newiv
        for i in range(max(0, lo), min(len(seq), hi + 1)):
            live_mask[i] &= ~(1 << w)
    nseg = {w: len(iv[w]) for w in range(n)}
    print("x-wire segments:", {w: nseg[w] for w in range(XW)})
    print("scratch segments:", {w: nseg[w] for w in range(XW, n)})

    occ = [0] * len(seq)
    for w in range(n):
        for (a, b) in iv[w]:
            for i in range(a, b + 1):
                occ[i] |= 1 << w
    for i in range(len(seq)):
        # live implies occupied
        occ[i] |= live_mask[i]
    cnt = [bin(x).count("1") for x in occ]
    print(f"peak occupied {max(cnt)}")
    runs, st = [], None
    for i, c in enumerate(cnt):
        if c == max(cnt) and st is None:
            st = i
        elif c != max(cnt) and st is not None:
            runs.append((st, i - 1))
            st = None
    if st is not None:
        runs.append((st, len(cnt) - 1))
    print("top runs at peak:", sorted(((b - a + 1, a, b) for a, b in runs), reverse=True)[:6])

    # interval colouring with x pinning: first and last segment of each x wire share a colour
    intervals = []
    for w in range(n):
        for k, (a, b) in enumerate(iv[w]):
            intervals.append((a, b, w, k))
    intervals.sort()
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    keys = [(w, k) for (_, _, w, k) in intervals]
    for k in keys:
        parent[k] = k
    for w in range(XW):
        if len(iv[w]) >= 2:
            union((w, 0), (w, len(iv[w]) - 1))

    colour = {}
    active = {}  # colour -> end time

    def free_at(t):
        return [c for c, e in active.items() if e < t]

    ncol = 0
    for (a, b, w, k) in intervals:
        key = (w, k)
        root = find(key)
        if root in colour:
            c = colour[root]
        else:
            cands = sorted(free_at(a))
            if cands:
                c = cands[0]
            else:
                c = ncol
                ncol += 1
            colour[root] = c
        colour[key] = colour[root]
        active[c] = max(active.get(c, -1), b)
    print(f"interval colouring -> {ncol} physical wires ({len(intervals)} intervals)")
    # report per-wire colour sets
    multi = {w: sorted({colour[(w, k)] for k in range(len(iv[w]))}) for w in range(n)}
    print("x-wire colours:", {w: multi[w] for w in range(XW)})
    print("scratch colours:", {w: multi[w] for w in range(XW, n)})


if __name__ == "__main__":
    main()
