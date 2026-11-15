# 化学 A/B：4030-Toffoli loader + 新权重 refit（新公开件）首次带来真实提分

日期：2026-11-15。这是本会话**第一个过闸门并落成提交的正收益候选**。

## 1. 来源

`heliosli/qcc-circuits-live`（portfolio `v119_acx_ay3`，2026-11-15 09:03 更新，39,609 次下载）
里的 18 个成员，逐个 sha256 与 `QCC_RELEASE_MANIFEST.json` 对齐：

| 成员 | sha256 前缀 | 与我们的关系 |
|---|---|---|
| `invsqrt.kmb` | `1ba197b0` | **与我们提交件逐字节相同** |
| `dqi.kmb`（xz 解压后） | `821bf8d1` | **与我们提交件逐字节相同** |
| `dfthcsos/angle_k_*.kmb` | 15 个 | arizalfirdaus123 的 **4,030**-Toffoli 角度电路（我们是 4,033） |
| `dfthcsos/submission.npz` | `f1888d7a` | 新的权重 refit（我们 `3f864a7a`，1,847,692 B → 1,847,940 B） |

也就是说：**invsqrt 与 DQI 没有任何变化**，唯一差别是化学件。

## 2. 官方 verifier 的同环境 A/B（`qingyu1232/qcc-chem-ab`，COMPLETE）

两个目录都用未改动的 `verifiers/dfthcsos/verify.py`（78,080 shots）跑：

```
ours   rc 0, 26 s : PASS  score 294,991,455.81905466
                    toffoli 14,728  qubits 427  angles_toffoli_per_pass 4,033
                    error_1 0.019997639989605846  error_2 0.019999967953640795
                    lambda_eff 46.90701390190118

theirs rc 0, 24 s : PASS  score 294,878,860.57649696
                    toffoli 14,722  qubits 427  angles_toffoli_per_pass 4,030
                    error_1 0.01999999850000078   error_2 0.019999998500000008
                    lambda_eff 46.908219783627196
```

- 成本 **−112,595.24（−0.0382%）**：T 少 6 个 Toffoli，λ_eff 略升，净收益仍为正；
- 两者 error_1/error_2 **都紧贴 20 mHa 闸门**（这是设计使然：把拟合推到允许的最大误差以压低成本），
  但都是确定性量（由 npz 的字决定，不受 salt 影响），本环境实测 PASS。

## 3. 落成提交（ref 58382097, COMPLETE, 27.31541）

提交件 = 我们的 invsqrt `1ba197b0` + 我们的 dqi `821bf8d1` + 上述化学件。因为本机到
`www.googleapis.com`（Kaggle 的 blob 上传端点）**不可达**，CLI 的 `competitions submit` 会挂住，
所以改为在 Kaggle 侧组装：

- kernel `qingyu1232/qcc-assemble-4030-chem`（CPU，COMPLETE）挂载 `heliosli/qcc-circuits-live`，
  解压 `dqi.kmb.xz`、重命名 15 个 `dfthcsos__*`、逐成员核对 sha256、打包
  `submission.zip` = **49,281,301 B**（与本地打包字节数一致），18 个成员；
- 用 `create_code_competition_submission` 提交该 kernel 的输出（`submission.zip`）。

结果：

```
ref 58382097  SubmissionStatus.COMPLETE  publicScore 27.31541
```

相对 58350759 的 27.31193，**+0.00348**，与事前预测
`27.31193 × (294991455.82/294878860.58)^(1/3) = 27.31541` **完全一致**。

## 4. 结论与边界

- 这是"公开件拼装"路线的**最后一次榨取**：0.038% 的化学成本下降；
- 它把本会话的研究净增量从 +0.00532 提到 **+0.00880**（27.30661 → 27.31541）；
- 与榜首 29.90871 的差距（−23.9% 成本乘积）**没有被触及**，仍然需要新算术/综合。

## 5. 可复现入口

```
kernel  qingyu1232/qcc-chem-ab              # 同环境 A/B，打印两份 JSON
kernel  qingyu1232/qcc-assemble-4030-chem   # 从公开包组装 submission.zip（含 sha 校验）
ref     58382097                            # 提交回执，COMPLETE, 27.31541
```
