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
