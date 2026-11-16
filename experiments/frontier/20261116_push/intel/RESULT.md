# 公开前沿侦察 / Frontier intel — 2026-11-16 08:00–08:30 UTC

> **09:45 增补**：08:30–09:45 无新公开件（4 个更新全是复现/占位）；榜面并列带从 143 队涨到 187 队，
> 我们 09:06 提交（ref 58424363，`sub1` chem）得 28.09486 / rank 188，未出带。详见 [RESCAN.md](RESCAN.md)。

只读侦察。没有提交、没有改 Kaggle 数据、没有动主仓库其他文件。所有下载物在
`artifacts/20261116_intel/`（untracked）。

窗口：2026-11-16 02:00 UTC → 08:30 UTC。方法：

```sh
~/.local/bin/kaggle competitions leaderboard -c google-verifiable-quantum-circuit-compilation -d   # 落到 artifacts/20261116_intel/lb.zip
~/.local/bin/kaggle kernels list --competition ... --sort-by dateRun --page-size 100 --csv
~/.local/bin/kaggle datasets list -s qcc --sort-by updated --csv
~/.local/bin/kaggle kernels pull / kernels output / datasets download / datasets files
```

**论坛不可达（如实记录）**：`kaggle forums topics list google-verifiable-quantum-circuit-compilation`
在默认 token 和 `access_token_qingyu1232` 下都返回
`403 Client Error: Forbidden ... ListTopics`；`https://www.kaggle.com/competitions/.../discussion`
是 JS 渲染，webfetch 只拿到标题。所以本轮论坛证据用两个代理：
`manwithacat/vqcc-chemistry-negative-results`（ledger 274 行，最后更新 2026-11-15 22:24，**11-16 无新行**）
和 alexchilton 的 public-salt 笔记本。**没有任何 11-16 的论坛帖被读到**。

---

## 0. 结论摘要

1. **公开前沿今天 02:52 UTC 换了一次顶**：`boristown`（暗黑AGI）的 51,854,649 B 真包给出
   invsqrt `f2cdab0b` 44Q / **75,006.3765**、DQI `ccc2ab84` 890Q / **347,375,470,571.73**、
   chemistry npz `bdae290f` 427Q / T=14,712 / **294,762,632.0818**，
   **raw GM 28.0948754**。这就是排名 88–230 那 143 支队并列的 28.09486。
2. 我们现在的 28.09090 用的是 `8b410e77`（75,038.134）和 `f6e12f02`（294,762,732.98），
   两项都比公开最好贵；换掉即到公开天花板（raw +0.00397）。
3. **除此之外没有任何真实公开件**越过 44Q / 890Q / T=14,712 / 294.7626M。
   `leotang09`(07:23)、`seshurajup`(07:18)、`muchat007`(06:18)、`drpatrickchan`(07:42)、
   `junmiaotiao`(08:01)、`atakanaldemir`(08:06) 全部逐字节检查过，见 §2。
4. 榜面 28.09498→28.5977 是一条 **71 队连续斜坡（rank 17–87）**，步长 0.0001–0.06，比“一根 invsqrt 线”
   （+0.216 GM）细得多，和“一个 DQI 量子位”（+0.0211）、“2 个 chemistry Toffoli”
   （+0.00127）同量级。→ 斜坡上的人是在做 **DQI 位宽 / chemistry loader 门数** 的逐个削减。
5. 榜首 30.28512 需要成本乘积 **×0.7984（−20.2%）**；单杠杆全部不够
   （DQI 最低 840Q 只到 29.199；invsqrt 最低 40Q 只到 29.002），**榜首必然至少两项同时改**。
   最贴的一个组合：**DQI 840Q + chemistry T≈13,186**（invsqrt 不动）→ 30.285。
6. 银线不是“稳的”：28.09486 是 143 队并列（rank 88–230），rank 156 在并列带**内部**。
   要稳过必须 raw ≥ 28.09498（比并列带上沿再高 ~0.00011），等价于 chemistry **再省 ~2 T**
   或 DQI **−0.005 个量子位**。公开件里没有这个 2 T。

---

## 1. 当前公开前沿（逐项，精确值）

参考值（官方）：invsqrt `2,076,774.233715`，DQI `24,439,463,583,672.93`，
chemistry `3,355,599,588.3155375`。GM = `(Ri/Ci · Rd/Cd · Rc/Cc)^(1/3)`。

