"""Track A 新基线分阶段对齐：ahmed(旧) -> baseline_hw06(新) 的边界映射与逐段对照.

只做静态文本比对 + kickmix 前缀快照的 directed-sample 功能等价检查。
tray/KMB 只做对照输入，不进入最终生成器（本轮仍是 replay 对照）。
输出 JSON 到 artifacts/20261102_hw06_opt/invsqrt/stage_align.json。
"""
from __future__ import annotations

import difflib
import io
import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

import kickmix  # noqa: E402

OLD = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt/ahmed.kmb"
NEW = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OUT = ROOT / "artifacts/20261102_hw06_opt/invsqrt/stage_align.json"

# 旧 REPORT 的宏观语义边界（含测量条件修正）。
OLD_BOUNDS = {
    "Hphase": (15244, 16127),
    "A": (16127, 20738),
    "B": (20738, 25630),
    "Lphase": (25630, 28726),
    "inverse_B": (28726, 32226),
    "inverse_A": (32226, 43870),
    "unlookup": (43870, 46706),
    "tail": (46706, 47201),
}


def load_ops(path: Path):
    circuit = kickmix.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [l for l in lines if l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    return circuit, header, ops


def general_rotations(ops):
    """41 条一般旋转：沿用 extract62 的过滤（半圈非 1/2、1/4 倍数），附条件栈。"""
    stack, rows = [], []
    for i, line in enumerate(ops):
        if line.startswith("PUSH_CONDITION"):
            stack.append(line.split()[-1])
        elif line.startswith("POP_CONDITION"):
            if stack:
                stack.pop()
        elif line.startswith("Z_POW"):
            half = Fraction(line.split()[2])
            if half % Fraction(1, 2) == 0 or half % Fraction(1, 4) == 0:
                continue
            rows.append({"op": i, "wire": line.split()[1],
                         "half_turns": [half.numerator, half.denominator],
                         "condition_stack": list(stack), "kmx": line})
    return rows


def main() -> None:
    new_circuit, new_header, new_ops = load_ops(NEW)
    _, old_header, old_ops = load_ops(OLD)
    assert new_header == old_header

    sm = difflib.SequenceMatcher(a=old_ops, b=new_ops, autojunk=False)
    hunks = [(t, i1, i2, j1, j2) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
    # 由 diff 反推分段偏移：B 区内两处改写，总 +57；其后边界整体 +57。
    hunks_old_span = [(i1, i2) for _, i1, i2, _, _ in hunks]
    assert all(i2 <= 25477 for i1, i2 in hunks_old_span), hunks_old_span
    assert all(i1 >= 21333 for i1, i2 in hunks_old_span), hunks_old_span
    net = len(new_ops) - len(old_ops)
    assert net == 57, net

    new_bounds, shift = {}, 0
    # 第一改写组旧 [21333,21588) -> 新 [21333,21641)：+53；第二组旧 [25458,25477) 再 +4。
    for name, (s, e) in OLD_BOUNDS.items():
        ds = 0 if s < 21333 else (53 if s < 25458 else 57)
        de = 0 if e <= 21333 else (53 if e <= 25458 else 57)
        new_bounds[name] = (s + ds, e + de)
    assert new_bounds["B"] == (20738, 25687), new_bounds["B"]
    assert new_bounds["tail"] == (46763, 47258), new_bounds["tail"]

    # 映射边界处 opcode 文本必须一致。
    boundary_check = {}
    for name, (s, e) in OLD_BOUNDS.items():
        ns, ne = new_bounds[name]
        boundary_check[name] = {
            "old_start": old_ops[s], "new_start": new_ops[ns],
            "start_equal": old_ops[s] == new_ops[ns],
            "old_end_prev": old_ops[e - 1], "new_end_prev": new_ops[ne - 1],
            "end_equal": old_ops[e - 1] == new_ops[ne - 1],
        }

    # Z_POW 多重集一致；41 条一般旋转按序比对（含条件栈）。
    assert sum(l.startswith("Z_POW") for l in new_ops) == \
        sum(l.startswith("Z_POW") for l in old_ops) == 68
    rn, ro = general_rotations(new_ops), general_rotations(old_ops)
    assert len(rn) == len(ro) == 41, (len(rn), len(ro))
    rot_rows = []
    for a, b in zip(rn, ro):
        same = (a["wire"] == b["wire"] and a["half_turns"] == b["half_turns"]
                and a["condition_stack"] == b["condition_stack"])
        rot_rows.append({"old_op": b["op"], "new_op": a["op"], "wire": a["wire"],
                         "equal": same})
    assert all(r["equal"] for r in rot_rows)

    # 每段门类直方图（新基线）。
    hist = {}
    for name, (s, e) in new_bounds.items():
        hist[name] = dict(Counter(l.split()[0] for l in new_ops[s:e]))

    # Directed-sample 功能等价：B 区改写前后，Lphase 入口及下游边界快照旧/新一致。
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    x_reg, _ = official.validate_registers(new_circuit, spec)
    xs = [1, 2, 3, 8, 128, 161, 888, 3133452]
    arr = np.array(xs, dtype=np.uint64)
    probes = kickmix.array([kickmix.q(i) for i in range(62)])

    def snapshot(header, ops, stop, seed):
        stage = kickmix.Circuit.from_file(
            io.StringIO("\n".join(header + ops[:stop]) + "\n"), format="kmx")
        sim = kickmix.Simulator(batch_size=len(xs), seed=seed)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(arr, 22))
        sim.do(stage)
        mat = np.asarray(sim.read_across_shots(probes))
        if mat.shape[0] != 62:
            mat = mat.T
        return mat

    equiv = {}
    for name in ("Lphase", "inverse_B", "inverse_A", "unlookup", "tail"):
        os_, oe = OLD_BOUNDS[name][0], OLD_BOUNDS[name][1]
        ns, ne = new_bounds[name]
        for label, o_stop, n_stop in (("entry", os_, ns), ("exit", oe, ne)):
            mo = snapshot(old_header, old_ops, o_stop, seed=101)
            mn = snapshot(new_header, new_ops, n_stop, seed=101)
            equiv[f"{name}.{label}"] = {
                "old_op": o_stop, "new_op": n_stop,
                "state_equal": bool(np.array_equal(mo, mn)),
                "live_qubits_old": int((mo.any(axis=1)).sum()),
                "live_qubits_new": int((mn.any(axis=1)).sum()),
            }
    assert all(v["state_equal"] for v in equiv.values()), equiv

    payload = {
        "old_ops": len(old_ops), "new_ops": len(new_ops), "net_delta": net,
        "diff_hunks": [{"tag": t, "old": [i1, i2], "new": [j1, j2]}
                       for t, i1, i2, j1, j2 in hunks],
        "rewrite_region": "全部改写落在旧 B 区 [21333,25477) 内；Hphase/A/Lphase 下游只发生整体 +57 平移",
        "old_bounds": {k: list(v) for k, v in OLD_BOUNDS.items()},
        "new_bounds": {k: list(v) for k, v in new_bounds.items()},
        "boundary_check": boundary_check,
        "rotations_41_equal": True,
        "rotation_map": rot_rows,
        "stage_histograms_new": hist,
        "directed_snapshot_equivalence": equiv,
        "directed_xs": xs,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"net": net, "new_bounds": payload["new_bounds"],
                      "equiv_ok": all(v["state_equal"] for v in equiv.values())}, indent=2))


if __name__ == "__main__":
    main()
