"""Manual Syed V9 cost/geometry census; no candidate or official validation."""
from __future__ import annotations

import bisect
import collections
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import random
import sys

import kickmix as km
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_direction_research/cost"
PAID = {"CCX", "CCZ", "CSWAP"}
MAXX = 3133452
N = 16384


def trace(gates, xs, seed, *, initial=None, n=None, fixed_zero=False, stop_after=None, return_state=False):
    """Sample classical trajectories and execution guards, never phase correctness."""
    n = len(xs) if n is None else n
    mask = (1 << n) - 1
    rng = random.Random(seed)
    initial = [sum(((x >> j) & 1) << i for i, x in enumerate(xs)) for j in range(22)] if initial is None else initial
    q, bits, stack = initial + [0] * 40, {}, []
    counts = [0] * len(gates)
    for i, (k, qs, p) in enumerate(gates[:stop_after]):
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k in PAID or k == "Z_POW":
            counts[i] = active.bit_count()
        if k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif k in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & active
            if k == "CSWAP":
                d &= q[qs[0]]
            q[a] ^= d
            q[b] ^= d
        elif k in {"HMR", "R"}:
            if k == "HMR":
                b = int(p[2][1:])
                bits[b] = (bits.get(b, 0) & ~active) | ((0 if fixed_zero else rng.getrandbits(n)) & active)
            q[qs[0]] &= ~active
        elif k not in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            raise ValueError((i, p))
    if return_state:
        return q, bits, stack
    assert not stack
    return counts, {"input_restore_failures": sum((q[j] ^ initial[j]).bit_count() for j in range(22)),
                    "dirty_scratch_bits": sum(v.bit_count() for v in q[22:])}


