# bs_lz.md：S1 二分 lz 替换（温度计→二分搜索）—— Q 不变，S1 门数 −77%

分支 `invsqrt-generator-rebuild`。基线：TH 版 `narrow_v62.py`（Q=132，
SHA `e036965d…`，官方 PASS 1581912.53）。本轮只动 S1（`build_lz_norm[_rev]`
→ 二分），不动拟合表（只读 BOTH）、不动 S2 归一化/查表/行/窗口/恢复钩子；
不读旧 KMB/tray；不截位；止于预筛 + 全域整数合同，未跑官方 200M-shot。
产物只在 `experiments/invsqrt/20261102_generator_v2/`（本文 +
`narrow_v62.py` 单线续改、`narrow_proof.py` +2 项、`prescreen_narrow_v.py`
dump-v 读路 + REC_SHA）与 `artifacts/20261102_generator_v2/invsqrt/`
（`narrow_v62.kmb`、`narrow_v62_stats.json`、`bs_lz_proof.log`、
`bs_lz_prescreen.log`、`bs_lz_contract.log`）。

## 0. 文件取舍（延续 narrow_v62.py 单线，理由）

- 本任务与 TH 收窄是同一容器、同一系表、同一调度上的增量块替换（只换
  S1 的 lz 求值块，不动 V 容器 `vd46/Vn30`、A/R 位宽移位、B 位偏移、S6、
  合并）。同 `th_narrow.md` §0 论证：另起文件会分叉 double-build 谱与
  REC_SHA；单线新旧 SHA 直接对比证明“只变了 S1”。
- 旧 SHA `e036965d…`（TH 版）对其对应电路继续有效、不被取代；作废含义仅为
  “旧值不适用于本电路”（A 门用新值 `813ba1ad…` 比对）。Q_CAP 保持 **132**
  （实测峰值仍在行，不在 S1，见 §5）。

## 1. R_S1 为何比 F_S1 贵近一倍（行级对账，先解释再动手）

对象 `width_opt62.py:129-182`（`_cmp/_hot/build_lz_norm/build_lz_norm_rev`，
`narrow_v62.py` 原样沿用）。孤立 S1 探针（/tmp，不进产物）实测：

| | flip 调用数 | toff(CCX) | HMR | CX | X |
|---|---|---|---|---|---|
| F_S1 正向 | 42 | 922 | 882 | 85 | 2062 |
| R_S1 逆向 | 82 | 1762 | 1722 | 85 | 4022 |

- 正向 42 次：首 `_cmp(c1)` 1 次 + 循环每 `i` 解散旧位/计算新位共 40 次 +
  尾解散 `c_21` 1 次（滑动窗口复用：`c_{i+1}` 上轮算好本轮当 `c_i` 用）。
- 逆向 82 次：`for i in reversed(range(21))` 每轮
  算 `c_i` + 算 `c_{i+1}` + `_hot-rev` + 解散 `c_{i+1}` + 解散 `c_i`
  （`i≥1` 4 次 ×20 + `i=0` 2 次）。每个阈值被摸 4 遍。
- 差值 40 flip × 21 CCX = 840 = 1762−922 **精确相等**；且 hot 编解码两侧
  各 40 CCX（922−42×21 = 1762−82×21 = 40，CX 85 对称）——**不对称 100%
  来自比较器重算，编码逻辑对称**。根因：逆序循环无法沿用正向滑动，
  实现选择了每轮双阈值重算+双解散（保守但贵一倍）。
- 遗留估计纠正：`width_opt62.py` D1 注“温度计 fwd 42 + rev 42 = 84 次”
  **是错的**，实为 42+82=**124** 次。凡引用“84”的旧比较（一律按 124 重算）。
- 备选（已评估，未采用）：把 rev 改成倒向滑动（每轮算 `c_i`、复用、
  解散 `c_{i+1}`，42 次，与正向对称），S1 2684→~1844（−31%），diff 最小。
  被二分支配（−77%，同宽度），降级为 fallback（见 §7）。

## 2. 探针表（先测量后决策）

