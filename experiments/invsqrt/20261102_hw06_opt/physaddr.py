"""Track A 物理线路地址编码建模（新基线）：允许非连续寄存器，不假设连续 19 位 T.

坐标用 input_coords.py 的 shift-14 规范：lz / a(8bit, 含parity) / delta(14bit)。
三组 directed 样本每次只动一个坐标：
  address-only：lz=0、delta=0，a 低 7 位扫 t=0..127（x=2^21+(t<<14)）
  delta-only：lz=0、a=0，delta 扫 {0,1,单比特 b0..b13,16383}（x=2^21+delta）
  s-only：同一尾数 (a=0,delta=0)，lz 扫 0..21（x=2^(21-lz)，lz=21 即 x=1）
在若干切点做前缀快照，对 62 条物理线按变化类归类。输出 JSON。
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from input_coords import decompose  # noqa: E402

NEW = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OUT = ROOT / "artifacts/20261102_hw06_opt/invsqrt/physaddr.json"

CUTS = {
    "post_complement_23": 23,
    "addr_probe_1200": 1200,
    "A_entry_16127": 16127,
    "B_entry_20738": 20738,
    "Lphase_entry_25687": 25687,
}


def build_samples():
    addr_xs = [2**21 + (t << 14) for t in range(128)]
    delta_vals = [0, 1] + [1 << b for b in range(14)] + [16383]
    delta_xs = [2**21 + d for d in delta_vals]
    s_xs = [2 ** (21 - lz) for lz in range(22)]  # lz=0..21
    return addr_xs, delta_xs, s_xs


def snapshot(header, ops, x_reg, stop, xs, seed=101):
    stage = kickmix.Circuit.from_file(
        io.StringIO("\n".join(header + ops[:stop]) + "\n"), format="kmx")
    sim = kickmix.Simulator(batch_size=len(xs), seed=seed)
    arr = np.array(xs, dtype=np.uint64)
    sim.clear_for_shot()
    sim.write_across_shots(x_reg, official.to_bits(arr, 22))
    sim.do(stage)
    probes = kickmix.array([kickmix.q(i) for i in range(62)])
    mat = np.asarray(sim.read_across_shots(probes))
    if mat.shape[0] != 62:
        mat = mat.T
    return mat


def main() -> None:
    circuit = kickmix.Circuit.from_file(NEW)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [l for l in lines if l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    x_reg, _ = official.validate_registers(circuit, spec)

    addr_xs, delta_xs, s_xs = build_samples()
    # 样本坐标自检。
    assert {decompose(x)["lz"] for x in addr_xs} == {0}
    assert {decompose(x)["delta"] for x in addr_xs} == {0}
    assert len({decompose(x)["a"] for x in addr_xs}) == 128
    assert {decompose(x)["a"] for x in delta_xs} == {0}
    assert {decompose(x)["lz"] for x in delta_xs} == {0}
    # s-only 组共享尾数：(a&127)==0、delta==0；a 的 parity 位随 lz 奇偶翻转是预期的。
    assert all((decompose(x)["a"] & 127) == 0 and decompose(x)["delta"] == 0 for x in s_xs)
    assert len({decompose(x)["lz"] for x in s_xs}) == 22

    report = {"samples": {"n_addr": len(addr_xs), "n_delta": len(delta_xs), "n_s": len(s_xs)},
              "cuts": {}}
    for name, stop in CUTS.items():
        ma = snapshot(header, ops, x_reg, stop, addr_xs)
        md = snapshot(header, ops, x_reg, stop, delta_xs)
        ms = snapshot(header, ops, x_reg, stop, s_xs)
        var_a = ma.var(axis=1) > 0
        var_d = md.var(axis=1) > 0
        var_s = ms.var(axis=1) > 0
        classes = {}
        for q in range(62):
            a, d, s = bool(var_a[q]), bool(var_d[q]), bool(var_s[q])
            if not (a or d or s):
                cls = "const"
            elif a and not d and not s:
                cls = "address-only"
            elif d and not a and not s:
                cls = "delta-only"
            elif s and not a and not d:
                cls = "s-only"
            else:
                cls = f"mixed(a={int(a)},d={int(d)},s={int(s)})"
            classes[str(q)] = cls
        summary = {}
        for cls in set(classes.values()):
            summary[cls] = sorted(int(q) for q, c in classes.items() if c == cls)
        report["cuts"][name] = {"stop": stop, "classes": classes, "summary": summary}
        print(name, {k: (len(v), v[:12]) for k, v in summary.items()})
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
