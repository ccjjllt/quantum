"""generator62_v2.py 骨架：独立整数生成器调度（§6，未填实现）.

只定函数签名、调度顺序与断言点；函数体一律 NotImplementedError。
最终入口只接受调用方传入的系数表（list[int]，来自主线程已验证的合同；
规范序列化格式见本目录 README：256×u64-B LE + 256×u32-A LE + 256×u16-R LE），
不得读旧 KMB/tray/嵌入指令串，不得做数值拟合。

手动 double-build 机制见 main()：同参数构建两次，逐指令比对 + SHA-256。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# 固定参数（合同位宽，待主线程验证；此处只作形状约束）
W_X = 22
W_LZ = 5
W_ADDR = 8
N_ADDR = 256
W_B, W_A, W_R = 33, 22, 12
W_DELTA, W_D, W_U, W_S = 14, 14, 9, 17
W_V = 55
W_P = 36
Q_CAP = 160  # 宽度上限断言（估计峰值 ~125，见 qrom.md §4；以生成电路为准）


@dataclass(frozen=True)
class CoefTables:
    """调用方提供的系数表（verified 合同的整数形态， Pac lists, LSB-first ints）."""

    B: tuple[int, ...]  # 256 项，各 < 2**33
    A: tuple[int, ...]  # 256 项，各 < 2**22
    R: tuple[int, ...]  # 256 项，各 < 2**12


def assert_tables(tables: CoefTables) -> None:
    """S0：供表形状与安全断言（V 非负下界等，阈值待合同验证后收紧）."""
    assert len(tables.B) == len(tables.A) == len(tables.R) == N_ADDR
    assert all(0 <= v < 2**W_B for v in tables.B)
    assert all(0 <= v < 2**W_A for v in tables.A)
    assert all(0 <= v < 2**W_R for v in tables.R)
    # V 非负安全边际：min(B<<12) 须覆盖 |2AD|+|RS| 上界（2**37 + 2**29）
    assert min(tables.B) > (2**37 + 2**29) >> 12, "B 下界不足以保证 V 非负"
    raise NotImplementedError


def build_lz_norm(b, x, lz) -> None:
    """S1：二分比较器求 lz（5 级，btol=inf 精确），见 lz_norm.md §1."""
    raise NotImplementedError


def build_normalize(b, x, lz) -> None:
    """S2：原地 left_rotate(x, lz)，rotl==逻辑左移（顶零保证），见 §2."""
    raise NotImplementedError


def build_square(b, d_view, coef, s_view) -> None:
    """S3：U=(delta>>5)-256 进 coef，学校式 9 行进 S（MSB 行变减），见 arith.md §2."""
    raise NotImplementedError


def qrom_sweep(b, cursor, table: tuple[int, ...], width: int, target) -> None:
    """S4：单扫：顺序 range(256)，每值按表 bit 做条件 CX（LSB-first 固定序）."""
    raise NotImplementedError


def build_v_asm(b, coef, d_view, s_view, v) -> None:
    """S5：B1 非受控加（V[12..45)）+ A1 14 行减 + R1 12 行加；行宽断言 ≥ 窗口."""
    raise NotImplementedError


def build_shift_round_phase(b, lz, v) -> None:
    """S6：t8=11-s-p → 索引重标 8 → barrel → V[t-1] 受控加一 → 36×z_pow.

    FILL-IN：z_pow 半-turn/turn 口径以 kickmix 语义复核；
    先行检查可用 km.Simulator 在 2–3 线小 gadget 上对 numpy 态矢量相位
    （非官方验证，仅语义自检），通过后再填入。
    """
    raise NotImplementedError


def build_forward(b, tables: CoefTables, regs: dict) -> None:
    """S7 正向调度：S0→S1→S2→S3→[QROM 单 pass 六扫+S5 穿插]→S6."""
    raise NotImplementedError


def build_reverse(b, tables: CoefTables, regs: dict) -> None:
    """S8 逆向调度：S6 逆→S5 镜像（QROM pass 重开逆序）→S3 逆→S2 逆→S1 逆."""
    raise NotImplementedError


def build_circuit(tables: CoefTables):
    """S9：按固定顺序建寄存器（x, lz, coef, V；具名、固定长），正→逆组装；
    终断言：除 x 外全归零；num_qubits ≤ Q_CAP."""
    raise NotImplementedError


def circuit_sha(circuit) -> str:
    return hashlib.sha256(str(circuit).encode()).hexdigest()


def main() -> None:
    """S10：确定性机制——同表构建两次，逐指令相等 + SHA 一致，否则失败.

    确定性来源：迭代一律 range(256)/enumerate LSB-first；表为 list 顺序；
    指数用 Fraction；无随机、无时间、无 dict/set 迭代。
    系数表此处用形状合法的占位确定性序列（非拟合结果）；
    真实系数待主线程验证后由调用方注入。
    """
    tables = CoefTables(
        B=tuple(((k * 0x9E3779B1) & (2**W_B - 1)) | (2**38) for k in range(256)),
        A=tuple((k * 0x85EBCA6B) & (2**W_A - 1) for k in range(256)),
        R=tuple((k * 0xC2B2AE35) & (2**W_R - 1) for k in range(256)),
    )
    c1 = build_circuit(tables)
    c2 = build_circuit(tables)
    assert str(c1) == str(c2), "两次构建逐指令不一致"
    print("sha256:", circuit_sha(c1), "qubits:", c1.num_qubits)


if __name__ == "__main__":
    main()
