# invsqrt 大窗跨寄存器重综合（[5006:7506] 2500 ops）× 仿真方向修正

日期：2026-11-09；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：Public Frontier `7c10edba`（`artifacts/20261108_public_frontier/release/invsqrt.kmb`，
62Q / 53,686 ops / 静态 Toffoli-like 1,403 = CCX 1,086 + CCZ 91 + CSWAP 226，
报告成本 95,430.78；计费 `score = Q × (Toffoli + T/4)`）。
与已 closed 切口（`20261109_xreg_resynth/` 900ops 交换/T删、`20261109_tphase_fusion/`、
`20261109_cache_borrow_mincut/`）无重叠：本实验只动 [2006:14215] 纯无条件算术池。

## 结论先行

1. **大窗重综合：closed（0 CCX 可省）。** [2006:14215] 12,209 ops 经查全部无条件
   （CX 12,058 + CCX 134 + X 17，无 HMR/R/条件/对角门），零分支字仿真在此处是精确的。
   穷举：死 CCX 0/134；同目标乘积相等对 0（含不同控制拼写）；控制恒 1 共 0；
   首尾双边界全等线对：大窗 0 对，[5006:7506]/[5506:8006]/[6006:8506] 三个 2500 窗
   均为 0 对；同目标共享一控制对 117 对，精确可交换性检验（共享控制稳定 M1 +
   逐门对易 M2）117/117 倒在 M1（共享控制在对间恒不稳定，最小间隔 73 ops，
   总线持续重载）。累加器 obstruction，与 cache_borrow 同构。
2. **仿真方向修正（重要）：`CX` 在 kmx 中的顺序是 control-target。**
   本工作区此前字仿真（含 `20261108_frontier_audit`、`20261109_xreg_resynth` 的
   `xreg_window_scan.py`）均按 `qv[p1] ^= qv[p2]`（反向）实现。最小真机电路
   仲裁：`X q0; CX q0 q1` 后 q1=1 ⇒ p1=control、p2=target，正确更新是
   `qv[p2] ^= qv[p1]`。修正前本实验曾给出 8 对“等乘积可对消”（例 5564/5646），
   Simulator 小批量探针证伪（10/16 格终态差异），真机逐点核对确认
   （x=1 在 5564 处 P=0、在 5646 处 P=1），遂修正并重跑全部普查。
   修正后字仿真与真机在 cut 7506 上 4 格 × 62 线逐位全等，可信。
   此前 closed 结论的方向性（乘积不等、累加器模式）不受影响，但其字仿真
   细节数字以修正后口径为准。
3. **候选：1 个零差分重排序候选，官方验证器 PASS（Δscore = 0，无收益）。**
   声明窗口 [5006:7506]（2500 ops 纯无条件算术：CX 2,468 + CCX 27 + X 5）内
   交换相邻不交线对 op5006/5007（`CX q42 q54 | CX q59 q14`），门数、T 数、Q 全不变。

## 候选与验证器日志

| 候选 | 改动 | 规模 | 静态 Δscore | 官方验证器 |
|---|---|---|---|---|
| `artifacts/20261109_xreg_bigwin/candidate_reorder_k5006.kmb` | [5006:7506] 内交换 op5006/5007（不交线对易） | 53,686 ops / 62Q / CCX 1,086（不变） | 0（实测 +0.19，salt 噪声带） | **PASS**，`artifacts/20261109_xreg_bigwin/verifier_reorder.log` |

- PASS：`status=PASS`，`verified_shots=200540928`（全量，非早停），
  `score=95430.96600456418`（基线公开报告 95430.78，差 +0.19 属 salt/硬币流噪声带，
  与此前 swap 候选 +0.20 一致），`max_toffoli_count=1403`（不变），
  `rotation_count=41`、`rotation_eps=2.434041480874084e-13`（与 maoxin_v2 实测一致），
  `worst_error_over_tolerance=0.9993@x=161`，`num_qubits=62`。
- 另有一次同候选验证器运行（未 tee，只取 tail 确认 PASS + EXIT:0），两次皆 PASS。

## 1. 窗口选择

- 池 [2006:14215]（12,209 ops）：`cond/deep=0`，成分 CX 12,058 + CCX 134 + X 17，
  整体即纯无条件算术窗。CCX 密度 ~27–29/2500 ops，重复三元组 extra ≤6。
- 池 [36305:49360]（13,055 ops）：CZ 11,449 + Z 1,481 + CX 59 + NEG 54 等，
  条件门 12,985，无 CCX/CCZ（0），无可省的付费门，排除。
- 声明窗口 **[5006:7506]**（2500 ops）：CX 2,468 + CCX 27 + X 5，全无条件；
  另用 [5300:5800]（500 ops：CX 494 + CCX 5 + X 1）做子窗探针（见 §2）。
- 结构：q14–q17 为累加总线（q14 被 CX 命中 4,500 次），q15/q16/q17 分别 ~3k/1.9k/753 次；
  每个 CCX 目标（q22–q61）恰累积 3–4 个 AND 项（部分乘积和），是典型 schoolbook 乘法器形状。

## 2. 子窗探针：证伪记录（deldup 假设 DEAD）

- 修正前（CX 反向）字仿真给出 8 对“同三元组等乘积、目标间无读写”对，
  以 q25 对 (5564,5646) 为代表构建删除候选（−2 CCX 假设）。
