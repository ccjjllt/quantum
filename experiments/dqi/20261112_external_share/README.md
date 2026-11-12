# DQI external-chain 乘积共享实验（`20261112_external_share`）

日期：2026-11-12；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**只读证明 + 单步切片 T 测量 + 只读 `.kmx` 块解剖**。未构建整件候选 `.kmb`，
未运行官方验证器，未提交 Kaggle。判决见 §0。

## 0. 结论先行

**no-go。** 前提「`external_corrected_product` 与 `external_mul_head` 各算一次**相同的**
24-bit 乘积，共享可省 75–99 T/步」**不成立**。

1. 两个乘法调用点的操作数确实落在同一组物理 qubit（`combine(head)`、同一个 `D`），
   但**逻辑值被 gauge 变换分开**，精确关系是（§2，12,800 组随机值 + 5 组定点全部命中）

   ```
   P_L = c · P_N  ⊕  (h · D)          （c≠0 分支）
   P_L =      h · D                    （c=0 分支，P_N 里另有一半是 (a⊕ct·h)·D）
   ```

   其中 `c·P_N` 是 0 T 线性映射，而 **`h·D` 是一个新的 12×24 乘积（两个 `mul_xor0` = 84 T）**。
   所以理论上限是 `99 − 84 = 15 T/步`，不是 75–99 T/步。
2. 该 block 内**没有**别处算过的 `h·D` 可复用：切片实测一个 c≠0 步的 paid 恰好
   **198 T = 99 + 99**（c=0 步 183 T = 84 + 99，first 步 0 T）。步内 paid 只有这两个乘积（§3）。
3. 想用这个关系必须把其中一个乘积**隔离**到 24-bit 暂存（24 个 CX 复制是 0 T，但寄存器要 24 个
   qubit）。该步本身已经在用 24 个 qubit 的 D（`b.alloc_qubits(24)`），而公开件的 ancilla
   峰值即全量、slack 0（§4），所以再要一个 24-bit 暂存只能把 Q 抬到 913：成本
   ×(913/889)² = **+5.47%**，而 T 只降 **−1.36%**（6,210 / 456,456）→ **净 +4.1%**。
4. 即使 Q 不涨，v21 也到不了 eae：static 456,456 → **450,246**（−1.36%），仍比 eae 的
   401,313 高 **12.2%**；mean 437,947 → ~432,000，而 3.40e11 需要 ≤358,709（Q=892，§4）。
5. eae 的 **186/178-T 块不是 v21 的 chain step**（v21 的链步实测是 183/198 T）。实测 eae 两类块
   各 105 / 91 个、extract 与 unextract 都有（共 392 个），形状是「单簇 186/178 个 CCX +
   每 CCX ~69/61 个 CX 的稠密展开（形状上接近 Vandermonde `conv`，具体归属未定）」，操作数是 **12-bit E62 vs 24-bit E60|E61**、
   y 集合也不同（E71 只在 186 块里）——不存在「同一个 24-bit 乘积算两次」。eae 的 tag 词表
   （`aligned_route`/`head_pivot`/`full_head_product`/`head_phase`/`multiply v`/`inverse12|24
   products|scalar|norm`）来自 `exp/r-main/narrow240/{measured_heads,direct_converter}.py` +
   `exp/jet24/pro_jet.py`，是 direct/gap-chart + jet 族，不是 `final_decoder/decode.py` 的
   `external_chain_step`（§5）。
6. 因此没有候选，也没有「块级移植到 eae」这一步可做；按任务约定不构建全电路、不跑验证器。

## 1. 输入、基线与口径

| 资产 | 位置 | 用途 |
|---|---|---|
| 公开生成器（Apache-2.0，team-1028-narrow240） | `artifacts/20261030_public_audit/dqi/somejoint_v21_source/…/source/`（worktree 只读副本 `artifacts/20261112_frontier_source/somejoint_v21_source/`） | 证明对象 |
| v21 源码副本 | `artifacts/20261112_external_share/source_copy/{decode,common,kernels}.py` + `.sha256` | 可复现 |
| eae 候选 | `artifacts/20261112_eae_candidate/dqi.kmb`（main，只读） | 块解剖 |
| eae 的 `.kmx` 文本 | `/private/var/…/T/dqi_branch/eae.kmx`（797 MB，`20261112_branch_recovery/dump_kmx.py` 生成，不进 Git） | 块解剖 |

基线（引用，不重测）：

| 件 | Q | static T | mean T（102,400 shots） | 成本 |
|---|---:|---:|---:|---:|
| v21（somejoint，889Q） | 889 | 456,456 | 437,947.6 | 3.4612e11（Q²T） |
| eae396ba | 892 | 401,313 | 394,089.27 | **3.7353e11** |
| 目标 | — | — | — | <3.7353e11，理想 ≤3.40e11（⇔ Q²·meanT ≤2.8542e11） |

