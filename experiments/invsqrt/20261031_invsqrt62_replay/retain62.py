"""Screen one retention candidate on the 62-qubit invsqrt circuit.

The screen covers ops 15583:36941. Repeated CCX segments are exact op-text
copies separated by more than 2000 ops, then grouped into rows. A copy enters
the savings ranking only when all of the following hold: frontier size is 1 or
2, the source and copy value signatures are equal, every frontier target is
zero before the copy, the retained value is not overwritten across its
lifetime, and the source-to-copy span does not cross an unexplained HMR/R.
Break-even uses baseline C = 1628.0743548387097. No second candidate is
applied. This script does not run the official verifier and does not write
retain_r1.kmb.
"""

from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

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
        self.and_of = {}
        self.meas_source = {}
        self._meas = 0
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
            self.and_of[atom] = key
        return self.vid(frozenset([atom]))

    def mux(self, control, a, b):
        return self.xor(b, self.and_(control, self.xor(a, b)))

    def measurement(self, op, bit):
        """A measurement leaf sourced at one HMR. Not the pre-measurement qubit."""
        self._meas += 1
        atom = 5_000_000 + self._meas
        vid = self.vid(frozenset([atom]))
        self.meas_source[atom] = {"op": op, "bit": bit, "kind": "HMR"}
        return vid, atom


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


