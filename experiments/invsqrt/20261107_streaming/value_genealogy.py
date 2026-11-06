"""Value genealogy: availability intervals of every fine-rotation support value.

A SWAP changes which wire carries a value, so "when was wire w last written"
overstates how late a coefficient bit appears.  This script fingerprints every
wire value over all 3,133,452 legal x and maintains, for each *distinct value
function*, the set of wires currently carrying it.  That gives exact
availability intervals: the value is usable at op p iff some wire holds it at p.

For every fine rotation we then report the earliest op at which all of its
support values are simultaneously available (on distinct wires, which is
automatic: one wire carries exactly one value).

Output: artifacts/20261107_streaming/value_genealogy.json
"""
from __future__ import annotations

import hashlib
import json

import common

STOP = 25662


def fp(mask: int, nbytes: int) -> bytes:
    return hashlib.blake2b(mask.to_bytes(nbytes, "little"), digest_size=16).digest()


def main() -> None:
    ops, gates = common.load_ops()
    sym = json.loads((common.OUT / "symbolic_masks.json").read_text())
    n = common.MAXX
    nbytes = (n + 7) // 8
    zero_fp = fp(0, nbytes)

    targets = {}
    for r in sym["per_rotation"]:
        for w in r["support"]:
            targets[(r["block_start"], w)] = None
    starts = sorted({b for b, _ in targets})
    state, _ = common.trace_checkpoints(gates, set(starts), n=n)
    for key in list(targets):
        b, w = key
        targets[key] = fp(state[b][w], nbytes)
    uniq = {}
    for key, h in targets.items():
        uniq.setdefault(h, []).append(key)
    print(f"{len(targets)} (block,wire) targets, {len(uniq)} distinct value functions")
    for h, keys in uniq.items():
        if len(keys) > 1:
            print("  identical values:", keys)

    q = common.initial_bits(n) + [0] * (common.NQ - 22)
    full = (1 << n) - 1
    on_wire = [None] * common.NQ
    where = {}                     # fp -> set of wires
    for w in range(common.NQ):
        h = fp(q[w], nbytes)
        on_wire[w] = h
        where.setdefault(h, set()).add(w)

    avail = {h: [None, None, []] for h in uniq}   # start, end, closed intervals
    watched = set(uniq)

    def note_states(i):
        for h, ws in where.items():
            if h not in watched:
                continue
            if ws and avail[h][0] is None:
                avail[h][0] = i
            elif not ws and avail[h][0] is not None:
                avail[h][2].append([avail[h][0], i - 1])
                avail[h][0] = None

    def set_wire(w, val, i):
        old = on_wire[w]
        if old is not None:
            s = where.get(old)
            if s is not None:
                s.discard(w)
        new = fp(val, nbytes)
        on_wire[w] = new
        where.setdefault(new, set()).add(w)

    note_states(0)
    stack: list[int] = []
    bits: dict[int, int] = {}

    for i, (k, qs, p) in enumerate(gates):
        if i >= STOP:
            break
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        touched = []
        if k == "X":
            q[qs[0]] ^= active
            touched = [qs[0]]
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
            touched = [qs[1]]
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
            touched = [qs[2]]
        elif k == "SWAP":
            a, b = qs
            d = (q[a] ^ q[b]) & active
            q[a] ^= d
            q[b] ^= d
            touched = [a, b]
        elif k == "CSWAP":
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & q[qs[0]] & active
            q[a] ^= d
            q[b] ^= d
            touched = [a, b]
        elif k in {"HMR", "R"}:
            q[qs[0]] = 0
            touched = [qs[0]]
            if k == "HMR":
                bits[int(p[2][1:])] = 0
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = (old & ~active if k == "BIT_STORE0"
                       else old | active if k == "BIT_STORE1" else old ^ active)
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, k, p))
        for w in touched:
            set_wire(w, q[w], i)
        note_states(i)
    for h in watched:
        if avail[h][0] is not None:
            avail[h][2].append([avail[h][0], STOP - 1])
            avail[h][0] = None

    print("trace done")

    summary = {}
    for (b, w), h in targets.items():
        ivs = [iv for iv in avail[h][2] if iv[0] <= b]
        summary[f"{b}:q{w}"] = {"fingerprint": h.hex(), "intervals": ivs,
                                "first_op": min(iv[0] for iv in ivs) if ivs else None}

    per_rot = []
    for r in sym["per_rotation"]:
        b = r["block_start"]
        iv_sets = []
        for w in r["support"]:
            h = targets[(b, w)]
            iv_sets.append(set(o for a, e in avail[h][2] if e >= 0
                               for o in range(a, e + 1) if o <= b))
        common_ops = set.intersection(*iv_sets) if iv_sets else set()
        earliest = min(common_ops) if common_ops else None
        per_rot.append({
            "rot": r["rot"], "op": r["op"], "block_start": b,
            "support_size": len(r["support"]),
            "earliest_coexistence": earliest,
            "gain_vs_actual": None if earliest is None else r["op"] - earliest,
            "per_value_first": {
                str(w): summary[f"{b}:q{w}"]["first_op"] for w in r["support"]},
        })
        print(f"rot{r['rot']:2d} op{r['op']:5d} support={len(r['support']):2d} "
              f"earliest coexistence {earliest} "
              f"(max gain {r['op'] - earliest if earliest is not None else None})")

    # compact: also report when the *whole* support set of a block first coexists
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "value_genealogy.json").write_text(json.dumps({
        "scope": "full legal domain, all-zero HMR branch; 128-bit value fingerprints",
        "stop": STOP,
        "values": summary,
        "rotations": per_rot,
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