口径：paid = `CCX + CCZ + CSWAP + CCX_CARRY`；`scale`/`cx`/`scalepair`/`swap`/`external_square24`
都只用 `CX`/`SWAP`（`field.py::linear_inplace` L40-48、`linear_xor` L35-37），**0 T**。

## 2. 只读证明：两个乘积的操作数关系

源码（`final_decoder/decode.py`，本实验副本 SHA-256
`a5f5dcb7…27ff`）：

```python
def external_mul_head(b,head,D,N,ct):                    # L300
    a,h=head; cx(b,h,a,ct)
    mul24_xor99(b,combine(head),D,N,K)                   # 99 T
    cx(b,h,a,ct)

def external_corrected_product(b,head,D,L,ct,c):         # L306
    if not c:
        ar.mul_xor0(b,h,D[:12],L[:12]); ar.mul_xor0(b,h,D[12:],L[12:])   # 84 T
    else:
        scale(b,a,c); cx(b,h,a,mul(c,ct)^1); scale(b,h,c)
        mul24_xor99(b,combine(head),D,L,K)               # 99 T
        scale(b,h,inv(c)); cx(b,h,a,mul(c,ct)^1); scale(b,a,inv(c))
```

逐门语义：`scale(x,c)` 是「乘 GF(2^12) 常数 c」的线性映射（0 T）；`cx(b,x,z,c)` 是
`z ^= c·x`（0 T）；`mul_xor0` 是 `z ^= x·y`（42 T）；`mul24_xor99(b,x,y,z,K)` 是
`z ^= emul(x,y)`，其中 `combine(head)=a|h<<12` 正是 `a+b·y` 的 24-bit 串，K 即 `y²+y=K`
（`mul99/kernels.py::tensor99_extension(K)` + `field.py::extension_columns` 文档 L337-342）。

推导（`head=(a,h)`，`v = mul(c,ct)⊕1`，`Y = (a⊕ct·h) + h·y`）：

```
c≠0 调用点：(c·a ⊕ v·h,  c·h)   ⇒  P_L = [c·(a+h·y) ⊕ v·h]·D
                                        = c·[(a + ct·h + h·y)·D] ⊕ (c·ct ⊕ v)·h·D
                                        = c·P_N ⊕ h·D           （c·ct ⊕ (c·ct⊕1) = 1）
c=0 调用点：(h)·D（两个 mul_xor0 = 标量乘）  ⇒  P_L = h·D
             P_N = (a⊕ct·h)·D ⊕ (h·y)·D，其中 (h·y)·D 是 h·D 的 0 T 线性像，
                   (a⊕ct·h)·D 是另一个 12×24 乘积（84 T）
```

验证（`prove_share.py`，用源码自己的 `mul/inv/emul/K`，逐条复刻上面的门序列）：

* c≠0：`c ∈ {2,4,…,32}`（即 `geometry()` 里 c=2i）× `ct ∈ {0,1}` × 400 组随机
  `(a,h,D,L0,N0)` = **12,800 次，0 次不符**；并断言尾部四个门确实复原 `(a,h)`。
* 定点扫描：固定 `(h,D)`、变 `a`，`P_L ⊕ c·P_N` 恒等于 `h·D`（4/4）；
  固定 `(a,h)`、变 `D`，`P_L = c·P_N ⊕ h·D` 5/5。
* c=0：200 组 × ct → `P_L == escale(D,h)`、`P_N == (a⊕ct h)·D ⊕ (h·y)·D`、
  `(h·y)·D == (K·(h·D)_hi | ((h·D)_lo ⊕ (h·D)_hi)<<12)`（0 T 可得），
  而 `(a⊕ct·h)·D` 必是新乘积 —— 400 次全部成立。

**结论**：操作数不是同一个值；`c·P_N` 0 T 可得，但差项 `h·D` 是新的 12×24 乘积。
省 99 T 不可能；上限 15 T/步。

## 3. 步内 paid 门穷举 + 单步切片实测

`external_chain_step`（L316）里所有 paid 调用只有两处：`external_corrected_product`
与 `external_mul_head`；`external_square24`（两份）、`scalepair`（三处）、`swap`、`cx`
全是 0 T。为排除「0 T 函数其实含 T」的误读，直接实测（`slice_step_t.py`，96-qubit
裸 builder，只数 Toffoli-like）：

| 电路 | T | Q |
|---|---:|---:|
| 单步 c≠0（真实 `external_chain_step`，c=4/12，ct=0/1） | **198** | 96 |
| 单步 c=0（`first=False`） | **183** | 96 |
| first 步（D=\|1⟩, N=\|0⟩，纯 CNOT） | **0** | 96 |
| 共享乘积补丁（99 + 84 + 0 T 复制/scale） | **183** | **120** |

