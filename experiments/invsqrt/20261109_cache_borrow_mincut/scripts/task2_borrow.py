"""Task2: [25300:28200] borrow-cost accounting for the 4 valid pairs.

- Re-verify control/target word equality at endpoints (before gate application).
- Check unconditionality (depth==0, no `if`) of the 8 endpoint CCX.
- Per-pair static untouched-wire table + zero/one flags at span start.
- Pairwise span overlap + global intersection.
- Borrow models: clean wire net -(k-1); dirty wire per-use 4-gate identity
  [CCX a b d][CX d t][CCX a b d][CX d t] (net +1 CCX per replaced gate);
  joint k=4 (distinct products), relay split, shortest-span subset.
- Verify (q26&q18) absence; re-check the 6 invalid pairs' mismatch popcounts.
"""
import io
import json
from pathlib import Path

import kickmix as km
import numpy as np

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
WLO, WHI = 25300, 28200
N_INPUTS = 3133452
N_WORDS = (N_INPUTS + 63) // 64

VALID = [
    ("CCX q0 q59 q21", 25512, 28198),
    ("CCX q4 q51 q21", 25641, 27995),
    ("CCX q7 q57 q21", 25670, 28028),
    ("CCX q10 q61 q21", 25699, 28074),
]
INVALID = [
    ("CCX q41 q30 q51", 25323, 25615),
    ("CCX q46 q30 q41", 25629, 27998),
    ("CCX q21 q26 q41", 25704, 28079),
    ("CCX q50 q47 q41", 28031, 28126),
    ("CCX q57 q56 q28", 28035, 28129),
    ("CCX q51 q31 q28", 28001, 28160),
]


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def main():
    ops = parse_ops()
    # unconditionality of the 8 endpoints
    depth = 0
    is_uncond = {}
    for idx, l in enumerate(ops):
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if l.startswith("CCX"):
            is_uncond[idx] = (depth == 0 and (" if " not in l))

    endpoints = sorted({a for _, a, _ in VALID + INVALID} |
                       {b for _, _, b in VALID + INVALID})
    starts = {a for _, a, _ in VALID}
    need = {}
    for _, a, b in VALID + INVALID:
        for i in (a, b):
            p = ops[i].split()
            need.setdefault(i, set()).update(
                [int(p[1][1:]), int(p[2][1:]), int(p[3][1:])])

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

    snap, zero_at = {}, {}
    depth = 0
    for idx, l in enumerate(ops):
        if idx in endpoints:
            snap[idx] = {w: q[w].copy() for w in need[idx]}
            if idx in starts:
                zf = {}
                for w in range(62):
                    a = q[w].copy()
                    a[-1] &= last_mask
                    if not np.any(a):
                        zf[w] = 0
                    else:
                        o = (a ^ ones).copy()
                        o[-1] &= last_mask
                        zf[w] = 1 if not np.any(o) else 2
                zero_at[idx] = zf
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

    def weq(x, y):
        xx, yy = x.copy(), y.copy()
        xx[-1] &= last_mask
        yy[-1] &= last_mask
        return bool(np.array_equal(xx, yy))

    def popxor(x, y):
        d = (x ^ y).copy()
        d[-1] &= last_mask
        return int(np.sum(np.bitwise_count(d)))

    def untouched(a, b):
        out = []
        for w in range(62):
            wq = f"q{w}"
            hit = False
            for j in range(a + 1, b):
                lj = ops[j]
                if lj.startswith(("PUSH", "POP")):
                    continue
                if wq in lj.split()[1:]:
                    hit = True
                    break
            if not hit:
                out.append(w)
        return out

    def touch_count(a, b):
        cnt = {}
        for w in range(62):
            wq = f"q{w}"
            c = 0
            for j in range(a + 1, b):
                lj = ops[j]
                if lj.startswith(("PUSH", "POP")):
                    continue
                if wq in lj.split()[1:]:
                    c += 1
            cnt[w] = c
        return cnt

    res = {"pairs": []}
    for name, a, b in VALID + INVALID:
        p = name.split()
        c1, c2, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
        ce = weq(snap[a][c1], snap[b][c1]) and weq(snap[a][c2], snap[b][c2])
        te = weq(snap[a][t], snap[b][t])
        dp = popxor(snap[a][c1] & snap[a][c2], snap[b][c1] & snap[b][c2])
        print(f"{name} [{a},{b}] uncond=({is_uncond.get(a)},{is_uncond.get(b)}) "
              f"ctrl_eq={ce} tgt_eq={te} prod_xor_pop={dp}")
        if (name, a, b) in [(n, x, y) for n, x, y in VALID]:
            ut = untouched(a, b)
            zf = zero_at[a]
            clean = [w for w in ut if zf[w] in (0, 1)]
            dirty = [w for w in ut if zf[w] == 2]
            tc = touch_count(a, b)
            least = sorted(tc.items(), key=lambda kv: kv[1])[:8]
            res["pairs"].append({
                "name": name, "span": [a, b], "span_len": b - a,
                "uncond": [is_uncond.get(a), is_uncond.get(b)],
                "controls_equal": ce, "target_equal": te,
                "product_xor_pop": dp,
                "untouched": ut, "clean_or_const1": clean,
                "dirty_untouched": dirty,
                "least_touched": least,
            })
            print(f"   untouched={ut}")
            print(f"   clean/const1={clean} dirty={dirty}")
            print(f"   least_touched={least}")

    spans = [(a, b) for _, a, b in VALID]
    for i in range(4):
        for j in range(i + 1, 4):
            lo = max(spans[i][0], spans[j][0])
            hi = min(spans[i][1], spans[j][1])
            print(f"overlap pair{i}-pair{j}: [{lo},{hi}] len={hi - lo}")
    glo = max(a for a, _ in spans)
    ghi = min(b for _, b in spans)
    print(f"global intersection: [{glo},{ghi}] len={ghi - glo}")
    res["global_intersection"] = [glo, ghi]

    # (q26&q18) presence check in window
    hits = [(i, l) for i, l in enumerate(ops[WLO:WHI], start=WLO)
            if l.startswith("CCX") and
            ({l.split()[1], l.split()[2]} == {"q26", "q18"})]
    print(f"(q26&q18) CCX in window: {hits}")
    res["q26_q18_in_window"] = hits

    Path("experiments/invsqrt/20261109_cache_borrow_mincut/task2_borrow.json").write_text(
        json.dumps(res, indent=2) + "\n")
    print("wrote task2_borrow.json")


if __name__ == "__main__":
    main()
