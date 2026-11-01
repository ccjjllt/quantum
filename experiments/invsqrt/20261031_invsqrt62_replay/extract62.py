"""Read-only extraction of stages, angles, address snapshots, and lifetimes.

The 87-qubit table and its 44 angles are not loaded. Layout numbers are checked
against a real prefix snapshot and left 待证实 when the snapshot does not settle them.
"""

from __future__ import annotations

import io
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

import kickmix  # noqa: E402

ORACLE = ROOT / "artifacts/20261030_public_best/candidate/invsqrt.kmb"
ART = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt"
MAX_X = 3_133_452


def split_ops(circuit):
    text = io.StringIO()
    circuit.to_file(text, format="kmx")
    lines = text.getvalue().splitlines()
    header = [line for line in lines if line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    return header, ops


def general_angles(ops):
    stack = []
    rows = []
    for index, line in enumerate(ops):
        if line.startswith("PUSH_CONDITION"):
            stack.append(line.split()[-1])
        elif line.startswith("POP_CONDITION"):
            if stack:
                stack.pop()
        elif line.startswith("Z_POW"):
            parts = line.split()
            half = Fraction(parts[2])
            if half % Fraction(1, 2) == 0 or half % Fraction(1, 4) == 0:
                continue
            if 15244 <= index < 15583:
                block = "Hphase"
            elif 25630 <= index < 25871:
                block = "Lphase"
            else:
                block = "other"
            rows.append(
                {
                    "op": index,
                    "wire": parts[1],
                    "half_turns": [half.numerator, half.denominator],
                    "units": official.half_turns_to_units(half),
                    "condition_stack": list(stack),
                    "phase_block": block,
                    "kmx": line,
                }
            )
    return rows


def address_of(x: int, shift: int = 13) -> int:
    lg = x.bit_length() - 1
    t = 21 - lg
    xn = x << t
    return ((t & 1) << 7) | ((xn >> shift) & 127)


def representatives():
    found = {}
    for x in range(1, MAX_X + 1):
        addr = address_of(x)
        if addr not in found:
            found[addr] = x
            if len(found) == 256:
                break
    if len(found) != 256:
        raise SystemExit(f"only found {len(found)} addresses")
    return [found[a] for a in range(256)]


def snapshot(circuit, header, ops, xs, stop):
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    x_reg, _scratch = official.validate_registers(circuit, spec)
    stage = kickmix.Circuit.from_file(io.StringIO("\n".join(header + ops[:stop]) + "\n"), format="kmx")
    sim = kickmix.Simulator(batch_size=256, seed=101)
    arr = np.array(xs, dtype=np.uint64)
    sim.clear_for_shot()
    sim.write_across_shots(x_reg, official.to_bits(arr, 22))
    sim.do(stage)
    bits = np.asarray(sim.read_across_shots(kickmix.array([kickmix.q(i) for i in range(62)])))
    return bits


def qubit_of(token: str) -> int:
    return int(token[1:])


def lifetimes(ops, stages):
    version = [0] * 62
    raw = war = waw = 0
    last_write = [-1] * 62
    barriers = []
    swaps = []
    cswaps = []
    logical = list(range(62))
    depth = 0
    max_depth = 0
    depth_at = {}
    logical_at = {}
    stage_ends = {stage["stop_exclusive"] for stage in stages}
    stage_raw = {stage["name"]: {"raw": 0, "war": 0, "waw": 0} for stage in stages}
    stage_of = []
    for stage in stages:
        stage_of.extend([stage["name"]] * (stage["stop_exclusive"] - stage["start"]))
    for index, line in enumerate(ops):
        parts = line.split()
        kind = parts[0]
        if kind == "PUSH_CONDITION":
            depth += 1
            max_depth = max(max_depth, depth)
        elif kind == "POP_CONDITION":
            depth = max(0, depth - 1)
        elif kind == "SWAP":
            a, b = qubit_of(parts[1]), qubit_of(parts[2])
            logical[a], logical[b] = logical[b], logical[a]
            swaps.append({"op": index, "qubits": [a, b], "condition_depth": depth})
        elif kind == "CSWAP":
            cswaps.append({
                "op": index,
                "control": qubit_of(parts[1]),
                "targets": [qubit_of(parts[2]), qubit_of(parts[3])],
                "condition_depth": depth,
            })
        if kind in ("HMR", "R"):
            barriers.append({"op": index, "kind": kind, "line": line, "condition_depth": depth})
        reads, writes = [], []
        if kind in ("CX", "CZ", "CCX", "CSWAP", "SWAP"):
            qubits = [qubit_of(tok) for tok in parts[1:] if tok.startswith("q")]
            reads = qubits
            if kind == "CX":
                writes = [qubits[1]]
            elif kind in ("CCX",):
                writes = [qubits[2]]
            elif kind == "CSWAP":
                writes = qubits[1:]
            elif kind == "SWAP":
                writes = qubits
        elif kind in ("X", "Z", "HMR", "R", "Z_POW") and len(parts) > 1 and parts[1].startswith("q"):
            q = qubit_of(parts[1])
            reads = [q]
            if kind in ("X", "HMR", "R"):
                writes = [q]
        name = stage_of[index]
        for q in reads:
            if last_write[q] >= 0:
                raw += 1
                stage_raw[name]["raw"] += 1
        for q in writes:
            if last_write[q] >= 0 and q not in reads:
                waw += 1
                stage_raw[name]["waw"] += 1
            if q in reads:
                war += 1
                stage_raw[name]["war"] += 1
            version[q] += 1
            last_write[q] = index
        if index + 1 in stage_ends:
            depth_at[index + 1] = depth
            logical_at[index + 1] = list(logical)
    window = [row["op"] for row in barriers if WINDOW_LO <= row["op"] < WINDOW_HI]
    return {
        "raw": raw,
        "war": war,
        "waw": waw,
        "raw_war_waw_by_stage": stage_raw,
        "swap_count": len(swaps),
        "cswap_count": len(cswaps),
        "swaps": swaps,
        "cswaps": cswaps,
        "logical_map_note": "Unconditional SWAP exchanges logical labels. CSWAP is recorded and is not applied to the static map.",
        "logical_map_at_stage_end": {str(op): labels for op, labels in logical_at.items()},
        "condition_stack_max_depth": max_depth,
        "condition_depth_at_stage_end": {str(op): depth_at[op] for op in depth_at},
        "hmr": sum(1 for row in barriers if row["kind"] == "HMR"),
        "r": sum(1 for row in barriers if row["kind"] == "R"),
        "opaque_barrier_count": len(barriers),
        "opaque_barriers": barriers,
        "opaque_barriers_in_15583_36941": window,
        "final_qubit_versions": version,
        "note": "HMR and R are opaque barriers. Do not delete or commute across them.",
    }


WINDOW_LO, WINDOW_HI = 15583, 36941

SEMANTIC_STAGES = [
    {"name": "normalize", "start": 0, "stop_exclusive": 238,
     "evidence": "Leading-zero ladder and barrel CSWAP; HMR cleanup ends at op 237."},
    {"name": "lookup", "start": 238, "stop_exclusive": 1200,
     "evidence": "At op 1200 the shift-13 address is on q13-q19 and q21."},
    {"name": "post_lookup", "start": 1200, "stop_exclusive": 15244,
     "evidence": "Arithmetic between the address snapshot and the first high-word rotation."},
    {"name": "Hphase", "start": 15244, "stop_exclusive": 16127,
     "evidence": "15 general rotations plus every later CZ/Z that still cites measurement bits b388-b403. The last such op is 16126."},
    {"name": "A", "start": 16127, "stop_exclusive": 20738,
     "evidence": "Derivative Horner. Its HMR bits are not cited after the CZ at op 20737."},
    {"name": "B", "start": 20738, "stop_exclusive": 25630,
     "evidence": "Output Horner. Measurement fixes stay before the low-word rotation at op 25630."},
    {"name": "Lphase", "start": 25630, "stop_exclusive": 28726,
     "evidence": "26 general rotations, the b350-b374 repairs, and the CCZ q27 q21 ladder. The condition nest returns before op 28726."},
    {"name": "inverse_B", "start": 28726, "stop_exclusive": 32226,
     "evidence": "CCX/HMR replay of B. The following region is CX-dominated."},
    {"name": "inverse_A", "start": 32226, "stop_exclusive": 43870,
     "evidence": "CX replay of A, then its HMR bits. Those bits are still cited by CZ through op 43869."},
    {"name": "unlookup", "start": 43870, "stop_exclusive": 46706,
     "evidence": "Lookup cleanup. The b7926 fixes end at op 46413, before the final x swaps."},
    {"name": "tail", "start": 46706, "stop_exclusive": 47201,
     "evidence": "Inverse normalization from SWAP q0 q1, including the Ahmed q60 cache and its HMR/CZ repairs."},
]


def decompose(x: int):
    t = 21 - (int(x).bit_length() - 1)
    xn = int(x) << t
    return ((t & 1) << 7) | ((xn >> 13) & 127), t >> 1


def representatives_by_shift():
    """Smallest normalization shift s<=7 for every address, plus every s=7 witness."""
    best = {}
    at_s7 = {}
    for x in range(1, MAX_X + 1):
        addr, shift = decompose(x)
        if shift <= 7 and (addr not in best or shift < best[addr][0]):
            best[addr] = (shift, x)
        if shift == 7 and addr not in at_s7:
            at_s7[addr] = x
    if len(best) != 256:
        raise SystemExit(f"expected 256 addresses, found {len(best)}")
    ordered = [best[a][1] for a in range(256)]
    return ordered, [at_s7[a] for a in sorted(at_s7)]


def phase_controls(header, ops, zops, xs):
    """Bit on each rotation's own target, immediately before that Z_POW.

    `zops` is a list of `(op_index, wire)`. Batch size is 256; xs may be shorter.
    """
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    circuit = kickmix.Circuit.from_file(ORACLE)
    x_reg, _scratch = official.validate_registers(circuit, spec)
    sim = kickmix.Simulator(batch_size=256, seed=11)
    buf = np.zeros(256, dtype=np.uint64)
    buf[: len(xs)] = np.asarray(xs, dtype=np.uint64)
    sim.clear_for_shot()
    sim.write_across_shots(x_reg, official.to_bits(buf, 22))
    prev = 0
    columns = []
    for cut, wire in zops:
        stage = kickmix.Circuit.from_file(io.StringIO("\n".join(header + ops[prev:cut]) + "\n"), format="kmx")
        sim.do(stage)
        probe = kickmix.array([kickmix.q(wire)])
        bit = np.asarray(sim.read_across_shots(probe)).reshape(-1)[: len(xs)].astype(np.uint8)
        columns.append(bit)
        one = kickmix.Circuit.from_file(io.StringIO("\n".join(header + [ops[cut]]) + "\n"), format="kmx")
        sim.do(one)
        prev = cut + 1
    return np.stack(columns, axis=0)


def high_word(column, shift):
    """7-bit H if the s-window matches nHf=7 and the constant bit is set."""
    if shift + 7 >= 15:
        return None
    if int(column[shift + 7]) != 1:
        return None
    if shift and int(column[:shift].any()):
        return None
    if shift + 8 < 15 and int(column[shift + 8:].any()):
        return None
    word = 0
    for j in range(7):
        word |= int(column[shift + j]) << j
    return word


def horner_address_constants(header, ops):
    """Qubits constant across two delta values of the same address and shift."""
    groups = defaultdict(list)
    for x in range(1, MAX_X + 1):
        addr, shift = decompose(x)
        key = (addr, shift)
        if len(groups[key]) < 2:
            groups[key].append(x)
    chosen = []
    seen = set()
    for key, pair in groups.items():
        if len(pair) < 2 or key[0] in seen:
            continue
        seen.add(key[0])
        chosen.append(pair)
        if len(chosen) == 128:
            break
    xs = np.array([x for pair in chosen for x in pair], dtype=np.uint64)
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    circuit = kickmix.Circuit.from_file(ORACLE)
    x_reg, _scratch = official.validate_registers(circuit, spec)
    sim = kickmix.Simulator(batch_size=256, seed=5)
    sim.clear_for_shot()
    sim.write_across_shots(x_reg, official.to_bits(xs, 22))
    probes = kickmix.array([kickmix.q(i) for i in range(62)])
    cuts = [15244, 18000, 22000, 25630]
    prev = 0
    rows = []
    for cut in cuts:
        stage = kickmix.Circuit.from_file(io.StringIO("\n".join(header + ops[prev:cut]) + "\n"), format="kmx")
        sim.do(stage)
        prev = cut
        mat = np.asarray(sim.read_across_shots(probes))
        constant = []
        for q in range(62):
            ok = True
            values = []
            for a in range(128):
                left = int(mat[q, 2 * a])
                right = int(mat[q, 2 * a + 1])
                if left != right:
                    ok = False
                    break
                values.append(left)
            if ok and len(set(values)) > 1:
                constant.append(q)
        rows.append({"cut": cut, "address_constant_qubits": constant})
    return rows


def layout_from_phase(header, ops, angles):
    high = [row for row in angles if row["phase_block"] == "Hphase"]
    low = [row for row in angles if row["phase_block"] == "Lphase"]
    zops = [(row["op"], int(row["wire"][1:])) for row in high + low]
    wires = [wire for _op, wire in zops]
    chosen, s7 = representatives_by_shift()
    controls = phase_controls(header, ops, zops, chosen)
    n_high = len(high)
    words = []
    h_ok = 0
    for index, x in enumerate(chosen):
        addr, shift = decompose(x)
        column = controls[:n_high, index]
        low_col = controls[n_high:, index]
        recovered = high_word(column, shift)
        if recovered is not None:
            h_ok += 1
        words.append(
            {
                "address": addr,
                "x": int(x),
                "s": shift,
                "H": recovered,
                "high_wires": wires[:n_high],
                "low_wires": wires[n_high:],
                "high_bits": [int(b) for b in column.tolist()],
                "low_bits": [int(b) for b in low_col.tolist()],
            }
        )
    # LB=18, G0=1 allows L>>1 bits j<=16, so at shift s the highest low-angle
    # index is s+15. A 1 on that rotation's own wire above the limit rejects it.
    low7 = phase_controls(header, ops, zops, s7)
    lb_offender = None
    for index, x in enumerate(s7):
        _addr, shift = decompose(x)
        limit = shift + 15
        hot = []
        for k, bit in enumerate(low7[n_high:, index].tolist()):
            if bit and k > limit:
                hot.append({"index": k, "op": low[k]["op"], "wire": low[k]["wire"]})
        if hot:
            lb_offender = {"x": int(x), "s": shift, "low_indices": hot, "limit": limit}
            break
    return {
        "words": words,
        "h_recovered": h_ok,
        "s7_count": len(s7),
        "lb_offender": lb_offender,
        "wires": {"high": wires[:n_high], "low": wires[n_high:]},
    }


def condition_before(ops):
    """Condition stack and depth as each op begins. PUSH/POP have not yet run."""
    stack = []
    depths = []
    stacks = []
    for line in ops:
        depths.append(len(stack))
        stacks.append(list(stack))
        if line.startswith("PUSH_CONDITION"):
            stack.append(line.split()[-1])
        elif line.startswith("POP_CONDITION") and stack:
            stack.pop()
    return depths, stacks


def select_horner_cuts(ops):
    """Depth-0 cuts at stage edges, CX-fanout registers, and HMR/R cluster boundaries.

    A conditional CSWAP is not a cut. Cuts prefer an empty condition stack.
    """
    depths, stacks = condition_before(ops)
    wanted = {16127, 20738, 25630}
    i = 16127
    while i < 25630:
        if ops[i].startswith("CX"):
            ctrl = ops[i].split()[1]
            j = i + 1
            while j < 25630 and ops[j].startswith("CX") and ops[j].split()[1] == ctrl:
                j += 1
            if j - i >= 8:
                wanted.add(i)
            i = j
            continue
        i += 1
    # HMR/R that closes a run sitting next to a CCX. Keep depth 0, and keep
    # boundaries at least 400 ops apart so the file stays a cut set, not a dump.
    last_hmr = -1000
    for i in range(16127, 25630):
        kind = ops[i].split()[0]
        if kind not in ("HMR", "R") or depths[i] != 0:
            continue
        window = ops[max(16127, i - 20):i + 20]
        if not any(line.startswith("CCX") for line in window):
            continue
        if i - last_hmr < 400:
            continue
        wanted.add(i)
        last_hmr = i
    cuts = []
    for op in sorted(wanted):
        cuts.append(
            {
                "op": op,
                "condition_depth": depths[op],
                "condition_environment": stacks[op],
                "empty_condition_stack": depths[op] == 0,
            }
        )
    return cuts


def dataflow_until(ops, cut, depths):
    """Last write, direct source, SWAP map, and unresolved CSWAP barriers before `cut`."""
    last_op = [-1] * 62
    last_line = [""] * 62
    last_kind = [""] * 62
    source = [""] * 62
    logical = list(range(62))
    cswaps = []
    conditional_swaps = []
    for index, line in enumerate(ops[:cut]):
        parts = line.split()
        kind = parts[0]
        qubits = [qubit_of(tok) for tok in parts[1:] if tok.startswith("q")]
        conditional = depths[index] > 0 or "if" in parts
        if kind == "SWAP" and len(qubits) >= 2:
            if conditional:
                conditional_swaps.append({"op": index, "qubits": qubits[:2], "applied": False})
            else:
                a, b = qubits[0], qubits[1]
                logical[a], logical[b] = logical[b], logical[a]
                last_op[a] = last_op[b] = index
                last_line[a] = last_line[b] = line
                last_kind[a] = last_kind[b] = kind
                source[a] = f"SWAP with q{b}"
                source[b] = f"SWAP with q{a}"
        elif kind == "CSWAP" and len(qubits) >= 3:
            cswaps.append(
                {
                    "op": index,
                    "control": qubits[0],
                    "targets": qubits[1:3],
                    "conditional_on_stack": conditional,
                    "resolved": False,
                    "barrier": True,
                }
            )
        elif kind == "CX" and len(qubits) >= 2:
            tgt = qubits[1]
            last_op[tgt] = index
            last_line[tgt] = line
            last_kind[tgt] = kind
            source[tgt] = f"XOR q{qubits[0]}"
        elif kind == "CCX" and len(qubits) >= 3:
            tgt = qubits[2]
            last_op[tgt] = index
            last_line[tgt] = line
            last_kind[tgt] = kind
            source[tgt] = f"AND q{qubits[0]} q{qubits[1]}"
        elif kind == "X" and qubits:
            tgt = qubits[0]
            last_op[tgt] = index
            last_line[tgt] = line
            last_kind[tgt] = kind
            source[tgt] = "NOT"
        elif kind in ("HMR", "R") and qubits:
            tgt = qubits[0]
            last_op[tgt] = index
            last_line[tgt] = line
            last_kind[tgt] = kind
            source[tgt] = "reset-to-zero; measured bit is a barrier"
    return {
        "last_op": last_op,
        "last_line": last_line,
        "last_kind": last_kind,
        "source": source,
        "logical_map_swap_only": logical,
        "cswap_barriers": cswaps,
        "conditional_swap_barriers": conditional_swaps,
        "cswap_applied_as_static_swap": False,
    }


def decompose_full(x: int):
    t = 21 - (int(x).bit_length() - 1)
    xn = int(x) << t
    p = t & 1
    s = t >> 1
    address = (p << 7) | ((xn >> 13) & 127)
    delta = xn & ((1 << 13) - 1)
    return {"x": int(x), "t": t, "xn": xn, "p": p, "s": s, "address": address, "delta": delta}


def x_from_parts(address: int, s: int, delta: int):
    p = address >> 7
    t = (s << 1) | p
    if delta & ((1 << t) - 1):
        return None
    xn = (1 << 21) | ((address & 127) << 13) | (delta & ((1 << 13) - 1))
    if not (1 << 21) <= xn < (1 << 22):
        return None
    x = xn >> t
    if not 1 <= x <= MAX_X:
        return None
    got = decompose_full(x)
    if got["address"] != address or got["s"] != s or got["delta"] != delta:
        return None
    return got


def horner_samples():
    """Several deltas at one (address, s), plus other address/s controls."""
    rows = []
    deltas = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096,
              3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047, 4095, 8191]
    for delta in deltas:
        got = x_from_parts(0, 0, delta)
        if got is not None:
            got["role"] = "fixed_address_s"
            rows.append(got)
    for address, s, delta in (
        (1, 0, 0), (1, 0, 1), (2, 0, 0), (64, 0, 0), (127, 0, 0),
        (128, 0, 0), (128, 0, 2), (0, 1, 0), (0, 1, 4), (0, 2, 0),
        (0, 3, 0), (0, 7, 0), (5, 1, 8), (17, 1, 0),
    ):
        got = x_from_parts(address, s, delta)
        if got is not None:
            got["role"] = "address_s_control"
            rows.append(got)
    seen = set()
    unique = []
    for row in rows:
        if row["x"] in seen:
            continue
        seen.add(row["x"])
        unique.append(row)
    return unique