| 任务 | SHA-12 | Q | T / 成本 | 作者 / 出处 | 证据级别 |
|---|---|---:|---|---|---|
| invsqrt | **`f2cdab0b`** | **44** | **75,006.3765**（toffoli_equiv 1704.6889；mean Toffoli 1464.12；33 rotations；worst/tol 0.99956） | maoxin123 的 44Q 改造，boristown 02:52 打包；`kaggle.com/code/boristown/qcc-gap-3-residue-repair-and-c43-native-compiler` | 三方各自跑**未改官方 verifier** PASS（boristown 02:52、maoxin 02:13、junmiaotiao 08:05；alexchilton 03:42 记 75006.37653863191）。本机未跑（200,540,928 shots 属重负载） |
| DQI | **`ccc2ab84`** | **890** | **347,375,470,571.73**（mean T 368,139.80，R=1.19126，0 value / 0 phase @ default salt） | syed3000 v13 890Q 线 + hayatohikawa retention + boristown cmerge/measure-first | 同上，三方 PASS；boristown 自记在 salt `notebook-verification` 有 **1 个 value error**（仍 PASS，成本 +0.46%） |
| chemistry | **`bdae290f`**（= boristown 的 `67d4f935` 包） | 427 | **T=14,712**（loader 4,025/pass），λ_eff 46.92160235，**294,762,632.0818** | marculera 表+loader；boristown 权重 refit | **本机官方 verifier 亲跑 PASS**（见 §2.3），与 alexchilton 03:42 的 294762632.0817748 逐位一致 |
| **GM** | | | **28.0948754**（榜面 28.09486） | | |

次优公开件（都更贵，作对照）：

| 任务 | SHA-12 | 成本 | 差额 |
|---|---|---:|---:|
| invsqrt | `8b410e77` | 75,038.1340 | +31.76（+0.042%） |
| invsqrt | `2c125b39` | 75,082.0925 | +75.72 |
| DQI | `4b350932` | 347,760,709,936.55 | +385.2e9（+0.111%） |
| DQI | `46446af1` | 347,904,227,555.54 | +528.8e9（+0.152%） |
| DQI 889Q | `821bf8d1` | 360,209,905,486.02 | +12.83e9（**+3.69%**） |
| chemistry | `sub1` (`367d46e9`) | 294,762,697.4384 | +65.36 |
| chemistry | `f6e12f02` | 294,762,732.9776 | +100.90 |
| chemistry | `894aef42` (Leo Tang) | 294,762,738.8257 | +106.74 |

独立第三方的完整清单（alexchilton v10，2026-11-16 03:42 UTC，全部跑官方 verifier）：
**61 条 invsqrt / 92 条 DQI（其中 90 条 Q<900）/ 266 条 chemistry**。

```text
invsqrt  entries 61   min Q 44   min cost 75,006.37653863191
DQI      entries 92   min Q 877（90 条 Q<900）  best 347,375,470,571.73 (890Q)；Q<890 最好 360,209,905,486.02 (889Q, +3.69%)
chem     entries 266  min T 14,712   min cost 294,762,632.0817748
chem T values seen: 14712, 14718, 14722, 14728, 14738, 14742, 14750, 14776, 14810, 14840, ...
```

来源：`artifacts/20261116_intel/kernels/alexchilton_28-09-lb-which-circuits-survive-private-salt/`
（行 760、1052 及 `VERIFIED` 字典）。

**榜面结构（同一份 CSV，08:01:15 快照，3154 行）**：

```text
rank   1  30.28512  Entangled Team        2026-11-15 17:15
rank   2  30.13063  Rithvik Redrouthu     2026-11-15 15:23
rank   4  29.98444  aadi_stonks           2026-11-16 07:20
rank   9  29.14389  Some Joint
rank  10  29.01003  Yannan Chen
rank  16  28.65386  Slow and Steady   <- 金线
rank  17  28.59774  Bingran You
rank  87  28.09498  GCYYfun
rank  88..230  28.09486  ×143 队        <- 公开天花板并列带
rank 156  28.09486                       <- 银线落在并列带内部
rank 273  28.09090  ccjjllt（我们，ref 58420406）
```

143 队同分是强证据：**公开榜对同一电路是确定性的**（同一 salt），不是 salt 抽奖；
所有分差都对应真实电路差异。

> 口径更正：`20261116_push/README.md` 与 `TARGETS.md` 把“当前三件”的 invsqrt 写成 `f2cdab0b`，
> 但实际回执（ref 58420406 的 description）和 28.09090 这个分数都对应 **`8b410e77` 75,038.134**。
> 用 `f2cdab0b` 的本地 GM 是 28.09487，会显示 28.09487，不是 28.09090。`f2cdab0b` 是**待换件**，
> 不是已提交件。

---

## 2. 窗口内（02:00–08:30）的新东西，逐字节核过

### 2.1 真包、真改进

