# DQI low-ancilla 重建实验（`20261112_low_ancilla`）

日期：2026-11-12；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**公开生成器本地重建 + 只读 .kmx 存活区间分析 + 4096-shot mean-T 测量**。
未运行 102,400-shot 全量官方验证器（原因见 §8）。判决见 §0。

## 0. 结论先行

- **no-go**：无法用现有资产构造 `Q²·meanT` 足够低、成本 ≤3.40e11 的 DQI 候选。
  当前最优仍是 `eae396ba`（3.7353e11）。
- **“ancilla 是 scratch、可以降到 845”的前提不成立。** 对两个独立解码器族做了
  逐 qubit 存活区间统计：
  - 公开 889Q：49 个 ancilla 中 **48 个是两个 24-bit external jet word**
    （`q840..q887`），从 extract 一直活到 unextract；剩下 1 个是 flag
    （`q888`，从行 4,387,746 活到行 59,714,140）。**峰值 49 = 全部 ancilla，slack 0。**
  - eae 892Q：52 个 ancilla 中同样是 **48 个 24-bit jet word**（`q840..q887`）
    + 4 个 flag（`q888..q891`），全部从 extract 活到 unextract。**峰值 52，slack 0。**
  这些 qubit 是贯穿全电路的数据，不是可替换的乘法 scratch；任何重编号/复用
  都不会降低 Q。
- 公开生成器**本来就用零 workspace 乘法**：`exp/arithmetic/field.py` 的
  `mul_xor0` 文档即 “ZEROworkspace”，GF(2^12) 42T、GF(2^24) 105T 与 scratch
  版本同秩；`decode.py` 里 99T 的 `mul24_xor99` 只占 1 个 pivot bit。
  把 99T 换成 105T 的 `mul24_xor_noscratch`（390 次，+2,340 static T）
  **不会降低 Q**，只会更差。
- 成本门槛（R=1.19126）：3.40e11 ⇔ `Q²·meanT ≤ 2.8542e11`。
  在契约下限 Q=840（零 ancilla）也要求 meanT ≤ 404,495；而公开族最好的
  meanT 是 **437,947**（Q=889），仍高 8.3%。在 Q=892 则要求 meanT ≤ 358,709
  （比 eae 低 9.0%）。现有公开解码器没有同时满足这两个条件的版本。

## 1. 目标与成本模型

- DQI 成本 = `R(ε+) · Q² · meanT`，R 在 102,400 shots、0 失败时固定
  **1.19126**，不可优化。
- 目标：≤3.40e11（比 eae 的 3.7353e11 低 ≥9%）；理想 ≤3.23e11（−13.5%）。
- 换算：3.40e11 ⇔ `Q²·meanT ≤ 2.8542e11`；3.23e11 ⇔ `≤ 2.7113e11`。

## 2. 输入与资产

| 资产 | 位置 | 用途 |
|---|---|---|
| team-1028 公开生成器（Apache-2.0） | `artifacts/20261030_public_audit/dqi/somejoint_v21_source/blocks/dqi/team-1028-narrow240/source/` | 889Q 原样重建、883Q baseline |
| 复制到本实验的源码 | `artifacts/20261112_low_ancilla/source/` | 只读重建 |
| eae 候选 | `artifacts/20261112_eae_candidate/dqi.kmb`（main 只读） | 对照 + 存活区间 |
| Heliosli QCC Circuits Live v97 | Kaggle dataset（11,065,412 B 的 `dqi.kmb.xz`） | 确认 DQI 版本 |
| Atakan h5 notebook v15 | `https://www.kaggle.com/api/v1/kernels/pull?userName=atakanaldemir&kernelSlug=quantum-circuits-iso-gap-dqi-h5` | 确认 eae 来源 |
| frontier source v3 | `artifacts/20261112_frontier_source/qcc-dqi-nonempty-projective-lean-source-v3/` | 评估“编译器作用在 eae 上” |

## 3. 公开生成器原样重建（step 1）

命令（worktree 根目录）：

```bash
.venv/bin/python artifacts/20261112_low_ancilla/source/build.py \
    artifacts/20261112_low_ancilla/public_889.kmb
```

结果：

