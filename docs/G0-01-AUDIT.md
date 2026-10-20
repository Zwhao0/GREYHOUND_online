# G0-01 静态审计与 G0-02 字段 PoC 记录

G0-01 已经[独立审核 PASS 并合并](https://github.com/Zwhao0/GREYHOUND_online/pull/2#issuecomment-6293155716)。下面 G0-01 段落保留静态交付时的历史语义；G0-02 执行边界以 [Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3) 为准，不沿用旧方案的多轮/完整性硬门槛。

2026-10-20；依据 [Issue 最新指令](https://github.com/Zwhao0/GREYHOUND_online/issues/1#issuecomment-6291225324)。基于 main `d2a47a6b0edb94199c611933f71777136f904649`。两个只读子审计，主窗口复核并写入；本分支为候选，未合并、未跨 Gate。DOC 静态证据不代表 GPU 可观测性。

## 结论及首测/备选

**选择 A 首测：NCCL 原生 Profiler example 的短窗口原始事件 PoC。选择 B 备选：Probing NCCL profiler，单独运行。** 优先使用实际加载 NCCL 所兼容的既有插件，不为候选升级 NCCL。Inspector 是 A 家族的已有摘要选项，但不能替代逐事件证据，也不与另一个 profiler 同时加载。方案均只是待单独授权的隔离试验候选，当前不具备完整生产契约。

- A：固定 2.27.x v4 接口有 commHash、rank、seqNumber、Host enqueue、GPU channel pTimer 与 ProxyStep；example 已导出关联字段和 GPU 原始时钟，接入走 `NCCL_PROFILER_PLUGIN`。但有限池会静默丢弃、退出导出保留尾窗，不能证明 drop=0，不能通过完整性门槛。先检验现成字段是否实际出现；需要补计数或修改插件时另行审查授权，本轮不开发采集器。
- Inspector：固定 2.29.7 的插件仅导出 v5，不能假设适配 2.27 v4。它有 `coll_sn`，但周期输出 latest completed collective 并非完整事件流；中间记录被覆盖，不能用聚合判断晚到/原发 Rank。仅在环境已有兼容版本时作为摘要核对，不为它升级环境。
- B：Probing 提供原生 NCCL profiler 入口与 ProxyOp/Step 数据，可能降低后续接入工作量；Linux v4/v3 导出并不证明实际版本兼容。callback 的 Mutex、同线程 flush/write 与损失统计缺口使其只能受控试验，不能承诺非阻塞或 fail-open。A 无兼容 ABI/字段不足时才评估 B；两者都失败则结论是暂不可进入 Rank 算法阶段。

所有来源/许可/字段证据集中在 [来源矩阵](SOURCES_AND_LICENSES.md)；最小身份、collective 关联与时钟要求集中在 [数据契约 §5](MEASUREMENT_CONTRACT.md#5-g0-01-最小事件契约静态候选2026-10-20)。本项目真实库版本、插件是否加载、字段完整性、开销、原发可区分性全部 UNKNOWN。

## GREYHOUND：可借鉴设计与禁止继承路径

固定上游 `d641b3997c17de700e1ef7d37e353418df7e336d`，永久链接如下；未复制源码。

| 机制 | 精确定位 | 结论 |
| --- | --- | --- |
| ACF 周期估计 | [slow_detection.py:142–163](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/control_plane/slow_detection.py#L142-L163)，[入口:161–176](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/control_plane/local_analyzer.py#L161-L176) | 假设迭代调用模式完全相同；固定 dense DDP 可参考，动态 bucket/无周期 UNKNOWN |
| BOCD/变点 | [slow_detection.py:89–128](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/control_plane/slow_detection.py#L89-L128) | README 称 BOCD，实现调用 Rbeast 对窗口分析；不能声称该实现已验证严格流式 BOCD |
| Group 筛选 | [global_analyzer.py:184–224](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/control_plane/global_analyzer.py#L184-L224) | 同位组 median 比较可参考；唯一同位组直接转主动验证，不适用于单 world DDP；无 peer 则 BASELINE_UNAVAILABLE |
| 暂停/主动测试 | [controller:180–225](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/control_plane/global_controller.py#L180-L225)，[handler:226–260](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/event_handler.cpp#L226-L260) | pause_training + 计算/通信 benchmark，禁止继承 |
| 额外通信 | [handler:198–224](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/event_handler.cpp#L198-L224)，[测试:25–75](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/event_handler.cpp#L25-L75) | world_comm broadcast 控制状态及现有 communicator 上主动 send/recv，隔离 |
| GPU 同步/时间 | [global_status.cpp:192–248](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/global_status.cpp#L192-L248) | MONITOR 提前返回；PROFILE/VALIDATE 调 cudaEventSynchronize，不能沿用 profiling 热路径。call_time 是进程相对 system_clock，不是 GPU 起始或跨进程基准 |
| 固定规模/内部 ABI | [config.hpp:39–53](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/config.hpp#L39-L53)，[comm.cpp:182–201](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/comm.cpp#L182-L201) | MAX_DEVS=4、最小记录大小1024、comm上限128、HackedComm 解码；不证明H800/任意拓扑兼容 |

因此 ACF/变点/同角色 Group 缩小范围均仅**参考设计**；detector 许可 UNVERIFIED，当前没有可直接复制的模块。两节点单 DDP world 不能靠组均值或最长等待产生精确 Rank 结论。

## 下一阶段最小 H800 PoC（仅计划，必须另行授权）

1. **先授权隔离单节点窗口**：使用现有受审查的固定 dense DDP benchmark，不改生产脚本/模型/框架/NCCL。先2 GPU；之后双节点各2 GPU、总4 rank，保持模型、batch、dtype、bucket、seed及采样配置固定。现有资源不足则重新定资源，不猜服务器配置。运行前记录实际 PID 加载的 libnccl 路径/版本/构建标识、Torch/CUDA/驱动与插件 SHA/ABI；`pip show` 或独立进程 ncclGetVersion 不能替代目标进程动态库证据。无匹配插件则停止，不升级。
2. **无注入健康对照**：无采集→A→无采集，3个配对重复；每次20 warmup + 100 measured steps，统一现有计时方式。先只短窗口启用所需 Coll/KernelCh，双机再加 ProxyOp/Step；记录精确 mask/池容量/输出窗口与启停。每个 rank 验证插件库确已映射、加载日志/协商 ABI、comm init 和非空预期事件；不能凭环境变量存在判 PASS。
3. **关联与时钟**：按契约重建全体成员、相同 collective key 和 func/count/datatype；测量窗口内每个预期 key 每 rank 恰一条 Coll，覆盖率目标100%、重复0、元数据冲突0。已有 benchmark/独立计数证明分母；只有导出记录数不能证明完整。分离 Host enqueue、GPU channel、Proxy 状态；保存原始时钟及转换/误差。无可信跨节点校准就仅比同域时长和序号，不比较绝对到达先后；原发结论 UNKNOWN。
4. **验证丢失与回退**：逐类记录 seen/emitted/dropped/overwritten/truncated。有界池/输出上限与精确 drop 无法核对即完整性 FAIL，绝不把空日志当健康。example 的静默丢弃/尾窗已是静态阻断：短窗可证明字段存在，不能单靠它宣布通过全契约。丢失计数改造、压力/故障演练均另需授权；移除插件环境/路径后重新启动隔离任务，训练成功且输出停止才算回退验证。
5. **开销/失效门槛**：报告 step p50/p95、吞吐、Host CPU、RSS、日志字节与容量；候选相对相邻无采集对照的平均额外 step 开销目标≤2%（工程假设，非既有事实），p95 增幅≤5%，RSS/输出不超预登记上限（初拟每rank 256 MiB/64 MiB，超过则停采并回退）。不增加训练内 collective/热路径GPU同步。挂起、训练错误、无界增长、指标缺失均不通过；移除配置恢复对照。fail-open 不能凭接口说明宣称成立。
6. **单节点通过后，另行批准双节点同配置重复**：检验网络 ProxyStep/peer、PXN 父链与跨 rank 对齐；单机成功不等于跨机支持。若需检查晚到与等待，必须再单独授权隔离故障注入：使用既有测试入口做已知单 rank 计算延迟与健康对照，真值对采集分析隔离；不为本轮修改训练代码。观察同一次 collective 上受害 peer 等待是否与原发晚到区分。没有独立真值/校准/完整证据则 SUSPECT/UNKNOWN，不以最长耗时当原发；本轮及首个无注入 PoC 不验证因果准确率。

验收分两层：字段 PoC 可通过“已加载且出现可关联原始字段”；完整可观测性必须额外满足完整性、时间域、原发/等待独立反例、开销和回退。任一关键项失败则停在 G0，提交缺口，不进入 G1/G2 或实现算法。B只在A不兼容/不足时按同一门槛单独试，不叠加多采集器。FR/RAS/DCGM仅在已知缺口需要时作为补充，不作为第三候选。

## 未解决与本轮验证

- 真实 H800 动态库/ABI、GPU与Proxy覆盖、comm成员映射、跨节点校准和独立真值：UNKNOWN。
- A 的精确丢失统计；Inspector latest 覆盖；B 的阻塞锁/flush 与完整性：阻断生产非暂停承诺。
- GREYHOUND detector 许可未证实；其他组件许可证只覆盖审查范围，依赖/分发需复核。
- DOC：现有 validate_docs.py PASS、git diff --check PASS；31个外链去重检查后修复1个RAS路径，PyTorch教程HEAD 403但浏览器读取成功，其余HTTP 200；CI以 PR 实际运行记录为准；CPU/GPU/MULTINODE：NOT_RUN。未访问H800、未运行上游程序、无算法或采集器实现。
- 回退本PR：关闭/撤回候选文档分支即可；main 未改变。交一个 Draft PR 后停止，等待 ChatGPT 独立审核。


## G0-02 执行记录（候选未合并，等待独立审核）

依据 [Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3)，base main `4d8a49c71f1dc24d7252f7ce21b56d06c9a9b225`。**结果 PARTIAL：单节点2×H800真实 NCCL 原始字段采集/对齐成功；dense DDP、step p50/p95 未验证。G0 总 Gate 未通过，G1 未授权。**

### 实际授权、接入与运行

资源检查时两个候选节点全部GPU有进程占用，未停止或读取现存训练日志。用户随后在本轮对话明确授权“共享GPU”，因此选第二候选节点GPU0/1（各约5204 MiB空闲）运行单独任务进程/目录；**设备共享而非独占隔离，性能受共租干扰**。只在这一台机器运行GPU任务，没有双机实验。结束后所选卡占用回到运行前75875 MiB；未评估对其他任务的影响。

宿主默认Python无Torch，Docker普通用户无访问权限。未使用sudo、未改权限/安装Torch。为避免搭环境，复用已安装官方 `nccl-tests 2.17.6` 的 `all_reduce_perf`：单机MPI2进程、每rank1 GPU，8MiB float32 sum，`-n40 -w5 -c0 -z0`，分别测out-of-place/in-place。它是**NCCL微基准，不是DDP step**；数值正确性检查关闭，不能宣称已验证训练正确性。

无插件对照一次完成后，从两个目标PID的 `LD_DEBUG=libs` 的 `calling init` 确认实际加载 `/opt/nccl-tests/bin/../lib/libnccl.so.2`；其自身NCCL日志均为 `2.28.3+cuda12.9`，测试程序同时报告 `nccl-library=22803`。实际cudart也由目标PID加载记录确认路径，`+cuda12.9`仅是NCCL构建后缀，不冒充独立查询过的cudaRuntimeGetVersion。驱动580.178.04，Torch未使用；不是用宿主pip元数据推断运行库。

插件选择官方 `v2.27.7-1` / `593de54e52679b51428571c13271e2ea9f91b1b1` 的未修改example，BSD-3-Clause。目标2.28.3加载器有[尝试v5后回退v4](https://github.com/NVIDIA/nccl/blob/f1308997d0420148b1be1c24d63f19d902ae589b/src/plugin/profiler.cc#L70-L75)路径；v4 example自带所需头文件，可不安装CUDA开发环境。仅在任务私有目录 `make -C ext-profiler/example CUDA_VERSION=12.9`（GCC13.3.0），没有重编译或替换NCCL。`CUDA_VERSION`是Makefile配置，不是升级。两rank真实日志均记录 `Loaded Example-profiler (v4)`、相同commHash、nranks=2及rank0/1；各自目标PID加载日志也包含插件路径。

- libnccl SHA256：`da4d22f215c45435fcbaa465351ad5d2b9c4a87dfd8005565b25b14e5695cf68`。
- 插件 SHA256：`3982ac146d710cfd3eca59e0c36fd1502790840211eb8f41c2d35934b51c9571`；仅导出`ncclProfiler_v4`。
- 插件配置：`NCCL_PROFILE_EVENT_MASK=64`（KernelCh及祖先Coll/Group）；Group/Coll pool各128；输出任务私有文件。非插件两次启动均清除插件变量；所有运行使用同样的NCCL INFO/loader记录方式。
- 完整脱敏事实、库/测试二进制/原始trace哈希和样例：[g0-02-summary.json](evidence/g0-02-summary.json)。原始主机名、地址、PID、GPU UUID、PCI地址、环境变量和私有路径不公开。摘要中的rank alias不改变实际commHash/sequence/时钟数值。

### 原始字段、对齐与时间语义

两rank各导出87条AllReduce，seq0–86，均为同一commHash；按本次run + commHash + type + seq匹配87对、无仅单侧键，count/datatype一致。global/local rank与device映射来自MPI nccl-tests自身JSON（0→GPU0、1→GPU1），并用相同PID的NCCL comm init及trace comm rank核对，不按时间最近匹配。单world、未重启的小样本不证明任意communicator映射。

| 原始样例（两个rank均有） | 值 |
| --- | --- |
| commHash / type / seq | `14248957799767872916` / `AllReduce` / `86` |
| comm rank / count / datatype | `0,1` / `2097152` / `ncclFloat32` |
| 每rank逻辑字节 / algorithm / protocol | `8388608` / `RING` / `SIMPLE` |
| channels / GPU子事件 | 每collective16 channels；每rank1392个KernelCh begin和1392个end |

Host Coll begin是插件CLOCK_MONOTONIC相对起点的微秒；导出Coll end由[refcount归零时刻](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/plugin.c#L470-L475)产生，启用KernelCh后**不能当独立Host enqueue end**。GPU类别的Chrome `ts`仍是Host观察时间；真正GPU证据在 `StartGpuClk/StopGpuClk`，保留原始GPU timer域而不冒充完整kernel launch边界。跨GPU校准未知，不能直接比较两个rank的绝对时间。Proxy未启用且单机路径无网络事件，本次不验证等待分解或原发Rank。

87个导出键全匹配仅证明这一小段可关联；官方example有限池/尾窗及精确drop缺口仍在，未证明全历史完整、无丢失或fail-open。没有为了字段PoC新增计数器/解析平台，B无需切换。

### 一次对照的基本开销、失败与回退

| 指标 | 无插件对照 | 插件短窗 | 解释 |
| --- | --- | --- | --- |
| out-of-place官方平均延迟（μs） | 76.111487 | 76.770263 | +0.866%，仅一次共享环境样本 |
| in-place官方平均延迟（μs） | 75.272838 | 75.997400 | +0.963%，不是2% SLA证明 |
| step p50/p95 | NOT_AVAILABLE | NOT_AVAILABLE | 此安装版本只导出聚合均值；没有把均值或channel时长冒充step分位数 |
| max RSS rank0/rank1（KiB） | 957944 / 956672 | 998512 / 993180 | `/usr/bin/time -v`，不是GPU显存峰值 |
| 本任务输出总字节 | 99442 | 1047739 | 含loader/NCCL日志；每rank trace各473139字节 |
| 两rank退出 / 异常停滞 | 0 / 未观察到 | 0 / 未观察到 | 不证明长期稳定/严格非阻塞/其他任务无影响 |

最初MPI启动因`--host localhost`只有1 slot而在GPU程序启动前失败；改成`localhost:2`后只完成上述一组对照/插件测试。没有故障注入或环境升级。官方2.28.3 example依赖本机缺少的CUDA开发头文件，未为此安装SDK或修补ABI，使用已审核的官方兼容v4 example。额外下载的开发依赖未安装、未进入仓库。

清除插件配置后仅做 `-n2 -w0` 启动/退出烟测：两rank退出0，实际加载日志无profiler，NCCL日志再次为`Could not find: libnccl-profiler.so`；未重复整轮性能实验。无任务残留配置写入全局环境。所有运行外层timeout120秒、TERM后5秒KILL仅限本次进程组，无sudo/系统变更、生产脚本修改或停止他人进程。

复现入口：[tools/g0_02_nccl_poc.sh](../tools/g0_02_nccl_poc.sh)，由实际执行命令整理，静态语法检查；使用已批准资源和私有目录，依次`baseline <dir>`、`plugin <dir> <official-plugin.so>`、`rollback <dir>`。不提交第三方源码或私有原始日志。结果报告里的版本/字段来自本次真实进程，不以脚本静态检查替代GPU证据。

**验证分类：** DOC=现有文档/链接与shell语法检查（CI看Draft实际记录）；CPU测试=NOT_RUN；GPU=PASS（仅本次共享单机NCCL微基准/加载/原始字段/回退）；DDP=NOT_RUN；MULTINODE=NOT_RUN；G0-02整体PARTIAL，待独立审核。

下一步建议先审核本Draft，并明确后续可用的既有Torch运行入口与共享/独占资源条件，再单独授权一次固定dense DDP及step分位数验证。当前不请求G1、双机、注入、Rank算法或生产部署，也不因微基准字段成功放行整个G0。
