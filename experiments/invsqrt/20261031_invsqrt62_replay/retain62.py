"""Screen one retention candidate on the 62-qubit invsqrt circuit.

The screen covers ops 15583:36941. Repeated CCX segments are exact op-text
copies separated by more than 2000 ops, then grouped into rows. A copy is
eligible only when the boolean value-id of 1 or 2 wires is cleared and later
recomputed by that copy. Break-even uses baseline C = 1628.0743548387097.
No second candidate is applied. This script does not run the official verifier.
"""

from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import kickmix

ROOT = Path(__file__).resolve().parents[3]
ORACLE = ROOT / "artifacts/20261030_public_best/candidate/invsqrt.kmb"
ART = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt"
WINDOW = (15583, 36941)
C_BASE = 1628.0743548387097
BREAK_EVEN = {63: C_BASE * (1 - 62 / 63), 64: C_BASE * (1 - 62 / 64), 65: None}


def qn(token: str) -> int:
    return int(token[1:])


def load_ops():
    circuit = kickmix.Circuit.from_file(ORACLE)
    text = io.StringIO()
    circuit.to_file(text, format="kmx")
    lines = text.getvalue().splitlines()
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    if len(ops) != 47201:
        raise SystemExit(f"expected 47201 ops, found {len(ops)}")
    return ops


def repeated_segments(ops):
    base, stop = WINDOW
    window = ops[base:stop]
    positions = defaultdict(list)
    for index, line in enumerate(window):
        if line.startswith("CCX"):
            positions[line].append(index)
    raw = []
    seen = set()
    for index in [i for i, line in enumerate(window) if line.startswith("CCX")]:
        for later in positions[window[index]]:
            if later <= index:
                continue
            left, right = index, later
            while left > 0 and right > index and window[left - 1] == window[right - 1]:
                left -= 1
                right -= 1
            end_l, end_r = index, later
            while (
                end_l + 1 < len(window)
                and end_r + 1 < len(window)
                and end_l + 1 < right
                and window[end_l + 1] == window[end_r + 1]
            ):
                end_l += 1
                end_r += 1
            key = (left, right)
            if key in seen:
                continue
            seen.add(key)
            length = end_l - left + 1
            sep = right - end_l
            if length >= 8 and sep >= 2000:
                raw.append((length, left, end_l, right, end_r))
    raw.sort(key=lambda item: -item[0])
    taken = [False] * len(window)
    chosen = []
    for length, left, end_l, right, end_r in raw:
        span = list(range(left, end_l + 1)) + list(range(right, end_r + 1))
        if any(taken[k] for k in span):
            continue
        for k in span:
            taken[k] = True
        ccx = sum(1 for k in range(left, end_l + 1) if window[k].startswith("CCX"))
        toffoli = sum(
            1
            for k in range(right, end_r + 1)
            if window[k].startswith(("CCX", "CCZ", "CSWAP"))
        )
        chosen.append(
            {
                "src": [base + left, base + end_l],
                "copy": [base + right, base + end_r],
                "length": length,
                "repeated_ccx": ccx,
                "copy_toffoli_like": toffoli,
            }
        )
    chosen.sort(key=lambda item: item["src"][0])
    groups = []
    for seg in chosen:
        if not groups or seg["src"][0] > groups[-1]["stop"] + 40:
            groups.append(
                {
                    "start": seg["src"][0],
                    "stop": seg["src"][1],
                    "repeated_ccx": seg["repeated_ccx"],
                    "parts": [seg],
                }
            )
        else:
            groups[-1]["stop"] = max(groups[-1]["stop"], seg["src"][1])
            groups[-1]["repeated_ccx"] += seg["repeated_ccx"]
            groups[-1]["parts"].append(seg)
    return chosen, groups


