# 外部工作、源码与许可检查

本表为初始化阶段的候选，不表示兼容、已获商用授权或已经在 H800 测试。

| 项目 | 来源 | 借鉴/评估点 | 引入代码门槛 |
| --- | --- | --- | --- |
| GREYHOUND (upstream) | https://github.com/wutianyuan1/Greyhound | ACF/BOCD、Group 定位、原 Validation 问题 | 原 detector 的明确复用许可仍需核实，**禁止直接复制** |
| Probing | https://github.com/DeepLink-org/probing | NCCL ProxyOp、culprit/victim SQL 归因、采集方案 | 逐组件核对 license、ABI、开销 |
| NCCL RAS / Inspector | https://github.com/NVIDIA/nccl | RAS 和 profiler 事件 | 与实际加载 NCCL 的 ABI/版本兼容 |
| PyTorch Flight Recorder | https://github.com/pytorch/pytorch | Collective 匹配、调用栈、Hang 证据 | 当前 PyTorch 版本功能与开销 |
| DCGM | https://github.com/NVIDIA/DCGM | GPU 硬件遥测 | 节点部署权限与 metrics 正确性 |
| Megatron-LM | https://github.com/NVIDIA/Megatron-LM | 原生 Straggler 观测对照 | 仅在其官方入口可用时进行对照 |
| CommInsight | https://github.com/redai-studio/comminsight | 采集/Step 语义/归因设计 | 公开组件与未开源 Server 区分；许可与 ABI |

**规则：** 仅因仓库公开并不意味着可任意商用、复制或修改。引入外部依赖前记录精确 Git SHA、许可证文件、包含的代码范围、第三方许可证与构建途径。

## G0-01 固定上游证据（2026-10-20，静态只读）

下表 `SUPPORTED` 只表示该固定版本存在相应接口，`UNSUPPORTED` 表示该来源没有所需语义，`UNKNOWN` 表示缺证据。**本项目所有运行时兼容性、覆盖率、开销均 UNKNOWN**。未导入任何上游代码；公开 URL 不代替许可证。暂不引入 Megatron/CommInsight，避免扩大采集组合。