| 时间 | kernel / dataset | 实际字节 | 内容 | 判决 |
|---|---|---:|---|---|
| 02:52 | `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler` | submission.zip **51,854,649 B**（49.5 MiB） | `f2cdab0b` + `ccc2ab84` + npz **`bdae290f`** | **新冠军包**（GM 28.0948754） |
| 05:53 | `neoluxlee/vqcc-verified-portfolio-reproduce-20261116-v2` | 输出为 42 成员重建包 **51,921,130 B**（18 payload + 24 NOTICE） | `f2cdab0b` + `ccc2ab84` + `bdae290f` | 又一个独立复现；自报 28.09486 / rank 86/3146；两额外 salt 各 102,400 shots **0 错**，另有一个公开 salt **1 个 value error**（仍 PASS） |
| 02:13 | `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` | **51,854,536 B** | 同上但 npz `f6e12f02` | f2cdab0b 的出处 |
| 07:18 | `seshurajup/quantum-circuits-3-tasks-lb-27-2900` | **51,854,743 B** | `f2cdab0b` + `ccc2ab84` + `bdae290f` | 与 boristown 同件 |
| 07:23 | `leotang09/vqcc-t7421-submission` | **51,839,530 B** | `f2cdab0b` + `ccc2ab84` + npz `894aef42` | chem 反而贵 5.85 |
| 07:42 | dataset `drpatrickchan/qcc-chem-sub1-weights` | **1,150,946 B** | npz `367d46e9` | `sub1`，我们亲跑 294,762,697.4384 |
| 08:01 | dataset `junmiaotiao/qcc-frontier-20261116n` | **20,162,903 B** | `f2cdab0b` + `ccc2ab84` + `f6e12f02` | 与旧包同件，chem 不是最好 |
| 06:17 | dataset `muchat007/c44-universal-xor-chemistry-compiler` | **1,447,077 B** | 自己的 J5 emitter，chem **317,442,845.48**（T=15,844） | 更差；其 npz = `bdae290f` |

`f2cdab0b` 是新东西：44Q / 75,006.38，比 8b410e77 便宜 31.76。作者链条
syed3000 → ahqirg 64 行表 → maoxin123 的 44Q 重调度（退休两条系数线、表读入吸收 value 寄存器、
phase 阶段联合退出、除法清理分段），Ozer 角度 refit。

`bdae290f` 是新的 chemistry 权重：boristown 02:52、seshurajup 07:18、muchat007 06:17 三个包的 npz 都是它；
leotang09 07:23 用的是另一个 `894aef42`（更贵 5.85）。
它是**只改 `submission.npz` 的权重 refit**，表、字、15 个 loader、angle 电路全部不动。

### 2.2 空包 / 更差 / 无提交

| 时间 | 对象 | 结果 |
|---|---|---|
| 08:06 | `atakanaldemir/qcc-terminal-readout-and-phase-folds` | 无 submission.zip；`joint226_scan_audit.json` 对 `ccc2ab84` 做 fusion/hmr/commute/merge 四段扫描，**saved_static_Toffoli 0**（`EXACT_DIRTY_TARGET_KRAUS_IDENTITY_PASS...`），并声明 `new_competition_submission: false` |
| 07:09 | `mizeroluckygall/quantum-circuits-exact-toffoli-scan-of-loaders` | `scan_report.json`：15 个 loader 共 **4,025 T/pass**，**correct model removable = 0/loader**；zero-word 模型 40 个候选全删后官方 verifier **FAIL**，`improved: false`，输出原包 |
| 02:10 | `masumhuq/qai-per-task-max-composite-28-09` | invsqrt `a0015c5b` **75,038.75**（更差）；chem/DQI 同我们 |
| 03:56 | `kawh1111/qcomp-harvest-2806` | 只重打包 hayatohikawa 28.066 |
| 07:25 | `ozertuu/quantum-ai-fast-runner-starter-notebook` | 56,360,753 B 真包，但内容仍是 27.31 时代（`1ba197b0`/`821bf8d1`/4030 chem） |
| 06:50 | `yorixum/quantum-circuits-iso-gap-dqi-h5` | 已知 `NameError`，从未跑通 |
| 06:59/05:51/04:17/04:09/04:03 | mzishran / radheshver / derrickirons / evgendvorkin / ayman | 无 submission，纯分析/EDA（mzishran 只放了一个 881 B 的 reference_v2.kmx） |

**教训（与 11-15 相反）**：`list_notebook_files` 的 size 完全不可信。
本轮 `leotang09`(列 850 B → 实际 51,839,530 B)、`seshurajup`(872 B → 51,854,743 B)、
`ozertuu 28-091`(872 B → 51,856,466 B) 都是真包；`boristown` 上一轮被记成 680 B 占位，
今天 02:52 的同名 kernel 是 51,854,649 B 真包。**只能下载后看字节 + hash。**

### 2.3 本机官方 chemistry verifier 四连跑（同一套 loader，只换 npz）

```sh
PYTHONPATH=data/competition/verifiers OMP_NUM_THREADS=4 \
  uv run python data/competition/verifiers/dfthcsos/verify.py <dfthcsos dir>
```

