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
    horner = horner_address_constants(header, ops)
    wide = [row for row in horner if len(row["address_constant_qubits"]) in (8, 19) or len(row["address_constant_qubits"]) >= 19]
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
            "note": "Horner prefix snapshots did not show an address-constant register whose width is 8 or 19.",
            "horner_cuts": horner,
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
                           "evidence": "no Horner cut had 19 address-constant qubits",
                           "cuts": horner},
                    "F2": {"hypothesis": 8, "status": "unconfirmed",
                           "evidence": "no Horner cut had 8 address-constant qubits",
                           "wide_cuts": wide},
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
