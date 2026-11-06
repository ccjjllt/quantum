# DQI 文献与开源算法适配审计

日期：2026-11-06（北京时间）。研究对象为 Syed V9 的 892Q 电路；不是从官方参考电路出发。外部资料均核对原始论文或作者仓库。本记录没有提出已通过完整 DQI 验证的新候选。

## 结论与成本口径

最值得短预算实证的是**保持现有接口的重复算术核联合重综合**；最值得生成器级研究的是**恢复调度、可重建状态与测量纠相共同设计**。新文献能提供不同于旧删除扫描的搜索空间，但尚不能证明当前电路存在高额可兑现收益。已取得并独立证明一个 42-CCX 的完整 GF(2^12) 乘加核，提供了可复用工具；它不是 Syed 25T `inverse12 products` 的可直接替换物。

比赛目标为 `R × Q² × mean Toffoli-like`。以下使用本地 256 普通输入的 `meanT=395395.47265625` 定价，保持 R 时，总 GM +0.1% 需约1184门；增加1Q需先省约885门，减少1Q可增加约888门仍打平。只有静态核门数时必须说明执行频率；不能把论文的 T-depth、CNOT、T-count 或 `T×Q` 改善直接当比赛收益。

本轮 `stage_census.json` 确认总静态计费395679，标签无异常。当前有标签的重复项为 `inverse12 norm/products/scalar` 各163次、每次15/25/18 CCX；`inverse24 norm/products` 各23次、每次42/70；`inverse24 scalar` 的58T由嵌套的inverse12组成，不能再与其子项相加。`multiply v` 为6×99。未标细节的恢复段很大，这些不是全机算术调用总数。

## 1. 首选短实验：联合张量重综合，保留低宽度接口

