# 状态快照（2026-11-18 06:20 北京）

## 一句话

公开件已到算法下限；**今晚提交 28.1807**；31.4 需要新一代解码器（2–6 周）。

## 正在发生的事

- **提交**：`submissions/20261118_281806/submit_at_reset.sh` 已后台运行（PID 18028），
  UTC 00:02（北京 08:02）名额重置后提交 `qingyu1232/qcc-integrator-281806` v1 的 `submission.zip`；
  失败自动改走本地 zip；日志 `submissions/20261118_281806/submit.log`。
- **包**：GM 28.18065942104198，18 成员 sha 全对，zip sha `2271b861…`（已二次下载核对）。

## 三条腿（官方 verifier 实测）

| 腿 | 成本 | Q | T | 参考 | 比值 |
|---|---:|---:|---:|---:|---:|
| invsqrt `563d0583` | 74,560.91 | 44 | 1,454.0 | 2,076,774.23 | 27.85× |
| DQI `575b043f` | 346,409,762,292.72 | 890 | 367,116.06 | 24,439,463,583,672.93 | 70.55× |
| chem `a73b25d2` | 294,643,137.73 | 427 | 14,706 | 3,355,599,588.32 | 11.39× |

## salt 鲁棒性（新测）

4 个 salt：3 个 0/0；`s2` 有 1 个 value error（rep_factor 1.1913→1.1967，整腿 +0.46%）。
若榜单落到这种 salt，GM 28.181 → 28.138。但 58464076（同一个 `dqi.kmb`）的 LB 28.15094
与其本地 default-salt GM 完全一致 ⇒ **预期 LB = 28.1807**。

## 已关闭的轴（12 条，全部实测）

initial shift / 块级冗余 / 乘法秩 / 归一化 divstep（贵 12×）/ 数组冗余 / qubit-for-uncompute（差 2.4–2.7×）
/ 参考 2 数组形式（贵 1.5×/行）/ Chien 下限 / chem brot·C·J·loader / reset 省 uncompute（flag 会漏相位）
/ chem loader uncompute（已是 MBUC）/ 反向多出的 367 行（= pool 清理，必要）。

## 榜单反解（Q=890，另两腿用我们的）

#1 264,691（−27.9%）；#6 304,934（−16.9%）；#10 339,478（−7.5%）；公开件 367,116。

## 下一步（按顺序，详见 WORKPLAN_31.md / FINAL_R3.md）

1. 统一「每步几行」的口径（三份实测不一致）。
2. 小参数上把 divstep 的相位通路跑通（`dqi_gen`：EEA 已对，卡在 MBUC gadget 的相位）。
3. 新生成器必须：每步 ≤2 逻辑数组、≤n+1 步、无每步除法、Chien 11 T/位置、Q ≤ 890。
4. 落地通道：`dqi_patch/splice.py` + `k_patch`（注意 verifier 要 `PYTHONPATH=COMP/kickmix`，
   解释器用 `sys.executable`，cwd=COMP/verifiers）。
