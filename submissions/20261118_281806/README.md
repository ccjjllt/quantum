# 2026-11-18 候选包：invsqrt `563d0583` + DQI `575b043f` + chem（18 成员官方 PASS）

**状态：已端到端官方验证 PASS，等待提交名额（UTC 00:00 = 北京 08:00 重置）。**
内核 `qingyu1232/qcc-integrator-281806` v1，manifest
`experiments/frontier/20261117_deep/integration/members_281806_correct.json`。

## 三条腿（installer 实测 JSON，未改动官方 verifier）

| 腿 | 件 | 官方 cost | Q | T | 错误 |
|---|---|---:|---:|---:|---|
| invsqrt | `563d0583` | **74,560.90687312803** | 44 | 1,454.0008 + T/4 | 200,540,928 shots PASS |
| DQI | `575b043f` | **346,409,762,292.7187** | 890 | 367,116.057 | 0 value / 0 phase |
| chem | `a73b25d2` + 15 loaders | **294,643,137.73357135** | 427 | 14,706 | PASS, λ_eff 46.9217168 |

几何平均 **GM = 28.18065942104198**（`scripts/gm.py` 复核 28.18066）。

zip：85,016,504 B，sha256
`2271b861eb44628f45e2bcbf836c1f41b8bc34446389849776817328ba800eb5`
18 成员；`dqi.kmb` sha `575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155`。

## 提交

```bash
kaggle competitions submit -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-integrator-281806 -v 1 -f submission.zip
```

**已排定自动提交**：`submit_at_reset.sh`（后台运行，日志 `submit.log`）在 UTC 00:00
名额重置后（北京 08:00）执行上面这条命令，最多重试 3 次，随后把 `competitions submissions`
的成绩追加到同一日志。取消：`pkill -f submit_at_reset.sh`。

- 11-17 UTC 当天 5/5 已用（01:36 / 02:13 / 02:43 / 03:23 / 09:29），所以之前
  `CreateCodeSubmission` 返回 400；内核输出里 `submission.zip` 已确认存在且 sha256 与回执一致
  （`qingyu1232/qcc-integrator-281806` 输出，85,016,504 B）。
- 同一 DQI 件 `575b043f` 在 58464076 那次提交拿到 LB 28.15094 = 其本地 GM，
  说明榜单 salt 对它是干净的；本包只把 invsqrt 从 `0af21cb8`(74,797.37) 换成
  `563d0583`(74,560.91)，预期 LB ≈ **28.1807**。

## 第三轮研究结论（为什么暂时只有 +0.03）

tape 的 Toffoli **100% 闭合**：EEA 两趟 317,748（7,565 个 GF(2¹²) 域乘法 × 42）
+ Chien 44,264（4,024 × 11）+ 相位 5,977 = 367,989。乘法秩 42 是 F₂ 上最好已知值
（33 是 F₄ 的数），对齐/桶形移位不存在，块级冗余为 0。详见
`experiments/frontier/20261118_push/SUMMARY_R3.md`。

到 31.4 的缺口 = EEA 的**商项调度**：现役是整除调度（每步 δ+1 项、Σ(δ+1)=104/35 步），
归一化 divstep（每步降 1 度、商恒为标量）把每趟乘法从 3,648 降到约 1,700–2,450，
T ≈ 195k–259k ⇒ GM **31.5–34.2**（榜首 31.427 正落在这一档）。这是生成器级工作，
落地的 tape 手术与验证通道已就绪（`dqi_patch/`，null-splice 逐字节可复现）。

提交前确认 receipt 中 `dqi.value_errors == 0`（本包已满足）。

## 更正说明

前一份回执（`submissions/20261117_inv563d0583/`）声称 GM 28.1806，但实测 zip 里装的是
`957d6733`（默认 salt 1 个 value error，GM 28.1310）。本包才是真正的 28.1806。
