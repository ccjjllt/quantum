# 换栈：28.059 公开组合（44Q invsqrt + 890Q DQI + marculera v6 化学）

日期：2026-11-16。这是本会话**最大的一次提分**，全部来自公开件，不含自研电路。

## 1. 来源

发布者 `jeffemerson` 的打包 notebook
`28-059-public-stack-44-qubit-invsqrt-x-ray`（2026-11-15 15:06 UTC 运行）给出了
三件公开电路与它们在官方 verifier 下的成本：

| 任务 | 构建者 | Q | T_mean | 官方成本 | 我们此前的成本 |
|---|---|--:|--:|--:|--:|
| inverse sqrt | syed3000 **v14** | **44** | 1,458.25 | **75,170.62** | 78,673.569（46Q） |
| DQI | syed3000 **v14** | **890** | 368,699.85 | **347,904,227,556** | 360,209,905,486（889Q） |
| chemistry | marculera **v6** | 427 | **14,712** | **294,800,582.44** | 294,878,860.58 |
| **几何平均** | | | | **28.0590** | 27.31541 |

两个 dataset：

- `syed3000/vqcc-own-circuit-portfolio`（v14）：`invsqrt.kmb` sha `47b31838…`（200,369 B）、
  `dqi.kmb` sha `46446af1…`（486,989,273 B）；
- `marculera/dfthc-c44-build`（v6）：15 个 `angle_k_*.kmb` + `submission.npz` sha `302e608c…`。

注意：**DQI 的 Q 从 889 升到 890，但 T_mean 从 383,008 降到 368,699.85**，
净成本 −3.4%——这是"Q 变大但 T 大幅变小"的典型换算法，也是此前只看 Q 的盲点。

## 2. 我们的独立复核（不是复制发布者的数字）

- 组装由 **SHA-256 定位**：kernel `qingyu1232/qcc-assemble-28059` 在 `/kaggle/input` 里按哈希
  找到 18/18 个成员，逐个复核后打包：

```
found 18 of 18 members
OK invsqrt.kmb 47b318383a03 200369
OK dqi.kmb 46446af11865 486989273
OK dfthcsos/submission.npz 302e608cbbcb 1847692
... (15 个 angle_k 全部 OK)
SUBMISSION /kaggle/working/submission.zip 51,858,038  87703019f2a95034...
MEMBERS 18
```

- 官方 verifier 独立复核：kernel `jiyujia/qcc-verify-28059`（chem → invsqrt → DQI，默认 salt）。
  发布者自报：三件在 4 个 salt 上 PASS；其中两个 salt 上 DQI 有 1/102,400 个失败 shot
  （DQI 成本 +0.46%，GM 28.016）。

## 3. 提交

```
ref 58392219  (kernel qingyu1232/qcc-assemble-28059 v1, submission.zip 51,858,038 B)
```

## 4. 为什么这一步能成立而自研路线不行

自研的三条线（invsqrt Q45、DQI Q888、化学 C≈37）都被实测关闭：
Q45 需要 ≥8-AND 重建（0–7 全域 0/10，q22 的有效判定 EMPTY、正控制 200/200），
DQI 24→23 位代数不可能（乘积像是满 24 维），化学 B/C/Adam/from-scratch 全部越界。
而 **Q 轴上的 46→44 是别人已经做出来的电路**——这正是"结合优秀公开方案"能拿到、
自研在会话内拿不到的那部分。