def interpret(ops, capture_ccx=None, capture_at=None, track=False, entry=None):
    """Boolean interpreter. A non-empty condition stack gates every write.

    The active condition is the AND of every pushed bit and any inline `if`.
    PUSH/POP themselves always update the stack. HMR and R are recorded as
    barriers and are not given a classical inverse.

    `track=False` is the retention path: every qubit starts as its own singleton
    and unseen classical bits are unsourced fresh values. `track=True` is the
    dataflow path. It does not run unless the caller asks for it.
    """
    values = Values()
    if track:
        wire = []
        for qubit in range(62):
            if entry is not None and qubit in entry:
                wire.append(values.one if entry[qubit] else values.zero)
            elif qubit <= 21:
                wire.append(values.vid(frozenset([qubit])))
            else:
                wire.append(values.zero)
    else:
        wire = [values.vid(frozenset([q])) for q in range(62)]
    condition = []
    bit_values = {}
    snap = {}
    cond_at = {}
    ccx_sig = {}
    history = [[] for _ in range(62)]
    barriers = []
    zpow = []
    measurement_resets = []
    unknown_ops = []
    capture_ccx = capture_ccx or set()
    capture_at = capture_at or set()
    entry_wires = tuple(wire)

    def ensure_bit(bit):
        if bit not in bit_values:
            # Tracking mode starts classical bits at zero. Retention still mints
            # an unsourced fresh value the first time a bit is mentioned.
            bit_values[bit] = values.zero if track else values.fresh()
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

    def write(q, new):
        wire[q] = new
        history[q].append((index, new))

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
            old = ensure_bit(bit)
            stored = values.zero if kind == "BIT_STORE0" else values.one
            bit_values[bit] = when(old, stored, cond)
        elif kind == "BIT_INVERT":
            bit = int(parts[1][1:])
            old = ensure_bit(bit)
            bit_values[bit] = when(old, values.xor(old, values.one), cond)
        elif kind == "SWAP":
            a, b = qn(parts[1]), qn(parts[2])
            old_a, old_b = wire[a], wire[b]
            write(a, when(old_a, old_b, cond))
            write(b, when(old_b, old_a, cond))
        elif kind == "CSWAP":
            c, a, b = qn(parts[1]), qn(parts[2]), qn(parts[3])
            old_a, old_b = wire[a], wire[b]
            swapped_a = values.mux(wire[c], old_b, old_a)
            swapped_b = values.mux(wire[c], old_a, old_b)
            write(a, when(old_a, swapped_a, cond))
            write(b, when(old_b, swapped_b, cond))
        elif kind == "CX":
            a, b = qn(parts[1]), qn(parts[2])
            old = wire[b]
            write(b, when(old, values.xor(old, wire[a]), cond))
        elif kind == "CCX":
            a, b, t = qn(parts[1]), qn(parts[2]), qn(parts[3])
            if index in capture_ccx:
                ccx_sig[index] = {
                    "op": index,
                    "controls": [wire[a], wire[b]],
                    "control_qubits": [a, b],
                    "target": wire[t],
                    "target_qubit": t,
                    "condition": list(condition),
                    "active_condition": cond,
                }
            old = wire[t]
            write(t, when(old, values.xor(old, values.and_(wire[a], wire[b])), cond))
        elif kind == "X":
            t = qn(parts[1])
            old = wire[t]
            write(t, when(old, values.xor(old, values.one), cond))
        elif kind in ("Z", "CZ", "CCZ", "NEG", "Z_POW"):
            # These do not change computational-basis values.
            if track and kind == "Z_POW" and len(parts) > 1 and parts[1].startswith("q"):
                qubit = qn(parts[1])
                zpow.append(
                    {
                        "op": index,
                        "wire": parts[1],
                        "qubit": qubit,
                        "value_id": wire[qubit],
                        "angle": parts[2] if len(parts) > 2 else None,
                        "condition": list(condition),
                        "active_condition": cond,
                    }
                )
        elif kind in ("HMR", "R"):
            barriers.append(
                {
                    "op": index,
                    "kind": kind,
                    "line": line,
                    "condition": list(condition),
                    "condition_depth": len(condition),
                }
            )
            q = qn(parts[1])
            old = wire[q]
            if track:
                bit = None
                leaf = None
                atom = None
                if kind == "HMR" and len(parts) > 2 and parts[2].startswith("b"):
                    bit = int(parts[2][1:])
                    leaf, atom = values.measurement(index, bit)
                    old_bit = bit_values.get(bit, values.zero)
                    bit_values[bit] = when(old_bit, leaf, cond)
                measurement_resets.append(
                    {
                        "op": index,
                        "kind": kind,
                        "line": line,
                        "qubit": q,
                        "pre_value": old,
                        "measurement_bit": bit,
                        "measurement_leaf": leaf,
                        "measurement_atom": atom,
                        "not_boolean_clear": True,
                        "not_equal_to_pre_value": True,
                        "condition": list(condition),
                    }
                )
                write(q, when(old, values.zero, cond))
            else:
                write(q, when(old, values.zero, cond))
                if len(parts) > 2 and parts[2].startswith("b"):
                    bit = int(parts[2][1:])
                    old_bit = bit_values.get(bit, values.fresh())
                    bit_values[bit] = when(old_bit, values.fresh(), cond)
        elif track:
            unknown_ops.append({"op": index, "line": line})
        if index in capture_at:
            snap[index] = tuple(wire)
            cond_at[index] = list(condition)
    return values, wire, snap, ccx_sig, {
        "history": history,
        "barriers": barriers,
        "cond_at": cond_at,
        "entry": entry_wires,
        "zpow": zpow,
        "measurement_resets": measurement_resets,
        "unknown_ops": unknown_ops,
        "track": track,
    }


def wires_after(op_lines):
    """Final qubit value ids after `op_lines`. Used to check the condition stack."""
    _values, wire, _snap, _sig, _extra = interpret(op_lines)
    return wire


def check_condition_semantics():
    """The shipped interpreter must match kickmix on a blocked X and a later X."""
    blocked = wires_after(["BIT_STORE0 b0", "PUSH_CONDITION if b0", "X q1"])
    base = wires_after([])
    if blocked[1] != base[1]:
        raise SystemExit("condition stack failed to block X q1")
    opened = wires_after(["BIT_STORE1 b0", "PUSH_CONDITION if b0", "X q1"])
    if opened[1] == base[1]:
        raise SystemExit("condition stack failed to fire X q1")
    text = "\n".join([
        "REGISTER r0 \"x\"",
        "APPEND_TO_REGISTER q0 r0",
        "APPEND_TO_REGISTER q1 r0",
        "BIT_STORE0 b0",
        "PUSH_CONDITION if b0",
        "X q1",
        "",
    ])
    circuit = kickmix.Circuit.from_file(io.StringIO(text), format="kmx")
    sim = kickmix.Simulator(batch_size=1, seed=1)
    sim.clear_for_shot()
    sim.do(circuit)
    bit = int(np_bit(sim, 1))
    if bit != 0:
        raise SystemExit(f"kickmix executed a blocked X, q1={bit}")


