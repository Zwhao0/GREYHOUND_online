# STATUS — Greenhound Online

2026-10-21（Asia/Shanghai）。[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)（Public）；以最新 main / Issue / PR / CI 为准。

## Gate / 当前任务

| 项目 | 审核结果 | 证据 |
| --- | --- | --- |
| G0 单节点观测 | **限定范围 PASS**；不重验 | [G0-01 PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2)、[G0-02 PARTIAL #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)、[G0-03 PASS #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) |
| G1-01 新软件栈/健康双节点 | **限定范围 PASS / MERGED** | [Issue #9 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/9)、[PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) |
| G1-02 采集质量与时钟契约 | **PARTIAL（CPU/DOC已接收）/ MERGED** | [Issue #14 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/14)、[PR #16](https://github.com/Zwhao0/GREYHOUND_online/pull/16)、[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/16#issuecomment-6307501674) |
| **G1-03 真实Host校时/采集审计** | **OPEN / NOT_RUN** | [下一唯一任务 Issue #17](https://github.com/Zwhao0/GREYHOUND_online/issues/17) |
| **G1 总 Gate** | **IN_PROGRESS / 未通过** | Host时钟可信对齐、逐类采集质量仍需现场补证 |
| G2/G3/G4 | **BLOCKED** | 无故障注入、根因归因或在线化授权 |

## 当前证据范围

- G1-01 在两台 H800 私有环境实际运行 Torch **2.14.1+cu130** / CUDA runtime **13.0.96** / NCCL **2.30.7** / 官方 example **Profiler v4**。真实健康4 Rank DDP短窗观察到 **70个四Rank匹配实例**；实际进程库/ABI、GPU和回退证据见[实验报告](docs/G1-01-RESULTS.md)。G0历史结果不跨版本重用。
- G1-02 未进行新 GPU / MULTINODE 实验；DOC+CPU最终 [CI PASS，33项测试](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39539775945)。从G1-01私有真实trace离线计算[质量报告](docs/evidence/g1-02-quality.json)，四Rank trace SHA与G1-01索引4/4匹配；每Rank Coll70/Group70/KernelCh553对、导出内部seq无gap/重复/异常。**不等于全集无损**：attempted/drop/overwritten/flush、共同遗漏、active-window、Proxy依旧 UNKNOWN。
- G1-02 四时间戳是 **CPU_SYNTHETIC数学测试**，不是现场校准。G1-01的每PID Host relative `ts`、各GPU globaltimer和CUDA event duration 不可跨Rank直接相减，`UNSAFE_TO_SUBTRACT`；Host origin、节点间offset/uncertainty尚无实测依据。[G1-02结果](docs/G1-02-RESULTS.md)、[数据契约](docs/MEASUREMENT_CONTRACT.md)。
- G1-01一次共享资源对照GPU step p50 **+6.10%～7.53%**、p95 **+6.60%～7.82%**；非稳定低开销SLA或生产fail-open证明。不进行原发/受害因果推断。
- G1-01实验PR squash `1c2ef7f491d5979f1d7e3a55a54bd4d537e7b77c`；G1-02 CPU PR squash `60cc604eccad5b7943033ed9323e79d24ddd9584`。本次收尾仅文档，不声称运行GPU。

## 唯一下一动作

**Codex执行 [Issue #17 — G1-03](https://github.com/Zwhao0/GREYHOUND_online/issues/17)**：固定软件栈，独立控制路径及同PID Host origin 实测对齐，最小逐类采集/导出状态，有限健康两机DDP验证。提交一个 Draft PR，含脱敏证据、真实与合成测试分类、紧凑 STATUS/HANDOFF，停止待 ChatGPT 独立审核。

共享H800隔离、少量健康GPU测试许可沿用；禁止故障注入、原发Rank评分/G2、修改生产训练/框架/NCCL核心、宿主驱动/全局包升级、影响其他任务或公开敏感原始数据。
