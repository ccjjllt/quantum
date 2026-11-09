# invsqrt 新切口：跨寄存器重综合（[15900:16800]）× 旋转基更换（梯-B 3×小角删除）

日期：2026-11-09；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：Public Frontier `7c10edba`（`artifacts/20261108_public_frontier/release/invsqrt.kmb`，
62Q / 53,686 ops / 静态 Toffoli-like 1,403 = CCX 1,086 + CCZ 91 + CSWAP 226 / HMR 858，
报告成本 95,430.78；计费 `score = Q × (Toffoli + T/4)`）。
与已 closed 方向（`20261109_cache_borrow_mincut/`、`20261109_tphase_fusion/`）无重叠：
本实验只做窗口内量子线重标记（不碰门数）与删除 3 个最小 Z_POW（不碰 CCX 结构）。

## 结论先行

1. **跨寄存器重综合 [15900:16800]（900 ops）：closed（0 CCX 可省），但产出 1 个**
   **零差分对称候选并送验证器仲裁。**
   全定义域字比较：窗内 41 个无条件 CCX 按（排序控制对，目标）分组得 30 组，
   8 组重复（k=2×7、k=5×1），**全部重复对乘积字两两不等**（累加器模式，
   与 cache_borrow 同一 obstruction）。两端边界全等线对仅为全零 ancilla
   {q25,q26,q27}（A 端零线 q25–q28，B 端零线 q21/q25–q27/q41/q50/q51/q57 交集）。
   唯一非平凡两端全等对 (q2,q23)@A 在窗内即分叉（@15925 `CX q27 q23` 改写 q23），
   不构成可交换对。q25↔q26 窗内重标记保持量子边界字全等（全定义域证明，起止皆零），
   且 24 格（8 真实 x × 3 seed）verifier 式 Simulator 抽查显示 62 线量子值、
   35 个窗内 HMR 经典位、shot 相位**全部零差异**；另 14 x × 3 seed（42 格）相位
   增补抽查同样零差异。期望 Δscore = 0（门数、T 数、Q 全不变），
   官方全量验证 **PASS**（200,540,928 shots，实测分 95430.98，基线 95430.78，
   差 +0.20 属噪声带）——对称性为真，机械链条走通，只是无收益。
2. **旋转基更换（梯-B 3 最小角删除 = 0 阶常数表近似）：closed（FAIL 仲裁）。**
   删除 op 25738/25748/25756（2.886e-11、5.873e-11、1.159e-10 半圈，和 1.017e-10 turns，
   Toffoli +0，n_rot 41→38）。T 模型估算省 **1,287–1,460 分**
   （proxy −1,373.7；±10× 带 −1,287.2/−1,460.2；即使假设 +4 CCX 显式查表成本净仍省
   1,039–1,212 分）。但同 seed 采样自检已证伪：x=3103559 处三掩码全 1，
   相位差恰为角和 1.017e-10 turns，而该 x 容差仅 3.38e-11 turns（**容差随 x 增大而
   缩小**，见 §2），超差 3.0×。官方验证器仲裁：**FAIL**
   （`x=644: phase error -2.360e-09 turns exceeds tolerance 2.349e-09`，
   首个超差 x 即停）。T 侧此切口无空间。

## 候选与验证器日志

| 候选 | 改动 | 规模 | 预期 Δscore | 官方验证器 |
|---|---|---|---|---|
| `artifacts/20261109_xreg_resynth/candidate_xreg_swap_q25q26.kmb` | [15900:16800] 内 q25↔q26 重标记 | 53,686 ops / 62Q（门数不变） | 0（实测 +0.20，salt 噪声带内） | **PASS**，`verifier_swap.log`（§3） |
| `artifacts/20261109_xreg_resynth/candidate_rotdrop_3small.kmb` | 删 3 最小梯-B Z_POW（41→38） | 53,683 ops / 62Q | −1,287–−1,460（省；未实现） | **FAIL**，`verifier_rotdrop.log` |

## 1. 跨寄存器扫描（`scripts/xreg_window_scan.py` → `xreg_scan.json`）

- 窗成分（900 ops）：CX 312、HMR 35、X 12、CCX 41、CSWAP 37、Z 44、CZ 209、
  SWAP 2、Z_POW 22、NEG 1、BIT_STORE0 16、BIT_INVERT 117、BIT_STORE1 14、
  CCZ 7（条件相位块 16287+）、R 1。
- 41 无条件 CCX → 30 不同三元组；8 组重复全部分属“同目标累加器”形状
  （5 组 `q21&*→q28` 相位梯 feeding、1 组 5 次 `(q1,q21)→q28`、1 组 `(q16,q32)→q1`），
  组内乘积字**全不等**（pop 487,946–1,099,781 量级残差），缓存语义 0 对成立。
- 两端全等对交集 = {25,26,27} 全零对（3 对）；q28 在 A 端零、B 端非零（梯输出），
  不可交换；(q2,q23) 仅 A 端全等。
- q25↔q26 对称性：全定义域边界字起止皆零（HMR 复位语义下精确）；verifier 式
  Simulator（`write_across_shots` 写真实 x 到 q0–q21，同 seed 跑 prefix+窗口原/交换
  变体）24 格 + 42 格相位格：q 差异 0 格、b 差异 0 格、相位差异 0 格。
  下游守卫非对称性说明：b6/b7 在抽查 x 下取值全等（故交换后经典位不变），
  但零分支字仿真无法证明**全部** x 下测前值全等——最终裁决交给验证器
  （候选门数与基线完全一致，Δscore 恒为 0）。