def np_bit(sim, qubit):
    bits = np.asarray(sim.read_across_shots(kickmix.array([kickmix.q(qubit)])))
    return int(bits.reshape(-1)[0])


def signature_key(row):
    return (row["controls"], row["target"], row["condition"], row["active_condition"])


def lifetime_evidence(q, source_value, zero, src_end, copy_start, copy_end, history):
    """The retained value may be cleared to zero, recomputed, and then left intact."""
    window = [
        {"op": op, "value_id": vid, "is_zero": vid == zero, "is_source_value": vid == source_value}
        for op, vid in history[q]
        if src_end < op <= copy_end
    ]
    pre = [item for item in window if item["op"] < copy_start]
    reasons = []
    if not pre or not pre[-1]["is_zero"]:
        reasons.append("not_cleared_to_zero_before_copy")
    if any(not item["is_zero"] and not item["is_source_value"] for item in pre):
        reasons.append("intermediate_value_before_copy")
    restored = False
    for item in window:
        if item["op"] < copy_start:
            continue
        if item["is_source_value"]:
            restored = True
        elif restored:
            reasons.append("overwritten_after_restore")
            break
    if not restored:
        reasons.append("source_value_not_restored")
    return {
        "qubit": q,
        "source_value_id": source_value,
        "unoverwritten": not reasons,
        "reasons": reasons,
        "writes": window,
    }


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
    values, _wire, snap, ccx_sig, extra = interpret(ops, ccx_in_segment, need)
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
        src_sig = [ccx_sig[i] for i in range(seg["src"][0], seg["src"][1] + 1) if i in ccx_sig]
        copy_sig = [ccx_sig[i] for i in range(seg["copy"][0], seg["copy"][1] + 1) if i in ccx_sig]
        equal = [signature_key(left) for left in src_sig] == [signature_key(right) for right in copy_sig]
        zero_rows = [
            {"qubit": q, "value_id": copy_before[q], "is_zero": copy_before[q] == values.zero}
            for q in outs
        ]
        zero_holds = bool(outs) and all(item["is_zero"] for item in zero_rows)
        copy_ccx_targets = [
            {
                "op": item["op"],
                "target_qubit": item["target_qubit"],
                "value_id_before": item["target"],
                "is_zero": item["target"] == values.zero,
                "condition": item["condition"],
                "active_condition": item["active_condition"],
            }
            for item in copy_sig
        ]
        lives = [
            lifetime_evidence(
                q, src_end[q], values.zero, seg["src"][1], seg["copy"][0], seg["copy"][1], extra["history"]
            )
            for q in outs
        ]
        life_ok = bool(outs) and all(item["unoverwritten"] for item in lives)
        crossed = [
            row for row in extra["barriers"]
            if seg["src"][0] <= row["op"] <= seg["copy"][1]
        ]
        # No HMR/R in this screen has a separate classical account, so every
        # barrier the span crosses is unexplained.
        unexplained = bool(crossed)
        frontier_ok = 1 <= len(outs) <= 2
        eligible = frontier_ok and equal and zero_holds and life_ok and not unexplained
        saved = seg["copy_toffoli_like"] if eligible else None
        row = dict(seg)
        row.update(
            {
                "frontier_qubits": outs,
                "frontier": len(outs),
                "width_if_retained": 62 + len(outs),
                "eligible": eligible,
                "conservative_toffoli_like_saved": saved,
                "versioned_signature": src_sig,
                "copy_versioned_signature": copy_sig,
                "value_signature_equal": equal,
                "condition_environment": {
                    "src_before": extra["cond_at"][seg["src"][0] - 1],
                    "src_after": extra["cond_at"][seg["src"][1]],
                    "copy_before": extra["cond_at"][seg["copy"][0] - 1],
                    "copy_after": extra["cond_at"][seg["copy"][1]],
                },
                "zero_before_copy": {
                    "holds": zero_holds,
                    "frontier": zero_rows,
                    "copy_ccx_targets": copy_ccx_targets,
                },
                "lifetime": {
                    "unoverwritten": life_ok,
                    "frontier": lives,
                },
                "hmr_r_barrier": {
                    "crossed": bool(crossed),
                    "unexplained": unexplained,
                    "count": len(crossed),
                    "ops": crossed,
                },
                "break_even_tests": break_even_tests(saved or 0, len(outs)) if eligible else None,
            }
        )
        scored.append(row)
    return scored


