"""Exact classical (basis-state) simulator for the invsqrt lineage.

Why this is exact: every gate in the circuit is either a computational-basis
permutation (X, CX, CCX, SWAP, CSWAP), a diagonal phase (Z, CZ, CCZ, Z_POW,
NEG) or a measurement (HMR / R).  On a basis-state input every measurement
outcome is a function of the state, so the circuit maps

    |x>|0...0>  ->  exp(2 pi i * phase(x)) |perm(x)>

with `phase` a sum of dyadic angles.  Tracking `phase` modulo one turn as an
integer number of 2^-64 turns keeps the comparison bit-exact against the
official verifier (which compares uint64 phase units mod 1 turn).

HMR kickback: measuring a Z-basis-function qubit in the X basis negates the
phase of the trajectories where the qubit was |1>, *if the outcome is true*,
i.e. it contributes `outcome AND qubit_value` half-turns.  The outcome itself is
an input of the model here: `Sim.hmr_outcome(i)` is set from an assignment so
the same trajectory can be replayed for a candidate circuit.

State layout: one uint64 per shot holding bits 0..61; classical bits in a
(n_bits, N) uint8 array; phase in uint64 units of 2^-64 turns (wrapping).
"""

from __future__ import annotations

import io
from fractions import Fraction
from pathlib import Path

import numpy as np

MASK64 = (1 << 64) - 1
HALF = np.uint64(1) << np.uint64(63)

# How the HMR outcome is chosen when no explicit assignment is supplied.
#   "value"  : outcome = the qubit's Z value (a valid representative branch)
#   "zero"   : outcome = 0 (no kickback at all)
#   "one"    : outcome = 1
#   "hash"   : outcome = a fixed pseudo-random function of (bit index, x)
HMR_MODE = "value"


