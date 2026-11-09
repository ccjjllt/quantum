"""Task3c: reconcile 233 vs 372 peak-interval discrepancy.

Same backward pass, 4 semantics variants:
  V0 = prior verbatim (init q0..q21, cond = inline-if only, ignore CZ/Z/SWAP,
       CSWAP adds cc only, HMR kills even in blocks)
  V1 = V0 + depth-aware cond (PUSH/POP blocks conservative)
  V2 = V1 + phase-gate reads (CZ/Z/Z_POW add operands)
  V3 = V2 + CSWAP/SWAP fix (= task3_mincut.py semantics, init empty)
Also V3b = V3 with init q0..q21 to isolate init-set effect.
"""
import io
from pathlib import Path

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def run(ops, depth_aware, phase_reads, cswap_fix, init_q0_21):
    n = len(ops)
    live = {f"q{i}" for i in range(22)} if init_q0_21 else set()
    lv = [0] * n
    depth = 0
    for idx in range(n - 1, -1, -1):
        l = ops[idx]
        if l.startswith("PUSH_CONDITION"):
            if depth_aware:
                depth -= 1
            lv[idx] = len(live)
            continue
        if l.startswith("POP_CONDITION"):
            if depth_aware:
                depth += 1
            lv[idx] = len(live)
            continue
        p = l.split()
        op = p[0]
        cond = (" if " in l) or (depth_aware and depth > 0)
        if op in ("HMR", "R"):
            if not cond:
                live.discard(p[1])
            else:
                live.add(p[1])
        elif op == "CX":
            a, b = p[1], p[2]
            if b in live or cond:
                live.add(a)
            if cond:
                live.add(b)
        elif op == "CCX":
            a, b, t = p[1], p[2], p[3]
            if t in live or cond:
                live.add(a)
                live.add(b)
            if cond:
                live.add(t)
        elif op == "CCZ":
            a, b, t = p[1], p[2], p[3]
            if t in live or cond or phase_reads:
                live.update([a, b, t])
        elif op == "CSWAP":
            cc, a, b = p[1], p[2], p[3]
            if cswap_fix:
                if a in live or b in live or cond:
                    live.update([cc, a, b])
            else:
                if a in live or b in live or cond:
                    live.add(cc)
                if cond:
                    live.update([a, b])
        elif op == "SWAP":
            if cswap_fix:
                a, b = p[1], p[2]
                if a in live or b in live or cond:
                    live.update([a, b])
        elif op in ("CZ", "Z", "Z_POW"):
            if phase_reads:
                live.update([t for t in p[1:] if t.startswith("q")])
        lv[idx] = len(live)
    ints = []
    s = None
    for i, v in enumerate(lv):
        if v == 62 and s is None:
            s = i
        if v < 62 and s is not None:
            ints.append((s, i - 1))
            s = None
    if s is not None:
        ints.append((s, n - 1))
    return max(lv), len(ints), sum(b - a + 1 for a, b in ints)


def main():
    ops = parse_ops()
    for name, kw in [
        ("V0 prior-verbatim", dict(depth_aware=False, phase_reads=False,
                                   cswap_fix=False, init_q0_21=True)),
        ("V1 +depth-aware", dict(depth_aware=True, phase_reads=False,
                                 cswap_fix=False, init_q0_21=True)),
        ("V2 +phase-reads", dict(depth_aware=True, phase_reads=True,
                                 cswap_fix=False, init_q0_21=True)),
        ("V3 +cswap/swap-fix,init-empty", dict(depth_aware=True,
                                               phase_reads=True,
                                               cswap_fix=True,
                                               init_q0_21=False)),
        ("V3b V3+init-q0..21", dict(depth_aware=True, phase_reads=True,
                                    cswap_fix=True, init_q0_21=True)),
    ]:
        mx, ni, tot = run(ops, **kw)
        print(f"{name}: max={mx} intervals={ni} ops={tot}")


if __name__ == "__main__":
    main()