| 来源 / pin | 许可证据与状态 | 可见字段 / 重要限制 / 结论 |
| --- | --- | --- |
| GREYHOUND `d641b3997c17de700e1ef7d37e353418df7e336d` | 根目录及 detector 未见许可证；[Megatron 子树 LICENSE](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/Megatron-LM/LICENSE)不能授权 detector。**UNVERIFIED，禁止复制** | ACF/变点/Group 可参考设计；[同步路径](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/global_status.cpp#L234-L248)违反本项目 profiling 约束；详见[机制定位](G0-01-AUDIT.md) |
| NCCL Profiler/example `v2.27.7-1` = `593de54e52679b51428571c13271e2ea9f91b1b1` | [LICENSE.txt](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/LICENSE.txt)：审查核心/example 为 BSD-3-Clause；含第三方许可，分发须保留 | [v4 ABI](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/src/include/plugin/profiler/profiler_v4.h#L10-L121) SUPPORTED：commHash/nNodes/nranks/comm rank、func/count/type/seq、KernelCh pTimer、ProxyStep；成员数组/global rank/GPU UUID UNSUPPORTED，外部映射 UNKNOWN |
| 同版本 ABI 与时钟 | 同上 | [加载器](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/src/plugin/profiler.cc#L52)依次尝试 v4/v3/v2/v1；[文档](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/README.md)说明 coll.stopEvent 仅 enqueue、v3 kernel 由 Host 探测会受调度延迟、v4 GPU时间戳及64元素/channel ring。网络自定义事件须net plugin配合；并非网络线速时间 |
| 同版本 example 导出/损失 | 同上 | [导出](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/print_event.c#L28)含 SeqNum/CommHash/Rank，[GPU时间](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/print_event.c#L112)含原始 GPU clock；[池满丢弃](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/plugin.c#L187-L237)、[finalize尾窗](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/plugin.c#L138-L180)，有界 SUPPORTED，累计drop计数 UNSUPPORTED。首测仅字段PoC |
| NCCL Inspector `v2.29.7-1` = `b91894bd5b190c874d98a017f93f5daa515b65d0` | [文件 Apache-2.0](https://github.com/NVIDIA/nccl/blob/b91894bd5b190c874d98a017f93f5daa515b65d0/plugins/profiler/inspector/inspector_plugin.cc#L1-L4)，[仓库混合许可](https://github.com/NVIDIA/nccl/blob/b91894bd5b190c874d98a017f93f5daa515b65d0/LICENSE.txt) | 同NCCL仓，2.27审查tag尚无此目录；[仅v5](https://github.com/NVIDIA/nccl/blob/b91894bd5b190c874d98a017f93f5daa515b65d0/plugins/profiler/inspector/inspector_plugin.cc#L487)，不能默认加载于2.27 v4；[只订阅Coll/KernelCh](https://github.com/NVIDIA/nccl/blob/b91894bd5b190c874d98a017f93f5daa515b65d0/plugins/profiler/inspector/inspector_plugin.cc#L117)，ProxyStep UNSUPPORTED；[coll_sn输出](https://github.com/NVIDIA/nccl/blob/b91894bd5b190c874d98a017f93f5daa515b65d0/plugins/profiler/inspector/inspector.cc#L494) SUPPORTED，但[覆盖latest completed](https://github.com/NVIDIA/nccl/blob/b91894bd5b190c874d98a017f93f5daa515b65d0/plugins/profiler/inspector/inspector_plugin.cc#L417)，完整逐事件/精确drop UNSUPPORTED |
| Probing `e5080d35717caab3b735afc5d69423dd9ec6dd70` | [Apache-2.0](https://github.com/DeepLink-org/probing/blob/e5080d35717caab3b735afc5d69423dd9ec6dd70/LICENSE)；依赖/二进制再分发另核 | [Linux导出v4/v3](https://github.com/DeepLink-org/probing/blob/e5080d35717caab3b735afc5d69423dd9ec6dd70/probing/extensions/nccl-profiler/src/lib.rs#L38-L69)，[tables schema](https://github.com/DeepLink-org/probing/blob/e5080d35717caab3b735afc5d69423dd9ec6dd70/probing/extensions/nccl-profiler/src/tables.rs)：coll_perf/proxy_ops/timing_source及pool/write计数 SUPPORTED；v3无GPU pTimer/完整comm元数据，缺值不能当零。全部预期事件的端到端精确损失 UNKNOWN；SQL culprit/victim名称不证明因果 |
| Probing 回调安全 | 同上 | [state Mutex](https://github.com/DeepLink-org/probing/blob/e5080d35717caab3b735afc5d69423dd9ec6dd70/probing/extensions/nccl-profiler/src/state.rs#L173)，[stop同步flush](https://github.com/DeepLink-org/probing/blob/e5080d35717caab3b735afc5d69423dd9ec6dd70/probing/extensions/nccl-profiler/src/state.rs#L301)，[writer lock/write](https://github.com/DeepLink-org/probing/blob/e5080d35717caab3b735afc5d69423dd9ec6dd70/probing/extensions/nccl-profiler/src/state.rs#L343)：完全非阻塞 UNSUPPORTED；实际开销/fail-open UNKNOWN。只作受控备选 |
| PyTorch Flight Recorder `v2.8.0` = `ba56102387ef21a3b04b357e5b183d48f0afefc7` | [LICENSE](https://github.com/pytorch/pytorch/blob/ba56102387ef21a3b04b357e5b183d48f0afefc7/LICENSE)：BSD风格与第三方条款 | [FlightRecorder.hpp](https://github.com/pytorch/pytorch/blob/ba56102387ef21a3b04b357e5b183d48f0afefc7/torch/csrc/distributed/c10d/FlightRecorder.hpp#L110)，[官方教程](https://docs.pytorch.org/tutorials/unstable/flight_recorder_tutorial.html)：PG/成员/seq、有限环形记录、可选CUDA timing SUPPORTED；Host发现started可能很晚，不能作真实GPU起点；FR seq不自动等于NCCL seq，Proxy等待/原发证明 UNSUPPORTED。需目标Torch版本核对，不默认启用 |
| NCCL RAS `v2.27.7-1`（SHA同上） | NCCL BSD条款，见上 | [ras/client.cc](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/src/ras/client.cc)，[官方文档](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2243/user-guide/docs/troubleshooting/ras.html)：RAS自2.24起提供运行健康/collective进度快照，SUPPORTED；完整逐collective GPU/Proxy轨迹及原发rank证据 UNSUPPORTED |
| DCGM `v4.3.1` = `1477d8785e899ab3450fdff2b486102e9bed096b` | [Apache-2.0](https://github.com/NVIDIA/DCGM/blob/1477d8785e899ab3450fdff2b486102e9bed096b/LICENSE)，附带组件另核 | [dcgm_fields.h](https://github.com/NVIDIA/DCGM/blob/1477d8785e899ab3450fdff2b486102e9bed096b/dcgmlib/dcgm_fields.h#L2408)：SM/DRAM/PCIe/NVLink及错误遥测 SUPPORTED；H800/权限/复用冲突 UNKNOWN；NCCL comm/seq UNSUPPORTED，低利用率可能是受害等待，不能独立证明原发rank |

主窗口另核 NCCL `v2.27.5-1` = `3ea7eedf3b9b94f1d9f99f4e55536dfcbd23c1ca` 的 [v4定义](https://github.com/NVIDIA/nccl/blob/3ea7eedf3b9b94f1d9f99f4e55536dfcbd23c1ca/ext-profiler/example/nccl/profiler_v4.h)与 example 损失路径，和上述2.27.7结论一致；这不证明2.27所有patch或目标环境兼容。较新tag的字段不能回填到旧ABI。

## G0-02 实际选用组件

- 仍使用上述官方NCCL `v2.27.7-1` example（BSD-3-Clause），未修改源码，只在私有构建目录编译。运行时NCCL报告2.28.3，实际DSO/插件SHA见[实测摘要](evidence/g0-02-summary.json)。[2.28.3加载器](https://github.com/NVIDIA/nccl/blob/f1308997d0420148b1be1c24d63f19d902ae589b/src/plugin/profiler.cc#L70-L75)支持v5→v4回退；两目标rank实际协商v4。该源码tag只作加载器依据，不声称已知已装DSO的构建commit。
- 复用已安装NVIDIA nccl-tests 2.17.6；[对应上游tag/README](https://github.com/NVIDIA/nccl-tests/blob/da0b547b1b9c6e3b1d4c15578087874522ae3761/README.md)、[BSD-3-Clause许可](https://github.com/NVIDIA/nccl-tests/blob/da0b547b1b9c6e3b1d4c15578087874522ae3761/LICENSE.txt)。安装二进制构建commit UNKNOWN，记录其版本输出与SHA，不冒充从该tag自行构建。没有将第三方源码/二进制复制入Public仓库。
