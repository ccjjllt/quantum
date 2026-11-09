# DQI 研究入口

当前公开比较基线：Public Frontier `4432ec5f`（892Q，静态 395,641，
默认 salt 成本 374,735,446,628.53）。每静态门 ≈947,843 分；
单失败 shot 边际 ≈1,721,030,308 分（+0.459%）。

## 2026-11-09 研究概况（全部 closed，无正收益）

| 实验 | 结论与放弃原因 |
|---|---|
| `20261108_frontier_audit` | −38 门三步拆解（Ozer −21/Kirill −14/Isabe −3）；HMR 窥孔已清零 |
| `20261109_affine_cache` | 跨阶段污染 bug 已定位；修复后 strict/mask 重复仍 0；自仿真 bug 根因 HMR 随机化 |
| `20261109_dqi_deepfix` | 仿射 141/1030 全 distinct 0 重复；368 组字面不同函数同但载体 0/1618；w17 净 −2.2e7（±175），不实施 |
| `20261109_dqi_dirtyk2` | 脏持有语义错误（toy 实测污染）；正确模型每处 +1；k>2 可行 0/192；CCZ 重复 0 |
| `20261109_dqi_decoder_struct` | 阶段特征全已存在；`(120,859):234` 广播 0/233 稳定；退路 84 对净 +7.6e8（负）；片段 diff 仅切片证据 |
| `20261109_dqi_r_nonw17` | 默认 salt 0 失败无分布；node-3 期望 3e-11；inverse24 0.42/102400 吻合残余；守卫净 +1.68e9（负） |

## 2026-11-09 清理
删除：5 个实验目录的分析脚本（`affine_clean.py`、`probe_affine.py`、
`step{1,1b,1c,2a,2b,3,3b,3c,3d,3e}_*.py`、`{a,b,c}_*.py`、`s{1..7}_*.py`）、
`20261109_subagent_research/diff_v9_to_frontier.py`（已过期）、
artifacts 内 `sim_out.pkl`（35M，buggy 仿真输出）、`lit_*.pkl`、
`a_groups.json`、`s1_blocks.json`（结论已记入 README；快照提交保留历史）。
保留：各 README、机器可读小 JSON（`affine_groups.json`、`step*.json`、
`s*_cache/guard/broadcast.json`、`a_fail.json`、`s7_broadcast.diff`、
`baseline_2048shot.json`）、本入口文件。
后续唯一切口：换码族，或 72-salt 约 7M shots 的 R 实证（未执行，需算力）。