补丁本身就写在这份切片里：`mul24_xor99(head,D,t)`（99）→ `N ^= t`（24 CX）→
`t *= c`（0 T）→ `L ^= t` → `L ^= h·D`（2×`mul_xor0`=84）→ 释放 t。它就是 183 T，
但比原步多 **24 个 qubit**。

## 4. 步数与成本上限（v21）

`EXTERNAL_HOMOGENEOUS = range(8,17)`，共 9 个 node chain，head 数 `2·gi`（gi=8..16），
每个方向 **216 步**。实测几何：`ks` 里每个 kap 出现两次，所以 `c` 在**偶数头**为 0：

* c=0 步：gi−1 个/节点 → 每方向 99 步 × 183 T
* c≠0 步：gi 个/节点 → 每方向 108 步 × 198 T
* first 步 9 个/方向 = 0 T

每方向链乘积 **39,501 T**（99×183 + 108×198），两方向 **79,002 T** = 456,456 的 17.3%。
可寻址节省 = 207 步/方向 × 15 T × 2 = **6,210 T = 1.36%**：

```
static 456,456 → 450,246          （仍比 eae 401,313 高 12.2%）
mean   437,947 → 432,000 左右      （3.40e11 在 Q=892 要求 ≤358,709）
```

而且实现它需要 24-qubit 暂存：整件 ancilla 无 slack（`20261112_low_ancilla` §0：889Q 的
49 / eae 的 52 个 ancilla 峰值即全量），Q 889→913 让 `Q²·meanT` × (913/889)² = **+5.47%**，
与 −1.36% 的 T 收益相抵后**净 +4.1%**。所以这一步连「不亏」都做不到。

## 5. eae 的 186/178 块是什么（只读 `.kmx` 实测）

`inspect_blocks.py`（gap=200 切段、簇间隙 150）与 `tag_fingerprint.py`：

| 块 | 每方向个数 | CCX | CX | SWAP | CCZ | 首操作数 x | 第二操作数 y | 目标 z |
|---|---:|---:|---:|---:|---:|---|---|---|
| 186 | 105 | 186 | 12,826 | 31 | 0 | E62（7 个 qubit，计数 97/42/29/9/6/2/1） | E70,E71,E73（8 个 qubit） | E64,E66 |
| 178 | 91 | 178 | 10,887 | 21 | 0 | E60,E61（93/85，两半各自低位峰值：E60#0 46、E61#0 48） | E70,E72,E73（无 E71） | E64,E66 |
| 99 | 311 / 76 | 99 | 6,461 | 19 | 0 | E8 或 E6（单寄存器） | E70..E73 | E64 |

（第三行是 eae 里 99-CCX 的块，65 CX/CCX，与 v21 链步实测的 198 CCX / 13,107 CX =
66.2 CX/CCX 同一量级，符合共轭稠密 mask 的 `mul24_xor99`。**CX 密度不能区分 186/178 块**，
判别依据是下面的块大小、操作数与 tag 词表。）

判定依据：

1. **个数/配对**：186 与 178 在 unextract 里交替出现（例：行 53,622,967 的 186 块之后
   紧接行 53,636,280 的 178 块），两者都写同一个 24-bit 目标字 E64|E66；合计
   `105×186 + 91×178 = 35,728 T`，extract 侧完全同构，共 **71,456 T = 401,313 的 17.8%**。
2. **操作数不同**：186 块的乘数是一个 12-bit 字（E62），178 块是 24-bit 字（E60|E61），
   y 集合也不同（E71 只在 186 块）。不存在「同一个 24-bit 乘积两次」。
3. **不是 v21 的链步**：块大小由 kernel 决定、与几何无关——v21 链步实测 183（84+99）
   或 198（99+99）CCX；eae 的 186/178 都不是这两个值，也不等于 `tensor(24)` 的 105 或
   `conv` 家族的 42 倍数（同电路的 `full_head_product` 是 126/168/210）。它们是单簇、
   每 CCX ~69/61 CX 的稠密展开，最接近
   `exp/r-main/narrow240/direct_kernels.py::conv/rank_update`（`expose` 稠密 CNOT 网络 +
   每秩项一次 CCX）这一类，但**具体归属未定**；本实验只用它排除「v21 链步」这一身份。
4. **族不同**：eae 的 tag 词表（`aligned_route`、`head_pivot`、`full_head_product`、
   `head_phase`、`multiply v`、`inverse12|24 products|scalar|norm`）来自
   `exp/r-main/narrow240/{measured_heads,direct_converter}.py` 与 `exp/jet24/pro_jet.py`；
   `final_decoder/decode.py` 的 `external_chain_step` 在 eae 里最多只作为
   `replay_erase/frozen_chart` 的一个被替换项，无法证明 186/178 是它。