def exclusion_reasons(row):
    reasons = []
    if not 1 <= row["frontier"] <= 2:
        reasons.append("frontier_not_in_1_2")
    if not row["value_signature_equal"]:
        reasons.append("value_signature_unequal")
    if not row["zero_before_copy"]["holds"]:
        reasons.append("target_not_zero_before_copy")
    if not row["lifetime"]["unoverwritten"]:
        reasons.append("lifetime_overwritten")
    if row["hmr_r_barrier"]["unexplained"]:
        reasons.append("unexplained_hmr_r_barrier")
    return reasons


def repeated_ccx_ops(ops, scored):
    listed = []
    for row in scored:
        reasons = exclusion_reasons(row)
        for index in range(row["src"][0], row["src"][1] + 1):
            if not ops[index].startswith("CCX"):
                continue
            listed.append(
                {
                    "op": index,
                    "line": ops[index],
                    "src": row["src"],
                    "copy": row["copy"],
                    "exclusion_reasons": reasons,
                }
            )
    return listed


def require_ranked_proofs(ranked):
    for row in ranked:
        if not 1 <= row["frontier"] <= 2:
            raise SystemExit("ranked row frontier is outside 1..2")
        if row["value_signature_equal"] is not True:
            raise SystemExit("ranked row signatures differ")
        if not row["versioned_signature"] or not row["copy_versioned_signature"]:
            raise SystemExit("ranked row is missing a version signature")
        if not row["zero_before_copy"]["holds"]:
            raise SystemExit("ranked row is missing zero-before-copy")
        if not row["lifetime"]["unoverwritten"]:
            raise SystemExit("ranked row lifetime is overwritten")
        if row["hmr_r_barrier"]["unexplained"]:
            raise SystemExit("ranked row crosses an unexplained HMR/R barrier")
        env = row["condition_environment"]
        for key in ("src_before", "src_after", "copy_before", "copy_after"):
            if key not in env:
                raise SystemExit(f"ranked row is missing condition environment {key}")
        if row["conservative_toffoli_like_saved"] is None:
            raise SystemExit("ranked row is missing a savings figure")


