"""Task2b: joint-cache product distinctness + dead-wire (HMR-hoist) check.

(a) Pairwise XOR popcount of the 4 pair-products at a common point in the global
    intersection (idx 25700) -- if any two coincide, one cache wire could serve both.
(b) For task2 pairs and task1 groups: untouched wires whose value is never read
    after span start (globally dead => HMR-hoist could manufacture a clean wire;
    next touch HMR/R or none). Static scan, no sim.
"""
import io
import json
from pathlib import Path

import kickmix as km
import numpy as np

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
N_INPUTS = 3133452
N_WORDS = (N_INPUTS + 63) // 64


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def main():
    ops = parse_ops()
    n = len(ops)

    # ---- (a) product distinctness at idx 25700 ----
    prod_wires = [0, 59, 4, 51, 7, 57, 10, 61]
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    last_mask = (np.uint64(1) << np.uint64(N_INPUTS % 64)) - np.uint64(1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF))
    ones[-1] = last_mask
    depth = 0
    for idx, l in enumerate(ops):
        if idx == 25700:
            snap = {w: q[w].copy() for w in prod_wires}
            break
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in l):
            continue
        p = l.split()
        op = p[0]
        if op in ("HMR", "R"):
            q[int(p[1][1:])].fill(0)
        elif op == "X":
            q[int(p[1][1:])] ^= ones
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[b] ^= q[a]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[a], q[b] = q[b].copy(), q[a].copy()
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            q[t] ^= (q[a] & q[b])
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            d = q[a] ^ q[b]
            pr = q[cc] & d
            q[a] ^= pr
            q[b] ^= pr
    pairs = [(0, 59), (4, 51), (7, 57), (10, 61)]
    prods = [(a, b, snap[a] & snap[b]) for a, b in pairs]
    print("pairwise product XOR popcounts @25700 (0 => identical functions):")
    for i in range(4):
        for j in range(i + 1, 4):
            d = (prods[i][2] ^ prods[j][2]).copy()
            d[-1] &= last_mask
            print(f"  p{i} (q{pairs[i][0]}&q{pairs[i][1]}) vs p{j}: "
                  f"{int(np.sum(np.bitwise_count(d)))}")

    # ---- (b) dead-wire check: next touch after span start ----
    t1 = json.load(open("experiments/invsqrt/20261109_cache_borrow_mincut/"
                        "task1_groups.json"))
    t2 = json.load(open("experiments/invsqrt/20261109_cache_borrow_mincut/"
                        "task2_borrow.json"))
    all_touch = {w: [] for w in range(62)}
    for i, l in enumerate(ops):
        if l.startswith(("PUSH", "POP")):
            continue
        for t in l.split()[1:]:
            if t.startswith("q") and t[1:].isdigit() and " " not in t and "b" not in t:
                w = int(t[1:])
                if 0 <= w < 62:
                    all_touch[w].append(i)
    # NOTE: tokens like 'b12600' contain no 'q'; guard tokens 'if' skipped by digit test
    import bisect

    def next_touch(w, pos):
        tl = all_touch[w]
        k = bisect.bisect_right(tl, pos)
        return tl[k] if k < len(tl) else None

    print("--- task2 pairs: untouched wires, next touch after span start ---")
    for pr in t2["pairs"]:
        a, b = pr["span"]
        info = []
        for w in pr["untouched"]:
            nt = next_touch(w, a)
            nop = ops[nt] if nt is not None else "END(dead)"
            info.append((w, nt, nop))
        pr["next_touch_after_start"] = [(w, nt, nop) for w, nt, nop in info]
        dead = [(w, nt) for w, nt, nop in info
                if nt is None or nop.split()[0] in ("HMR", "R")]
        print(f"{pr['name']} [{a},{b}]: next-touch sample={info[:6]}")
        print(f"   dead-or-hmr-next (HMR-hoistable): {dead}")

    print("--- task1 groups: untouched wires, next touch after span start ---")
    for g in t1["groups_k_ge_2"]:
        a, b = g["span"]
        dead = []
        for w in g["untouched"]:
            nt = next_touch(w, a)
            nop = ops[nt].split()[0] if nt is not None else "END"
            if nt is None or nop in ("HMR", "R"):
                dead.append((w, nt, ops[nt] if nt is not None else "END"))
        g["hmr_hoistable"] = dead
        print(f"{g['sym']} [{a},{b}]: hoistable={dead}")

    json.dump(t2, open("experiments/invsqrt/20261109_cache_borrow_mincut/"
                       "task2_borrow.json", "w"), indent=2)
    json.dump(t1, open("experiments/invsqrt/20261109_cache_borrow_mincut/"
                       "task1_groups.json", "w"), indent=2)
    print("updated JSONs with next-touch info")


if __name__ == "__main__":
    main()
