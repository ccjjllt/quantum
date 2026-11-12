"""external chain 乘积共享：值级证明/证伪（只读，不建电路）。

对象：somejoint_v21 源码
  .../team-1028-narrow240/source/playbook/kit/decoder/final_decoder/decode.py
  external_corrected_product  L306
  external_mul_head           L300
  external_chain_step         L316

方法：把这两段电路逐门翻译成"值级"操作。所有用到的门类在源码里的语义：

  scale(b,x,c)            ar.linear_inplace(x, constcols(c))  ->  x := c*x          (Clifford, 0 T)
  cx(b,x,z,c)  c 常数      ar.linear_xor(z, x, constcols(c))   ->  z := z ^ c*x      (Clifford, 0 T)
  ar.mul_xor0(b,x,y,z)                                        ->  z := z ^ x*y      (42 T)
  mul24_xor99(b,x,y,z,K)                                      ->  z := z ^ emul(x,y) (99 T)

  * constcols(c) = (mul(c,1<<i) for i in 12)，所以 scale/cx 就是 GF(2^12) 里"乘常数 c"
    （cx 是把这个线性映射的像 XOR 进 z）。见 exp/decoder/common.py L50-L58。
  * mul24_xor99 的 y 基与 emul 一致：mul99/kernels.py `tensor99_extension(K)` 用
    `extension_columns(K)` 做基变换；exp/arithmetic/field.py L337 明确写
    "Map base12 pair a+b*y to standard GF24 polynomial basis ... y^2+y=K"。
    `combine(head) = a | h<<12` 正好是 a+b*y 的 24 bit 串。
  * 平方 external_square24 用 emul(.,.) 的列，0 T。

因此下面用 mul/inv/K/emul（源码自己的域原语）做的检查，与电路门级行为是同一件事。
"""
import sys
from pathlib import Path

import kickmix as km

sys.modules['circ'] = km      # build.py 的做法：kit 内 `import circ as km`
SRC = Path(__file__).resolve().parents[3] / 'artifacts/20261112_frontier_source/somejoint_v21_source/blocks/dqi/team-1028-narrow240/source/playbook/kit/decoder'
sys.path.insert(0, str(SRC))
from exp.decoder.common import mul, inv, K, emul, gf   # noqa: E402

M = 0xfff


def lo(v): return v & M
def hi(v): return (v >> 12) & M
def emb(a, h): return a | (h << 12)


def escale(v, s):
    """24-bit word × GF(2^12) 标量：两半各乘一次（= c=0 分支的两个 mul_xor0）。"""
    return mul(lo(v), s) | (mul(hi(v), s) << 12)


def scale_word(w, c):
    """scale(b,x,c)"""
    return mul(c, w) if c != 1 else w


def cx_const(w, x, c):
    """cx(b,x,w,c)：w ^= c*x（c==1 时源码走 b.cx）"""
    return w ^ mul(c, x) if c else w


def mul_xor0(z, x, y):
    """ar.mul_xor0(b,x,y,z)"""
    return z ^ mul(x, y)


def mul24(z, x, y):
    """mul24_xor99(b,x,y,z,K)"""
    return z ^ emul(x, y)


# ---------------------------------------------------------------- 电路片段的直译
def corrected_product_c0(a, h, D, L, ct, c):
    """external_corrected_product, c=0 分支：两个 mul_xor0（84 T）。"""
    assert c == 0
    L = mul_xor0(lo(L), h, lo(D)) | (mul_xor0(hi(L), h, hi(D)) << 12)
    return a, h, L


def corrected_product_cneq(a, h, D, L, ct, c):
    """external_corrected_product, c!=0 分支（99 T + 0 T 线性门）。"""
    assert c != 0
    v = mul(c, ct) ^ 1
    a = scale_word(a, c)          # scale(b,a,c)
    a = cx_const(a, h, v)         # cx(b,h,a,mul(c,ct)^1)
    h = scale_word(h, c)          # scale(b,h,c)
    L = mul24(L, emb(a, h), D)    # mul24_xor99(combine(head),D,L,K)
    h = scale_word(h, inv(c))     # scale(b,h,inv(c))
    a = cx_const(a, h, v)         # cx(b,h,a,mul(c,ct)^1)
    a = scale_word(a, inv(c))     # scale(b,a,inv(c))
    return a, h, L


def mul_head(a, h, D, N, ct):
    """external_mul_head（99 T + 0 T 线性门）。"""
    a = cx_const(a, h, ct)        # cx(b,h,a,ct)
    N = mul24(N, emb(a, h), D)    # mul24_xor99(combine(head),D,N,K)
    a = cx_const(a, h, ct)        # cx(b,h,a,ct)
    return a, h, N