class Sim:
    def __init__(self, n: int, n_qubits: int = 62, n_bits: int = 1024):
        self.n = n
        self.v = np.zeros(n, dtype=np.uint64)
        self.b = np.zeros((n_bits, n), dtype=np.uint8)
        self.phase = np.zeros(n, dtype=np.uint64)
        self.n_qubits = n_qubits
        self.hmr_count = 0
        self.hmr_outcomes: dict[int, np.ndarray] = {}

    # ---- helpers -----------------------------------------------------
    def qbit(self, q: int) -> np.ndarray:
        return ((self.v >> np.uint64(q)) & np.uint64(1)).astype(bool)

    @staticmethod
    def _and(masks):
        out = None
        for m in masks:
            out = m if out is None else (out & m)
        return out

    def _add(self, sel, units: np.uint64) -> None:
        if sel is None:
            self.phase += units
        else:
            self.phase += np.where(sel, units, np.uint64(0)).astype(np.uint64)

    # ---- gates -------------------------------------------------------
    def x(self, q: int, m=None):
        bit = np.uint64(1) << np.uint64(q)
        self.v ^= bit if m is None else np.where(m, bit, np.uint64(0)).astype(np.uint64)

    def cx(self, a: int, b: int, m=None):
        sel = ((self.v >> np.uint64(a)) & np.uint64(1)).astype(bool)
        if m is not None:
            sel = sel & m
        self.v ^= np.where(sel, np.uint64(1) << np.uint64(b), np.uint64(0)).astype(np.uint64)

    def ccx(self, a: int, b: int, c: int, m=None):
        sel = ((self.v >> np.uint64(a)) & np.uint64(1)).astype(bool)
        sel = sel & ((self.v >> np.uint64(b)) & np.uint64(1)).astype(bool)
        if m is not None:
            sel = sel & m
        self.v ^= np.where(sel, np.uint64(1) << np.uint64(c), np.uint64(0)).astype(np.uint64)

    def cswap(self, a: int, b: int, c: int, m=None):
        sel = ((self.v >> np.uint64(a)) & np.uint64(1)).astype(bool)
        if m is not None:
            sel = sel & m
        diff = (((self.v >> np.uint64(b)) ^ (self.v >> np.uint64(c))) & np.uint64(1)).astype(bool)
        diff = diff & sel
        self.v ^= np.where(diff, (np.uint64(1) << np.uint64(b)) | (np.uint64(1) << np.uint64(c)),
                           np.uint64(0)).astype(np.uint64)

    def swap(self, a: int, b: int):
        da = (self.v >> np.uint64(a)) & np.uint64(1)
        db = (self.v >> np.uint64(b)) & np.uint64(1)
        diff = (da ^ db).astype(bool)
        self.v ^= np.where(diff, (np.uint64(1) << np.uint64(a)) | (np.uint64(1) << np.uint64(b)),
                           np.uint64(0)).astype(np.uint64)

    def z(self, q: int, m=None):
        sel = self.qbit(q)
        self._add(sel if m is None else (sel & m), HALF)

    def cz(self, a: int, b: int, m=None):
        sel = self.qbit(a) & self.qbit(b)
        self._add(sel if m is None else (sel & m), HALF)

    def ccz(self, a: int, b: int, c: int, m=None):
        sel = self.qbit(a) & self.qbit(b) & self.qbit(c)
        self._add(sel if m is None else (sel & m), HALF)

    def zpow(self, q: int, arg: str, m=None):
        f = Fraction(arg)
        units = np.uint64((f.numerator << 63) // f.denominator)
        sel = self.qbit(q)
        self._add(sel if m is None else (sel & m), units)

    def neg(self, m=None):
        self._add(m, HALF)

    def r(self, q: int, m=None):
        """Reset: on a basis state this is a no-op except it randomises the
        phase if the qubit is 1, which kickmix warns about; the lineage never
        resets a nonzero qubit, so treat as a no-op on values."""
        pass

    def hmr(self, q: int, bit: int, m=None):
        v = self.qbit(q)
        ran = np.ones(self.n, dtype=bool) if m is None else m
        if self.hmr_count in self.hmr_outcomes:
            out = self.hmr_outcomes[self.hmr_count]
        elif HMR_MODE == "value":
            out = v
        else:
            out = _default_outcome(HMR_MODE, bit, self.n)
        out = np.asarray(out, dtype=bool) & ran
        if m is None:
            self.b[bit] = out.astype(np.uint8)
        else:
            self.b[bit] = np.where(m, out, self.b[bit].astype(bool)).astype(np.uint8)
        self._add(v & out, HALF)
        self.v &= np.where(ran, ~(np.uint64(1) << np.uint64(q)), np.uint64(MASK64)).astype(np.uint64)
        self.hmr_count += 1

    def bit_store0(self, bit: int, m=None):
        self.b[bit] = 0 if m is None else np.where(m, 0, self.b[bit]).astype(np.uint8)

    def bit_store1(self, bit: int, m=None):
        self.b[bit] = 1 if m is None else np.where(m, 1, self.b[bit]).astype(np.uint8)

    def bit_invert(self, bit: int, m=None):
        self.b[bit] ^= 1 if m is None else m.astype(np.uint8)


def _default_outcome(mode: str, bit: int, n: int) -> np.ndarray:
    if mode == "zero":
        return np.zeros(n, dtype=bool)
    if mode == "one":
        return np.ones(n, dtype=bool)
    if mode == "hash":
        rng = np.random.default_rng(1000 + bit)
        return rng.integers(0, 2, size=n).astype(bool)
    raise ValueError(mode)


def op_table(path: Path) -> tuple[list, int]:
    """Flat op list with conditions resolved into (stack, inline) form.

    A kmx line can carry a condition inline (`Z q if b3`) or through an
    enclosing PUSH_CONDITION/POP_CONDITION block; the stack snapshots the bit's
    value at push time, so both forms are kept separate here.
    """
    import kickmix as km

    circuit = km.Circuit.from_file(str(path), format="auto")
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    out = []
    for line in buf.getvalue().splitlines():
        parts = line.split()
        if not parts:
            continue
        head = parts[0]
        if head in ("APPEND_TO_REGISTER", "REGISTER"):
            continue
        if head == "PUSH_CONDITION":
            out.append(("PUSH", [parts[2]], (), None))
            continue
        if head == "POP_CONDITION":
            out.append(("POP", [], (), None))
            continue
        args = parts[1:]
        inline = None
        if "if" in args:
            k = args.index("if")
            inline = int(args[k + 1][1:])
            args = args[:k]
        out.append((head, args, (), inline))
    return out, circuit.num_qubits


def qargs(args):
    return [int(a[1:]) for a in args if a.startswith("q")]


def bargs(args):
    return [int(a[1:]) for a in args if a.startswith("b")]


def run(sim: Sim, table, limit: int | None = None) -> None:
    """Apply ops in order; condition stack is snapshotted at PUSH time."""
    snaps: list[np.ndarray] = []
    for idx, (kind, args, _unused, inline) in enumerate(table):
        if limit is not None and idx >= limit:
            break
        if kind == "PUSH":
            b = int(args[0][1:])
            snaps.append(sim.b[b].astype(bool).copy())
            continue
        if kind == "POP":
            snaps.pop()
            continue
        masks = list(snaps)
        if inline is not None:
            masks.append(sim.b[inline].astype(bool))
        m = Sim._and(masks)
        if kind == "CX":
            q = qargs(args)
            sim.cx(q[0], q[1], m)
        elif kind == "CCX":
            q = qargs(args)
            sim.ccx(q[0], q[1], q[2], m)
        elif kind == "X":
            sim.x(qargs(args)[0], m)
        elif kind == "SWAP":
            q = qargs(args)
            sim.swap(q[0], q[1])
        elif kind == "CSWAP":
            q = qargs(args)
            sim.cswap(q[0], q[1], q[2], m)
        elif kind == "Z":
            sim.z(qargs(args)[0], m)
        elif kind == "CZ":
            q = qargs(args)
            sim.cz(q[0], q[1], m)
        elif kind == "CCZ":
            q = qargs(args)
            sim.ccz(q[0], q[1], q[2], m)
        elif kind == "Z_POW":
            sim.zpow(qargs(args)[0], args[1], m)
        elif kind == "HMR":
            sim.hmr(qargs(args)[0], bargs(args)[0], m)
        elif kind == "R":
            sim.r(qargs(args)[0], m)
        elif kind == "NEG":
            sim.neg(m)
        elif kind == "BIT_STORE0":
            sim.bit_store0(bargs(args)[0], m)
        elif kind == "BIT_STORE1":
            sim.bit_store1(bargs(args)[0], m)
        elif kind == "BIT_INVERT":
            sim.bit_invert(bargs(args)[0], m)
        else:
            raise ValueError(f"unhandled op {kind}: {args}")