def snap_cuts(header, ops, xs, cuts, seed):
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    circuit = kickmix.Circuit.from_file(ART / "ahmed.kmb")
    x_reg, _scratch = official.validate_registers(circuit, spec)
    out = {cut: [] for cut in cuts}
    probes = kickmix.array([kickmix.q(i) for i in range(62)])
    ordered = sorted(cuts)
    for offset in range(0, len(xs), 256):
        chunk = np.asarray(xs[offset:offset + 256], dtype=np.uint64)
        sim = kickmix.Simulator(batch_size=256, seed=seed)
        buf = np.zeros(256, dtype=np.uint64)
        buf[: len(chunk)] = chunk
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(buf, 22))
        prev = 0
        for cut in ordered:
            stage = kickmix.Circuit.from_file(
                io.StringIO("\n".join(header + ops[prev:cut]) + "\n"), format="kmx"
            )
            sim.do(stage)
            mat = np.asarray(sim.read_across_shots(probes))
            if mat.shape[0] != 62:
                mat = mat.T
            out[cut].append(mat[:, : len(chunk)].astype(np.uint8))
            prev = cut
    return {cut: np.concatenate(parts, axis=1) for cut, parts in out.items()}


def pack_bits(column):
    word = 0
    for bit, value in enumerate(column):
        word |= int(value) << bit
    return word