## 2. 旋转基更换估算与证伪（`scripts/build_candidates.py` → `rotdrop_estimates.json`、`phase_selfcheck.json`）

- 模型 `T(n)=n(0.56·log2(1/eps_n)+5.3)`，`eps_n=eps41·41/n`，
  `eps41=2.434041480874084e-13`（maoxin_v2 实测，沿用 tphase 口径并给 ±10× 带）：
  41→38 的 ΔT=88.63（proxy），Δscore=−1,373.7；±10× 带 −1,287.2/−1,460.2。
  显式查表假设 +4 CCX（+248 分@62Q）后净仍省 1,039–1,212 分。
- 同 seed 采样自检（200 x × 2 seed = 800 格，基线 vs rotdrop 同 seed 对比，
  容差取验证器自带 `reference_values`）：最坏格 x=3103559 相位差 −1.017e-10 turns
  （恰为三删除角之和 ⇒ 三掩码在该 x 全 1），容差 3.38e-11 turns，超差 3.0×。
  关键结构洞察：`tol(x)=min(r>>shift, 2^63)` 随 x 增大而缩小（大 x 相位目标小），
  故“小角可忽略”直觉在高 x 区不成立——即使 1e-10 turns 量级删除也会在
  x≈3.1M 处超差。任何 0 阶/低阶多项式近似若误差 ≥3e-11 turns 同样失败；
  要通过需近似误差 ≪3e-11 turns，即实质精确——旋转基更换在此切口 closed。
- 官方仲裁（hash seed，含 HMR 硬币流变化）：FAIL 于 x=644
  （error −2.360e-09 vs tol 2.349e-09，~1.005×，首个超差即停），与自检结论一致
  （自检 200 采样未抽中 x=644 附近早死区，官方全量扫描补足）。

## 3. 验证范围声明（必须如实区分）

- **官方验证器运行 2 次**：
  - rotdrop 候选完整验证器运行 1 次，**FAIL**
    （`artifacts/20261109_xreg_resynth/verifier_rotdrop.log`，1.1s 早停，
    `x=644: phase error -2.360e-09 turns exceeds tolerance 2.349e-09`，`EXIT:1`）。
  - swap 候选完整验证器运行 1 次，**PASS**
    （`artifacts/20261109_xreg_resynth/verifier_swap.log`，约 4 min，
    `verified_shots=200540928`，`score=95430.98409404865`，
    `toffoli_equivalent=1539.2094208717524`，`rotation_count=41`，
    `rotation_eps=2.434041480874084e-13`（与 maoxin_v2 实测 eps41 完全一致，
    本次为 frontier 电路上的独立复测），`worst_error_over_tolerance=0.9993@x=161`，
    `EXIT:0`）。PASS 分数与基线公开报告 95,430.78 差 +0.20，
    属 salt/硬币流噪声带（不同电路 hash → 不同 HMR 硬币流），Δscore 实质为 0。
    该 PASS 证明了本切口机械链条的有效性：全定义域边界字等价 +
    小批量 Simulator 抽查筛选出的寄存器重标记，可原样通过 2 亿 shots 全量验证。
- **未运行基线 7c10edba 的官方验证**（报告成本沿用公开值；eps 用 maoxin_v2
  实测值代理并给 ±10× 敏感带，不假装是 frontier 实测）。
- 其余全部为**静态结构统计 + 全定义域零分支字仿真 + verifier 式小批量
  Simulator 探针**（24 格边界等价 + 42 格相位格 + 800 格容差自检），
  不改电路语义；裁决依据是验证器 FAIL 与容差不等式，不是探针外推。
- **未产生可提交候选**（2 个构建电路均为仲裁原型：1 零差分对称、1 FAIL），
  无打包、无提交、无推送。

## 复现（macOS PyPI kickmix，`.venv/bin/python`）

```bash
.venv/bin/python experiments/invsqrt/20261109_xreg_resynth/scripts/xreg_window_scan.py
.venv/bin/python experiments/invsqrt/20261109_xreg_resynth/scripts/build_candidates.py
.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
    artifacts/20261109_xreg_resynth/candidate_rotdrop_3small.kmb
.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
    artifacts/20261109_xreg_resynth/candidate_xreg_swap_q25q26.kmb
```

## 引用

- 窗口定义与 Q 峰值背景：`experiments/invsqrt/20261108_frontier_audit/README.md` §3
  （`[15900:16800]` 局部 62Q→61Q 峰值区）；梯-B 角度表与 T 计费模型：
  `experiments/invsqrt/20261109_tphase_fusion/README.md` §1–2
  （26 个梯-B 角 2.9e-11→9.8e-4 半圈；`Δscore=62·ΔT/4`；eps41 代理来源
  `20261106_cleanup` maoxin_v2 实测）。
- 位并行字仿真口径（48,961×uint64，跳条件块/对角门，HMR/R 置零）沿用
  `20261108_frontier_audit/audit_frontier_7c10edba.py`；
  同分支真机掩码教训（零分支假阳性）沿用 tphase `prefix_branch_check.py`。
- 验证器：`data/competition/verifiers/invsqrt/verify_submission_invsqrt.py`
  （`reference_values` 容差、`write_across_shots` 输入装载、本次 1 PASS + 1 FAIL 日志）。
