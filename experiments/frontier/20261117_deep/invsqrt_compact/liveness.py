"""Static liveness / occupancy analysis of invsqrt 0af21cb8 (no simulation).

Models computed:
  A  naive interval model: wire live on [first_op, last_op]  (sweep-line peak)
  B  constancy model: a wire is OCCUPIED while it holds a non-constant value.
     Writes are XOR-accumulating, so a wire becomes occupied at the first op that
     puts an unknown value on it and is released only by an unconditional HMR
     (measure + reset to |0>).  This is the model that decides wire reuse.
  C  reset-segment model: split each wire's op list at unconditional HMRs into
     segments, then interval colour the segments (greedy).

Outputs a JSON + a human report. Reads only the .kmx text form.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
KMX = HERE / "invsqrt_0af21cb8.kmx"

ONE_Q = {"X", "Z", "H", "R", "Z_POW", "NEG"}
TWO_Q = {"CX", "CZ", "SWAP"}
THREE_Q = {"CCX", "CCZ", "CSWAP"}
MEASURE = {"HMR"}
CLASSICAL = {"BIT_INVERT", "BIT_STORE0", "BIT_STORE1"}


def parse(path: pathlib.Path):
    lines = path.read_text().splitlines()
    header = [l for l in lines if l.startswith("APPEND_TO_REGISTER") or l.startswith("REGISTER")]
    body = [l for l in lines if l not in header]
    ops = []
    depth = 0
    max_depth = 0
    for i, line in enumerate(body):
        tok = line.split()
        name = tok[0]
        if name == "PUSH_CONDITION":
            depth += 1
            max_depth = max(max_depth, depth)
            continue
        if name == "POP_CONDITION":
            depth -= 1
            continue
        qs = [int(t[1:]) for t in tok[1:] if re.fullmatch(r"q\d+", t)]
        bs = [int(t[1:]) for t in tok[1:] if re.fullmatch(r"b\d+", t)]
        cond = "if" in tok
        ops.append({"i": i, "op": name, "q": qs, "b": bs, "cond": cond, "depth": depth})
    return header, body, ops, max_depth


def intervals(ops, nw):
    first = [None] * nw
    last = [None] * nw
    for o in ops:
        for w in o["q"]:
            if first[w] is None:
                first[w] = o["i"]
            last[w] = o["i"]
    return first, last


def sweep(segs, nw):
    """segs = list of (start, end, wire, tag). Returns peak, op, live set at peak."""
    ev = []
    for s, e, w, tag in segs:
        ev.append((s, 1, w, tag))
        ev.append((e, 0, w, tag))  # end processed before start at same index
    ev.sort(key=lambda x: (x[0], x[1]))
    live = {}
    peak = 0
    peak_at = None
    peak_set = []
    curve = {}
    for idx, kind, w, tag in ev:
        if kind == 1:
            live[(w, tag)] = True
        else:
            live.pop((w, tag), None)
        if len(live) > peak:
            peak = len(live)
            peak_at = idx
            peak_set = sorted(k[0] for k in live)
            curve[idx] = len(live)
        else:
            curve[idx] = max(curve.get(idx, 0), len(live))
    return peak, peak_at, peak_set, curve


def constancy_sweep(ops, nw):
    """Occupied = holds a value that is not a known computational-basis constant.

    Returns peak occupancy, op index, live wire set, and the occupancy curve.
    Conservative: a conditional HMR is NOT allowed to release the wire.
    """
    XWIRES = 22  # q0..q21 hold the input |x>, i.e. unknown non-constant data
    const = [True] * nw          # True => known basis state (|0> or |1>)
    val = [0] * nw               # known basis value when const
    for w in range(XWIRES):
        const[w] = False         # input register carries arbitrary x

    def occ():
        return sum(1 for w in range(nw) if not const[w])

    peak = 0
    peak_at = None
    peak_set = []
    curve = []
    releases = 0
    cond_release_blocked = 0
    for o in ops:
        name = o["op"]
        qs = o["q"]
        if name == "HMR" and qs:
            w = qs[0]
            if o["cond"]:
                # conditional measure+reset: do not trust the reset
                cond_release_blocked += 1
            else:
                const[w] = True
                val[w] = 0
        elif name == "X" and qs:
            w = qs[0]
            if const[w]:
                val[w] ^= 1
            # non-constant stays non-constant
        elif name == "CX" and len(qs) == 2:
            a, b = qs
            if not const[a]:
                const[b] = False
            elif val[a] == 1:
                if const[b]:
                    val[b] ^= 1
        elif name in ("CCX", "CCZ") and len(qs) == 3:
            a, b, c = qs
            if not const[a] and not const[b]:
                if name == "CCX":
                    const[c] = False
                # CCZ: phase only, no value change
            elif const[a] and const[b] and val[a] and val[b]:
                if name == "CCX":
                    if const[c]:
                        val[c] ^= 1
                # CCZ with both controls |1>: phase only
            elif name == "CCX" and not const[a] and const[b] and val[b]:
                const[c] = False
            elif name == "CCX" and not const[b] and const[a] and val[a]:
                const[c] = False
        elif name == "SWAP" and len(qs) == 2:
            a, b = qs
            const[a], const[b] = const[b], const[a]
            val[a], val[b] = val[b], val[a]
        elif name == "CSWAP" and len(qs) == 3:
            a, b, c = qs
            if not const[a] or (const[a] and val[a] == 1):
                const[b], const[c] = const[c], const[b]
                val[b], val[c] = val[c], val[b]
        elif name in ONE_Q and qs:
            pass  # phase-only / no value change (Z_POW, Z, R ...)
        elif name in CLASSICAL:
            pass
        k = occ()
        curve.append((o["i"], k))
        if k > peak:
            peak = k
            peak_at = o["i"]
            peak_set = [w for w in range(nw) if not const[w]]
    return peak, peak_at, peak_set, curve, cond_release_blocked


def segment_model(ops, nw):
    """Split each wire at unconditional HMR events; intervals are whole segments.

    An HMR measures the wire (so the segment must include it) and resets it to
    |0>, which is the only point where the wire becomes free again.
    """
    cur = [None] * nw
    segs = []
    for o in ops:
        for w in o["q"]:
            is_hmr = o["op"] == "HMR" and o["q"][0] == w and not o["cond"]
            if cur[w] is None:
                cur[w] = o["i"]
            if is_hmr:
                segs.append((cur[w], o["i"], w, "s"))
                cur[w] = None
    for w in range(nw):
        if cur[w] is not None:
            segs.append((cur[w], last_use(ops, w), w, "s"))
    return segs


def last_use(ops, w):
    t = None
    for o in ops:
        if w in o["q"]:
            t = o["i"]
    return t


def interval_colour(segs):
    """Greedy interval-graph colouring: returns (#colours, colour per segment)."""
    order = sorted(segs, key=lambda s: (s[0], s[1]))
    free = {}          # colour -> last end
    assigned = []
    ncol = 0
    for s, e, w, tag in order:
        pick = None
        for c, last in free.items():
            if last < s:
                pick = c
                break
        if pick is None:
            pick = ncol
            ncol += 1
        free[pick] = e
        assigned.append((s, e, w, pick))
    return ncol, assigned


def main() -> None:
    header, body, ops, max_depth = parse(KMX)
    nw = 44
    print(f"ops {len(ops)}/{len(body)}  cond nesting max {max_depth}")
    print(f"conditional ops {sum(1 for o in ops if o['cond'])}")
    hmr = [o for o in ops if o["op"] == "HMR"]
    print(f"HMR {len(hmr)}  conditional HMR {sum(1 for o in hmr if o['cond'])}")

    first, last = intervals(ops, nw)
    segA = [(first[w], last[w], w, "A") for w in range(nw) if first[w] is not None]
    peakA, atA, setA, _ = sweep(segA, nw)
    print(f"\nA naive interval peak {peakA} at op {atA}")
    print(f"  wires at peak: {setA}")

    peakB, atB, setB, curveB, cond_blk = constancy_sweep(ops, nw)
    print(f"\nB constancy peak {peakB} at op {atB}")
    print(f"  op at peak: {ops[[o['i'] for o in ops].index(atB)]}")
    print(f"  wires at peak: {setB}")
    print(f"  conditional HMRs not allowed to release: {cond_blk}")
    n_at = {}
    for i, k in curveB:
        n_at[k] = n_at.get(k, 0) + 1
    print("  occupancy histogram (ops):", dict(sorted(n_at.items(), reverse=True)))
    over = [i for i, k in curveB if k >= 44]
    print(f"  ops at occupancy 44: {len(over)}  first {over[0] if over else None} last {over[-1] if over else None}")

    segs = segment_model(ops, nw)
    peakC, atC, setC, _ = sweep(segs, nw)
    print(f"\nC reset-segment peak {peakC} at op {atC}")
    print(f"  segments {len(segs)}  wires at peak {setC}")

    out = {
        "ops": len(ops),
        "max_cond_depth": max_depth,
        "hmr_total": len(hmr),
        "hmr_conditional": sum(1 for o in hmr if o["cond"]),
        "A_interval_peak": peakA,
        "A_peak_op": atA,
        "A_peak_wires": setA,
        "B_constancy_peak": peakB,
        "B_peak_op": atB,
        "B_peak_wires": setB,
        "B_ops_at_44": len(over),
        "B_hist": dict(sorted(n_at.items(), reverse=True)),
        "C_segment_peak": peakC,
        "C_peak_op": atC,
        "C_peak_wires": setC,
        "first": first,
        "last": last,
    }
    (HERE / "liveness.json").write_text(json.dumps(out, indent=2))
    print("\nwrote liveness.json")


if __name__ == "__main__":
    sys.exit(main())