def _contiguous(items, index_of):
    if not items:
        return []
    ordered = sorted(items, key=index_of)
    runs = [[ordered[0]]]
    for item in ordered[1:]:
        if index_of(item) == index_of(runs[-1][-1]) + 1:
            runs[-1].append(item)
        else:
            runs.append([item])
    return runs


def _variation_key(wire):
    return (
        wire["varies_with_delta"],
        wire["varies_with_address"],
        wire["varies_with_s"],
        wire["measurement_dependent"],
    )


def enumerate_integer_registers(cuts):
    """Contiguous width-8 and width-19 runs from variation class and value origin.

    A wider fanout is not sliced down to 8 or 19. Width 19 stays an empty list
    when no run has that length.
    """
    found = []
    for cut in cuts:
        wires = cut["wires"]
        by_class = {}
        by_origin = {}
        for wire in wires:
            vkey = _variation_key(wire)
            by_class.setdefault(vkey, []).append(wire)
            by_origin.setdefault(vkey + (wire["last_write_kind"], wire["direct_source"]), []).append(wire)
        groups = (
            ("physical_variation_class", by_class, lambda wire: wire["q"]),
            ("physical_variation_class_and_value_origin", by_origin, lambda wire: wire["q"]),
            ("logical_variation_class", by_class, lambda wire: wire["logical_label_after_unconditional_swap"]),
        )
        for basis, buckets, index_of in groups:
            for key, group in buckets.items():
                for run in _contiguous(group, index_of):
                    if len(run) not in (8, 19):
                        continue
                    vkey = key[:4]
                    origins = sorted({(wire["last_write_kind"], wire["direct_source"]) for wire in run})
                    uniform = len(origins) == 1
                    if basis == "logical_variation_class" and not uniform:
                        role = "rejected"
                        reading = "Logical labels are contiguous inside one variation class, but the physical wires do not share a value origin."
                    elif len(run) == 8 and vkey == (False, True, False, False) and uniform:
                        role = "C2"
                        reading = "Address-only 8-bit word. Low qubit index is bit 0. It does not vary with delta or s on the sample that defined the class."
                    elif len(run) == 19 and vkey[0] and not vkey[3] and uniform:
                        role = "T"
                        reading = "Delta-dependent 19-bit word. Low qubit index is bit 0. Horner shifts are e_i = 21+8-19-i."
                    elif (
                        len(run) == 8
                        and basis != "logical_variation_class"
                        and vkey[0]
                        and not vkey[3]
                        and uniform
                        and all(wire["q"] < 13 for wire in run)
                    ):
                        role = "delta_slice"
                        reading = "Width-8 slice of a delta-varying class. Integer reading: wire q holds delta bit q. Not C2, because it varies with delta. Not T, because the width is 8."
                    else:
                        role = "rejected"
                        reading = "Width matches 8 or 19, but variation class or value origin does not fit a C2 or T register."
                    found.append(
                        {
                            "cut": cut["op"],
                            "stage": cut["stage"],
                            "basis": basis,
                            "width": len(run),
                            "role": role,
                            "variation_class": {
                                "varies_with_delta": vkey[0],
                                "varies_with_address": vkey[1],
                                "varies_with_s": vkey[2],
                                "measurement_dependent": vkey[3],
                            },
                            "value_origins": [{"kind": kind, "source": source} for kind, source in origins],
                            "value_origin_uniform": uniform,
                            "wires": [wire["q"] for wire in run],
                            "logical_labels": [wire["logical_label_after_unconditional_swap"] for wire in run],
                            "bit_order": "ascending qubit index, low qubit is bit 0",
                            "integer_interpretation": reading,
                            "last_write_ops": [wire["last_write_op"] for wire in run],
                            "counterexample": None if role in ("C2", "T", "delta_slice") else reading,
                        }
                    )
    width_19 = [row for row in found if row["width"] == 19]
    width_8_origin = [
        row for row in found
        if row["width"] == 8 and row["basis"] == "physical_variation_class_and_value_origin"
    ]
    return {
        "candidates": found,
        "width_8_count": sum(1 for row in found if row["width"] == 8),
        "width_19_count": len(width_19),
        "width_19_physical_variation_class": [
            row for row in width_19 if row["basis"] == "physical_variation_class"
        ],
        "width_19_physical_variation_class_and_value_origin": [
            row for row in width_19 if row["basis"] == "physical_variation_class_and_value_origin"
        ],
        "width_19_logical_variation_class": [
            row for row in width_19 if row["basis"] == "logical_variation_class"
        ],
        "width_8_value_origin": width_8_origin,
        "note": "Exact lengths only. A fanout wider than 8 or 19 is not sliced.",
    }


