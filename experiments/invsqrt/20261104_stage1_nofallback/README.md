# Stage1 无回退选择器（2026-11-04 实测）

> 保留有效历史方法及其证明。当前实现使用[公开基线迁移版](../20261104_public62_optimization/README.md)，
> 当前最佳候选见[invsqrt入口](../README.md)。

基线：`joint_tail_combined.kmb`（`04ea98e7…`，本地成本约100502.64）。
候选：`artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb`（`80ba3fef…`，62Q，49096 ops，全部68 Z_POW不变）。

## 改写

保留 trial1（`0x1cbc6090`）、trial2（`0x185ecd3`），第三个改用固定种子8121 trial40（`0x1d398c43 = 0x1cbc6090 XOR 0x185ecd3`，30线，残差`0x2`）。
三失败异或为零，`(1,1,1)`不可达，删除原双选择器回退（约924 ops），空回退分支零成本。

生成：`experiments/invsqrt/20261104_stage1_nofallback/stage1_nofallback.py`（显式接收基线路径/SHA，记录父SHA、旧窗口及内容长度）。
审计、资源、样本脚本均只读实际KMB，不导入生成器。

## 证据（全部手动实测）

- 独立等价证明 `audit_stage1_nofallback.json`：PASS。完整前缀65项UNSAT（q21→x≤63、q28/q40全零、63点全线）、三分支ANF输出恢复+HMR相位消去+相位含q21、原两选择器generic语义UNSAT、三失败互斥UNSAT。
- 精确成本 `audit_stage1_resources.json`：PASS。实际字节全条件栈计费：旧`524287/262144`（2-2^-18），新`1`，净省`262143/262144=0.999996…C`；加尾部三AND后总计`311295/262144=1.187496…C`。相对新基线（旧联合成本9/8）新增`0.125C`。
- 实际模拟 `stage1_sample.json`：seeds 101/202/303 ×21760输入，0恢复失败、0 scratch、0相位差、0容差失败，最坏x=161、误差比0.9993237与基线一致，观测节省约1.18–1.26C（含尾部）。
- 完整官方验证双seed各200,540,928 shots，均PASS（`verify_stage1_seed*.log`）：
  - 20261031：候选100494.89112607106，比同环境新基线100502.63923182432降7.7481（观测0.12497C）
  - 20261101：候选100494.89685789104，比100502.6456404039降7.7488（观测0.12498C）
  - 62Q、41一般旋转、rotation_eps、最坏x/误差比均与基线一致。对比见`stage1_official_comparison.json`。

## 结论

第一阶段交付完成：相对新基线新增`0.125C`（约7.75成本），累计相对原公开基线`1.187496C`。
该轮新增`2C`研究目标未达成。无收益Stage2副线已收官并清理，结论见
[清理记录](../20261104_cleanup/README.md)；后续跨HMR的2C收益单独记录。
未提交Kaggle，未推送代码，未覆盖历史基线。