| 指标 | 值 |
|---|---:|
| SHA-256 | `6349d2bc82eb1ef3a4e8c52c71a312823d756532517463b5e18eb25cc81195a8` |
| Q | 889 |
| static T | 456,456 |
| num_ops | 60,010,899 |
| build 秒数 | 38.9 |

SHA 与生成器 docstring 公布的 `6349d2bc…95a8` 完全一致，说明本地重建逐字节
匹配公开件。

mean T（官方 sampler/simulator，4,096 shots，salt `mean-t`）：

```bash
.venv/bin/python experiments/dqi/20261112_low_ancilla/mean_t.py \
    artifacts/20261112_low_ancilla/public_889.kmb --shots 4096 \
    --out artifacts/20261112_low_ancilla/public_889.mean.json
```

| 指标 | 值 |
|---|---:|
| mean T | **437,946.74609375** |
| value / phase errors（样本） | 0 / 0 |
| Q²·meanT | 3.461185e11 |
| 成本（R=1.19126） | **4.123173e11** |
| 相对 eae | **+10.383%** |

这与 team-1028 notebook 自报的 mean T 437,947.6、Q²T 3.4612e11 一致。

stage census（`experiments/dqi/20261112_low_ancilla/stage_census.py`，
kmx 放系统临时目录）：

| stage | paid | CCX | CSWAP | CCZ |
|---|---:|---:|---:|---:|
| extract | 67,761 | 67,233 | 528 | 0 |
| synthesis | 33,317 | 33,293 | 24 | 0 |
| convert | 63,435 | 57,075 | 6,360 | 0 |
| scan | 44,275 | 44,275 | 0 | 0 |
| unconvert | 65,872 | 59,272 | 6,600 | 0 |
| unsynthesis | 54,936 | 54,912 | 24 | 0 |
| unextract | 126,860 | 118,740 | 1,368 | 6,752 |
| **合计** | **456,456** | | | |

与 eae 的 stage 表相比：unsynthesis +14,507、unextract +23,825，
extract/convert/unconvert 再 +15,129；scan 完全相同（44,275）。
公开族的 T 劣势集中在反向链（uncompute 的 retain/replay 策略）。

## 4. 低 ancilla 分析（step 2）

### 4.1 源码事实：零 scratch 乘法已经是默认

`playbook/kit/decoder/exp/arithmetic/field.py`：

- `mul_xor0(b,x,y,z)`：docstring “Standard polynomial basis arbitrary target
  product with **ZERO workspace** … Same 42/105 T counts.”
- `mul24_xor105_zero`：零 private qubit、105T。
- `mul_xor`（非零版）只在重叠输入时用 3 个 scratch；主路径用 `mul_xor0`。

`final_decoder/decode.py` 使用 `mul24_xor99`（99T）做 24-bit 乘法；
`exp/noscratch/kernels.py` 的 `mul24_xor_noscratch` 是 105T。若替换：
+6T × 390 次 = **+2,340 static T**，Q 不变。结论：noscratch 替换对 Q
没有收益，只有 T 损失。

### 4.2 存活区间：48 个 ancilla 是两个 24-bit word

用 `experiments/dqi/20261112_low_ancilla/ancilla_live.py`
（对 `.kmx` 逐行统计 q≥840 的 first/last/uses 与最大重叠）：

`public_889.kmb` → `public.kmx`：

| 组 | qubit | 首次出现行 | 最后出现行 |
|---|---|---:|---:|
| 24-bit word A/B | q840..q887（48 个） | 2,698,638–2,709,566（extract） | 57.9M–59.7M（unextract） |
| flag | q888 | 4,387,746 | 59,714,140 |

- `distinct_ancilla = 49`，`peak_live = 49`，**slack = 0**。
- 峰值出现在行 4,387,746（extract），此时 49 个全部同时存活。

`eae.kmb` → `eae.kmx`（main 的只读文件）：

| 组 | qubit | 首次出现行 | 最后出现行 |
|---|---|---:|---:|
| 24-bit word A/B | q840..q887（48 个） | 2,698,652–2,701,310 | ~61.16M |
| 4 个 flag | q888..q891 | 2,908,157–2,909,361 | ~61.15M |