| 探针 | 结果 | 结论 |
|---|---|---|
| `flip_if_less_than(x22, 2^k)`，k=1..21 | **恒 21 CCX**（无 2 幂优化） | **全宽二分否决**：31×21×2+MUX ≈1400，仅 ~2 倍，且 L3 需 4 谓词+21 scratch 并存，宽度反涨 |
| `flip_if_equal(x[a:b],0)` 切片 | w=11→11，6→6，5→5，3→3，2→2，**1→0**（CX+X） | 切片谓词线性成本，1 位免费 |
| 2:1 MUX（s 保持，对合） | 2 CCX + 2 X，0 scratch | 修正层便宜 |
| AND5（HMR 链，解码匹配） | 4 toff + HMR/R/CZ，0 alloc 跟踪 | 折叠解码可行 |
| S1-only 二分 fwd | nq=47（基 32，live +15），toff 181 | 全局 108+15=123 ≤132，宽度有余量 9 |
| 当前线 F_S1/R_S1（TH，改前） | 922 / 1762，共 2684，占全 toff 22.8% | 首要怪象确认 |

决策：**切片二分**（5 层切片谓词 + MUX 修正 + L5 折叠解码直达 lz），
全宽二分按探针证据否决（门省一半、宽度恶化，不值得 churn）。

## 3. 设计（二分树 + 修正 + 解码，x≥1，lz=22−bitlen）

e=bitlen−1 ∈ 0..21，lz=21−e。谓词全是“某切片全零”（给定上文路径即等价于
`x<2^k`，numpy 全域验证了等价性）：

| 层 | 选择 | 候选（F-first 字典序，内层选择变化最快） |
|---|---|---|
| L1 | — | d1=(x[11:22]==0)，11 CCX |
| L2 | d1 | F:(x[17:22]==0) 5；T:(x[5:11]==0) 6；1 MUX |
| L3 | d1,d2 | (20,22)2/(14,17)3/(8,11)3/(2,5)3；3 MUX |
| L4 | d1..d3 | (21,22)0/(18,20)2/(15,17)2/(12,14)2/(9,11)2/(6,8)2/(3,5)2/(1,2)0；7 MUX |
| 解码 | d1..d4 | 16 路 AND4：10 单叶直写 lz，6 对位叶重算 1 位阈值 `~x[eT+1]` 按 (bT,bF) 混合写入 |

- L5 不建 MUX 树：16 候选中 10 为哑叶（常量 0，无分配），6 为 1 位叶；
  直接并入解码（省 15 MUX + 15 中间位，峰值 −20）。
- 解码映射 `path4→lz` 由构建时整数推导（`_bs_decode_entries`，e=0..21
  代表元走阈值树；纯确定性整数循环，无随机/KMB/拟合表），numpy 4194304
  全域交叉验证（22 双射，0 不一致）。
- F-first 叶序教训（dev 实锤 bug）：相邻配对恒为 [F,T] 时通用
  `mux2(s,T=cur[i+1],F=cur[i])` 才成立；一度用反序导致 170 万错配，
  由 numpy 全域抓获（`bad=1716938` → 归零）。
- 脏暂存教训 ×2（均由预筛 B 抓获，非纸面推导）：
  1. F/R 间 d 不存活（F 末已释放）：rev 首步必须由 x **重算** d1..d4
     再解码清 lz（与温度计 rev 重算阈值同模式）。
  2. 脏释放复用：d 带路径值释放后重配到脏线，`^=` 重算全错。故正向亦
     采用 compute-copy-uncompute（levels→解码→倒序清 d，d 进零出零），
     正逆化为**同一序列**（levels 与解码皆自逆）。

## 4. 证明（先行，已 PASS）

`narrow_proof.py` 新增两项（Wx=6 缩比：d1+L2 MUX+折叠解码+归一化，
与全尺寸同构；AND2 与全尺寸 AND5 同 init_and 链模式，仅元数不同）：

```
bslz6: 63/63 ok                    # x=1..63 穷举，lz==5-(bitlen-1)，d 外余零
bsroundtrip6: 63 samples ok        # fwd→rotl→rotr→rev（含 d 释放重配），x 复原全零
NARROW-PROOF PASS                  # 旧 12 项穷举亦 PASS，无回归
```

全尺寸补充（/tmp 开发证据，不进产物）：numpy 切片树 4194304 全域
`bad=0`；全宽量子 45 定向样本（2^k±1 全边界 + 域内点 + 顶值）
lz 精确 + d 路径精确 + 余零 PASS；往返恒等 PASS。
**证明只管等价性**，宽度/门数由 §2 探针与 §5 实测裁决。

## 5. diff（vs TH 版 `e036965d…`）

- `narrow_v62.py`：新增 S1 二分节（`_BS_L2/L3/L4`、`_BS_TH3/TH4`、
  `_bs_decode_entries`、`_bs_mux2/_pred/_tree_mux/_and4/_decode_fwd`、
  `build_bs_fwd/rev` + `_bs_levels_fwd/rev`）；`build_forward_nv` /
  `build_reverse_nv` 的 S1 块由 `e2+h1 + W.build_lz_norm[_rev]` 换成
  `d5 + build_bs_fwd/rev`（STAGE 名保留，阶段对账连续）。