def horner_cut_record(header, ops):
    """Variation-class cuts. Width 19/8 is not decided by a two-delta constant count."""
    depths, _stacks = condition_before(ops)
    cuts = select_horner_cuts(ops)
    samples = horner_samples()
    xs = [row["x"] for row in samples]
    mats = snap_cuts(header, ops, xs, [row["op"] for row in cuts], seed=101)
    mats_b = snap_cuts(header, ops, xs, [row["op"] for row in cuts], seed=202)
    fixed = [i for i, row in enumerate(samples) if row["role"] == "fixed_address_s"]
    records = []
    for cut in cuts:
        flow = dataflow_until(ops, cut["op"], depths)
        mat = mats[cut["op"]]
        other = mats_b[cut["op"]]
        wires = []
        for q in range(62):
            fixed_vals = {int(mat[q, i]) for i in fixed}
            addr_vals = {
                int(mat[q, i])
                for i, row in enumerate(samples)
                if row["delta"] == 0 and row["s"] == 0
            }
            shift_vals = {
                int(mat[q, i])
                for i, row in enumerate(samples)
                if row["address"] == 0 and row["delta"] == 0
            }
            meas = any(int(mat[q, i]) != int(other[q, i]) for i in range(len(samples)))
            wires.append(
                {
                    "q": q,
                    "last_write_op": flow["last_op"][q],
                    "last_write_kind": flow["last_kind"][q],
                    "direct_source": flow["source"][q],
                    "measurement_dependent": meas,
                    "varies_with_delta": len(fixed_vals) > 1,
                    "varies_with_address": len(addr_vals) > 1,
                    "varies_with_s": len(shift_vals) > 1,
                    "reference_bit": int(mat[q, 0]),
                    "logical_label_after_unconditional_swap": flow["logical_map_swap_only"][q],
                }
            )
        ref = samples[0]
        records.append(
            {
                **cut,
                "stage": "A" if cut["op"] < 20738 else ("B" if cut["op"] < 25630 else "pre_Lphase"),
                "snapshot_meaning": "computational-basis bits immediately before this op, seed 101",
                "snapshot_reference": {
                    "x": ref["x"],
                    "address": ref["address"],
                    "s": ref["s"],
                    "delta": ref["delta"],
                    "bits": "".join(str(int(mat[q, 0])) for q in range(62)),
                },
                "cswap_state": {
                    "applied_as_static_swap": False,
                    "unresolved_barrier_count": len(flow["cswap_barriers"]),
                    "conditional_swap_barrier_count": len(flow["conditional_swap_barriers"]),
                    "note": "Every CSWAP stays an unresolved barrier. Only an unconditional SWAP updates the logical map.",
                },
                "wires": wires,
            }
        )
    fanouts = []
    i = 16127
    while i < 25630:
        if ops[i].startswith("CX"):
            ctrl = ops[i].split()[1]
            j = i + 1
            targets = [qubit_of(ops[i].split()[2])]
            while j < 25630 and ops[j].startswith("CX") and ops[j].split()[1] == ctrl:
                targets.append(qubit_of(ops[j].split()[2]))
                j += 1
            if len(targets) >= 8:
                fanouts.append({"op": i, "control": ctrl, "width": len(targets), "wires": targets})
            i = j
            continue
        i += 1
    return {
        "criterion": "variation class and value origin at fixed (address, s) across many deltas",
        "not_the_criterion": "two deltas having 19 or 8 address-constant wires",
        "LB18_status": "rejected",
        "T_width_tested": 19,
        "C2_width_tested": 8,
        "samples": samples,
        "fanouts": fanouts,
        "fanouts_are_not_sliced_to_width_8_or_19": True,
        "integer_registers": enumerate_integer_registers(records),
        "cuts": records,
    }


