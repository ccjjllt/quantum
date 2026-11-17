# 2026-11-17 深度并行研究计划（Kaggle CPU）

目标：在公开最佳 **28.15083**（本账号 ref `58454232`，COMPLETE）之上大幅提分。
所有电路模拟与官方验证只在 **Kaggle CPU kernel** 上跑（`enable_gpu=false`、
`enable_tpu=false`）；本机只做静态阅读、小文件解析和公式算术，不做仿真、不跑验证器。

截止 2027-01-20，每日 5 次提交；当前榜：gold=28.71339（rank 16），silver=28.14702（rank 161），
本账号 28.15083（rank 87–115，与 29 队并列）。榜首 31.01379。

## 0. 已确证的事实（不要重复验证）

- 官方三条 cost 公式已反解并逐位复现（`experiments/frontier/20261116_push/intel/RESULT_cost_model.md`）：
  - invsqrt `score = Q·(Toffoli + T/4)`；本件 44Q / 1459.3749 / 2.4999 / 33 rot @ ε=1.64e-13 → 74,797.365
  - dqi `score = R(ε+)·Q²·T`；本件 890Q / T=367,120.004 / R=1.1912605 → 346,413,579,540（clean）
  - chem `score = λ_eff·T_total·Q_total`；本件 427Q / T=14,706 / λ_eff=46.921717 → 294,643,137.73
- 公开分是确定性的：每个 DQI 文件只有 clean 或 clean×1.0045925 两种公开 cost
  （`intel/RESULT_public_salt_model.md`）。选腿规则 = 公开 cost 最低。
- 公开字节重组已到顶（29 队并列 28.15083），三条腿都已是已知字节最小。
- 金线换算：单腿再便宜 **5.496%**（invsqrt ≤70,686；DQI ≤327.37e9；chem ≤278.45M）。

## 1. 研究线、账号与目标

| 线 | 账号 | 主攻 | 决定性指标 | 目录 |
|---|---|---|---|---|
| DQI 宽度/条件执行 | `zhuating` | Q 890 下探；mean-T 条件化 | cost < 346.41e9 | `dqi/` |
| invsqrt 新合成体 | `jiyujia` | Q 44→42/40 或 C −6% | score < 74,797.37 | `invsqrt/` |
| 化学形状/λ | `qingyu1232` | (R,B,C,brot,J) 形状与 λ·T·Q | cost < 294.643M | `chem/` |
| 公开前沿/开源侦察 | `qingyu1232` | 新字节、论文、开源实现 | 任何更便宜的件 | `scout/` |

收益换算（其余两腿不变，GM ∝ cost^(-1/3)）：

| 改动 | 新 GM | 增量 |
|---|---:|---:|
| DQI Q 890→880（T 不变） | 28.307 | +0.216 |
| DQI Q→870 / Q→860 / Q→840 | 28.524 / 28.745 / 29.257 | +0.43 / +0.65 / +1.11 |
| DQI T −5.5% | 28.69 | +0.54 |
| invsqrt Q 44→42 / 44→40 | 28.534 / 29.002 | +0.44 / +0.91 |
| invsqrt C −5.5% | 28.69 | +0.54 |
| chem T 14,706→14,000 / →13,500 | 28.59 / 28.94 | +0.47 / +0.82 |
| chem Q 427→400 / →380 | 28.60 / 28.85 | +0.45 / +0.70 |

## 2. 硬规则

1. **只在 Kaggle CPU kernel 跑**（`scripts/kgpu.py`，已内置 `enable_gpu=false`）。不在本机
   import kickmix 做仿真、不在本机跑 `verify*.py`。
2. 候选电路必须用**未修改的官方 verifier**、full shots 复核：invsqrt 200,540,928；
   DQI 102,400；chem 78,080。
3. 提交权只在主会话（main）；研究线不得自己 `kaggle competitions submit`。
4. 每条线把结论写进自己的 `RESULT*.md`：假设、改动、实测数字、Kaggle kernel ref、
   验证范围（局部/完整/榜分三者分开写）。
5. 负结果同样记录，避免下一个人重复。

## 3. 共享工具

```bash
# 建 kernel（CPU-only、可挂数据集/内核输出）
python3 scripts/kgpu.py new --dir <DIR> --slug <NAME> --account <acct> \
    [--dataset grantprater/vqcc-dqi-61c8348d-merged-closings] \
    [--kernel maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier] --competition
python3 scripts/kgpu.py push   --dir <DIR> --account <acct> --wait 0
python3 scripts/kgpu.py status --kernel <owner/slug> --account <acct> --wait 5400
python3 scripts/kgpu.py fetch  --kernel <owner/slug> --account <acct> --out <OUTDIR>
```

比赛数据在 kernel 内的 `/kaggle/input/google-verifiable-quantum-circuit-compilation/`
（含 `verifiers/` 与 `kickmix/`）。DQI 巨件在
`/kaggle/input/vqcc-dqi-61c8348d-merged-closings/`（`dqi.kmb` 479 MB，sha `61c8348d…`）。
invsqrt 基线 44Q 件在 `experiments/frontier/20261116_push/pipeline/invsqrt_0af21cb8.kmb.b64`
（zlib+base64，解出 sha `0af21cb8…`）。

## 4. 关键结构性发现（本轮新增，供各线使用）

- chemistry 的 heuristic 部分是 **形状的纯函数**（`SpinFreeData_V1`，`optimize_qubits=True`）：
  `Q_total = 84 + J·brot + max(90, inner_temp, angles_temp)`，本形状 (8,143,44,8) 落在
  `inner_temp=303` 的口袋（k2=5 时 606 刚好超 `brot·(N−1)=600`，模型退到 k2=4）。B=128 会退到
  575（Q 658），B=144 → T 7016。**改形状必须同时改训练分解**，不是免费参数。
- DQI 宽度换汇：每 qubit 0.225%/Q²；相对 28.15083 的盈亏平衡是 826–900 T/qubit（Q889–840），
  金线在 Q865 只容忍 6.6 T/qubit。实测最便宜机制 925 T/qubit（q864，每 episode 1 CCX），
  **只超盈亏平衡 7.4%**——这是全项目离「能赚」最近的一处。
- DQI `T` 是 **逐 shot 的均值**，被测量位条件的门只在置位 shot 计数。本件已有
  263.8e9 次 POP/PUSH_CONDITION。
- invsqrt 的 33 个非 Clifford 旋转占 C 的 14.11%，只因 `worst_error/tol=0.99956` 没有合成余量。

## 5. 时间盒

每条线先做 30–60 分钟可判定的测量（一个 Kaggle kernel），给出 go/no-go，再决定是否深入。
最终由 main 汇总：任一线拿到 `cost` 改进 → 用官方 verifier 全 shots 复核三件套 → 高于
28.15083 才提交。
