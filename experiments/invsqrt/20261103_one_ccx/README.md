# 62Q 基线上的真实 AND 缓存与相位选择补丁

日期：2026-11-03（北京时间）。分支 `invsqrt-generator-rebuild`。
目标已完成：在固定 62Q 基线上得到真实可生成补丁，精确期望平均节省
`278527/262144 = 1.0624961853027344` 个 CCX 等价门；独立等价/成本证明及
两个 seed 的完整官方本地验证均通过。最终候选为
`artifacts/20261103_one_ccx/invsqrt/joint_tail_combined.kmb`。
这是约 0.0656% 的实际本地资源改善，尚非 5% 级改进。
未提交 Kaggle，未修改官方验证器。

## 基线与改写

基线是 `artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb`，62Q，
SHA-256 `bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47`。
不是 132Q 独立生成器。全部 68 条 Z_POW（其中 41 条一般旋转）原文保持。

实际改写窗口为基线半开区间 `[47113,47186)`。该段在外层 `~b318 & ~b319`
中，分别由 b320 和 b322 控制的两次修正会计算相同 AND 前缀。

- `two_and`：第一次计算后将两个积复制到已经清零的 q34/q35；第二分支
  若 b320 已执行则用 CX 复用，否则仍执行原 CCX。最后 HMR 缓存并用 CZ
  修正全部测量结果的相位。
- `three_and`：再把首次 CCZ 改成等成本 CCX+CZ，在闲置 q36 保留第三个积；
  第二分支同样复用，最后清理三条缓存线。
- 新增经典位 b90001…b90004 与基线无冲突。辅助量子线没有增加，最终全部归零。

独立成本证明：当 `~b318 & ~b319 & b320 & b322` 成立时，分别少执行 2 / 3 个
CCX；其他分支成本差为零。四个逐级 HMR 结果独立均匀，故期望节省为
`2/16 = 0.125` / `3/16 = 0.1875` Toffoli-equivalent/shot，期望分数下降
7.75 / 11.625。**不是平均省下 2 / 3 个 CCX，也不是静态总门数下降。**

## 生成与证明（手动）

生成代码 `discrete_window.py` 的 `--tail-cache` / `--tail-cache-extended`，
分别输出 `artifacts/20261103_one_ccx/invsqrt/tail_cache_{two,three}_and.kmb`。
原始局部证明包括任意入口量子值、全部旧/新增测量结果、输出量子线、旧经典位、
条件栈与总 π 相位；清洁入口分别证明。

`audit_tail_cache.py` 是第二套独立解释器，直接读取实际原/新 KMB，
不导入生成器或旧 patch62 证明器；按输出经典位名和版本对齐 HMR，检查
真实 diff、相同前后缀、全部 Z_POW、事件执行条件、恢复、总相位和精确分支成本。
两套 miter 均 UNSAT。详见 `audit_tail_cache_{two_and,three_and}.json`。

```sh
uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/discrete_window.py --tail-cache
uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/discrete_window.py --tail-cache-extended
uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/audit_tail_cache.py --candidate both
```

候选 SHA-256：

| 版本 | 规范 KMB SHA-256 |
|---|---|
| two_and | `d155f0c8a1ef65e4cf85eb45ab06bdf016e63299b98e205df301c9b7b86ca89a` |
| three_and | `c2c255036961fcddbbabca84c231d4101ae928cbf34ae9a3da75926b7b665a0f` |

## 实际模拟与完整官方验证

`compare_candidate.py` 手动比较每候选 21,760 输入 × seeds 101/202/303。
两候选均没有输入恢复失败、scratch 残留、相位差或容差失败。
输入含 1…4096、随机输入、归一化/地址边界，并显式补入 max_x 重复输入凑满 batch；
不是全域验证。新增 HMR 会改变后续批次随机流，因此小样本成本差不是严格配对
分支差，不替代上述精确期望证明。

完整验证使用未修改官方文件，Python 3.12.13、macOS 原生 kickmix 1.0.0，
batch=256、shots_per_x=64、max_workers=4。通过 `scripts/manual_verify.py`
显式指定 seed。每次覆盖 200,540,928 shots。

| 版本 | seed 20261031 成本 | seed 20261101 成本 | 状态 |
|---|---:|---:|---|
| 原基线（已有同环境记录） | 100568.59044232983 | 100568.58506496616 | 两次完整 PASS |
| two_and | 100560.80035158835 | 100560.73193340242 | 两次完整 PASS |
| three_and | 100556.95211976506 | 100556.90399169168 | 两次完整 PASS |