- `prescreen_narrow_v.py`：`dump_v` 前缀同步换二分；`REC_SHA→813ba1ad…`。
- 整数 oracle `nv_model_phase` **未动**（数学终值不变，合同 maxrel 同值）。

## 6. 成本对比（实测）

| 口径 | TH 版（`e036965d…`） | 二分（本任务，`813ba1ad…`） | 变化 |
|---|---|---|---|
| Q（num_qubits） | 132 | 132 | 0（峰值仍在行，S1 局部 ~123） |
| F_S1 / R_S1 toff（阶段实测） | 922 / 1762 | **304 / 304**（严格对称，怪象消除） | −618/−1458 |
| S1 合计 | 2684（占 22.8%） | **608**（占 6.3%） | **−77.3%** |
| `toffoli_like`（CCX+CSWAP） | 11752 | **9676** | −2076（−17.7%） |
| `num_instructions` | 109642 | 90354 | −19288（−17.6%） |
| Q×toff（静态） | 1551264 | **1277232** | **−17.7%** |
| 文本 SHA | e036965d… | 813ba1ad… | 新 REC_SHA（A PASS，double-build `str` 相等） |
| maxrel 全域（合同重跑） | 0.8712321494 | **同值**（模型未动） | 仍 <1 PASS，最坏 x=1796095 不变 |
| min_margin 全域 | 105643461 | 同值 | 仍 >0 |
| 16 样本 C | 全 >0（最小 524594562 @2097151） | 全 >0（逐点同值，dphase 全 0） | 全 >0 |
| 官方验证 | PASS 1581912.53（TH） | **未跑**（门禁） | — |

预筛证据（EXIT=0，全 PASS）：

```
uv run python .../narrow_proof.py
  ... bslz6: 63/63 ok / bsroundtrip6: 63 samples ok / NARROW-PROOF PASS  # bs_lz_proof.log
uv run python .../prescreen_narrow_v.py --a --b --c --dump-v
  sha1=sha2=recorded=813ba1ad… → PRESCREEN-A PASS
  checked 16 samples x 132 qubits: x-recovery ok, scratch all zero: True → PASS
  16/16 dphase=0，余量全>0（最小 524594562 @2097151）→ PRESCREEN-C PASS
  16/16 Vn 精确一致 → DUMP-V PASS   # bs_lz_prescreen.log
uv run python .../prescreen_narrow_v.py --contract-full
  checked=3133452 fails=0 maxrel=0.8712321494 worst=(1796095, 3.87e-11)
  min_margin_units=105643461.0 ... CONTRACT-FULL PASS  # bs_lz_contract.log
```

16 样本同各线：`1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`。

## 7. 否决 / 备选 / 下一步

- **否决**：全宽二分（每层 ~22 位比较器原文案）：探针 P2 实锤 flip 恒 21
  CCX → 仅 ~2 倍收益且宽度恶化，否决。5~8Q 式纸面估计一律以探针为准。
- **备选（未采用）**：rev 倒向滑动（−31%，diff 最小）。二分 −77% 支配它；
  若将来二分在官方 score 口径下不及预期（score 含 HMR/R/X 权重，静态
  toff −17.7% 未必等比转化为 score），回退到滑动版只需换 S1 块。
- **未做**：官方 200M-shot 验证（门禁；送验前需主线程确认——静态
  −17.7% 的 score 跟进幅度未知，预期 ~130w 量级但以实测为准，不 claim）。
- **下一步**：S1 现仅占 6.3%，主导转为 A1/R1 行与 QROM（B/A/R mini-pass
  各 254×6 + 行）。S1 宽度余量 9Q 可供后续行优化借用（需重测峰值）。
  位宽截短继续禁止；`btol` 全程 inf。

## 完整官方验证 PASS（2026-11-02，主线程，seed 20261031）

`artifacts/20261102_generator_v2/invsqrt/verify_bslz_seed20261031.log`（EXIT=0）：
`status=PASS`，200,540,928 shots，`score=1307880.5265214771`
（相对 TH 版 1581912.53 **−17.3%**，与静态 −17.7% 吻合；约为基线 13.0 倍），
`num_qubits=132`，`toffoli_count=9676`，`worst_error_over_tolerance=0.8712321628530258`
@ x=1796095（不变），`circuit_sha256=614abf6a…`。