# ---------------------------------------------------------------- 检查
def main():
    import random
    rng = random.Random(20261112)
    cs = sorted({c for c in range(2, 33, 2)})          # geometry(): c = 2*i, i=1..16
    bad = 0
    trials = 0
    for trial in range(400):
        a, h = rng.randrange(4096), rng.randrange(4096)
        D = rng.randrange(1 << 24)
        for ct in (0, 1):
            for c in cs:
                trials += 1
                L0, N0 = rng.randrange(1 << 24), rng.randrange(1 << 24)
                a1, h1, L1 = corrected_product_cneq(a, h, D, L0, ct, c)
                a2, h2, N1 = mul_head(a, h, D, N0, ct)
                assert (a1, h1) == (a, h), 'gauge 未复原'
                assert (a2, h2) == (a, h), 'cx 对未复原'
                P1 = L1 ^ L0
                P2 = N1 ^ N0
                # 关系式 P1 = c*P2 ^ (h*D)
                lhs = P1
                rhs = emul(P2, c) ^ escale(D, h)
                if lhs != rhs:
                    bad += 1
                    if bad <= 5:
                        print('MISMATCH', dict(a=a, h=h, D=D, ct=ct, c=c,
                                               P1=P1, P2=P2, rhs=rhs))
                # 也检查"P1 != c*P2"（即差项 h*D 一般非零）
    print(f'[c!=0] trials={trials} mismatches={bad}')

    # ---- c=0 分支
    bad0 = 0
    trials0 = 0
    for trial in range(200):
        a, h = rng.randrange(4096), rng.randrange(4096)
        D = rng.randrange(1 << 24)
        for ct in (0, 1):
            trials0 += 1
            L0, N0 = rng.randrange(1 << 24), rng.randrange(1 << 24)
            _, _, L1 = corrected_product_c0(a, h, D, L0, ct, 0)
            _, _, N1 = mul_head(a, h, D, N0, ct)
            P1, P2 = L1 ^ L0, N1 ^ N0
            assert P1 == escale(D, h), 'c=0 的 corrected product 不是 h*D'
            assert P2 == emul(emb(a ^ mul(ct, h), h), D)
            # 双线性拆分：P2 = (a ^ ct*h)*D ^ (h*t)*D
            s = a ^ mul(ct, h)
            part_a = emul(emb(s, 0), D)
            part_h = emul(emb(0, h), D)
            assert P2 == part_a ^ part_h
            # (h*t)*D 可以从 h*D 0 T 得到（K*h*d1 在低半，h*d0^h*d1 在高半）
            hD = escale(D, h)
            assert part_h == (mul(K, hi(hD)) | ((lo(hD) ^ hi(hD)) << 12))
            # 而 part_a = s*D 是另一个 12x24 标量乘（两个 mul_xor0 = 84 T）
            assert part_a == (mul(s, lo(D)) | (mul(s, hi(D)) << 12))
            if a and D:
                # part_a 不是 h*D 的函数：同一 (h,D) 下改 a 会改 P2
                bad0 += 0
    print(f'[c=0]  trials={trials0} mismatches={bad0}')

    # ---- 反向：P2 是否真的需要"新"乘积才能从 P1 得到
    # 固定 h,D，扫 a：P1 与 P2 的差随 a 变化 => 不是常数/标量关系
    h, D = 0x357, 0x123456
    c, ct = 6, 0
    seen = []
    for a in (0x001, 0x002, 0x123, 0xabc):
        _, _, L1 = corrected_product_cneq(a, h, D, 0, ct, c)
        _, _, N1 = mul_head(a, h, D, 0, ct)
        seen.append((a, L1, N1, L1 ^ emul(N1, c)))
    print('[c!=0] 固定 h,D 扫 a，P1 ^ c*P2 =')
    for a, P1, P2, d in seen:
        print(f'   a={a:#05x} P1={P1:#08x} P2={P2:#08x} diff={d:#08x} '
              f'(== h*D ? {d == escale(D, h)})')

    # ---- 关键算术：P1 能不能在 P2 之外 0 T 得到？
    # P1 = c*P2 ^ h*D，其中 h*D 是 12x24 双线性乘积，不能用线性门从 (P2,head,D) 得到。
    # 给出维度论证的实例：固定 head、变 D，h*D 与 P2 不成比例。
    a, h = 0x111, 0x222
    rows = []
    for D in (1, 2, 3, 0x1000, 0x1001):
        P1 = corrected_product_cneq(a, h, D, 0, 0, 4)[2]
        P2 = mul_head(a, h, D, 0, 0)[2]
        rows.append((D, P1, P2, P1 ^ emul(P2, 4) == escale(D, h)))
    print('[check] P1 == 4*P2 ^ h*D 对 5 个 D:', all(r[3] for r in rows))

    # ---- 规模：12-bit 乘法的秩与当前 kernel
    print(f'[cost] 12-bit 乘法秩 42 T (field.tensor4 = 7x6), '
          f'12x24 = 2*(12x12) = 84 T; 24-bit mul24_xor99 = 99 T')


if __name__ == '__main__':
    main()
