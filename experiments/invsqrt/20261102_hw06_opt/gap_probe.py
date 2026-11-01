"""Track A 缺口探针（新基线）：coarse 控制字 / fine 残留位 / LUT_c 候选.

1. coarse/fine 控制字：41 条一般旋转都是无条件 Z_POW（条件栈为空已由
   stage_align.json 证实），控制信息在旋转目标线的计算基值里。逐条在旋转前做
   前缀快照，读目标线在 address/delta/s 三组样本上的值。
2. fine 残留位：新基线 [25679,25687) 与旧 [25622,25630) 文本一致，则
   dataflow62 的 local/prefix 结论（公式 value-id != 捕获 value-id，最低失败
   op 为 CCX）直接平移；检查旋转后 HMR 是否引入测量分支依赖。
3. LUT_c：报告 A 出口/B 入口/Lphase 入口的 address-only 线集作为系数表输出候选。
输出 JSON。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

import kickmix  # noqa: E402

NEW = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OUT = ROOT / "artifacts/20261102_hw06_opt/invsqrt/gap_probe.json"


def main() -> None:
    circuit = kickmix.Circuit.from_file(NEW)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [l for l in lines if l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    align = json.loads((ROOT / "artifacts/20261102_hw06_opt/invsqrt/stage_align.json").read_text())
    rots = align["rotation_map"]  # 41 条，old/new op 对照已证 equal
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    x_reg, _ = official.validate_registers(circuit, spec)

    addr_xs = [2**21 + (t << 14) for t in range(128)]
    delta_xs = [2**21 + d for d in ([0, 1] + [1 << b for b in range(14)] + [16383])]
    s_xs = [2 ** (21 - lz) for lz in range(22)]

    def snap(stop, xs, seed=101):
        stage = kickmix.Circuit.from_file(
            io.StringIO("\n".join(header + ops[:stop]) + "\n"), format="kmx")
        sim = kickmix.Simulator(batch_size=len(xs), seed=seed)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(np.array(xs, dtype=np.uint64), 22))
        sim.do(stage)
        return sim

    # 1. 逐旋转控制值。
    ctrl = []
    for row in rots:
        op = row["new_op"]
        q = int(row["wire"][1:])
        probe = kickmix.array([kickmix.q(q)])
        vals = {}
        for label, xs in (("addr", addr_xs), ("delta", delta_xs), ("s", s_xs)):
            sim = snap(op, xs)
            mat = np.asarray(sim.read_across_shots(probe)).reshape(-1)
            vals[label] = {"n": len(xs), "ones": int(mat.sum()),
                           "varies": bool(mat.var() > 0),
                           "pattern_hex": hex(int("".join(str(int(b)) for b in mat[::-1]), 2))[:66]}
        ctrl.append({"op": op, "wire": row["wire"], "samples": vals})
    n_vary_addr = sum(1 for c in ctrl if c["samples"]["addr"]["varies"])
    n_vary_delta = sum(1 for c in ctrl if c["samples"]["delta"]["varies"])
    n_vary_s = sum(1 for c in ctrl if c["samples"]["s"]["varies"])
    print("controls vary: addr", n_vary_addr, "delta", n_vary_delta, "s", n_vary_s)

    # 2. fine 残留位切片：文本一致 + 旋转后首条 HMR。
    old_slice = ["CX q14 q50", "CCX q21 q14 q50", "CX q23 q21", "CSWAP q27 q50 q2",
                 "CSWAP q18 q50 q0", "CX q27 q18", "CCX q54 q18 q50", "CX q27 q18"]
    new_slice = ops[25679:25687]
    assert new_slice == old_slice, new_slice
    post = ops[25687:25695]
    first_hmr = next((i for i, l in enumerate(ops[25687:], start=25687)
                      if l.startswith(("HMR", "R"))), None)
    residual = {
        "slice_text_equal_old": True,
        "dataflow_local_conclusion_carries": "local 128/128 一致；prefix 在旧索引 op25623(CCX) 处 "
            "公式 value-id != 捕获 value-id，本轮未重跑 prefix 证明，仅平移结论",
        "first_post_rotation_measure_op": first_hmr,
        "first_post_rotation_measure_line": ops[first_hmr] if first_hmr else None,
        "post_rotation_ops": post,
        "residual_depends_on_measurement_branch": "未判定Remainder: 旋转在 HMR 之前，"
            "计算基值与测量分支无关；但相位修正语义需 full-prefix value-id 重证",
    }

    # 3. LUT_c 候选（address-only 线集，来自 physaddr.json）。
    phys = json.loads((ROOT / "artifacts/20261102_hw06_opt/invsqrt/physaddr.json").read_text())
    lut = {cut: phys["cuts"][cut]["summary"].get("address-only", [])
           for cut in ("addr_probe_1200", "A_entry_16127", "B_entry_20738", "Lphase_entry_25687")}
    payload = {"control_words": ctrl,
               "control_vary_counts": {"addr": n_vary_addr, "delta": n_vary_delta, "s": n_vary_s},
               "fine_residual": residual,
               "lut_c_candidates": lut,
               "lut_c_status": "open: 仅有线集候选，无 256 项系数表值级解码（下一步）"}
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"vary": payload["control_vary_counts"],
                      "first_hmr": residual["first_post_rotation_measure_op"],
                      "lut": {k: len(v) for k, v in lut.items()}}, indent=2))


if __name__ == "__main__":
    main()
