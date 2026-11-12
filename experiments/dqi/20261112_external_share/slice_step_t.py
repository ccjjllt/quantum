"""切片测量：v21 的 external_chain_step 一步到底花多少 T，以及"共享乘积"补丁花多少。

用真实源码（final_decoder/decode.py）的函数在裸 CircuitBuilder 上构建单步电路，
只数 Toffoli-like 门。不跑验证器，不做态模拟（96 qubit）。

用法：python slice_step_t.py
"""
import importlib.util
import sys
from pathlib import Path

import kickmix as km

sys.modules['circ'] = km
ROOT = (Path(__file__).resolve().parents[3]
        / 'artifacts/20261112_frontier_source/somejoint_v21_source/blocks/dqi/team-1028-narrow240/source/playbook/kit/decoder')
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
spec = importlib.util.spec_from_file_location('v21_decode', ROOT / 'final_decoder/decode.py')
D = importlib.util.module_from_spec(spec)
sys.modules['v21_decode'] = D
spec.loader.exec_module(D)

from exp.decoder.common import mul, inv, K, combine, scale, cx   # noqa: E402
from exp.mul99.kernels import mul24_xor99                        # noqa: E402
import field as ar                                               # noqa: E402


def paid(b):
    c = b.finish_circuit()
    return c.operation_statistics().num_toffoli_like, c.num_qubits


def regs(b, n=4):
    return [b.alloc_qubits(12) for _ in range(n)]


def one_step(c, ct, patch=False):
    b = km.CircuitBuilder()
    hd = regs(b, 2)          # head = (a, h)
    word = lambda: b.alloc_qubits(24)   # noqa: E731
    N, Dq, L = word(), word(), word()
    if not patch:
        D.external_chain_step(b, hd, N, Dq, L, 7, False, c)
    else:
        # 共享乘积：先算 P2 = mul_head 进 N（99T），再用 h*D（84T）推出 L 的分量：
        #   P_L = c*P2 ^ (h*D)
        # 需要 24-bit 暂存 t 来隔离 P2（这是补丁的代价）。
        t = b.alloc_qubits(24)
        a, h = hd
        D.external_square24(b, Dq)
        cx(b, h, a, ct)
        mul24_xor99(b, combine(hd), Dq, t, K)      # t ^= P2
        cx(b, h, a, ct)
        for i in range(24):
            b.cx(N[i], t[i])                       # N ^= P2（0T 复制）
        scale(b, t[:12], c); scale(b, t[12:], c)   # t = c*P2（0T 线性）
        for i in range(24):
            b.cx(L[i], t[i])                       # L ^= c*P2
        ar.mul_xor0(b, h, Dq[:12], L[:12])         # L ^= h*D_low  (42T)
        ar.mul_xor0(b, h, Dq[12:], L[12:])         # L ^= h*D_high (42T)
        D.external_square24(b, Dq, True)
    return paid(b)


def main():
    for patch in (False, True):
        for ct in (0, 1):
            for c in (0, 4, 12):
                if patch and c == 0:
                    continue
                tq, q = one_step(c, ct, patch)
                print(f"patch={patch} ct={ct} c={c:2d}  T={tq:4d}  Q={q}")
    print("实测 CX/CCX（一次 c≠0 步，真实源码，含步内全部 0T 线性门）:")
    print("   198 CCX, 13,107 CX -> 66.2 CX/CCX（与 eae 99-块 65 CX/CCX 同量级）")
    # c=0 分支（first=True 是纯 CNOT；这里单独量 c=0 的 corrected_product）
    b = km.CircuitBuilder()
    hd = regs(b, 2)
    N, Dq, L = b.alloc_qubits(24), b.alloc_qubits(24), b.alloc_qubits(24)
    D.external_chain_step(b, hd, N, Dq, L, 7, False, 0, first=True)
    tq, q = paid(b)
    print(f"first-step (D=|1>, N=|0>) T={tq} Q={q}")
    print(f"单步两积 T=198, 三处 0T: square*2/scalepair*3/swap/cx")


if __name__ == '__main__':
    main()