| npz SHA-12 | 来源 | score | λ_eff | T | Q |
|---|---|---:|---:|---:|---:|
| **`bdae290f`** | boristown 02:52 / seshurajup 07:18 | **294,762,632.0817748** | 46.92160235 | 14,712 | 427 |
| `367d46e9` | drpatrickchan `sub1` | 294,762,697.43843937 | 46.92161275 | 14,712 | 427 |
| `f6e12f02` | 我们现用 / junmiaotiao N | 294,762,732.9775791 | 46.92161841 | 14,712 | 427 |
| `894aef42` | leotang09 07:23 | 294,762,738.8257419 | 46.92161934 | 14,712 | 427 |

全部 `PASS`，error_1/error_2 都是 0.0199999985、E_gap 3.9148980015。四次都是 T=14,712、Q=427，
差别只在 λ_eff 的第 5–7 位 → **chemistry 公开空间确实只剩 10⁻⁷ 量级**。
本机用 PyPI 原生 kickmix（未用 Kaggle Linux 的 `kickmix.so`），与 Kaggle 侧 alexchilton 的
294762632.0817748 逐位一致，可信。

---

## 3. 榜首分数反推

### 3.1 公式与基线

公开天花板 `GM₀ = 28.0948754`（f2cdab0b / ccc2ab84 / bdae290f），成本乘积
`Ci·Cd·Cc = 7.680151e24`。目标 GM 需要成本乘积 **乘以** `P = (GM₀/GM)³`。
“等效”列都是**只动这一项、另两项保持公开最好**时的值。

| 目标 GM | 需要 P | 单项统一降 | DQI Q（T 不变） | DQI T（Q 不变） | invsqrt Q（C 不变） | invsqrt C | chemistry T（Q,λ 不变） |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30.28512 榜首 | 0.7984 | −7.23% | **795.2** ✗ | 293,904 | **35.13** ✗ | 1360.9 | **11,745** |
| 30.13063 rank2 | 0.8107 | −6.76% | 801.3 ✗ | 298,449 | 35.67 ✗ | 1382.0 | 11,927 |
| 30.00881 rank3 | 0.8206 | −6.38% | 806.2 ✗ | 302,098 | 36.11 ✗ | 1398.9 | 12,073 |
| 29.98444 aadi | 0.8226 | −6.30% | 807.2 ✗ | 302,835 | 36.19 ✗ | 1402.3 | 12,102 |
| 29.97900 rank5 | 0.8231 | −6.28% | 807.4 ✗ | 303,000 | 36.21 ✗ | 1403.1 | 12,109 |
| 29.57281 Slingshot | 0.8574 | −5.00% | 824.1 ✗ | 315,658 | 37.73 ✗ | 1461.7 | 12,615 |
| 29.45707 rank8 | 0.8676 | −4.62% | 829.0 ✗ | 319,393 | 38.17 ✗ | 1479.0 | 12,764 |
| 29.14389 Some Joint | 0.8959 | −3.60% | 842.4 ✗ | 329,801 | 39.42 ✗ | 1527.2 | 13,180 |
| 29.01003 Yannan | 0.9083 | −3.15% | 848.2 ✗ | 334,387 | 39.97 ✗ | 1548.4 | 13,363 |
| 28.65386 **金线 rank16** | 0.9426 | −1.95% | **864.1** | 347,012 | **41.47** | 1606.9 | **13,868** |
| 28.59774 rank17 | 0.9482 | −1.76% | 866.6 | 349,059 | 41.72 | 1616.3 | 13,949 |
| 28.54484 rank20 | 0.9535 | −1.58% | 869.0 | 351,003 | 41.95 | 1625.3 | 14,027 |
| 28.31547 rank24 | 0.9768 | −0.78% | 879.6 | 359,603 | 42.98 | 1665.2 | 14,371 |
| 28.24143 rank31 | 0.9845 | −0.52% | 883.1 | 362,438 | 43.32 | 1678.3 | 14,484 |
| 28.16205 rank40 | 0.9929 | −0.24% | 886.8 | 365,512 | 43.69 | 1692.5 | 14,607 |
| 28.11037 rank60 | 0.9983 | −0.06% | 889.3 | 367,531 | 43.93 | 1701.9 | 14,688 |

✗ = 低于契约下界：DQI 70 个 syndrome 寄存器 × 12 bit = **840Q 硬地板**；invsqrt Q 不可能低于
当前 44（见 §4）。所以**单杠杆解释不了 29.2 以上**：
DQI 就算做到 840Q 地板也只到 **29.199**；invsqrt 做到 40Q 只到 **29.002**。

### 3.2 单点预测（另两项不动）

