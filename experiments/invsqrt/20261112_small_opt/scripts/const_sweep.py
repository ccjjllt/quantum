"""Sound constant-value sweep over an invsqrt kmx.

Tracks each qubit's value as 0 / 1 / unknown, exactly and conservatively:
  * x qubits start unknown, all scratch starts 0
  * HMR leaves its qubit at 0 (X-basis measure + reset)
  * a gate inside a condition that may be false sets its target unknown
  * values are only marked constant when the value is state-independent

Then reports paid gates that are provably
  (a) no-ops  -- a control is constant 0, so deleting the gate is exact, or
  (b) downgradable -- a control is constant 1, so
      CCX -> CX, CCZ -> CZ, CSWAP -> SWAP.
These rewrites preserve the value of every qubit for every input and every
measurement outcome, so they also preserve the tracked phase exactly.

Usage: python const_sweep.py circuit.kmx [--apply out.kmx]
"""

from __future__ import annotations

import sys
from collections import Counter

PAID = {"CCX", "CCZ", "CSWAP"}


def load(path):
    ops = []
    for line in open(path):
        p = line.split()
        if not p or p[0] in ("APPEND_TO_REGISTER", "REGISTER"):
            continue
        ops.append(p)
    return ops


def cond_bits(p, stack):
    cb = list(dict.fromkeys(stack))
    if len(p) >= 2 and p[-2] == "if" and p[-1] not in cb:
        cb.append(p[-1])
    return cb


def run(ops, apply=None):
    val = {}          # qubit name -> 0/1/None
    bit = {}          # classical bit name -> 0/1/None
    stack = []
    report = []
    out = []
    known = lambda q: val.get(q, None)
    for i, p in enumerate(ops):
        op = p[0]
        cb = cond_bits(p, stack)
        # condition truth: True only if every bit is known 1; False if any known 0.
        truth = True
        for c in cb:
            bv = bit.get(c, None)
            if bv == 0:
                truth = False
                break
            if bv is None:
                truth = None
        line = " ".join(p)
        if op == "PUSH_CONDITION":
            stack.append(p[2])
            out.append(line)
            continue
        if op == "POP_CONDITION":
            stack.pop()
            out.append(line)
            continue
        if op in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            tgt = p[1]
            if op == "BIT_STORE0":
                bit[tgt] = 0 if len(p) == 2 else (0 if truth is False else None)
            elif op == "BIT_STORE1":
                bit[tgt] = 1 if len(p) == 2 else (1 if truth else None if truth is None else 0)
            else:
                if len(p) == 2:
                    bit[tgt] = None if bit.get(tgt, None) is None else 1 - bit[tgt]
                else:
                    bit[tgt] = None
            out.append(line)
            continue
        if op == "HMR":
            if truth is False:
                # skipped: keeps its value
                pass
            else:
                report.append((i, "HMR-const" if False else "", line))
                val[p[1]] = 0 if truth else None
            out.append(line)
            continue
        # value gates
        newline = line
        if op == "X":
            q = p[1]
            if truth is False:
                pass
            elif truth and known(q) is not None:
                val[q] = 1 - val[q]
            else:
                val[q] = None
        elif op == "CX":
            a, b = p[1], p[2]
            if truth is False:
                pass
            elif truth:
                if known(a) == 0:
                    pass
                elif known(a) == 1:
                    if known(b) is not None:
                        val[b] = 1 - val[b]
                    else:
                        val[b] = None
                else:
                    val[b] = None
            else:
                if known(a) == 0:
                    pass
                else:
                    val[b] = None
        elif op == "CCX":
            a, b, c = p[1], p[2], p[3]
            if truth is False:
                pass
            else:
                va, vb = known(a), known(b)
                noop = (va == 0) or (vb == 0)
                if noop:
                    report.append((i, "noop-CCX", line))
                elif truth is None:
                    val[c] = None
                elif va == 1 and vb == 1:
                    report.append((i, "ccx->x", line))
                    val[c] = None if known(c) is None else 1 - val[c]
                elif va == 1 or vb == 1:
                    report.append((i, "ccx->cx", line))
                    other = b if va == 1 else a
                    if known(other) is None:
                        val[c] = None
                    elif known(other) == 1:
                        val[c] = None if known(c) is None else 1 - val[c]
                else:
                    val[c] = None
        elif op == "CSWAP":
            c, a, b = p[1], p[2], p[3]
            if truth is False:
                pass
            else:
                vc = known(c)
                if vc == 0:
                    report.append((i, "noop-CSWAP", line))
                elif truth is None:
                    if known(a) == known(b) and known(a) is not None:
                        pass
                    else:
                        val[a] = None
                        val[b] = None
                elif vc == 1:
                    report.append((i, "cswap->swap", line))
                    val[a], val[b] = val.get(b), val.get(a)
                else:
                    if known(a) == known(b) and known(a) is not None:
                        pass
                    else:
                        val[a] = None
                        val[b] = None
        elif op == "SWAP":
            a, b = p[1], p[2]
            if truth is False:
                pass
            elif truth:
                val[a], val[b] = val.get(b), val.get(a)
            else:
                if known(a) != known(b) or known(a) is None:
                    val[a] = None
                    val[b] = None
        elif op == "CCZ":
            if truth is not False:
                va, vb, vc = known(p[1]), known(p[2]), known(p[3])
                if va == 0 or vb == 0 or vc == 0:
                    report.append((i, "noop-CCZ", line))
                elif truth and (va == 1 or vb == 1 or vc == 1):
                    report.append((i, "ccz->cz", line))
        out.append(newline)
    return report, out


def main():
    path = sys.argv[1]
    ops = load(path)
    report, out = run(ops)
    kinds = Counter(r[1] for r in report if r[1])
    print("findings:", dict(kinds))
    for i, k, line in report:
        if k:
            print(f"  op {i:6d} {k:12s} {line}")
    if "--apply" in sys.argv:
        dst = sys.argv[sys.argv.index("--apply") + 1]
        open(dst, "w").write("\n".join(out) + "\n")
        print("wrote", dst)


if __name__ == "__main__":
    main()