- `distinct_ancilla = 52`，`peak_live = 52`，**slack = 0**。

这说明两个独立族的设计是同一个：**840 syndrome + 48 external jet + 少量
flag**。48 个 qubit 是算法贯穿保留（reverse 需要原来的外部字），不是
可回收 scratch。Q 的下界由“是否保留两个 24-bit jet word”决定；在本架构内
无法通过替换乘法/整理 allocator 降低。

### 4.3 低 Q baseline 实测：883Q 反而更贵

`playbook/kit/decoder/decode.py`（docstring 自报 “sets Q at 883”）重建：

```bash
.venv/bin/python experiments/dqi/20261112_low_ancilla/build_variant.py \
    artifacts/20261112_low_ancilla/source/playbook/kit/decoder \
    artifacts/20261112_low_ancilla/source/playbook/kit/decoder/decode.py \
    artifacts/20261112_low_ancilla/baseline_playbook.kmb
```

| 指标 | 值 |
|---|---:|
| SHA-256 | `00c1d2a6065d43fe262a5c2f169474bd2b4985193d76d48c85f60956f06e296d` |
| Q | 883 |
| static T | 485,513 |
| mean T（4,096） | 467,869.64697265625 |
| Q²·meanT | 3.647928e11 |
| 成本 | **4.345633e11（+16.338%）** |

即：Q 从 889 降到 883 付出 +30.6k mean T（+7.0%），Q² 只降 1.34%，
净亏。这给出了公开族的局部 Q–T 斜率：**每减 1 Q 约 +5.0k mean T**。
按此外推，Q=860 的 mean T 约 582k、Q=845 约 657k，成本都在 4.4e11 以上，
远离目标。

## 5. 成本算术（step 3 的判定）

R=1.19126。目标 3.40e11 下每个 Q 允许的最大 mean T：

| Q | 允许 meanT（3.40e11） | 允许 meanT（3.23e11） |
|---:|---:|---:|
| 892 | 358,709 | 340,774 |
| 889 | 361,134 | 343,078 |
| 883 | 366,059 | 347,756 |
| 870 | 377,080 | 358,226 |
| 860 | 385,900 | 366,605 |
| 850 | 395,034 | 375,282 |
| 845 | 399,723 | 379,737 |
| 840（契约下限） | 404,495 | 384,271 |

对照实测：

- 公开族最好 meanT = **437,947**（Q=889）→ 即使 Q 强行压到 840，
  也比 404,495 高 **8.3%**，成本至少 4.10e11。
- eae meanT = **394,089**（Q=892）→ 要保持 Q=892 需 −9.0% meanT；
  要 Q=845 则 meanT 必须≈399.7k，即 **砍掉 47 个 ancilla 且 T 不增加**。
  由 §4.2，47 个里 48 个是贯穿全电路的数据字，做不到。

## 6. eae 生成器源码搜索（step 4）

- Atakan h5 notebook（v15，2026-11-09 run）明确写：
  “Our 892-qubit DQI … remains **byte-identical to our scored V14**”，
  DQI 在 `MEMBERS` 里以 `eae396ba…` 的 SHA 被引用，**不包含生成器**；
  notebook 只嵌入 4T GF(64) phase 的 `new_phase4.kmx` 证明与 inverse 的
  literal，不含 decoder 构建源码。
- Kaggle `heliosli/qcc-circuits-live` v97（2026-11-12）的
  `QCC_RELEASE_MANIFEST.json` 里 `dqi.kmb` 的 SHA 仍是
  `eae396baf0fa52952e07d891237e271257e35bc0483afe57abd17c77857785bd`
  （11,065,412 B 的 xz 解压后 557,739,238 B）。**v97 没有比 eae 更新的 DQI。**
- 因此没有可重建的 eae 源，无法在源级降 ancilla。

## 7. “编译器直接作用在 eae 上”评估

`artifacts/20261112_frontier_source/qcc-dqi-nonempty-projective-lean-source-v3/`：