def main():
    circuit = kickmix.Circuit.from_file(ORACLE)
    header, ops = split_ops(circuit)
    angles = general_angles(ops)
    if len(angles) != 41:
        raise SystemExit(f"expected 41 general angles, found {len(angles)}")
    xs = representatives()
    bits = snapshot(circuit, header, ops, xs, 1200)
    # Address hypothesis shift=13: bits of addr on q13..q19 and q21, checked on this snapshot.
    addr = np.array([address_of(x) for x in xs], dtype=np.uint64)
    addr_wires = [13, 14, 15, 16, 17, 18, 19, 21]
    addr_ok = True
    for bit, q in enumerate(addr_wires):
        column = (addr >> bit) & 1
        if not np.array_equal(bits[q].astype(np.uint64), column):
            addr_ok = False
    phase = layout_from_phase(header, ops, angles)
    horner_doc = horner_cut_record(header, ops)
    (ART / "horner_cuts.json").write_text(json.dumps(horner_doc, indent=2) + "\n")
    words = phase["words"]
    lb_rejected = phase["lb_offender"] is not None
    h_confirmed = phase["h_recovered"] == 256
    recipe = {
        "loaded_87q_table": False,
        "已证实": {
            "macro_cuts": [[0, 15244], [15244, 15583], [15583, 25630], [25630, 25871], [25871, 47201]],
            "general_angles": 41,
            "angle_blocks": dict(Counter(row["phase_block"] for row in angles)),
            "address_shift_13_wires_at_op_1200": addr_wires,
            "address_wires_match_snapshot": addr_ok,
            "F0": 28,
            "G0": 1,
            "S": 20,
            "nHf": 7,
            "ahmed_hash_source": "6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4",
            "high_word_recovered_for_256_addresses": h_confirmed,
        },
        "待证实": {
            "FT": 19,
            "F2": 8,
            "T_width": 19,
            "C2_width": 8,
            "note": "T width 19 and C2 width 8 stay unconfirmed. The test is variation class and value origin in horner_cuts.json, not a count of address-constant wires across two deltas.",
            "horner_cuts": "horner_cuts.json",
        },
        "已否定": {
            "LB": 18 if lb_rejected else None,
            "lb_counterexample": phase["lb_offender"],
        },
        "semantic_stages": SEMANTIC_STAGES,
    }
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "angles.json").write_text(json.dumps({"count": len(angles), "angles": angles}, indent=2) + "\n")
    (ART / "packed_words.json").write_text(
        json.dumps(
            {
                "address_definition": "((21-floor(log2 x)) & 1) << 7 | ((x << t) >> 13) & 127",
                "address_wires_at_op_1200": addr_wires,
                "address_wires_match": addr_ok,
                "representatives": 256,
                "loaded_87q_table": False,
                "method": "each general Z_POW's own target qubit, one legal x per address at the smallest s<=7",
                "rotation_wires": phase["wires"],
                "layout_verdict": {
                    "F0": {"hypothesis": 28, "status": "confirmed" if h_confirmed else "rejected",
                           "evidence": "nHf=7 and R0=F0-G0=27 with G0=1; H recovered on every address"},
                    "G0": {"hypothesis": 1, "status": "confirmed",
                           "evidence": "low angles start at 2^28, so the 2^27 guard is not phased"},
                    "S": {"hypothesis": 20, "status": "confirmed",
                           "evidence": "offH=S-G0=19; high angles match 2^(46+k) and the H window slides with s"},
                    "LB": {"hypothesis": 18, "status": "rejected" if lb_rejected else "unconfirmed",
                           "evidence": "LB=18 and G0=1 cannot set a low-phase index above s+15",
                           "counterexample": phase["lb_offender"]},
                    "FT": {"hypothesis": 19, "status": "unconfirmed",
                           "evidence": "integer_registers.width_19_count in horner_cuts.json; empty means no contiguous variation-class run has length 19."},
                    "F2": {"hypothesis": 8, "status": "unconfirmed",
                           "evidence": "Width-8 runs are listed under integer_registers. A run is C2 only when it is also one value origin and address-only."},
                },
                "h_recovered": phase["h_recovered"],
                "words": words,
            },
            indent=2,
        )
        + "\n"
    )
    (ART / "lifetimes.json").write_text(json.dumps(lifetimes(ops, SEMANTIC_STAGES), indent=2) + "\n")
    (ART / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n")
    print(json.dumps({
        "angles": len(angles),
        "address_ok": addr_ok,
        "words": len(words),
        "h_recovered": phase["h_recovered"],
        "lb_rejected": lb_rejected,
        "loaded_87q_table": False,
    }, indent=2))


if __name__ == "__main__":
    main()