- Simulator 小批量探针（8 x × 2 seed 全电路终态+相位比较）：10/16 格差异，
  且差异与 seed 无关（确定性函数差异）；真机截断电路核对 x=1：
  5564 前 q14=0,q15=0（P=0），5646 前 q14=1,q15=1（P=1）——乘积根本不等。
- 根因：CX 方向反了（见结论 2）。该候选 `.kmb` 已删除，
  探针证据保留在 `deldup_probe.json`（10 差异格明细）中备查，不送验证器
  （Simulator 已证伪，不浪费验证器仲裁）。

## 3. 穷举普查（修正后口径，全定义域 3,133,452 输入字比较）

`scripts/bigwin_scan.py → bigwin_scan.json`（[2006:14215] 全窗）：

- 死 CCX（乘积字全零）：0/134；最大乘积 pop 1,103,186（无全 1）。
- 同目标等乘积对（任意控制拼写）：0（`scripts` 内联复核，全 134 个乘积字两两比较）。
- 控制恒 1（`CCX(a,1,t)=CX(a,t)` 可省）：0；恒 0 蕴含于死门（0）。
- 双边界全等线对：大窗 `dup_both=[]`（A 端仅零 ancilla q55–q60 全等，B 端 0 对）；
  三个 2500 窗 `dup_both` 均为空、端点零线 0 条（`followup.json` F3）。
- 同目标共享一控制对 117 对（`merge_check.json`）：M1（共享控制字稳定）通过 0/117，
  最小间隔 73 ops——总线在对间必被重载，合并恒等式无着陆点；M2 未启用。
- 交换/合并两条路在此窗均无着陆点：closed。

`scripts/followup.py → followup.json`（F1 控制 pop 表 + F3 三窗边界对偶）与
`scripts/merge_check.py → merge_check.json`（精确对易规则见文件头注释）
为上述数字的生成代码，可复现（macOS PyPI kickmix，`.venv/bin/python`）。

## 4. 候选构建与等价证据（`scripts/build_reorder_candidate.py`）

- 编辑：`ops[5006] ↔ ops[5007]`（`CX q42 q54 | CX q59 q14`，线集 {q42,q54}∩{q59,q14}=∅）。
  静态证明：不交量子线上的门精确对易（经典可逆门，张量积分解），
  门数/类型/Q/CCX 数恒不变 ⇒ Δscore 恒为 0。
- 全定义域字比较：窗终点 7506 处 62 线边界字 base vs reorder **0 差异**
 （`reorder_probe.json: fulldomain_boundary_wdiff_at_7506=[]`）。
- Simulator 小批量（verifier 式：真实 x 写入 q0–q21，同 seed 跑全电路，
  比较终态 62 量子位 + shot 相位）：8 x × 2 seed = 16 格，
  `cells_with_qdiff=0`，`cells_with_phasediff=0`。

## 验证范围声明（必须如实区分）

- **官方验证器运行 2 次**：均为同一重排序候选的完整验证，2 次皆 **PASS**
  （第 1 次 tail + EXIT:0 确认；第 2 次全量 tee 为
  `artifacts/20261109_xreg_bigwin/verifier_reorder.log`，17 行完整 JSON，
  `status=PASS`，`verified_shots=200540928`）。PASS 分数与基线公开报告差 +0.19，
  属 salt/硬币流噪声带，Δscore 实质为 0。
- **未运行基线 7c10edba 的官方验证**（报告成本沿用公开值）。
- 其余全部为**静态结构统计 + 全定义域字仿真（修正后口径，真机 4 格 × 62 线
  逐位核对一致）+ verifier 式小批量 Simulator 探针**；裁决依据是字仿真不等式
  （关闭省门方向）与验证器 PASS（确认零差分链条）。
- **未产生可提交候选**（唯一构建电路为 0 增益对称原型），无打包、无提交、无推送。
- 产物：`artifacts/20261109_xreg_bigwin/`（1 .kmb + 1 verifier log），
  `experiments/invsqrt/20261109_xreg_bigwin/`（本 README + 4 脚本 + 4 JSON）。

## 复现（macOS PyPI kickmix，`.venv/bin/python`）

```bash
.venv/bin/python experiments/invsqrt/20261109_xreg_bigwin/scripts/bigwin_scan.py
.venv/bin/python experiments/invsqrt/20261109_xreg_bigwin/scripts/followup.py
.venv/bin/python experiments/invsqrt/20261109_xreg_bigwin/scripts/merge_check.py
.venv/bin/python experiments/invsqrt/20261109_xreg_bigwin/scripts/build_reorder_candidate.py
.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
    artifacts/20261109_xreg_bigwin/candidate_reorder_k5006.kmb
```

## 引用

- 窗口与基线：`experiments/invsqrt/README.md` 谱系；`20261108_frontier_audit/`（Q 峰值背景）。
- 方法口径：`20261109_xreg_resynth/scripts/xreg_window_scan.py`（本实验修正其 CX 方向；
  原 swap-PASS 结论不受影响——对称性不依赖仿真方向，但其 §1 的字仿真细节数字
  应以修正后口径重读）；`20261109_tphase_fusion/`（零分支假阳性教训：本实验一切
  字仿真结论均经真机逐点核对）。
- 验证器：`data/competition/verifiers/invsqrt/verify_submission_invsqrt.py`。