def main():
    check_condition_semantics()
    ops = load_ops()
    segments, groups = repeated_segments(ops)
    scored = frontier(ops, segments)
    ranked = [row for row in scored if row["eligible"]]
    ranked.sort(key=lambda row: -row["conservative_toffoli_like_saved"])
    require_ranked_proofs(ranked)
    best = ranked[0] if ranked else None
    if best is None:
        decision = "no_eligible_candidate"
        reason = (
            "窗口 15583:36941 在当前筛选规则下没有可证明的保留条目。"
            "规则同时要求 frontier 为 1 或 2、source/copy 值签名相等、copy 前目标为零、"
            "保留值存活期无覆盖，以及未跨越未解释的 HMR/R。"
            "这不是保留路线的全局否定。"
        )
    else:
        tests = best["break_even_tests"]
        decision = "stop"
        if (tests["q63"]["passed"] or tests["q64"]["passed"]) and not tests["q65"]["passed"]:
            decision = "keep"
        reason = "有通过证明的条目，但没有越过 63Q 或 64Q 回本线。" if decision == "stop" else "有条目越过回本线。"
    ccx_ops = repeated_ccx_ops(ops, scored)
    measured = sum(group["repeated_ccx"] for group in groups)
    if len(ccx_ops) != measured:
        raise SystemExit(f"repeated CCX list {len(ccx_ops)} != measured {measured}")
    if any(not item["exclusion_reasons"] for item in ccx_ops) and best is None:
        raise SystemExit("an unexcluded CCX is outside the savings ranking")
    report = {
        "window": list(WINDOW),
        "decision_scope": "仅限窗口 15583:36941 与当前筛选规则，不是保留路线的全局否定。",
        "segment_groups": len(groups),
        "segments_15": len(groups),
        "matched_parts": len(segments),
        "repeated_ccx": measured,
        "repeated_ccx_ops": ccx_ops,
        "repeated_ccx_reconciliation": {
            "measured": measured,
            "measured_ops_listed": len(ccx_ops),
            "historical_141": "历史数字不可复现",
            "reconciliation": "历史数字不可复现",
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
                        "frontier_qubits": part["frontier_qubits"],
                        "eligible": part["eligible"],
                        "value_signature_equal": part["value_signature_equal"],
                        "versioned_signature": part["versioned_signature"],
                        "copy_versioned_signature": part["copy_versioned_signature"],
                        "condition_environment": part["condition_environment"],
                        "zero_before_copy": part["zero_before_copy"],
                        "lifetime": part["lifetime"],
                        "hmr_r_barrier": part["hmr_r_barrier"],
                        "conservative_toffoli_like_saved": part["conservative_toffoli_like_saved"],
                        "exclusion_reasons": exclusion_reasons(part),
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
        "ranked": [
            {
                "src": row["src"],
                "copy": row["copy"],
                "frontier": row["frontier"],
                "frontier_qubits": row["frontier_qubits"],
                "value_signature_equal": row["value_signature_equal"],
                "versioned_signature": row["versioned_signature"],
                "copy_versioned_signature": row["copy_versioned_signature"],
                "condition_environment": row["condition_environment"],
                "zero_before_copy": row["zero_before_copy"],
                "lifetime": row["lifetime"],
                "hmr_r_barrier": row["hmr_r_barrier"],
                "conservative_toffoli_like_saved": row["conservative_toffoli_like_saved"],
                "break_even_tests": row["break_even_tests"],
            }
            for row in ranked
        ],
        "best": None if best is None else {
            "src": best["src"],
            "copy": best["copy"],
            "frontier": best["frontier"],
            "conservative_toffoli_like_saved": best["conservative_toffoli_like_saved"],
            "break_even_tests": best["break_even_tests"],
        },
        "best_frontier_le_2": None,
        "decision": decision,
        "reason": reason,
        "retain_r1_written": False,
        "official_verify_allowed": False,
        "official_verifier_shots": 0,
        "signature": "boolean value-id; PUSH stack and inline if are ANDed; conditional CX/CCX/X are not unconditional",
    }
    if best is None and report["best"] is not None:
        raise SystemExit("best was set without an eligible row")
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if best is None and "\"conservative_toffoli_like_saved\": 4" in text:
        raise SystemExit("ineligible screen wrote a savings of 4")
    if "历史数字不可复现" not in text:
        raise SystemExit("missing the historical-list statement")
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "retention_candidates.json").write_text(text)
    retain = ART / "retain_r1.kmb"
    if retain.exists():
        retain.unlink()
    print(json.dumps({
        "decision": decision,
        "groups": len(groups),
        "repeated_ccx": measured,
        "listed_ccx": len(ccx_ops),
        "ranked": len(ranked),
        "best": None if best is None else best["src"],
    }, indent=2))


if __name__ == "__main__":
    main()
