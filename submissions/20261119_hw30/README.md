# 2026-11-19 公开 HW-30 DQI（`35fa5ef9`）：28.20311 包

**状态：COMPLETE，public 28.20311，rank 134 / 3332（ref `58517010`，2026-11-18T16:10:22Z）。**

- 上一版 ref `58514074`：28.20041，rank 134（16:00Z 为 124，16:27Z 为 134）。
- 绝对分数 **+0.00270 GM**；名次没有变化：同期已有 34 队提交同一公开 HW-30 件，
  28.20311 并列块从 16:00Z 的 rank 100–108 扩到 rank 100–134。

## 变更

相对 ref `58514074`（28.20041）**只替换 DQI**。

| 腿 | 件 | Q | 成本 | 说明 |
|---|---|---:|---:|---|
| invsqrt | `d0227f3c` | 44 | **74,405.67238374705** | 与上一版相同（本账号已全量复核） |
| DQI | **`35fa5ef9a2bf21e423b47cab71579d451d7827225b6ecc8c655fa2c2ce0c2ba4`** | 890 | **346,305,191,933（预期）** | hedge **HW-30**：`5f901c55` + VUMANIAcom 的五个 retention patch，每 shot 少 **104.93** 个 Toffoli |
| chem | `4d63be3d` + 15 loaders | 427 | 294,642,170.565169 | 与上一版相同 |

来源与交叉证据：

- `manwithacat/vqcc-hedge-wizardry`（Apache-2.0）`README.md` HW-30 行：
  “Two public DQI siblings merged: VUMANIAcom's five retention patches on the current pick,
  105 Toffolis fewer”，base `5f901c55` → `35fa5ef9a2bf`，`ΔT(mean per shot) = −104.9`，gates `all met`。
- `rishabhbafnaiiitd/frontier-quantum-circuit-compilation` 把 `DQI_HW30_SHA = 35fa5ef9…` 写进
  VERIFIED_PINS，并给出 expected ratio **70.572×**（`5f901c55` 是 70.5519×）。
- `ratnachand/vqcc-verified-public-floor`（2026-11-18T15:45Z 版本，标题即“each re-checked with
  the official verifiers at full shot counts”）整包就是 `d0227f3c` + `35fa5ef9` + `4d63be3d`。

## 预期分数

| dqi ΔT | mean T | dqi 成本 | ratio | GM |
|---:|---:|---:|---:|---:|
| −104.93 | 367,005.236 | 346,305,191,933 | 70.57204 | **28.20311** |

与 `58514074` 的 28.20041 相比：**+0.00269 GM**；榜面 28.20311 在 2026-11-18T16:00Z 快照对应 rank 100–108
（我们当时 134，28.20041）。

## 18 成员 SHA-256

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
35fa5ef9a2bf21e423b47cab71579d451d7827225b6ecc8c655fa2c2ce0c2ba4  dqi.kmb
d0227f3c548ae7f1a409159a143cf4a401de56a2414a5230a3efc4b38e0a8160  invsqrt.kmb
```

- 打包：`submission.zip`，**49,432,877 B**，SHA-256
  `d7b97b31609aa72ab5fb232bbedf366dd204c742064567a9de2526be1cb2838f`（DEFLATE level 9）。
- 成员来自 `ratnachand/vqcc-verified-public-floor`（54,917,284 B 数据集 zip，18 成员哈希与上面逐项一致）。

## 验证范围

- invsqrt `d0227f3c` 与 chem `4d63be3d` 已在 ref `58514074` / `58496528` 中由本账号用未改官方
  verifier 全量复核（200,540,928 / 78,080 shots，PASS），文件逐字节相同。
- DQI `35fa5ef9` **独立复核完成**：内核 `jiyujia/qcc-dqi-hw30-verify` **v2**（CPU only，
  `enable_gpu=false`、`enable_tpu=false`），未改官方 verifier，**102,400 shots**：

  ```json
  {"status":"PASS","score":346305114280.16675,"m":4095,"n":70,"degree":12,"r":2016,
   "verified_shots":102400,"value_errors":0,"phase_errors":0,"empirical_error_rate":0.0,
   "effective_error_rate":0.0008660587301657926,"log2_delta":-128.0,
   "repetition_factor":1.1912604648115832,"mean_error_weight":31.046737331746634,
   "toffoli_count":367005.1539746094,"max_toffoli_count":367867,
   "reaction_depth":40105,"num_ops":57520375,"num_qubits":890,"num_bits":66730,
   "circuit_sha256":"35fa5ef9a2bf21e423b47cab71579d451d7827225b6ecc8c655fa2c2ce0c2ba4"}
  ```

  对比 `5f901c55`：mean T **367,110.166 → 367,005.154（−105.012）**，`max_toffoli_count`
  367,983 → 367,867，cost **346,404,203,610.11 → 346,305,114,280.17**（−0.0286%），Q 仍 890。
- 用本账号已复核的 invsqrt/chem 复算 GM = **28.20312**（28.2004255 × (346404203610.11/346305114280.17)^(1/3)）。
- 公开侧三处独立记录（hedge README HW-30、rishabhbafnaiiitd 的 `DQI_HW30_SHA`、
  ratnachand 的 “full shot count” 整包）都指向同一 SHA 与 −104.9 T，与本次实测 −105.01 T 一致。
- 本包只换件，不改官方 verifier；榜单成绩以 Kaggle 回执为准。