| 改动 | 新 GM | 增量 |
|---|---:|---:|
| DQI 889Q | 28.116 | +0.021 |
| DQI 880 / 870 / 860 / 850 / **840** | 28.307 / 28.524 / 28.745 / 28.970 / **29.199** | +0.21 / +0.43 / +0.65 / +0.88 / **+1.10** |
| invsqrt 43 / 42 / 41 / **40** | 28.311 / 28.534 / 28.764 / **29.002** | +0.22 / +0.44 / +0.67 / **+0.91** |
| chemistry T 14,500 / 14,000 / 13,500 / 13,000 / 12,000 | 28.231 / 28.563 / 28.912 / 29.278 / 30.069 | +0.14 / +0.47 / +0.82 / +1.19 / +1.98 |

**门级灵敏度**（这是本轮最有用的新数字）：

| 一个单位 | GM 变化 |
|---|---:|
| invsqrt −1 qubit | **+0.2161** |
| invsqrt −1 Toffoli-equivalent | +0.00214 |
| DQI −1 qubit | **+0.02106** |
| DQI −1,000 T | +0.02548 |
| chemistry −1 T（总，forward+reverse 各算一次） | **+0.000637** |
| chemistry −10 T / −100 T | +0.00637 / +0.06395 |
| chemistry λ_eff −1 ppm | +0.0000094 |

→ **chemistry 的每一个 Toffoli 值 +0.00064 GM，是 DQI 每个量子位的 1/33、invsqrt 每根线的 1/339，
但 chemistry 一次只能省 1–2 个门时它仍然最便宜**：并列带宽度只有 ~0.00011，
**省 2 个 Toffoli 就够跳出 143 队并列**（0.19 T 就够，1 个门 = 2 T）。

### 3.3 斜坡拟合（假设写在前面）

假设三件都取自公开天花板，只让一个参数变：

- **H1：DQI 整数位宽**（T=368,139.80 固定）。rank 16–87 的 72 个分数，到最近整数 Q 的
  残差中位数 **0.0035**、最大 0.0102（相邻 Q 间隔 0.0211）。
- **H2：invsqrt 整数位宽**（C=1704.6889 固定）。同样 72 个分数，残差中位数 **0.0201**、最大 0.1102
  （相邻 Q 间隔 0.2161）。

H1 明显更贴，但 0.0035 相对步长 0.021 只是“不矛盾”，不是证明。真正可靠的结论是**粗粒度**：
斜坡步长 0.0001–0.06 **远细于** invsqrt 一根线（0.216），所以：
**28.095→28.60 这段没有一支队是靠“少一根 invsqrt 线”上去的**；它只能由
DQI 位宽（0.021/位）、chemistry loader 门数（0.0013/2 门）、chemistry λ refit（10⁻⁵ 级）
这三类小步组成。invsqrt 宽度改进会直接跳到 28.31 / 28.53 / 28.76（rank 24/20/14 附近），
在斜坡上只会出现 4 个离散台阶，**不能解释 72 个连续分数**。

### 3.4 榜首/前四的可行分解（多杠杆）

P=0.7984。下面每个都精确到 ±0.02：

| 组合 | 乘积 | 预测 GM |
|---|---:|---:|
| DQI 840 + chemistry T=13,186（invsqrt 不动） | 0.891×0.8963 | **30.284** |
| DQI 840 + invsqrt 41 + chemistry T=14,151 | 0.891×0.932×0.962 | **30.284** |
| DQI 850 + invsqrt 42 + chemistry T=13,491 | 0.912×0.955×0.917 | **30.284** |
| DQI 860 + invsqrt 41 + chemistry T=13,500 | 0.934×0.932×0.918 | **30.285** |
| DQI 840 + invsqrt 42（chem 不动） | 0.891×0.955 | 29.655 |
| DQI 840 + invsqrt 40（chem 不动） | 0.891×0.909 | 30.142 |
| chemistry T=11,745（另两项不动） | 0.798 | **30.285** |

**最贴我们已有研究的一条**：`DQI 840 + chemistry T≈13,186` 正好等于我们
`docs/research-map.md` 里对 R=5/B=143/C=75 形状 + Maoxin loader 的投影 **T≈13,219**。
也就是说，如果某队真的做成了 (6,143,64)/(5,143,75) 这一族，chemistry 一项就能把 28.09 推到 29.12，
再配 840Q DQI 就是 30.2–30.3。这条线我们当时因为“本地 loader 比 Maoxin 差 26%”“R=5 的 B 必须
涨到 180–255”而关闭——**但那是本地构造器的限制，不是数学上的限制**。