two_and 的 Q=62、41一般旋转、最坏 x=161、误差比 0.9993237694056958、
rotation_eps=2.434041480874084e-13 均与基线一致。
日志为 `verify_tail_cache_seed20261031.log` 和 `verify_tail_cache_seed20261101.log`。
three_and 日志为 `verify_tail_cache_three_seed*.log`，两次进程均 EXIT=0。
其余量、最坏输入、41 一般旋转及 rotation_eps 同样保持不变。
相对同 seed 基线分别下降 11.63832256 / 11.68107327（约 0.0116%）；
观测等价门差 0.18771488 / 0.18840441，与理论 0.1875 的小偏差来自随机执行计数。
完整对比与命令、环境、验证器哈希保存在 `three_and_official_comparison.json`。
上述 4 次运行共 802,163,712 官方 shots，不包括以前的基线验证。

## 有限输入域上的相位选择压缩

`phase_cache.py` 生成了独立候选 `phase_last_selector.kmb`，只改基线
`[28345,28783)`。完整前缀 SSA 证明 `q27 & q21` 只可能在 x=1、2、3 成立，
并证明这三个输入的 19 条 word 线对任意前缀测量结果都有固定值。
这些值由常数及 q14/q16 张成，因此用经典 XOR 聚合原 19 个系数，
把量子选择器改成 2 个系数及一个免费的 CZ 常数项。

原 19 个系数来自 28 个独立无条件 HMR，GF(2) 秩为 19；新两个系数秩为 2。
精确期望收益为 `(1−2^-19)−3/4 = 0.2499980926513672` 等价门/shot。
没有新增量子线或测量，全部 Z_POW 不变。实际窗口由 438 条操作减到 44 条。
第二套 `audit_phase_cache.py` 直接读取实际 KMB，独立重建完整前缀及实际窗口，
其域约束、word 值、旧经典位、量子输出、条件栈、相位及成本公式 miter 全部 UNSAT。
证据在 `audit_phase_cache.json`；该独立审计不导入生成器。

候选 SHA-256 为 `e30937769d6245c405e9933336e57e8d1701aeb0d67e42dc0133f490a4fbbabe`。
三 seed 共 65,280 个实际样本均无恢复、scratch、相位或容差失败。
本条记录写入时，单独的相位候选未跑完整官方验证。

`combine_candidates.py` 将该候选与 `three_and` 按不相交的基线窗口合并，
输出 `phase_tail_combined.kmb`，SHA-256 为
`6384951a562337d34d365653f43a7b7584f7b67af4fae4d6c899b51e6e0a76bf`。
合并后 62Q、46,886 条操作，理论期望省 `0.4374980926513672` 等价门。
新增经典位集合互不相交，三个 seed 共 65,280 样本也通过。
双 seed 完整官方验证均已 PASS（进程 EXIT=0），每次 200,540,928 shots：

| seed | 合并候选成本 | 比同 seed 基线下降 | 观测等价门差 |
|---|---:|---:|---:|
| 20261031 | 100541.44979485312 | 27.14064747671 | 0.43775237866 |
| 20261101 | 100541.40015744194 | 27.18490752422 | 0.43846625039 |

仍为 62Q、41 一般旋转、最坏 x=161、误差比 0.9993237694056958，
rotation_eps=2.434041480874084e-13。日志 `verify_phase_tail_seed*.log`；
完整环境、哈希、命令和对比在 `phase_tail_official_comparison.json`。
至此本轮 6 次完整官方验证共 1,203,245,568 shots，均为本地结果。

## 没有采用的尝试与范围

- `affine_probe.py`、`approx_window.py`：合法输入位并行发现，不把样本命中当证明。
  单个 CCX 的直接线性替代未找到跨种子的稳定候选。
- 之前两个窗口 W1/W2 在 4096 个合法输入、固定测量结果为零时，输出函数空间
  相对入口分别新增 3 个独立函数。这是该固定数据变换至少需要 3 个 CCX 的
  有限见证，故转向尾部跨分支缓存；不据此否定全电路优化。
- `search_window.py` 的小块仿射重综合未找到可用候选，受规模限制的项仍记未判定。
- 单门 CCZ→CZ/三条 Clifford 替代被真实合法前缀反例（例如 x=10、14）否决，
  未放入候选。对应 `discrete_proof_*.json`。

## 自适应联合选择器：跨过 1 个等价门的候选

`phase_cache.py --joint --prove` 输出 `phase_joint_selector.kmb`，替换基线
`[27775,28783)` 的两个选择器。候选 SHA-256 为
`7e2e2843bae6bc0b44063a9d2c4bedee63b4aca8031d78ce626606b91824057e`。
它替代上面的单选择器方案，两者不能重复叠加计费。

完整前缀证明共 65 项，全部 UNSAT：`q21=1` 蕴含 `x≤63`；q28/q40 对所有
合法输入和测量结果都为零；每个 x=1…63 的全部 62 条线都精确等于记录中的
truth table，与前缀任意测量结果无关。63 点采样只用于发现矩阵，完整前缀证明
才将该矩阵提升为普遍有效的窗口契约。