即使把 §2 的关系式硬套到 eae（196 步/方向 × 2 方向 = 392 对），上限也只有
`392 × 15 = 5,880 T = 1.47%`（static 395,433）；加上 24-qubit 暂存后的 Q² 惩罚
（892→916 = +5.45%）同样净亏。**不改判决。**

## 6. 反例检查（为什么没有「更大的共享」）

* **步内第三处乘积**：无（§3 实测 198 = 99+99，183 = 84+99）。
* **相邻步**：`D_{k+1} = N_k`、`N_{k+1} = q_k·(D_k ⊕ Y_k·D_k)`，即
  `D_{k+2} = q_k·(1 ⊕ Y_k)·D_k`。`Y_k` 是量子数据，不是已知常数，所以下一/隔步的
  `X·D_{k+2}` 不能由 `X·D_k` 0 T 推出。
* **`external_normalize_paired`**（L352，每节点一次）：`multiply_forward99(N,D)` 与
  `external_square24(D)` 后的 `multiply_forward99(L,D²)` —— 同一个 D 但乘数不同
  （N vs L），且第二处用的是 D²，没有共享项。
* **`jet_forward`/`ordinary node`**：99 的 `mul_xor99(v,u,out)` 每步只有一次乘积，
  不存在「同乘积两目标」的情形。
* **c=0 分支在 v21 里**确实会被用到（偶数头，99 步/方向），但它当前只付 84+99；改用
  「84 + 84 + 0 T 线性像」同样是省 15 T，同样要 24-bit 暂存。**两条分支上限一致。**
* **不用暂存的替代写法也不成立**：例如先做 `mul_head`（P2 进 N）再 `swap(N,D)`，此时
  `N = D_old ⊕ P2`，于是 `L ^= c·N ⊕ (c⊕h)·D_old`——`c·N` 是 0 T（`cx(b,N,L,c)`），
  但 `(c⊕h)·D_old` 又是一个 12×24 乘积（84 T），而且 `D_old` 已被 swap 覆盖、`P2`
  不可再分离。换个写法的代价仍是 84 T + 需要一个 24-bit 中间值。

## 7. 数字汇总

| 项 | 值 |
|---|---:|
| v21 每方向链步 / 其中 c=0 / c≠0 / first | 216 / 99 / 108 / 9 |
| v21 每方向链乘积 T（两方向） | 39,501（79,002） |
| 共享可省（15 T/步 × 207 × 2） | **6,210 T = 1.36%** |
| 若实施后 v21 static | **450,246**（eae 401,313，差 12.2%） |
| 实施所需额外 qubit | +24（Q 889→913，成本 ×1.0547） |
| 净成本变化（T 收益 vs Q² 惩罚） | **+4.1%** |
| eae 186/178 块总量 | 71,456 T（两方向，401,313 的 17.8%） |
| eae 上同类上限（若关系成立） | 5,880 T = 1.47%（static 395,433） |
| 结论 | **no-go，无候选，无块级移植** |

## 8. 验证范围（明确未做）

* 未构建整件 v21 变体 `.kmb`，未测 4,096-shot mean，未跑
  `scripts/manual_verify.py`，未提交 Kaggle。理由：T 上限已差 eae 12.2%（且净成本更差），
  不满足「≤eae 才移植 / <3.7353e11 才算候选」的前置条件。
* `slice_step_t.py` 只建 96-qubit 单步电路并计 paid T，**没有做态模拟/等价检查**
  （96 qubit 的态向量不可行）；等价性由 §2 的值级证明承担（同一域原语、12,800 组随机值）。
* eae 的 186/178 块只做门级解剖，**没有**独立证明其语义；「不是 v21 chain step」是
  形状+操作数+tag 词表三重证据，不是源码级证明（eae 的精确源码不在本仓库）。
* 所有 T 数为 static（`num_toffoli_like`），mean 数引用既有记录。

## 9. 复现

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi
.venv/bin/python experiments/dqi/20261112_external_share/prove_share.py        # §2 值级证明
.venv/bin/python experiments/dqi/20261112_external_share/slice_step_t.py       # §3 单步 T
.venv/bin/python experiments/dqi/20261112_external_share/inspect_blocks.py 150 # §5 块解剖（~55 s，读 797 MB kmx）
.venv/bin/python experiments/dqi/20261112_external_share/tag_fingerprint.py    # §5 tag 指纹（~55 s）
```

产物：`artifacts/20261112_external_share/{logs/*.log, eae_blocks/block186.txt,
eae_blocks/block178.txt, source_copy/*, source_copy.sha256}`。