Khoruzhii、Gelß、Pokutta 的 [PolyTOF 论文 v2](https://arxiv.org/html/2602.15285v2)（2026-10-26）直接最小化 cubic phase 的 CCZ 数，并提供 bilinear tensor 路径。其 Table 3 的任意累加器 `c += a*b` 使用 GF(2^12)42 CCX、GF(2^6)15 CCX；允许输入寄存器和累加器内部改变线性基。作者实现 [ZIB-IOL/polytof](https://github.com/ZIB-IOL/polytof/tree/0dcac107d15adc34dc646242d222f21ae7d32699) 固定至 `0dcac107d15adc34dc646242d222f21ae7d32699`，2026-10-21，MIT；旧地址 `khoruzhii/polytof` 已迁移。

**本地新增证据。** 从固定版本取得 `data/paper/circuits/gf2p012.qc`，其域多项式是 `t^12+t^3+1`。自写 ANF 解释器仅读取门文本，未执行上游程序。逐门传播36个输入变量的精确布尔多项式，验证全部输出等于 `(a,b,c+a*b)`：**42 CCX、308 CX、36线、0 ancilla、0输出失配、最高次数2**。这是涵盖全部 `2^36` 基态的代数恒等验证，不是随机采样。无相位门和测量，因此不涉及遗漏测量纠相。换成比赛域的线性同构尚未构造，也未证明能代入任何 Syed 窗口。

**同轮实际结构核查已进一步缩小对象。** `kernels/structure.json` 对Syed原始窗口全边界独立变量传播ANF：五个算术窗口都为不变输入加到任意累加器的二次/仿射函数，所有delta都不依赖被改输出。`inverse12 norm` 的二次图可分为6+6输入，`multiply v`可分为24+24；这是可直接建立三分组bilinear tensor的实际证据。`inverse12 products`为18输入/12输出、25CCX，`inverse24 products`为36输入/24输出、70CCX，但二次图在当前基下非二部，不能直接宣称是两组独立乘数的tensor。可对后两者做“输入×输入→输出”受限二次MAC分解，输出不得进入输入parity，也不得引入H gadget。delta中的线性项单独保留。未证明每次同名调用都具有同一ABI，后续需逐实例核对。

可证伪的小实验现已变成：先对抽出的 `inverse12 norm`/`multiply v` tensor做保持接口的bilinear搜索；对products做受限二次MAC或允许换输入基的联合分解。允许新分解先增加中间项再下降，不局限删除现有门。旧“删1至4无解/2→1无解”不排除这类重综合。没有新分解前，只有适配结构已证实，节省门数仍未知。

定价门槛：同一合法窗口每次省1门，仅带来163门；省8门为1304门，才超过上述GM+0.1%量级。**8门是投入价值门槛，不是预测能达到。** 有标签products总计4075门，对它寄望数万门不合理；需收益出现后才查未标记的同构核。若只重排CX或降低T-depth，比赛直接收益为零。

合法落地范围：标准 PolyTOF 一般Clifford路径可能引入H或额外Hadamard gadget。kickmix DQI不能直接接受此类全局替换。可用范围限于能还原成X/CX/CCX的三分组双线性映射，或直接作用于原线路的CCZ phase块；必须保留低阶phase项与全末态映射。不能把整个58M操作程序直接送入一般优化器并认定输出合法。

## 2. 次选短实验：稳定单控制的整块线性网络

Kim、Laakkonen 的 [arXiv:2512.24982v1](https://arxiv.org/html/2512.24982v1)（2025-12-31）给出：对n线CNOT网络整体加一个量子控制，可无ancilla构造成至多n个Toffoli（用矩阵有理标准形得更细的n−c），而非逐个CNOT提升为CCX。它是计费门数结果，区别于论文另有的降低深度但加门方案。

对 Syed 的对象应是**控制线在整个窗口保持不变、除控制外整体是可逆线性/仿射映射**的窗口。提取其两支完整GF(2)矩阵；若原付费数大于n，则理论上存在可降门实现。若有多个控制、测量、控制线被写，或子块本身含变量×变量乘法，则不满足该定理。应先枚举合格窗口并汇总 `max(0, old_paid−n)` 的保守可证节省，再决定是否实现综合。

收益判据：仅省几十门不足高收益目标；相同控制网络重复数乘每窗差值需到约1184门，且新增全局Q须为零。特别地，`aligned_route` 6240个CSWAP不能直接算成大机会：n/2个独立SWAP的受控版本本来就只需n/2个CSWAP，n上界更差。旧full_head控制churn的结论也不能被此论文推翻。当前尚未找到并证明Syed存在满足超界条件的窗口。

## 3. 生成器主线：恢复表示与测量纠相共同重写

Jeon、Huang、Cai 的 [arXiv:2609.31605v1](https://arxiv.org/html/2609.31605v1)（2026-09-25）用垃圾支撑的仿射秩描述测量诱导phase；在所给结构条件下，可根据测量outcome选择不同的纠相oracle。式(25)的无更优纠相fallback平均成本上界为 `(1−2^−r) C_U`，收益依赖有效秩r，不能笼统称反计算“免费”。

适配重点：给一个恢复子块写出垃圾函数 `g(x)`、仍活跃的输入/表示以及需要的phase `m·g(x)`，直接综合后一标量函数，避免先恢复整个g再抹除。父方向的 `convert/unconvert` 与 `unextract` 合计约220148静态门；若其中真实计费恢复工作能降1%，规模约2201门，但这个比例仍是假设，须从一个可证明子块开始。

这里要优化**确定性纠相或精确定价的稀有错误**。不能照搬纯post-selection后丢弃shot：比赛会把未修正phase计入失败，并有其自己的R。r=12时仅跳过零测量综合症的fallback保证是1/4096，通常不值重新设计；低秩垃圾与廉价测量分支才有价值。现有小门MBU扫描没有找到真uncompute，说明需改变值的表示/生命周期，而不是再次删除HMR附近CCX。

基础来源 [Gidney 2018, arXiv:1709.06648v3](https://arxiv.org/abs/1709.06648v3) 的临时AND与 [Luongo等 2024 v1](https://arxiv.org/abs/2407.20167v1) 的模整数加法MBU提供机制，但Syed已经采用MBU。它们的加法百分比不是GF(2^12)解码器的增益预测。

## 4. 生成器主线：按真实节点成本做测量辅助pebbling

Lee、Lee、Jeong 的 [arXiv:2610.09434v1](https://arxiv.org/html/2610.09434v1)（2026-10-07）研究二叉依赖树的spooky pebbling，用分块清理减少重复重算，给出空间—工作量边界；RNS椭圆曲线示例在同峰值空间下降约21–23%门。该比例只属于其树与算术实例，不能套用DQI。

本地可执行问题：还原一个 retained-head/prefix-jump 恢复子图，给每节点标注真实Toffoli、占用qubits、哪些phase债必须偿还，在Q≤892和允许+1/+2Q下枚举少量边界checkpoint。顺序链与共享DAG不是论文的完整二叉树，因此需用其清理思想，不能套其渐近最优性证明。重点减少恢复阶段“同值重算次数”，而非减少免费CX或单纯并行深度。

最小收益接受条件仍是全局Q²T下降；若从892减至891，重算总代价须低于约888 meanT。六个阶段达到892Q，改善一个局部峰不够。因为840输入线占主体，通用pebbling“省90% ancilla但多3至4倍门”的路线很可能整体更差，应在投入实现前用相同全局宽度换算。

## 5. 不应优先投入的看似先进方向

- [AlphaTensor-Quantum，Nature Machine Intelligence 2025](https://www.nature.com/articles/s42256-025-01001-1) 优化T-count且可能依赖gadgets；[作者仓库](https://github.com/google-deepmind/alphatensor_quantum)公开说明完整src不是直接可运行训练管线，仅demo可运行，转换器另在[circuit-to-tensor](https://github.com/tlaakkonen/circuit-to-tensor)。先用PolyTOF或现成分解做小核实验，不能假定重训RL就有大收益。
- [Vandaele 2025 v1](https://arxiv.org/abs/2501.16136v1) 与 [Yosri/Gavinsky/Maslov 2026 v3](https://arxiv.org/html/2511.20618v3) 的大域乘法/除法工作以深度、CNOT或`10×Toffoli+CNOT`为主要目标；后者明确用更省CNOT的多项式与addition chains。DQI的CX免费，m=12很小，当前又是tower/特化算术，不能由大m渐近结论推算收益。其PCTOF与加法链思想可用于重建接口后的比较。
- [Vandaele ZX qubit优化 v1](https://arxiv.org/abs/2407.10171v1) 可保持非Clifford数降低width，但主要处理H gadget/ZX结构。当前电路无H且841以上工作线生命周期密集，通用ZX导出未必仍在kickmix门集内，不宜替代对q891实际37个冲突区间的研究。
- Gu等 [arXiv:2610.22367v1](https://arxiv.org/abs/2610.22367v1) 公开RS生成器值得拆算术核与恢复不变量；其整体442397T/1837Q、固定mask和量化权重契约不等于比赛，整体替换不划算。详见本轮算法及公开实现记录，避免重复计入收益。

## 复现与证据范围

```sh
.venv/bin/python experiments/dqi/20261106_high_return_research/verify_gf12_anf.py
```

真实运行结果为 `exact_anf_match=true`，42 Toffoli、308 CNOT、0失配。上游QC与MIT许可保存于 `artifacts/20261106_high_return_research/literature/`，源路径固定版本链接为 [gf2p012.qc](https://github.com/ZIB-IOL/polytof/blob/0dcac107d15adc34dc646242d222f21ae7d32699/data/paper/circuits/gf2p012.qc)。脚本保留在实验目录，可从源电路重新生成ANF核查JSON。

这轮仅做资料研究、源电路文本读取与局部精确代数检查；未构建或运行PolyTOF搜索、未生成Syed替换候选、未运行完整官方verifier、未提交Kaggle。文献“可用的工具/理论”与“本电路可兑现收益”是不同证据等级。