class Values:
    def __init__(self):
        self.fs_of = {}
        self.fs = []
        self.ands = {}
        self.zero = self.vid(frozenset())
        self.one = self.vid(frozenset([-1]))
        self._fresh = 0

    def fresh(self):
        """A value id that is not a qubit singleton and not an AND atom."""
        self._fresh += 1
        return self.vid(frozenset({1_000_000 + self._fresh}))

    def vid(self, bits):
        bits = frozenset(bits)
        hit = self.fs_of.get(bits)
        if hit is not None:
            return hit
        index = len(self.fs)
        self.fs_of[bits] = index
        self.fs.append(bits)
        return index

    def xor(self, left, right):
        return self.vid(self.fs[left] ^ self.fs[right])

    def and_(self, left, right):
        if left == self.zero or right == self.zero:
            return self.zero
        if left == self.one:
            return right
        if right == self.one:
            return left
        key = (left, right) if left <= right else (right, left)
        atom = self.ands.get(key)
        if atom is None:
            # Qubit singletons use atoms 0..61. AND atoms start at 62.
            atom = 62 + len(self.ands)
            self.ands[key] = atom
        return self.vid(frozenset([atom]))

    def mux(self, control, a, b):
        return self.xor(b, self.and_(control, self.xor(a, b)))


def break_even_tests(save, frontier_size):
    """Charge one new ancilla per retained output. 65Q and above are rejected."""
    width = 62 + frontier_size
    q63 = {
        "qubits": 63,
        "required_net_save": BREAK_EVEN[63],
        "applies": frontier_size <= 1,
        "conservative_save": save if frontier_size <= 1 else 0,
        "passed": frontier_size <= 1 and save > BREAK_EVEN[63],
    }
    q64 = {
        "qubits": 64,
        "required_net_save": BREAK_EVEN[64],
        "applies": frontier_size <= 2,
        "conservative_save": save if frontier_size <= 2 else 0,
        "passed": frontier_size <= 2 and save > BREAK_EVEN[64],
    }
    if frontier_size > 2:
        q63["passed"] = False
        q64["passed"] = False
        q63["conservative_save"] = 0
        q64["conservative_save"] = 0
    return {
        "assumed_width": width,
        "q63": q63,
        "q64": q64,
        "q65": {"qubits": 65, "status": "rejected", "passed": False},
    }


def interpret(ops, capture_ccx=None, capture_at=None):
    """Boolean interpreter. A non-empty condition stack gates every write.

    The active condition is the AND of every pushed bit and any inline `if`.
    PUSH/POP themselves always update the stack.
    """
    values = Values()
    wire = [values.vid(frozenset([q])) for q in range(62)]
    condition = []
    bit_values = {}
    snap = {}
    ccx_sig = {}
    capture_ccx = capture_ccx or set()
    capture_at = capture_at or set()

    def ensure_bit(bit):
        if bit not in bit_values:
            bit_values[bit] = values.fresh()
        return bit_values[bit]

    def active(parts):
        factors = [ensure_bit(int(tok[1:])) for tok in condition if tok.startswith("b")]
        if "if" in parts:
            factors.append(ensure_bit(int(parts[parts.index("if") + 1][1:])))
        if not factors:
            return None
        acc = factors[0]
        for factor in factors[1:]:
            acc = values.and_(acc, factor)
        if acc == values.one:
            return None
        return acc

    def when(old, new, cond):
        if cond is None:
            return new
        return values.mux(cond, new, old)

    for index, line in enumerate(ops):
        parts = line.split()
        kind = parts[0]
        cond = active(parts)
        if kind == "PUSH_CONDITION":
            condition.append(parts[-1])
        elif kind == "POP_CONDITION":
            if condition:
                condition.pop()
        elif kind in ("BIT_STORE0", "BIT_STORE1"):
            bit = int(parts[1][1:])
            old = bit_values.get(bit, values.fresh())
            stored = values.zero if kind == "BIT_STORE0" else values.one
            bit_values[bit] = when(old, stored, cond)
        elif kind == "BIT_INVERT":
            bit = int(parts[1][1:])
            old = bit_values.get(bit, values.fresh())
            bit_values[bit] = when(old, values.xor(old, values.one), cond)
        elif kind == "SWAP":
            a, b = qn(parts[1]), qn(parts[2])
            old_a, old_b = wire[a], wire[b]
            wire[a] = when(old_a, old_b, cond)
            wire[b] = when(old_b, old_a, cond)
        elif kind == "CSWAP":
            c, a, b = qn(parts[1]), qn(parts[2]), qn(parts[3])
            old_a, old_b = wire[a], wire[b]
            swapped_a = values.mux(wire[c], old_b, old_a)
            swapped_b = values.mux(wire[c], old_a, old_b)
            wire[a] = when(old_a, swapped_a, cond)
            wire[b] = when(old_b, swapped_b, cond)
        elif kind == "CX":
            a, b = qn(parts[1]), qn(parts[2])
            old = wire[b]
            wire[b] = when(old, values.xor(old, wire[a]), cond)
        elif kind == "CCX":
            a, b, t = qn(parts[1]), qn(parts[2]), qn(parts[3])
            if index in capture_ccx:
                ccx_sig[index] = {
                    "op": index,
                    "controls": [wire[a], wire[b]],
                    "target": wire[t],
                    "condition": list(condition),
                    "active_condition": cond,
                }
            old = wire[t]
            wire[t] = when(old, values.xor(old, values.and_(wire[a], wire[b])), cond)
        elif kind == "X":
            t = qn(parts[1])
            old = wire[t]
            wire[t] = when(old, values.xor(old, values.one), cond)
        elif kind in ("HMR", "R"):
            q = qn(parts[1])
            old = wire[q]
            wire[q] = when(old, values.zero, cond)
            if len(parts) > 2 and parts[2].startswith("b"):
                bit = int(parts[2][1:])
                old_bit = bit_values.get(bit, values.fresh())
                bit_values[bit] = when(old_bit, values.fresh(), cond)
        if index in capture_at:
            snap[index] = tuple(wire)
    return values, wire, snap, ccx_sig


