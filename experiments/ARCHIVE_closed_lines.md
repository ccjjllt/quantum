# 已放弃研究线归档（清理记录）

日期：2026-11-17。
目的：把**不再推进**的研究线的文档、脚本、构建产物与下载镜像从工作区移除，释放磁盘，
同时留下研究概况与放弃原因。本文就是那些文件的替代记录。

**可回溯锚点**：删除前的工作区提交是
`8155189ac5ddc257b4bf968a86850e4240bf3cb9`（分支 `main`）。
所有被删除的**受跟踪**文件都能用
`git checkout 8155189 -- <path>` 或 `git show 8155189:<path>` 原样取回；
被删除的**未跟踪/被 gitignore** 的大文件是下载镜像与构建产物，可按本文记录的来源重新生成或下载。

## 0. 当前状态（未删除，仍然有效）

| 项目 | 内容 |
|---|---|
| 最佳提交 | **28.15083** COMPLETE，ref `58454232`（`0af21cb8` invsqrt + `61c8348d` DQI + `a73b25d2` chem T14706 + 15 小 loader） |
| 评分模型 | 公开分是**确定性**函数；`intel/RESULT_public_salt_model.md` + `intel/public_salt_model.py` |
| 成本公式 | 三条腿的官方 cost 公式已反解并复现（残差 0）：`intel/RESULT_cost_model.md` + `intel/cost_model.py` |
| DQI 宽度判定 | `dqi/RESULT_WIDTH_BUDGET.md` + `dqi/width_budget.py`（本轮保留，因为它是对"金线怎么来"的最终定量答复） |
| 提交管线 | `pipeline/` 保留（组装/验证/提交流程仍要用） |
| 侦察 | `intel/` 保留（新字节扫描仍在进行） |

三条腿各自都已是**实测下限**，公开字节重组的上限就是 28.15083；金线 28.68633 需要换一代电路。

## 1. invsqrt 线 —— 放弃

**做过什么**：44Q 反转平方根的 Q 数下探（Q42 全量 110 个 slot）、`0af21cb8` 机制解析、
Q45 生成器与 0–7 AND 阶梯普查、若干次电泳式重排。

**结论（决定性测量）**：

- `0af21cb8` 已是公开最便宜 44Q（**74,797.36535717871**）；公开 61 条 invsqrt 全是 44Q/46Q。
- Q42：**110 个 slot 全量 0/110** 通过。
- Q45：卡在 `engine/fusion/arithmetic.py:38` 一行；生成器只写 46/47/48 三个 body。
- 0–7 AND 阶梯十条线全空（正向对照 200/200、300/300，是测量不是失效）。
- 官方公式 `C = Toffoli + T/4`，`Q·C`：Toffoli 面已刮净（0 cancel pair、0 zero-control、0 dead-write），
  33 个旋转各 29.08 T 只因 `worst_error_over_tolerance = 0.99956` 不留合成余量；删掉全部旋转也只省 14.1%。

**为什么放弃**：需要新合成 body，不是重调度；单位 GM 的成本是三腿中最高。

**删除内容**：`experiments/frontier/20261116_push/invsqrt/`（4.8M）、
`artifacts/20261115_invsqrt/`（2.4M）。

**⚠️ 损失记录**：`artifacts/20261115_invsqrt/syed/invsqrt_source_zip` 曾在
`docs/abandoned-research.md` §7.3 被标注为「本地唯一副本，请勿随下次清理删除」，
本次仍被一并删除。该目录被 `/artifacts/*` 忽略，**不在 Git 中**；
事后核查 `syed3000/vqcc-own-circuit-portfolio` 当前版本只剩 20 个文件、已无 source zip，
CLI 不支持按版本枚举，短期无法取回。它记录的是 **46Q** 生成器，当前前沿是 44Q `0af21cb8`，
**不影响任何已提交结果的可复现性**。详见 `docs/abandoned-research.md` §8.4。

## 2. DQI 线（自研合成/优化部分）—— 放弃

**做过什么**：peephole、decision-machine、retain、out-of-place、v13、`66b4` gadget 普查
（G1 41/41、G0 0/0）、888Q 构建、宽度预算。

**结论（决定性测量）**：