- `MANIFEST.json` 自报：**Q=892, static_T=458,203**，比 eae 静态 T 高 14.2%。
- 用户实测 `decode_best.py`：Q=900, static T=484,418，更差。
- `tools/` 的 emitter（`dqi_chain_cache_emit_v4.py`、`dqi_live_product_emit.py`、
  `peak900_clifford_emit.py` 等）不是通用 kmb rewriter：它们读自己打包的
  `ops/a3/b3/t3/a2/...` numpy 段和扫描器产出的 `plans/*/events.npy`，
  按事件下标改写。要作用在 eae 上，必须先实现 kmb→该 packed 格式的转换、
  重新跑 scanner 生成事件，再写回 kmb；这是移植工程，不是现成工具调用。
- 即使移植成功，其自身预算也只是从 484k 降到 458k（−26k static），
  在 Q=892 仍需要 meanT ≤358.7k（−9.0%），差距远大于该工具的收益。

结论：该路线在本会话内不可行，且量级不够。

## 8. 验证范围

- **本地构建**：`public_889.kmb`（SHA 与公开件逐字节一致）、
  `baseline_playbook.kmb`。
- **局部/抽样检查**：用官方 verifier 的 sampler + simulator 跑 4,096 shots
  测 mean T；public 与 eae 均 0 value / 0 phase。这只是抽样，不是全量验证。
- **未运行 102,400-shot 全量官方验证**：没有候选满足 ≤3.40e11 的门槛，
  按任务约定不做全量验证，也不把抽样 0/0 写成“通过”。
- 未提交 Kaggle、未 push、未改 main。

## 9. 判决与后续

**no-go（低 ancilla 路线）**。精确结论：

1. 两个可用解码器族的 ancilla 都是“48 个贯穿全电路的 24-bit jet word
   + 1–4 个 flag”，slack=0；没有 scratch 可回收，Q 不能靠替换
   noscratch/allocator 降低。
2. 公开族降低 Q 的实测斜率是负收益（883Q 比 889Q 贵 5.4%）。
3. 契约下限 Q=840 也不够：最好的公开 meanT 437.9k 仍比允许值 404.5k 高 8.3%。
4. 要真正达到 3.40e11，需要**换解码器族**：在 Q≤892 时把 meanT 压到
   ≤358.7k，或在 Q≤845 时保持 eae 的 meanT 并去掉 47 个 ancilla。
   这两者都不是本仓库现有源码/工具能完成的门级改写。

建议：把 DQI 资源继续投在“换族/更便宜的反向 uncompute 算法”，而不是
Q 重整；任何新候选仍应以 `Q²·meanT ≤ 2.8542e11` 作为进入全量验证的硬门槛。

## 10. 复现命令

```bash
# worktree 根目录
# 1) 公开 889 原样构建
.venv/bin/python artifacts/20261112_low_ancilla/source/build.py \
    artifacts/20261112_low_ancilla/public_889.kmb

# 2) 883Q baseline
.venv/bin/python experiments/dqi/20261112_low_ancilla/build_variant.py \
    artifacts/20261112_low_ancilla/source/playbook/kit/decoder \
    artifacts/20261112_low_ancilla/source/playbook/kit/decoder/decode.py \
    artifacts/20261112_low_ancilla/baseline_playbook.kmb

# 3) kmb -> kmx（放系统临时目录，约 819 MB，不进 Git）
.venv/bin/python experiments/dqi/20261112_low_ancilla/dump_kmx.py \
    artifacts/20261112_low_ancilla/public_889.kmb

# 4) ancilla 存活区间
.venv/bin/python experiments/dqi/20261112_low_ancilla/ancilla_live.py \
    /private/var/folders/.../T/dqi_low_ancilla/public.kmx 840

# 5) 4096-shot mean T
.venv/bin/python experiments/dqi/20261112_low_ancilla/mean_t.py \
    artifacts/20261112_low_ancilla/public_889.kmb --shots 4096
```

产物：

- 候选/对照：`artifacts/20261112_low_ancilla/{public_889.kmb,
  baseline_playbook.kmb}`（gitignored）
- 数字汇总：`artifacts/20261112_low_ancilla/summary.json`
- 脚本：`experiments/dqi/20261112_low_ancilla/{stage_census.py,
  alloc_probe.py, alloc_timeline.py, ancilla_live.py, build_variant.py,
  mean_t.py}`
