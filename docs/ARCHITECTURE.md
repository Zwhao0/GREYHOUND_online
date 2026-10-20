# 概念架构 — 非实现承诺

```text
real dense-model training (2×8 H800, NCCL; later DP/TP/PP)
            |
            +--> approved non-blocking NCCL observations (plugin/launcher)
            +--> PyTorch FR / NCCL RAS as available, host/device telemetry
                              |
                     typed event contract
                              |
                  trigger: ACF / BOCD ideas
                              |
                 suspect communicator/group
                              |
              offline-first Rank attribution
                 |              |              |
               event matching  wait causality  health baselines
                              |
       ROOT_CANDIDATE / SUSPECT_GROUP_OR_EDGE / UNKNOWN
                              |
            (G3 only) streaming/online processor
```

## 关键设计约束

- **单一时间来源不可假设：** Host enqueue、GPU kernel、proxy progress 不同；跨进程 monotonic 基准需实验校准。
- **不阻断热路径：** 不在训练步骤中执行网络 RPC、同步 CUDA Event 或等待中央分析服务；缓冲耗尽可丢数据，必须可见。
- **匹配实例而非粗排时长：** communicator epoch/hash + op type + sequence + rank/group identity + evidence source，缺字段时显式说明不能匹配。
- **区分原因与受害：** 结合发起/完成/等待、peer 有向关系、系统事件判断；单纯长 NCCL 时间只支持可疑而非根因。
- **基线辅助，而非魔法：** 健康窗口和同角色/同规模工作定义存在时才计算；整体同时退化时 peer 基线不可视为健康。
- **可恢复观测降级：** 任何观测器失败不导致训练故障，记录丢样率/能力降级。

## 待做的架构决策（G0 再决定）

- 是否直接复用 Probing 插件，还是用版本匹配的原生 NCCL Profiler。
- GREYHOUND 公开源码的许可、同步与固定规模问题是否允许直接改用。
- 数据事件时序、跨节点时间校准与稳定的 Group 角色识别方式。