在这 63 点上，选择三种已有线的 XOR 奇偶 u，使常数、已有线与 u 乘已有线
张成 62 维空间。每种表示只缺一个方向，对应 29 个独立 HMR 源的一个经典
parity。三个失败 parity 线性独立。按顺序选择第一个适用表示：在 q28 上计算 u，
用一个 CCX 将 `q21*u` 放在 q40，以 Z/CZ 实现全部目标相位，HMR q40 并以
CZ 修正测量相位，最后逆 CX 清 q28。所有表示都失败时，执行原两个选择器。
新增经典位为 420xx，与尾部缓存 900xx 无冲突；不增加量子线。

独立成本核对：旧两个 mask 各秩 19，旧平均成本为 `2−2^-18`；三种表示全失败
概率是 1/8，且全失败与任一旧 mask 全零不相容。因此新平均成本恰为
`7/8 × 1 + 1/8 × 2 = 1.125`，净省 `0.8749961853027344`，不是仅有保守界。
与尾部 three_and 合并后，精确平均收益为 `1.0624961853027344` 等价门，
对应 62Q 成本下降 `65.87476348876953`。

`combine_candidates.py --joint` 输出最终合并候选 `joint_tail_combined.kmb`，
SHA-256 为 `04ea98e71a544f39d417f4414fae1e11551a673c1842dc5f3c98dc561bbd5e07`。
仍为 62Q、全部 Z_POW 不变；操作数为 50,020（Clifford 与经典操作增加，
所优化的是实际 Toffoli-equivalent 成本）。单独和合并候选各完成 65,280 个
实际 native kickmix 样本，全部无相位、恢复、scratch 或容差失败。
两个完整官方验证均已 PASS、进程 EXIT=0；每次覆盖 200,540,928 shots：

| seed | 同环境原基线成本 | 最终合并候选成本 | 降低 |
|---|---:|---:|---:|
| 20261031 | 100568.59044232983 | 100502.63923182432 | 65.95121050551 |
| 20261101 | 100568.58506496616 | 100502.6456404039 | 65.93942456226 |

相对改善约 0.0656%。最坏 x=161、误差比 0.9993237694056958、41 个一般旋转、
rotation_eps=2.434041480874084e-13 与基线相同。观测成本与理论均值的小差别
来自新增 HMR 对实际随机执行计数的影响，不改写为理论均值。
日志 `verify_joint_tail_seed*.log`，完整对比 `joint_tail_official_comparison.json`。
本轮 8 次完整官方验证共 1,604,327,424 shots，不含既有基线；这些均为本地结果。

独立 `audit_joint_resources.py` 已直接按实际 CCX/CCZ 的完整经典条件栈和
inline 条件逐门求概率，得到联合补丁精确收益 `229375/262144`、加尾部后
`278527/262144`。证据 `phase_joint_resource_audit.json` 含测量源独立性、
借线清洁、逐门方程及不相容性证明。
独立 `audit_joint_selector.py` 的实际分支 ANF、全部输出恢复、新 HMR 相位消去、
63×29 个来源方向矩阵恒等式和原选择器 generic Z3 语义检查已 PASS；
第二套完整前缀 65 项证明也已全部 UNSAT，最终独立审计状态 PASS，
详见 `audit_joint_selector.json`。它使用独立 BitVec22 输入域及 SSA，
不导入候选生成器；完整前缀和 emitted-phase 两部分都覆盖任意测量结果。
生成侧 `--joint-certify` 也已执行 PASS，核对 87 个 source-vector 的 GF(2)
分解、一般缓存的量子恢复与 HMR 相位消去、8 种失败 parity 的选择覆盖，
并在内存重建相同 KMB 字节。命令、环境、时间及最终脚本哈希记录于
`phase_joint_selector.json`；归档后已重新运行资源审计，结果仍 PASS。

手动复现命令：

```sh
uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/phase_cache.py --joint --prove
uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/phase_cache.py --joint-certify
uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/audit_joint_selector.py --prove
uv run python experiments/invsqrt/20261103_one_ccx/audit_joint_resources.py
uv run python experiments/invsqrt/20261103_one_ccx/combine_candidates.py --joint
uv run python experiments/invsqrt/20261103_one_ccx/compare_candidate.py artifacts/20261103_one_ccx/invsqrt/joint_tail_combined.kmb --output artifacts/20261103_one_ccx/invsqrt/joint_tail_combined_sample.json
uv run python scripts/manual_verify.py invsqrt artifacts/20261103_one_ccx/invsqrt/joint_tail_combined.kmb --seed 20261031 -- --max-workers 4
uv run python scripts/manual_verify.py invsqrt artifacts/20261103_one_ccx/invsqrt/joint_tail_combined.kmb --seed 20261101 -- --max-workers 4
```

本轮小目标至此完成。后续若继续研究，应以这个已验证的 62Q 合并候选作为工作
基准，保留原公开基线用于比较；本轮结果不代表已证明全局最优。