另一个数值得记：金线 28.65386 ⇒ DQI **864.1Q**（T 不变）。864 = **840 + 24**，
恰好是“契约地板 + 一个 24-bit external jet word，0 个额外 ancilla”。
这和我们 `dqi_ancilla/REPORT.md` 的“49 = 24+1+24、五个见证点各自顶到 889”是同一张图的反面。
**假设**（未证实）：前 15 名里有队伍把重复的 24-bit 见证减到 1 个。
这一条如果成立，DQI 位宽路线的收益上限就不是 +0.02，而是 +0.56（金线）。

---

## 4. 任务点名的四条线索，逐条证据

### 4.1 DQI Q≈840 —— 公开无证据，且公开最优在 890

- alexchilton 的 92 条官方验证 DQI：**min Q = 877**；Q<890 的最好是 **889Q / 360.2e9（+3.69%）**；
  再往下 889Q/360.3e9、889Q/360.5e9。
- atlas `circuits.csv`（1840 行，11-15 16:19 扫描）：DQI 最低 Q=873（`77947749aa4e`, T=1,069,899），
  按 R·Q²·T 折 9.7e11，是公开最好的 2.8 倍；888Q `2ed7ccf189f1` T=443,898 ⇒ 4.17e11（+20%）；
  883Q `80897db7042f` T=485,604 ⇒ 4.51e11（+30%）。
- 我们自己的账：`dqi_ancilla/REPORT.md` 五见证平台；NR-0234 “Toffoli-weighted mean width 884.7Q,
  336k of 395.6k Toffolis above 869Q；narrower layout 1.03×（best 0.949×）”；NR-0259/0260
  （889→888 要 ~1,019–1,650 次峰值运行里找 idle wire，或 ~3,100 T 重建，对 ~860 T 盈亏）。
- **结论**：840Q 公开不存在；公开能买到的最低价是 890Q。谁先做出 870/860，谁就白拿 +0.43/+0.65。

### 4.2 invsqrt Q 40–42 —— 公开无证据，公开最优 44

- alexchilton 61 条：**全部 Q=44 或 46**，min cost 75,006.3765。
- atlas 65 条（11-15 扫描，早于 44Q 公开）：min Q=46，min T=1,359。
- 我们自己的判决：`qcc-inv45c-census` 生成器只写 46/47/48 三个 body；
  `qcc-inv45d-stack` 的 Q45 卡在 `engine/fusion/arithmetic.py:38` 一条线；
  `qcc-inv45t-sevenand-cpu` + `qcc-inv45u-sevenand-atlas`：0–7 AND 阶梯十条线全空
  （POSITIVE_CONTROL 200/200、300/300，是测量不是失效）。
- **结论**：40–42 公开不存在，而且**比 DQI 难得多**（要新合成 body，不是重调度）。但收益也大：
  一根线 +0.216，三根线就 +0.67（≈金线）。

### 4.3 chemistry T 12–13k —— 公开无证据，公开最优 14,712

- alexchilton 266 条官方验证 chemistry：**min T = 14,712**，T 只出现在
  {14,712, 14,718, 14,722, 14,728, 14,738, 14,742, 14,750, 14,776, 14,810, 14,840, ...}。
  266 条全是同一批 4,025/pass loader 或更老的 4,030–4,089 loader。
- 公开 loader 史：4,123 → 4,097 → 4,089 → 4,038 → 4,033 → 4,030 → **4,025**（每步 −1~−13 T/pass）。
- `mizeroluckygall` 的**精确**扫描（全 2,048 地址真值表 + GF(2) 消元）：
  15 个 loader 合计 **4,025 T/pass**，**correct（dirty-word）模型下可删 0 个**；
  zero-word 模型的 40 个候选全删 → 官方 verifier **FAIL**。→ 清理路线已死。
- 计数下限（manwithacat ledger NR-0268）：每电路 291 shipped vs **270 counting floor**
  （190 paired products + 80 caches），whole-line ceiling **−1.8% chemistry / +0.6% GM**；
  mockturtle/ANF 综合（NR-0273）无收益。
- 我们自己的账：B 轴（B=143→129）实测关闭（B=129 连续 e2 19.83 mHa，量化后 >25）；
  C 轴 (143,40)=20.103、(143,36)=29.127 连续值，Adam 补不上；J 轴最优 J=7 只 −1.15%。
- **结论**：T=12–13k 需要**换 shape/factorization**（R=5 或 R=6 + 大 C + 新 basis + 新 loader），
  不是优化现有 4,025。公开一件都没有，正因如此它才是最大的一块。

### 4.4 新算法族 —— 只有一个“新名字”，没有新电路

- `boristown` 标题里的 **“C43 native compiler”** 没有兑现：他 02:52 的真包 chemistry 仍是
  4,025/pass、T=14,712、C=44 表。C43 只是标题。
