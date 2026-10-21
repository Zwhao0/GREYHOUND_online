# G1-01 两节点 DDP 采集结果（候选，等待独立审核）

2026-10-21（Asia/Shanghai），执行 [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 的更新授权。**G0 保持限定范围 PASS，未重复其完整验收；G1 总 Gate 仍 IN_PROGRESS。** 本次两机隔离升级、短烟测和四 Rank 被动采集已完成，结果提交 Draft 待 ChatGPT 独立审核。

[脱敏实测汇总及原始输入 SHA256](evidence/g1-01-summary.json)；[70 个实例的逐键匹配结果](evidence/g1-01-matches.json)；[包版本/分发 URL/哈希锁](../tools/g1_01_pylock.toml)。原始日志和 PID/GPU UUID 映射仅在私有目录保留。

## 环境选择与实际加载

两台获授权共享 H800 节点均为 Driver **580.178.04**。采用官方 **PyTorch 2.14.1+cu130 / CUDA runtime 13.0.96 / 配套 NCCL 2.30.7**，两机相同私有 Python 3.12 venv，30 包逐个核对 SHA256，`pip check` 均通过。2.14.1 是本次查询官方 cu130 索引可用的最新稳定 Torch；现有驱动下选择 CUDA 13.0，未为追更高 Toolkit 改驱动。没有独立覆盖 Torch 配套 NCCL 以追 2.32.3，也没有采用旧 Torch 2.7 环境代替升级。

每个训练 PID 在 communicator 初始化后、warmup 前读取 `/proc/self/maps`、对已加载 DSO 做哈希，并从同一 DSO 查询版本。smoke 2 + baseline 4 + plugin 4 个进程均已核实：

| DSO basename | 实测查询/ABI | SHA256 |
| --- | --- | --- |
| `libcudart.so.13` | runtime=13000，返回0 | `96c42e418cec19054186b9429c321603cc190bf26a18104e19408117a2a817b0` |
| `libnccl.so.2` | NCCL=23007，返回0 | `618968ee277041751512e619190132a9bdf351c3ce7129c73484f6ef441ad692` |
| `libnccl-profiler-example.so` | 官方 example，实际协商 **v4** | `3982ac146d710cfd3eca59e0c36fd1502790840211eb8f41c2d35934b51c9571` |

Torch版本来自同训练PID的 `torch.__version__` 与所安装官方wheel；未额外记录libtorch DSO哈希。原始归档保存进程内DSO哈希记录，不包含库二进制供离线复哈希。baseline 四进程没有映射 Profiler DSO。插件来自已审官方 `v2.27.7-1` example 原样构建；NCCL 2.30.7 的加载器支持 v4 回退。**这是新 NCCL 实际使用 v4 接口，不是 v6 collector 实测。** 固定源码、混合许可和构建依据见[来源记录](SOURCES_AND_LICENSES.md#g1-01-隔离升级依赖候选实测见独立摘要)。

## 执行与资源边界

用户已再次确认两台机器持续按共享资源使用。现场有驻留 vLLM，每卡空余约节点 A 2.4GiB、节点 B 5.2GiB；每机仅暴露两张 H800，OMP=1，Torch allocator 上限为设备显存的1%，单个 launcher 外层限时180秒、process group 超时60秒。真实 Torch 最大分配约96.3MiB/rank；此值**不含 CUDA context/NCCL，聚合 GPU 峰值 UNKNOWN**。未停止现有任务，收尾各节点原有8个 GPU 应用仍在，本项目训练进程剩余0；不据此断言共享服务延迟完全未受影响。

1. 新栈单节点只跑一次 **1 warmup +2 steps**：两个 Rank exit=0，forward/backward/SGD 正常，每 Rank 导出6条 Coll、81条 GPU channel；只作兼容性 smoke，不统计为重做 G0。
2. 双节点4 Rank：一次无插件 baseline、一次 plugin，各 **5 warmup +30 steps**；两个 launcher 每次均 exit=0。两层 Linear(1024,1024)+ReLU，随机输入[32,1024]，平方均值 loss、SGD；为本项目独立合成负载，不涉及生产模型或数据。
3. 没有额外诊断 collective；正常 DDP 初始化/梯度通信属于训练负载。仅 warmup 和测量末尾有 CUDA 同步，没有每 step 热路径同步。

旧 v4 example 只支持32个 channel。两组测试统一设 `MIN_NCHANNELS=1, MAX_NCHANNELS=32, MIN_CTAS=1, MAX_CTAS=32, NVLS_NCHANNELS=16`，清除旧 NRINGS 环境变量；实际捕获 channel 最大索引7。mask=66，仅 Coll/KernelCh（Group父链隐式采集），Proxy **NOT_COLLECTED**。Group/Coll 池各128，其他池各1；约1.28GiB/rank的 Coll 池为 Host 虚拟预分配，不能当作实际 RSS 增幅。

## 跨 Rank 身份与实例匹配

每个 plugin 进程完整日志恰有1个相同 WORLD comm 的 init/finalize，`nranks=4`，comm rank 分别0–3；与同 PID 的 Torch WORLD `[0,1,2,3]`、launch global/local rank、节点别名及私有 GPU UUID 交叉核对。四个 GPU UUID 互异，NCCL 日志均报告 `nNodes=2`、所选 network=`IB`。这里只报告 NCCL 的传输选择，不披露内网地址、接口或物理拓扑。

| 节点别名 | Global rank | Local rank | Comm rank |
| --- | --- | --- | --- |
| node-a | 0 / 1 | 0 / 1 | 0 / 1 |
| node-b | 2 / 3 | 0 / 1 | 2 / 3 |

归并先核对完整 init 清单，再按 **run_id + rank_epoch +已验证 WORLD comm+operation+seq** 匹配，独立核对 count/datatype/algorithm/protocol/nChannels。不按时间最近、进程内指针或单独 hash 猜成员。seq 按 operation 分开，AllGather 与 AllReduce 都可从0开始。

- 每 Rank **70 条完整 Coll**，共 **70 个四 Rank 匹配实例**：1个 AllGather(seq0)、69个 AllReduce(seq0–68)。观察到的键并集中缺侧0、重复0、metadata冲突0、成员/hash冲突0、局部 b/e 配对问题0。
- AllGather：count=8 / ncclInt8 / RING / LL /1 channel；AllReduce：1个 count=2099200，68个 count=1049600，均 ncclFloat32 / TREE / SIMPLE /8 channels。count 是逻辑输入元素，不是物理网络字节。
- 每 Rank **553 组 GPU channel 原始计时**，均 `StopGpuClk > StartGpuClk >0`；不是553个独立 Collective。
- **覆盖仅限导出窗口**。双方/四方共同遗漏、静默丢弃、尾窗覆盖与精确 drop 均 UNKNOWN；未观察到的操作（包括初始化 Broadcast）不宣称已被该接口完整捕获。root参数未导出，UNKNOWN。不能用70个匹配实例证明全历史无损。
- 映射仅对本次固定单WORLD成立；没有实现通用多组/重建 communicator 识别或 hash 碰撞解析。

## 时间与方向性性能

Chrome `ts`（包括 `cat=GPU`）是本进程相对 CLOCK_MONOTONIC 微秒；Coll end 可等待子事件引用归零，不能独立叫 Host enqueue end。`StartGpuClk/StopGpuClk` 才是 GPU globaltimer 原始纳秒，描述 channel work，不能称完整 kernel launch。训练 step 使用本 GPU CUDA event 毫秒；Host dispatch 使用本地 perf_counter，分别保留。**跨进程/跨 GPU/跨节点校准与误差界 UNKNOWN，未做绝对时间相减；step→Coll、原发/受害因果均 UNKNOWN/未实现。**

每格为 GPU step p50 / p95（ms），分位数已从每 Rank 的30个原始值独立复算；数组及 Host dispatch/RSS/Torch memory 数据在实测汇总中。

| Rank | baseline | plugin | p50 变化 | p95 变化 |
| --- | --- | --- | --- | --- |
| 0 | 0.878080 / 0.988869 | 0.944224 / 1.062939 | +7.53% | +7.49% |
| 1 | 0.881616 / 0.987994 | 0.942080 / 1.065290 | +6.86% | +7.82% |
| 2 | 0.885072 / 0.999774 | 0.940080 / 1.065778 | +6.22% | +6.60% |
| 3 | 0.885104 / 0.991000 | 0.939072 / 1.064269 | +6.10% | +7.39% |

单次顺序对照、短窗、共享 GPU，存在调度和其他作业混杂；**不是稳定开销估计，也没有达到或宣称 ≤2% SLA**。按本 Issue 范围报告方向性结果，不为压低数字追加轮次。官方 example 仍有 mutex、有限池与 finalize 文件写入失败风险；完全非阻塞、生产 fail-open/长期稳定性尚未验证。

## 重现与回退

在两台已授权测试节点建立相同私有 venv，按锁文件下载并核对包哈希，安装后运行 `pip check`。按原 Makefile 编译上述固定官方 example，不修改框架/NCCL/生产源码。复制本仓库 capture/run 两脚本进私有 task 目录，显式选择两个设备，并以同一 run/epoch 从两节点并行启动；每个 mode 目录必须不存在。先 `smoke`，再一次 `baseline` 和一次 `plugin`，调用参数见 [启动脚本](../tools/g1_01_run.sh)。本轮已完成，不要求审核者重跑 G0 或全部 GPU 实验。

原始文件从两机各自完整目录取回后，离线执行（路径为占位符，输出 manifest 含敏感字段，必须保密）：

```sh
python3 tools/g1_01_make_manifest.py node-a=PRIVATE_NODE_A_PLUGIN node-b=PRIVATE_NODE_B_PLUGIN --output PRIVATE_MANIFEST.json
python3 tools/g1_01_match_trace.py PRIVATE_MANIFEST.json --redact-identifiers --output PUBLIC_MATCHES.json
python3 -m unittest discover -s tests -v
python3 tools/validate_docs.py
```

9个 CPU synthetic fixture 测试只证明逻辑，不代替真实 GPU/MULTINODE 证据。CI 同样只有 DOC/CPU。公开数据仅别名、统计、step数组、哈希；两机私有 raw 各约0.5MiB，均低于64MiB/node归档上限。原始证据保留至独立审核完成，随后7天内手动清理；没有安装后台自动清理任务。

停用插件使用 `NCCL_PROFILER_PLUGIN=none`（本次新栈 baseline 已实际运行）；离开/deactivate 私有 venv 即返回既有环境，旧 NGC 缓存仍保留。没有修改宿主 driver/kernel、Docker daemon或全局包；未追加旧栈 GPU 回退测试。故障注入、主动减速、Rank打分、G2/G3和生产改造 **NOT_RUN**。**完成本候选后停止，等待 ChatGPT 独立审核，不合并 PR、不关闭 Issue、不自行判定 G1 Gate PASS。**
