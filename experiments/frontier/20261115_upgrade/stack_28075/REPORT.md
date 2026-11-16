# 换件：当前最高的**真实**公开包（Atakan v15，GM 28.07503）

日期：2026-11-16。目标：用"当前最高分的公开方案"提交一次。

## 1. 公开件甄别：大部分 28.0x notebook 是占位假件

2026-11-15 晚上出现了一波 28.0x "SOTA" notebook。逐个拉取输出后：

| notebook | 自报 | 实际输出 |
|---|---|---|
| `ozertuu/vqcc-verified-portfolio-28-082-sota` | 28.075 | `submission.zip` **658 B** |
| `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler` | 28.085 | `submission.zip` **680 B**，其余"证据"全部 ~700 B |
| `jeffemerson/28-071-44-qubit-stack-our-and-merge-cut` | 28.071 | 列表 API 报 680 B，**实际下载 51,845,158 B（真）** |
| `atakanaldemir/qcc-terminal-readout-and-phase-folds` | 28.075 | **实际 51,855,023 B（真）** |
| `yorixum/quantum-circuits-iso-gap-dqi-h5` | 28.58+ | 代码含 `r[sha12]` 的 `NameError`，**从未跑通** |

教训：`list_notebook_files` 的 `size` 字段不可信，必须 `kaggle kernels output` 下载后看真实字节。
另外 `yorixum` 的脚本里有一张硬编码的 `VERIFIED_CACHE_BY_PREFIX`，会把未验证的项标成 PASS，
不能作为证据。

## 2. 采用的真实最高公开包

`atakanaldemir/qcc-terminal-readout-and-phase-folds` 的输出 `submission.zip`
（51,855,023 B，sha256 `95cdc8be…32996`）：

| 任务 | SHA-12 | Q | 官方成本（我们复核） | 原 28.059 |
|---|---|---:|---:|---:|
| invsqrt | `2c125b395e67` | 44 | **75,082.0925** | 75,170.6203 |
| DQI | `4b350932b039` | 890 | **347,760,709,936.55** | 347,904,227,555.54 |
| 化学 | `881d9daed46e` | 427 | **294,763,525.6805** | 294,800,582.4430 |
| **GM** | | | **28.07503** | 28.05896 |

三个 SHA 都来自公开 manifest（`manwithacat/vqcc-apache-public-circuits`）里已记录的
"local official verifier, default salt" 条目，作者链条：Syed Asad Ali → Jeff Emerson
（q28 AND-merge）→ Atakan（相位 LP / 读取折叠）；DQI 是 Syed v12 cutoff-18 + Hayato 的
product retention；化学是 marculera 表 + Asterios GRG refit。

## 3. 我们的独立复核

Kaggle kernel `qingyu1232/qcc-adopt-28075`（CPU，无 TPU）：

1. 在 `/kaggle/input` 里按 zip sha256 找到该包（不依赖目录名）；
2. 断言 18 个成员哈希（invsqrt / dqi / npz / 15 个 angle_k）；
3. 用**未修改**的官方 verifier 依次跑化学、invsqrt、DQI；
4. 重新打包为 `/kaggle/working/submission.zip`。

```text
CHEM     rc 0  28 s : PASS 294,763,525.6805207  Q=427  T=14,712  lambda_eff 46.92174459704718
INVSQRT  rc 0 634 s : PASS 75,082.09249369454   Q=44   T=1,456.249  200,540,928 shots
                      worst_error_over_tolerance 0.9912101319
DQI      rc 0 139 s : PASS 347,760,709,936.5516 Q=890  T=368,547.756
                      102,400 shots, value_errors 0, phase_errors 0
SUBMISSION /kaggle/working/submission.zip 51,855,023  ea5dd5a4fa23e5db...
```

## 4. 提交

```text
ref 58410043   qingyu1232/qcc-adopt-28075 v1   submission.zip 51,855,023 B
状态 COMPLETE   public 28.07502   rank 181 / 3138
```

本地三件复核 GM 28.07503，实际 public **28.07502**（DQI 的 salt 抽样差异）。
相对上一版 28.05896：**+0.01606**，排名 314 → **181**。
