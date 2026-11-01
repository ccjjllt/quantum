"""Track A 输入坐标全域验证：m=x<<lz, a=(parity<<7)|((m>>14)&127), delta=m&16383.

只用纯 Python，不读 KMB/tray。输出 JSON 到 artifacts/20261102_hw06_opt/invsqrt/。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261102_hw06_opt/invsqrt/input_coords.json"
MAX_X = 3_133_452


def decompose(x: int) -> dict:
    bl = int(x).bit_length()
    lz = 22 - bl
    m = int(x) << lz
    parity = lz & 1
    s = lz >> 1
    a = (parity << 7) | ((m >> 14) & 127)
    delta = m & 16383
    return {"lz": lz, "m": m, "parity": parity, "s": s, "a": a, "delta": delta}


def rebuild(lz: int, a: int, delta: int) -> tuple[int, int]:
    # bit21 是归一化隐含前导 1；a 覆盖 m 的 bit14..bit20（含 bit20）；delta 覆盖 bit0..bit13。
    m = (1 << 21) | ((a & 127) << 14) | (delta & 16383)
    return m, m >> lz


def main() -> None:
    bad = 0
    first_bad = None
    addr_only_keys = set()
    full_keys = set()
    for x in range(1, MAX_X + 1):
        d = decompose(x)
        m2, x2 = rebuild(d["lz"], d["a"], d["delta"])
        if m2 != d["m"] or x2 != x:
            bad += 1
            if first_bad is None:
                first_bad = {"x": x, "dec": d, "m2": m2, "x2": x2}
        full_keys.add((d["lz"], d["a"], d["delta"]))
        addr_only_keys.add((d["a"], d["delta"]))
    # 碰撞反例：(a,delta) 相同但 x 不同（跨尺度共享尾数，lz 不同是预期的）。
    demo = {x: decompose(x) for x in (1, 2, 3, 4, 8, 12, 16, 32, 128, 161, 888, MAX_X)}
    collisions = {
        "(a,delta)=(0,0)": [x for x in (2, 8, 32) ],
        "(a,delta)=(64,0)": [x for x in (3, 12)],
        "(a,delta)=(128,0)": [x for x in (1, 4, 16)],
    }
    for label, xs in collisions.items():
        keys = {(decompose(x)["a"], decompose(x)["delta"]) for x in xs}
        assert len(keys) == 1, (label, keys)
        lzs = {decompose(x)["lz"] for x in xs}
        assert len(lzs) == len(xs), (label, "lz 应区分这些 x")
    # x=2/3 不是碰撞：a 不同。
    assert (decompose(2)["a"], decompose(2)["delta"]) != (decompose(3)["a"], decompose(3)["delta"])
    payload = {
        "spec": "m=x<<lz, lz=22-bitlen(x); a=(parity<<7)|((m>>14)&127); delta=m&16383; "
                "bit21 为隐含前导1; bit20 落在 a 的 bit6",
        "domain": [1, MAX_X],
        "roundtrip_failures": bad,
        "first_failure": first_bad,
        "distinct_full_keys_lz_a_delta": len(full_keys),
        "distinct_addr_only_keys_a_delta": len(addr_only_keys),
        "addr_only_collisions_expected": MAX_X - len(addr_only_keys),
        "collision_demo": demo,
        "x2_x3_is_collision": False,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: v for k, v in payload.items() if k != "collision_demo"}, indent=2))
    print("demo x=2:", demo[2])
    print("demo x=8:", demo[8])
    print("demo x=3:", demo[3])
    assert bad == 0 and len(full_keys) == MAX_X


if __name__ == "__main__":
    main()
