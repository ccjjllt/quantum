# 2026-11-18 公开 SOTA 28.23163（DQI `15a4b740`，−1,110.95 mean T）

**状态：COMPLETE，public `28.23162`，rank 183 / 3,355（ref `58522779`，2026-11-18T19:20:43Z；本地复算 GM `28.231630`）。**

## 变更

相对 ref `58517010`（28.20311）**只替换 DQI**。

| 腿 | 件 | Q | 成本 | 说明 |
|---|---|---:|---:|---|
| invsqrt | `d0227f3c` | 44 | **74,405.67238374705** | 不变（本账号已全量复核 200,540,928 shots） |
| DQI | **`15a4b7403356092e0ef6cc61c9f18644864964daae9630575d77c29314f75c8b`** | 890 | **345,256,821,433.9815** | 超级合并件：`40294f00`（balramsrinivasan 的 CSWAP converter）+ 32 个 GF(2^24) closings（−672 T）+ 8 MBUC（−8 T）+ PW4/retention（−44 T）+ HW-30（−116 T）→ mean T **365,894.20047851565** |
| chem | `4d63be3d` + 15 loaders | 427 | 294,642,170.565169 | 不变 |

来源：`ozertuu/28-23163-sota-verified-compilation-top-portfolio`（v3，notebook 输出 `submission.zip` + `receipt.json`，2026-11-18T16:53Z）。该 notebook 挂载 `asteriospanoras/qcc-circuit-atlas`、`junmiaotiao/qcc-frontier-20261118w`、`ozertuu/quantum-sim-linalg-cache`、`manwithacat/vqcc-hedge-wizardry`、`balramsrinivasan/vqcc-public-work-1118`，在 notebook 内合成这个 DQI。

## 预期分数

| dqi 成本 | ratio | GM |
|---:|---:|---:|
| 346,305,114,280.17（HW-30） | 70.57204 | 28.203115 |
| **345,256,821,433.98（`15a4b740`）** | **70.78633** | **28.231630** |

ΔGM **+0.02852**；mean T 少 **1,110.953**（367,005.154 → 365,894.200）。

## 18 成员 SHA-256（与 `receipt.json` 逐项一致）

```
ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538  dfthcsos/angle_k_0.kmb
8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd  dfthcsos/angle_k_1.kmb
e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f  dfthcsos/angle_k_2.kmb
b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e  dfthcsos/angle_k_3.kmb
ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d  dfthcsos/angle_k_4.kmb
21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856  dfthcsos/angle_k_5.kmb
1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1  dfthcsos/angle_k_6.kmb
8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0  dfthcsos/angle_k_7.kmb
0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563  dfthcsos/angle_k_8.kmb
b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71  dfthcsos/angle_k_9.kmb
41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6  dfthcsos/angle_k_10.kmb
76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca  dfthcsos/angle_k_11.kmb
e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f  dfthcsos/angle_k_12.kmb
9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8  dfthcsos/angle_k_13.kmb
fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f  dfthcsos/angle_k_14.kmb
4d63be3d5c26cfa447a3464eeaf515a652814a1dd4c78f1f1af2f5b7d9e9b8b3  dfthcsos/submission.npz
15a4b7403356092e0ef6cc61c9f18644864964daae9630575d77c29314f75c8b  dqi.kmb
d0227f3c548ae7f1a409159a143cf4a401de56a2414a5230a3efc4b38e0a8160  invsqrt.kmb
```

- 打包：作者容器 `submission.zip`，**50,391,549 B**（18 成员 477,185,608 B 未压缩）。
- notebook 的 `receipt.json`（同一份文件）记录 DQI：`PASS`、0 value / 0 phase、102,400 shots、
  `toffoli_count 365894.20047851565`、`max_toffoli_count 366216`、`num_qubits 890`、`num_bits 74545`、
  `num_ops 56,854,639`（含 `CSWAP` 1,061,273,600 次 shot 级执行）。

## 验证范围

- invsqrt `d0227f3c` 与 chem `4d63be3d` 已由本账号在 ref `58514074` / `58496528` 中全量复核
  （200,540,928 / 78,080 shots PASS），文件逐字节相同。
- DQI `15a4b740` **独立复核完成**：内核 `jiyujia/qcc-dqi-15a4b740-verify` **v1 COMPLETE**
  （CPU only，`enable_gpu=false`、`enable_tpu=false`），未改官方 verifier，102,400 shots：

  ```json
  {"status":"PASS","score":345256821433.9815,"verified_shots":102400,
   "value_errors":0,"phase_errors":0,"repetition_factor":1.1912604648115832,
   "toffoli_count":365894.20047851565,"max_toffoli_count":366216,
   "num_qubits":890,"num_bits":74545,"num_ops":56854639,
   "circuit_sha256":"15a4b7403356092e0ef6cc61c9f18644864964daae9630575d77c29314f75c8b"}
  ```

  与作者 `receipt.json` 逐位一致（`365894.20047851565` / `366216` / `345256821433.9815`）。
  与 HW-30 对比：mean T **367,005.154 → 365,894.200（−1,110.953）**，`max_toffoli_count`
  367,867 → 366,216（−1,651），说明它是**结构性**更便宜（多了 `CSWAP` 层、`num_bits` 74,545）。
- 作者 `receipt.json` 亦记录三腿 PASS。榜单成绩以 Kaggle 回执为准。
- 注意：该件引入了 `CSWAP`（`num_bits` 74,545，比 HW-30 多 7,815 个经典位），
  `max_toffoli_count` 366,216 比 HW-30 少 1,651——所以它是结构性更便宜，不只是数据相关跳过。