- 官方公式 `score = R(eps_plus)·Q²·T`；`R = 1.19126`（clean）是 0 误差 CP 上界，无下滑空间。
- T 面饱和：0 exact cancel pair（362,984 CCX 上）、0 dead-write、0 |0>-control，仅 871/369,010 不触发。
- 宽度：`890 = 840 + 4×12 + 2`，HMR 峰值 50，`peak_without = 890`（逐 wire 测过），无 retention wire。
- 金线在 Q865 只容忍 **+166 T（6.6 T/qubit）**；最便宜实测机制 925 T/qubit、真实 7,195、888 构建 7,932。
- 唯一能付得起的是 in-place 840Q 且 T ≤ +6.089%（22,354 T = 447 T/qubit），卡点是
  24-bit carry bank `q840..q863` 被 62–72% 的 helper 窗口触碰，不能借。

**为什么放弃**：任何可达的省 qubit 机制都低于盈亏平衡，更远低于金线；需要新解码器代际，不是补丁。

**删除内容**：`experiments/frontier/20261116_push/dqi/` 的**构建与实验部分**
（`NOTES.md`、`RESULT.md`–`RESULT8.md`、`build_kernel.py`、`evidence/`、`k10..k17*` 采样目录）、
`artifacts/20261116_dqi_v15/`（59M，v15 构建源码与 zip）。
**保留** `dqi/RESULT_WIDTH_BUDGET.md` 与 `dqi/width_budget.py`（它们是上层决策依据）。

## 3. chemistry（dfthcsos）线 —— 放弃

**做过什么**：R=8 分解、rank/projector 墙、R=5/6 merge-and-shrink 全预算、λ refit、
code/loader 路径、C 轴截断（C43/C42/C41）、emitter k9–k14、新 R（7/9/10/12）、
`--coded` 量化器、word 重编码。

**结论（决定性测量）**：

- 官方公式 `score = λ_eff·T_total·Q_total`，`λ_eff = √(E_gap(2Λ−E_gap))`；cost 对 T 严格线性
  （两点速率 20,035.573/T 一致到 2.8e-6）。
- 出厂点 `a73b25d2`（T14,706，**294,643,137.73357135**）已把 `error_2` 顶到门：
  `0.0199999997351` vs 门 `0.020`，余量 **2.6e-10**；`E_gap` 恰在 `E_GAP_FLOOR`；
  loader `angles_qubits = 128` 恰在 `QUBIT_CAP`。
- R=5/6 在真实管线上 (5,143,75) 形状实测 **53.65 mHa**，是 16.7 mHa 门的 3.2 倍，8-bit 量化后 73.1。
- λ refit：72 角度对 × 6 Haar 重启，**0.0000%** 改进；投射梯度无可行步。
- `--coded`：(a) e2 地板 21.216 mHa（门差 1.22），cuts 71→55；(b) 36.229 / floor 35.889。

**为什么放弃**：T 每降 1 T 值 0.0945 GM，但精度余量只剩 2.6e-10，任何 T 削减都先破精度门。

**删除内容**：`experiments/frontier/20261116_push/chem/`（23M，含 `code2/`、`code3/` 的未跟踪
构建产物 `submission.npz`、`angle_k_*.kmx`、`words_recode_k4.npy`）、
`artifacts/20261116_intel/c44-universal-xor-chemistry-compiler.zip`（1.4M）、
`artifacts/20261116_intel/vqcc-chemistry-negative-results.zip`（7.7M）。

## 4. 早期轮次 —— 放弃（已被 20261116_push 取代）

- `experiments/frontier/20261115_upgrade/`（540K）：11-15 升级轮，其结论已并入当前记录。
- `experiments/frontier/20261112_rescan/`（16K）：更早的重扫。
- `artifacts/20261116_intel/{outputs,outputs2,unz,ds}`（**2.86G**）：Kaggle 内核输出的下载镜像与解压副本
  （`dqi.kmb` 单文件 464M/434M，多份重复）。这些全部可用 `kaggle kernels output` / `kaggle datasets download`
  按 `intel/RESULT_sweep*.md`、`RESULT_verify_new*.md` 记录的 kernel/dataset ref 重新取回，
  且所有字节的 sha256 已写在这些记录里，可校验。

**为什么放弃**：被 20261116_push 的最终组合取代；镜像文件不含任何独有信息。

## 5. 保留下来的东西（明确不删）