def wires_after(op_lines):
    """Final qubit value ids after `op_lines`. Used to check the condition stack."""
    _values, wire, _snap, _sig = interpret(op_lines)
    return wire


def frontier(ops, segments):
    need = {0}
    ccx_in_segment = set()
    for seg in segments:
        for end in (seg["src"][0] - 1, seg["src"][1], seg["copy"][0] - 1, seg["copy"][1]):
            if end >= 0:
                need.add(end)
        for index in range(seg["src"][0], seg["src"][1] + 1):
            if ops[index].startswith("CCX"):
                ccx_in_segment.add(index)
        for index in range(seg["copy"][0], seg["copy"][1] + 1):
            if ops[index].startswith("CCX"):
                ccx_in_segment.add(index)
    values, _wire, snap, ccx_sig = interpret(ops, ccx_in_segment, need)
    scored = []
    for seg in segments:
        src_before = snap[seg["src"][0] - 1]
        src_end = snap[seg["src"][1]]
        copy_before = snap[seg["copy"][0] - 1]
        copy_end = snap[seg["copy"][1]]
        outs = []
        for q in range(62):
            if (
                src_end[q] == copy_end[q]
                and src_end[q] != copy_before[q]
                and src_end[q] != values.zero
                and src_end[q] != src_before[q]
            ):
                outs.append(q)
        row = dict(seg)
        row["frontier_qubits"] = outs
        row["frontier"] = len(outs)
        row["width_if_retained"] = 62 + len(outs)
        # The copy is the recomputation. Keeping the value removes that copy's
        # Toffoli-like gates. Count only that copy, and only for a frontier of
        # one or two outputs. The clear may share wires with other live data.
        row["conservative_toffoli_like_saved"] = seg["copy_toffoli_like"] if 1 <= len(outs) <= 2 else 0
        src_sig = [ccx_sig[i] for i in range(seg["src"][0], seg["src"][1] + 1) if i in ccx_sig]
        copy_sig = [ccx_sig[i] for i in range(seg["copy"][0], seg["copy"][1] + 1) if i in ccx_sig]
        row["versioned_signature"] = src_sig
        row["copy_versioned_signature"] = copy_sig
        row["value_signature_equal"] = [
            (left["controls"], left["target"], left["condition"], left["active_condition"])
            for left in src_sig
        ] == [
            (right["controls"], right["target"], right["condition"], right["active_condition"])
            for right in copy_sig
        ]
        row["break_even_tests"] = break_even_tests(row["conservative_toffoli_like_saved"], len(outs))
        scored.append(row)
    return scored