- `muchat007` 06:18 的 **“C44 universal XOR with clean workspace”** 是今天唯一真正新的 emitter：
  自己实现 top-bit gauge + cached address monomials，J5 族 **317,442,845.48**（T=15,844），
  J4 318,376,491.52，都更贵；他自己的结论是 “Further output-group and address-split screens
  did not beat J5”。附带一个可用的审计结论：**inherited chemistry family 在“任意 target word”
  审计下会失败**（官方 verifier 只要求 reachable 状态，所以不影响得分）。
- `atakanaldemir` 08:06 的 joint226（fusion / HMR / commute / merge）对 `ccc2ab84`
  **0 saving**，并明确 `new_competition_submission: false`。
- DQI 新族：唯一公开的“别的族”仍是 Gu/Kemeny/Yelin/Lukin arXiv:2610.22367 的 442k T / 1,837Q，
  Q²T 比我们差；我们的 half-gcd / BM / trace / Welch 下界账（`docs/research-map.md` 第十九轮）
  已经全部 no-go。
- **结论**：今天没有新的 invsqrt 族、没有新的 DQI 族、没有低于 4,025 的 loader。
- 另一个负面结果：榜首/次席/第四名下 8 个账号（`jackvd`、`jsday96`、`tonylica`、`yeoyunsianggeremie`、
  `corerazed`、`rithvikredrouthu`、`taiseiu`、`aadistonks`）逐个用 `kernels list --user` 查过，
  **没有任何本赛题的公开 notebook**（他们的 kernel 全属别的比赛）。29+ 段只有榜面分数，没有可读电路。

---

## 5. 三条最值得投入的方向（按 期望收益 / 公开缺口）

### ① chemistry 换 shape（R=5/6 + 大 C），目标 T 13.2–13.5k —— 期望 +0.82…+1.19
- 单点：T=13,500 → **28.912（+0.82）**；T=13,000 → **29.278（+1.19）**；
  我们自己的 R=5/B=143/C=75 投影 T≈13,219 → **29.12（+1.02）**。
- 为什么公开件没有：266 条公开 chemistry 全部 T≥14,712；公开出现过的 shape 只有 R=4/8/9/10
  四族，R=5/6 从未出现（R=4 被迫 B=255 才过门）。
  清理路线已被 `mizeroluckygall` 的精确扫描判死（0 可删门），所以**别人也没法用 4,025 的旧件
  蹭到这块**——必须像我们一样重训 basis+loader，这正是护城河。
- 关键风险（必须先解决）：R=5 的 8-bit 量化 e2 地板。公开 R=4/B=255/C=120 过 19.9 mHa 说明
  “小 R 必须大 B”；若 B 涨到 180–255，rows=76+R·B 反而变高，T 收益消失。所以先做
  **B=143 下 R=5/6 的连续 e2 曲线**，只有 e2(连续)+5.2 mHa(量化) ≤ 19.9 才继续。
- 次优子方向：Maoxin 式 7-bit block + pair-cache loader 在 **791 行**（R=5）上的实例化，
  我们旧账投影 211/电路（vs 1,220 行的 292）。这是把 T 拉到 13.2k 的唯一已知构造。

### ② DQI 位宽 890→870/860（T 中性）—— 每位 +0.021，10 位 +0.21，20 位 +0.43
- 单点：880 → **28.307**；870 → **28.524**；860 → **28.745**；840 → **29.199**。
- 为什么公开件没有：92 条公开 DQI 里 Q<890 最便宜 360.2e9（+3.69%），883Q 要 4.5e11（+30%）；
  143 队并列在 890Q 这一件事本身，就证明**没有任何队公开发布过更便宜的 sub-890**。
- 可行性：`dqi_ancilla` 的五见证平台说明单点补丁不改 Q；`NR-0259/0260` 说明 889→888
  需要 ~3,100 T 重建 vs ~860 T 预算。所以**不是重编号，是重写调度**（release-and-recompute）。
  建议先做 888 的完整构建 + 全 shots，验证“ΔT≤862”能否兑现；成功一次就有了可复制的模板。
- 注意：榜单本身说明有人已经在 866Q 附近（28.59774 ≡ 866.6Q @ T 不变）。若 §3.4 的 864=840+24
  假设成立，做到 870 就够进前 20。

### ③ invsqrt 44→42/41 —— 每根线 +0.216，两根 +0.44，三根 +0.67（≈金线）
- 单点：42 → **28.534**；41 → **28.764**；40 → **29.002**。
- 为什么公开件没有：61 条公开 invsqrt 全是 44Q/46Q；生成器只写 46/47/48 body；
  Q45 卡在一条 `alloc_qubits(1)`；0–7 AND 全域为空。
- 现实评估：这是三条里**最难**的（要新合成 body + 重搜 loader certificate），
  但也是唯一“一根线就 0.22”的杠杆。若目标是金线，44→42 + chemistry T=14,000
  （0.955×0.9516=0.909）→ 29.00；单靠 42 只有 28.53。