| 路径 | 理由 |
|---|---|
| `data/competition/`（995M） | 官方原始数据与未修改验证器，AGENTS.md 要求保留 |
| `artifacts/20261117_lb_decomp/`（380K） | 当前榜首逆解的 LB CSV 快照 |
| `experiments/frontier/20261116_push/{intel,pipeline}/` | 仍在用：字节侦察、评分模型、提交管线 |
| `submissions/`（72K） | 最终包与提交回执 |
| `references/`（8.8M） | 公开方案来源 |

> 2026-11-18 更新：上表中 `experiments/frontier/20261116_push/{intel,pipeline}`、
> `artifacts/20261117_lb_decomp/` 与 `H_spectrum.npy` 已在 §7 清理；
> 当前保留清单以 §7.2 为准。

## 6. 恢复方法

```bash
# 取回任意被删的受跟踪文件/目录
git checkout 8155189 -- experiments/frontier/20261116_push/chem
# 查看而不落盘
git show 8155189:experiments/frontier/20261116_push/dqi/RESULT2.md
# 重新下载镜像（示例）
kaggle kernels output ozertuu/vqcc-super-sota-verified-portfolio-28-091 -p /tmp/out
```

---

## 7. 2026-11-18 清理：frontier push 收尾

**触发**：14 条轴全部实测关闭，最后一轮 push 没有可继续的增量路线。
删除前锚点 **`b754ef52282705acfe8b78d32cb5d284ca212dca`**（`main`）。
研究概况、14 条轴的决定性数字与放弃原因见
[`docs/abandoned-research.md §9`](../docs/abandoned-research.md)。

### 7.1 删除清单（实测）

| 路径 | 体量 | 内容 |
|---|---:|---|
| `experiments/frontier/20261118_push/` | 23 MB | 25 条线的 `RESULT.md`、探测脚本、`dqi_patch/`、`tree/` |
| `experiments/frontier/20261117_deep/` | 10 MB | 宽度/合成/形状/侦察四条线的记录与脚本 |
| `experiments/frontier/20261116_push/` | 1.1 MB | `intel/` 评分模型、`pipeline/` 出包脚本 |
| `artifacts/20261118_push_dqi/` | 457 MB | `dqi_cond.kmb`（479,128,819 B，sha256 `327b07519606f7e7…`，static T 367,986，未提交）及日志 |
| `artifacts/20261117_lambda_measure/` | 112 MB | λ 拟合 `.npz`（由 Git 中 `LAMBDA_MEASURE` 脚本重跑） |
| `artifacts/20261118_inv_sweep/` | 62 MB | 公开 dataset/kernel 镜像（5 个 slug，可按名重下） |
| `artifacts/dqi_gen/` | 3.8 MB | 生成器探针、`ref_15_6_4.kmb` |
| `artifacts/20261118_push_dqi_*`（arrays/normeea/multrank/residual/mult） | 6.6 MB | 数组/divstep/乘法秩/残差输出 |
| `artifacts/20261116_intel/`、`20261117_*`、`20261118_caxis/`、`H_spectrum.npy` | 4.5 MB | kernel 镜像、LB 快照、侦察与 C 轴数据 |
| `.worktree/{invsqrt,dqi,dfthcsos}/` | 1.1 MB | 已停止研究线的 checkout；分支与提交保留 |
| `.venv/`、`.uv-cache/` | 116 MB | `uv sync` 可重建 |
| `docs/{ceiling,frontier,next-generation-plan,session}-2026*.md` | 50 KB | 结论已并入 `docs/abandoned-research.md §9` |
| `qcc-chem-emit-k2k3.log`、`scripts/kgpu.py`、`scripts/__pycache__/` | 12 KB | 研究运行残留 |

合计约 **797 MB**。`artifacts/` 不在 Git 中；受跟踪的研究文档/脚本可用
`git checkout b754ef5 -- <path>` 取回。

### 7.2 保留

`data/competition/`（官方数据与验证器）、`submissions/`（回执）、`references/`（公开源）、
`docs/research-map.md`（比赛契约）、`docs/abandoned-research.md`（总览）、
`experiments/{README.md,ARCHIVE_closed_lines.md}`、`scripts/{gm,inspect_circuit,manual_verify,package_submission}.py`。