def main():
    ops = load_ops()
    segments, groups = repeated_segments(ops)
    scored = frontier(ops, segments)
    eligible = [row for row in scored if 1 <= row["frontier"] <= 2]
    eligible.sort(key=lambda row: -row["conservative_toffoli_like_saved"])
    best = eligible[0] if eligible else None
    save = best["conservative_toffoli_like_saved"] if best else 0
    best_tests = best["break_even_tests"] if best else break_even_tests(0, 0)
    decision = "stop"
    if best and (best_tests["q63"]["passed"] or best_tests["q64"]["passed"]) and not best_tests["q65"]["passed"]:
        decision = "keep"
    reason = (
        "No frontier-1 or frontier-2 copy clears its width-specific break-even. "
        f"The largest conservative saving is {save} Toffoli-like gates. "
        f"63Q requires >{BREAK_EVEN[63]:.3f}, 64Q requires >{BREAK_EVEN[64]:.3f}, and 65Q is rejected."
    )
    if decision == "keep":
        reason = "A frontier-1 or frontier-2 copy cleared its break-even."
    report = {
        "window": list(WINDOW),
        "segment_groups": len(groups),
        "segments_15": len(groups),
        "matched_parts": len(segments),
        "repeated_ccx": sum(group["repeated_ccx"] for group in groups),
        "repeated_ccx_reconciliation": {
            "measured": sum(group["repeated_ccx"] for group in groups),
            "audit_figure": 141,
            "difference": 141 - sum(group["repeated_ccx"] for group in groups),
            "measured_rule": "Non-overlapping exact op-text copies of length at least 8, separated by at least 2000 ops, then grouped into 15 source rows.",
            "audit_figure_meaning": "141 is the earlier audit count of ordered repeated CCX in ops 15583:36941.",
            "effect_on_stop": "The stop uses the measured count. The 8-gate difference cannot lift the best frontier-2 save of 4 above the 64Q line 50.877.",
        },
        "groups": [
            {
                "start": group["start"],
                "stop": group["stop"],
                "repeated_ccx": group["repeated_ccx"],
                "parts": [
                    {
                        "src": part["src"],
                        "copy": part["copy"],
                        "repeated_ccx": part["repeated_ccx"],
                        "frontier": part["frontier"],
                        "value_signature_equal": part["value_signature_equal"],
                        "versioned_signature": part["versioned_signature"],
                        "break_even_tests": part["break_even_tests"],
                    }
                    for part in (
                        next(row for row in scored if row["src"] == part_src["src"])
                        for part_src in group["parts"]
                    )
                ],
            }
            for group in groups
        ],
        "break_even": {
            "C": C_BASE,
            "q63_net_save_required": BREAK_EVEN[63],
            "q64_net_save_required": BREAK_EVEN[64],
            "q65": "rejected",
        },
        "best_frontier_le_2": {
            "src": best["src"],
            "copy": best["copy"],
            "frontier": best["frontier"],
            "frontier_qubits": best["frontier_qubits"],
            "conservative_toffoli_like_saved": best["conservative_toffoli_like_saved"],
            "break_even_tests": best_tests,
        } if best else None,
        "break_even_tests": best_tests,
        "decision": decision,
        "reason": reason,
        "retain_r1_written": False,
        "official_verify_allowed": False,
        "signature": "boolean value-id; PUSH stack and inline if are ANDed; conditional CX/CCX/X are not unconditional",
    }
    text = json.dumps(report, indent=2) + "\n"
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "retention_candidates.json").write_text(text)
    retain = ART / "retain_r1.kmb"
    if retain.exists():
        retain.unlink()
    print(json.dumps({"decision": decision, "groups": len(groups), "repeated_ccx": report["repeated_ccx"], "best_save": save}, indent=2))


if __name__ == "__main__":
    main()