- 折中：先做 **Q=43**（+0.216，等于 10 个 DQI 位），盈亏平衡 C 只需 ≤1744.7（+40 门）。

### 立刻可做、零风险（不属于研究线）
把 invsqrt 换成 `f2cdab0b`（−31.76）、chemistry 换成 `bdae290f`（−100.90）：
raw **28.0948754**，榜面 28.09486–28.09487，rank 88–230（并列带）。
这是**当前唯一能拿到的公开分**，但要清楚它不保证银牌（见 §6）。

---

## 6. 风险与口径（写给主 session）

1. **银线在并列带内部**：28.09486 覆盖 rank 88–230（143 队），银线 rank 156 在其中。
   榜面是 5 位截断（我们 28.0909082 → 28.09090，可验证），所以要**严格高于** 28.09486
   必须 raw ≥ 28.09487（最好 ≥28.09498 才稳过 rank 87）。这需要成本再降 **0.0013%**，
   等价 chemistry **−0.19 T**（取整后 2 T）或 DQI **−0.005 Q**。公开件里没有。
   → 换件提交是“进并列带”，不是“锁银”。
2. **DQI `ccc2ab84` 的 salt 风险**：作者自记在 salt `notebook-verification` 出现 **1 个 value error**
   （仍 PASS，R 抬高 → 成本 +0.46% → GM −0.15% → 28.052）。alexchilton 对同线 821bf8d1 测 8 salts：
   4/8 有 1 个错误、成本 360.21→361.86e9（+0.46%）。**143 队并列意味着大家共担这个风险**，
   所以相对名次不变，但绝对分会掉。
3. **invsqrt `f2cdab0b` 的余量很薄**：worst/tol **0.99956**（1ba197b0 是 0.99867，余量是它的 3 倍）。
   private salt 下失败概率不能忽略；一旦 FAIL 整份提交 0 分。这是“只换 invsqrt”的隐性代价。
4. **公开榜是确定性的**：143 队精确同分（28.09486）说明同一电路同一 salt 分数完全可复现，
   不存在“多交几次抽好 salt”。我们的 28.09090 vs 天花板 28.09486 是**真实的 0.004 差距**，不是抽签。
5. **口径**：本报告所有“验证”分级写明——§2.3 是我们本机官方 verifier 亲跑；
   invsqrt/DQI 的最好值只有作者 + 两个第三方（alexchilton 03:42、junmiaotiao 08:05）的 PASS，
   **本机没有重跑**（200,540,928 shots / 102,400 shots 不在本机做）。论坛没读到（403）。

---

## 7. 证据文件（都在 `artifacts/20261116_intel/`，untracked）

```
lb.zip / google-...-publicleaderboard-2026-11-16T08:01:15.csv   3154 行排行榜快照
kernels/                                                         拉下来的 notebook 源码+转文本
  alexchilton_28-09-.../                                        61/92/266 条官方验证清单（关键）
  drpatrickchan_...sub1.../                                      sub1 声明与三条 salt
  junmiaotiao_qcc-portfolio-assembly/                            28.09486 组装与逐件 SHA
  maoxin123_...44-qubit-invsqrt.../                              f2cdab0b 出处
  mizeroluckygall_...toffoli-scan.../                            loader 精确扫描源码
  muchat007_c44-.../                                            新 emitter（更差）
outputs/
  boristown_.../submission.zip            51,854,649  f2cdab0b+ccc2ab84+bdae290f
  maoxin123_.../submission.zip            51,854,536
  ozertuu_...28-091/submission.zip        51,856,466  8b410e77+ccc2ab84+f6e12f02（我们现用）
  leotang09_.../submission.zip            51,839,530  ...+894aef42
  seshurajup_.../submission.zip           51,854,743  ...+bdae290f
  mizeroluckygall_scan/scan_report.json    improved=false，correct-model removable=0
  atakanaldemir_.../joint226_scan_audit.json  saved_static_Toffoli=0
ds/
  jn/                     junmiaotiao N（f6e12f02）
  sub1/                   drpatrickchan sub1
  c44/                    muchat007 包（RESULTS.md 317.44M）
  neg/                    manwithacat negative-results（ledger 274 行 + dqi-failure-atlas）
  circuits.csv            atlas 1840 行
unz/{leotang,seshurajup,sub1}/  解包后逐件 hash 的对照
```

复现用的两条命令：

```sh
# 逐件 hash（本轮所有“真/假”判断都出自这一步）
unzip -p submission.zip invsqrt.kmb | shasum -a 256 | cut -c1-12
# chemistry 官方 verifier（本机 PyPI kickmix）
PYTHONPATH=data/competition/verifiers OMP_NUM_THREADS=4 \
  uv run python data/competition/verifiers/dfthcsos/verify.py <dir>
```