def native_sample(circuit, xs, seed):
    sim = km.Simulator(batch_size=256, seed=seed, counting_operations=True)
    xreg = circuit.register_data["x"]
    bad = 0
    for lo in range(0, len(xs), 256):
        arr = np.asarray(xs[lo:lo + 256], dtype=np.uint64)
        raw = ((arr[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1).astype(np.bool_)
        sim.clear_for_shot()
        sim.write_across_shots(xreg, raw)
        sim.do(circuit)
        bad += int(np.count_nonzero(np.asarray(sim.read_across_shots(xreg)) != raw))
    s = sim.operation_statistics()
    return {"native_mean_paid": int(s.num_toffoli_like) / len(xs),
            "native_mean_T": int(s.num_t_like) / len(xs),
            "native_mean_rotations": int(s.num_z_pow(min_clifford_hierarchy_level=4)) / len(xs),
            "native_input_restore_bit_failures": bad,
            "note": "Native and Python coins are independent; total means are a consistency check, not paired equivalence."}


def writes(k, qs):
    if k in {"X", "R", "HMR"}:
        return qs[:1]
    if k in {"CX", "CCX"}:
        return qs[-1:]
    if k in {"SWAP", "CSWAP"}:
        return qs[-2:]
    return []


def q23_collision(gates, circuit_sha):
    """Exhaustive legal-x basis-state collision on one reachable coin branch."""
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    initial = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)]
    q, bits, stack = trace(gates, None, 0, initial=initial, n=MAXX,
                           fixed_zero=True, stop_after=3468, return_state=True)
    mask = (1 << MAXX) - 1
    states = np.zeros(MAXX, dtype=np.uint64)
    def unpack(v):
        return np.unpackbits(np.frombuffer(v.to_bytes((MAXX + 7) // 8, "little"), dtype=np.uint8), bitorder="little")[:MAXX]
    dropped = unpack(q[23])
    for j, v in enumerate(q):
        if j != 23:
            states |= unpack(v).astype(np.uint64) << j
    order = np.argsort(states)
    sorted_states = states[order]
    candidates = np.flatnonzero((sorted_states[:-1] == sorted_states[1:]) & (dropped[order[:-1]] != dropped[order[1:]]))
    pairs = []
    for idx in candidates[:10000]:
        a, b = int(order[idx]), int(order[idx + 1])
        if any(((v >> a) & 1) != ((v >> b) & 1) for v in bits.values()):
            continue
        pairs.append({"x_a": a + 1, "x_b": b + 1, "remaining_61_bits_integer": int(states[a]),
                      "q23_a": int(dropped[a]), "q23_b": int(dropped[b]), "all_classical_bits_equal": True})
        if len(pairs) == 10:
            break
    out = {"scope": "Exhaustive legal-input local basis-state collision search on fixed all-zero HMR branch; not official validation and not a global space lower bound",
           "baseline_sha256": circuit_sha, "checkpoint": "after zero-based operation 3467 (prefix [0,3468))",
           "inputs": MAXX, "dropped_q": 23, "all_HMR_results": 0,
           "classical_bit_count": len(bits), "nonconstant_classical_bits": [b for b, v in bits.items() if v not in (0, mask)],
           "constant_one_classical_bits": [b for b, v in bits.items() if v == mask],
           "active_condition_stack_size": len(stack),
           "quantum_collision_adjacencies": len(candidates), "example_pairs": pairs,
           "conclusion": "q23 is not a deterministic function of the remaining 61 current quantum bits plus current classical bits at this checkpoint" if pairs else "No qualifying pair found; no lower-bound conclusion"}
    (OUT / "q23_collision.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    circuit = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    official = json.loads((BASE.parent / "official_run.json").read_text())["official_result"]
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == official["circuit_sha256"]
    if "--q23-collision" in sys.argv:
        q23_collision(gates, official["circuit_sha256"])
        return
    stack, stacks = [], []
    for k, qs, p in gates:
        stacks.append(tuple(stack))
        if k == "PUSH_CONDITION":
            stack.append(p[-1])
        elif k == "POP_CONDITION":
            stack.pop()
    assert not stack
    batches, totals = [], [0] * len(ops)
    for seed in (101, 202, 303):
        rng = random.Random(20261106 + seed)
        xs = [rng.randint(1, MAXX) for _ in range(N)]
        counts, restoration = trace(gates, xs, seed)
        totals = [a + b for a, b in zip(totals, counts)]
        row = {"seed": seed, "input_seed": 20261106 + seed, "shots": N,
               "python_mean_paid": sum(counts[i] for i, (k, _, _) in enumerate(gates) if k in PAID) / N,
               **restoration, **native_sample(circuit, xs, seed)}
        batches.append(row)
        print(json.dumps(row), flush=True)
    means = [n / (N * len(batches)) for n in totals]
    paid = [i for i, (k, _, _) in enumerate(gates) if k in PAID]

    def row(lo, hi):
        inds = [j for j in paid if lo <= j < hi]
        return {"window": [lo, hi], "static_paid": len(inds),
                "paid_types": dict(collections.Counter(gates[j][0] for j in inds)),
                "sample_mean_paid": sum(means[j] for j in inds),
                "static_unconditional_paid": sum(not stacks[j] and "if" not in gates[j][2] for j in inds),
                "HMR": sum(gates[j][0] == "HMR" for j in range(lo, hi)),
                "rotations": sum(gates[j][0] == "Z_POW" and Fraction(gates[j][2][2]) % Fraction(1, 4) != 0 for j in range(lo, hi))}

    stages = [row(lo, hi) for lo, hi in zip([0, 15278, 15617, 25408, 25649], [15278, 15617, 25408, 25649, len(ops)])]
    bins = [row(lo, min(lo + 2000, len(ops))) for lo in range(0, len(ops), 2000)]
    quadratic = []
    lo = 0
    for i in range(len(ops) + 1):
        if i < len(ops) and gates[i][0] in {"X", "CX", "CCX"} and "if" not in gates[i][2]:
            continue
        ccx = [j for j in range(lo, i) if gates[j][0] == "CCX"]
        if len(ccx) >= 2:
            targets = collections.Counter(gates[j][1][-1] for j in ccx)
            r = row(lo, i)
            r.update(target_histogram=dict(targets), max_same_target=max(targets.values()),
                     wire_count=len({q for j in range(lo, i) for q in gates[j][1]}),
                     ccx_instructions=[[j, ops[j]] for j in ccx], condition_stack=list(stacks[lo]),
                     warning="X/CX/CCX run; repeated target is only geometry. Quadratic degree/reachable-domain redundancy not proved.")
            quadratic.append(r)
        lo = i + 1
    quadratic.sort(key=lambda r: (r["max_same_target"], r["static_paid"]), reverse=True)

    windows = []
    for a, b, d in zip(paid, paid[1:], paid[2:]):
        if d - a > 600:
            continue
        ks = [gates[j][0] for j in range(a, d + 1)]
        if ks.count("HMR") != 1 or any(k in {"Z_POW", "R", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "PUSH_CONDITION", "POP_CONDITION"} for k in ks):
            continue
        wires = sorted({q for j in range(a, d + 1) for q in gates[j][1]})
        if len(wires) > 32 or any(s != stacks[a] for s in stacks[a:d + 1]):
            continue
        r = row(a, d + 1)
        r.update(paid_indices=[a, b, d], wire_count=len(wires), wires=wires,
                 condition_stack=list(stacks[a]), hmr_index=a + ks.index("HMR"),
                 hypothetical_one_paid_reduction_C=means[a],
                 instructions=ops[a:d + 1])
        windows.append(r)
    windows.sort(key=lambda r: (r["window"][1], r["window"][0]))
    ends = [r["window"][1] for r in windows]
    dp = [(0, [])]
    for i, r in enumerate(windows):
        prev = bisect.bisect_right(ends, r["window"][0], 0, i)
        take = (dp[prev][0] + r["hypothetical_one_paid_reduction_C"], dp[prev][1] + [i])
        dp.append(take if take[0] > dp[-1][0] else dp[-1])
    selected = [windows[i] for i in dp[-1][1]]

    segments = []
    touches_by_q = [[i for i, (_, qs, _) in enumerate(gates) if q in qs] for q in range(62)]
    for q, touches in enumerate(touches_by_q):
        current = []
        first = True
        for i in touches + [len(ops)]:
            reset = i < len(ops) and gates[i][0] in {"HMR", "R"} and not stacks[i] and "if" not in gates[i][2]
            if reset or i == len(ops):
                if current or (q < 22 and first):
                    a = 0 if q < 22 and first else current[0]
                    b = len(ops) if q < 22 and i == len(ops) else i + 1 if reset else current[-1] + 1
                    segments.append({"q": q, "window": [a, b], "touches": current + ([i] if reset else [])})
                current = []
                first = False
            else:
                current.append(i)
    events = collections.Counter()
    for s in segments:
        events[s["window"][0]] += 1
        events[s["window"][1]] -= 1
    live, peak, at = 0, 0, 0
    for i, delta in sorted(events.items()):
        live += delta
        if live > peak:
            peak, at = live, i
    live = 0
    peak_intervals = []
    points = sorted(events)
    for i, j in zip(points, points[1:]):
        live += events[i]
        if live == peak:
            if peak_intervals and peak_intervals[-1][1] == i:
                peak_intervals[-1][1] = j
            else:
                peak_intervals.append([i, j])
    active = []
    for s in segments:
        a, b = s["window"]
        if not a <= at < b:
            continue
        ts = s["touches"]
        ws = [j for j in ts if s["q"] in writes(gates[j][0], gates[j][1]) and gates[j][0] not in {"R", "HMR"}]
        prev = [j for j in ts if j <= at]
        nxt = [j for j in ts if j > at]
        birth_controls = gates[ws[0]][1][:2] if ws and gates[ws[0]][0] == "CCX" else []
        control_modifications = [j for j in range(ws[0] + 1, b) if any(q in writes(gates[j][0], gates[j][1]) for q in birth_controls)] if birth_controls else []
        active.append({"q": s["q"], "window": [a, b], "touch_count": len(ts),
                       "previous_use": prev[-1] if prev else None, "next_use": nxt[0] if nxt else None,
                       "next_use_distance": nxt[0] - at if nxt else None,
                       "write_count": len(ws), "paid_write_count": sum(gates[j][0] in PAID for j in ws),
                       "first_write": [ws[0], ops[ws[0]]] if ws else None,
                       "birth_CCX_controls": birth_controls,
                       "birth_control_modification_count": len(control_modifications),
                       "first_birth_control_modification": [control_modifications[0], ops[control_modifications[0]]] if control_modifications else None,
                       "last_use": [ts[-1], ops[ts[-1]]] if ts else None,
                       "all_writes": [[j, ops[j]] for j in ws]})
    rotation_cost = official["rotation_count"] * (0.56 * math.log2(1 / official["rotation_eps"]) + 5.3) / 4
    result = {"scope": "Current KMB static geometry + 3x16384 uniform-input random-coin cost samples; no candidate and no new official validation",
              "baseline_sha256": official["circuit_sha256"], "coordinate_convention": "zero-based KMX operations excluding register declarations; half-open intervals",
              "official_existing": official, "cost_components_C": {"paid": official["toffoli_count"], "T": official["t_count"] / 4, "rotation": rotation_cost},
              "budget": {"one_percent_C": official["toffoli_equivalent"] * .01, "five_percent_C": official["toffoli_equivalent"] * .05,
                         "one_qubit_reduction_break_even_extra_C": official["toffoli_equivalent"] / 61,
                         "two_qubit_reduction_break_even_extra_C": 2 * official["toffoli_equivalent"] / 60},
              "batches": batches, "stages": stages, "bins_2000": bins,
              "quadratic_candidate_runs": quadratic,
              "cross_HMR": {"qualified": len(windows), "selected_nonoverlapping": len(selected),
                            "static_bound_if_at_most_one_paid_saved_per_selected_window_C": len(selected),
                            "selected_hypothetical_one_paid_reduction_C": dp[-1][0], "windows": selected,
                            "note": "No equivalence/synthesis; no exclusion based on historical coordinates. Hypothetical budget assumes exactly one paid gate per active branch saved in every selected window."},
              "liveness": {"model": "Conservative touch-to-unconditional-reset segments, input/output registers pinned at circuit ends. Conditional resets do NOT split lifetimes. Not a qubit lower bound or allocation proof.",
                           "segment_count": len(segments), "peak": peak, "first_peak_op": at,
                           "peak_intervals": peak_intervals, "active_segments": active},
              "demonstrated_new_gain_C": 0}
    (OUT / "census.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / "paid_gate_samples.json").write_text(json.dumps([{ "op": i, "instruction": ops[i], "mean_execution_probability": means[i], "condition_stack": list(stacks[i])} for i in paid], indent=2) + "\n")
    print(json.dumps({"stages": stages, "peak": peak, "peak_op": at, "cross_hmr_selected": len(selected), "hypothetical_C": dp[-1][0], "cost_components_C": result["cost_components_C"], "budget": result["budget"]}, indent=2))


if __name__ == "__main__":
    main()
