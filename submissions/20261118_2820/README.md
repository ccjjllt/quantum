# 2026-11-18 公开前沿 28.20042 包（invsqrt `d0227f3c`）

**状态：COMPLETE，public 28.20041，rank 120 / 3327（ref `58514074`，2026-11-18T14:46:45Z）。**

- 上一版 ref `58496528`：28.18965，rank 224（同日 14:40Z 快照）。
- 增量：**+0.01077 GM，名次 +104**；银线为前 5%（166 名），当前在银线内 46 位。
- 榜单按 5 位小数显示 28.20041（本地 GM 28.200418239，截断一致）。

## 来源

只换件：相对 ref `58496528`（28.18965）**只替换 invsqrt**。

| 腿 | 件 | Q | 成本 | 来源 |
|---|---|---:|---:|---|
| invsqrt | **`d0227f3c`** | 44 | **74,405.73**（作者官方 full-shot PASS） | maoxin123，notebook `qcc-28-20-4-022-toffoli-chemistry-loaders` **v4**（文件以 base64 嵌入代码），生成器线归 Syed Asad Ali |
| DQI | `5f901c55` | 890 | 346,404,203,610.1118 | boristown 的 PW4 补丁 + Grant Prater 的解码器 |
| chem | `4d63be3d` + 15 loaders | 427 | 294,642,170.565169 | leotang09 refit + maoxin123 4,022-Toffoli loaders |

公开侧交叉证据：`asteriospanoras/qcc-28-20041-lb-what-works-what-fails-and-why`（v23）
自称重建并复核同一组合、榜单 **28.20041**；本包采用更便宜的 chem `4d63be3d`
（该 notebook 用的是同一件），因此本地复算 GM **28.200418**。

## 预期分数

invsqrt 74490.94707587373 → 74405.73，单腿因子 `(74490.947/74405.73)^(1/3) = 1.000381622`：

| 版本 | invsqrt | GM |
|---|---:|---:|
| ref `58496528` | 74,490.947 | 28.189660448 |
| 本包 | 74,405.73 | **28.200418239**（+0.01076） |

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
5f901c556cafd02dc11641eee7766171a454e3a0b6687d890ff9f99944e1934c  dqi.kmb
d0227f3c548ae7f1a409159a143cf4a401de56a2414a5230a3efc4b38e0a8160  invsqrt.kmb
```

- 打包：`artifacts/candidate_2820/` → `artifacts/candidate_2820_l9.zip`，
  **49,434,074 B**，SHA-256 `f57f2b4207364d4c4a2c8baeb4b9607772d1509ad93526eef28c48729fc1a31c`。
- 注意：提交 API 要求文件名必须是 `submission.zip`；同内容改名为 `candidate_2820.zip` /
  `candidate_2820_l9.zip` 会返回 `400 Bad Request`（两次尝试被拒，未产生提交）。

## 验证范围

- DQI `5f901c55` 与 chem `4d63be3d` 已在 ref `58496528` 中由本账号用未改官方 verifier
  全量复核（102,400 / 78,080 shots，0/0 与 PASS），文件逐字节相同。
- invsqrt `d0227f3c` **独立复核完成**：内核 `jiyujia/qcc-invsqrt-d0227f3c-verify` **v4**
  （CPU only，`enable_gpu=false`、`enable_tpu=false`），未改官方 verifier，**200,540,928 shots**：

  ```json
  {"status":"PASS","score":74405.67238374705,"toffoli_equivalent":1691.0380087215237,
   "toffoli_count":1451.4360825387225,"max_toffoli_count":1549,"t_count":3.999899935638076,
   "rotation_count":33.0,"rotation_eps":2.0054235445130315e-13,"num_qubits":44,
   "reaction_depth":1235,"num_ops":20526,"verified_shots":200540928,
   "worst_error_over_tolerance":0.9994556024653497,"worst_x":231,
   "circuit_sha256":"d0227f3c548ae7f1a409159a143cf4a401de56a2414a5230a3efc4b38e0a8160"}
  ```

  与 `864f81cd` 对比：`toffoli_count` 1453.374 → **1451.436**（−1.938），`max_toffoli_count`
  1548 → 1549，`t_count` 4.00009 → 3.99990，33 rotations 与 `rotation_eps` 不变；
  44Q 不变。官方复核值 **74,405.672** 比作者公布的 74,405.73 还低 0.058。
- 内核内同时重算了 18 个成员的 SHA-256，与上表逐项一致（含 `d0227f3c`）。
- 本包只换件，不改官方 verifier。Kaggle 回执 `COMPLETE`，public **28.20041**。
