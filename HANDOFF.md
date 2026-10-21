# HANDOFF — Greenhound Online

> 跨 ChatGPT/Codex 简明交接，2026-10-21（Asia/Shanghai）。以 [GitHub main](https://github.com/Zwhao0/GREYHOUND_online)、最新 Issue/PR/CI 为准；详细证据留在PR和实验报告。

## 当前真实状态

- **G0：限定PASS**（单节点）；**G1：`PASS_SCOPED_OBSERVABILITY`，已经独立审核，结束G1，不重验**。G1-01 [PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) PASS；G1-02 [#16](https://github.com/Zwhao0/GREYHOUND_online/pull/16) CPU PARTIAL接收；G1-03 [#19](https://github.com/Zwhao0/GREYHOUND_online/pull/19) PARTIAL接收；G1-04 [PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22) **scoped PASS并合并**、[Issue #20关闭](https://github.com/Zwhao0/GREYHOUND_online/issues/20)。[最终独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/22#issuecomment-6310090904)、[CI DOC+100 CPU PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39557871658)。
- **已经证明**：两台共享H800，Torch2.14.1+cu130/NCCL2.30.7/实际Profiler v4，健康4Rank dense DDP的70个观察Collective匹配；106637组sidecar四时间戳，280/280个实际Host begin事件有≤1ms半宽的严格因果时间包络，source半宽p50/p95/max 0.511319/0.526649/0.583573ms，69个连续AllReduce满足预算。[纠错报告](docs/G1-04-CORRECTION.md)、[真实逐事件统计](docs/evidence/g1-04-correction-summary.json)。
- **能力边界**：196/280=70%跨节点事件对无法确定严格先后；Host callback不等于GPU执行时刻。没有原发/受害Rank定位、全量零drop、跨GPU时钟、step关联、长期fail-open或≤2%低开销证明。历史p50 +6%～8%风险保留。
- **G2/G3/G4：NOT_STARTED / BLOCKED_PENDING_EXPLICIT_USER_APPROVAL。** 不因G1 scoped PASS自动开启G2。

## 唯一下一步：等待用户授权 G2

技术上建议采用**小样本独立真值盲测**作为G2的第一项可证伪实验：比较健康、单一计算慢、通信路径异常的真实被动观测，分清 late-to-collective 与 waiting；若分不开先降级至组/边/UNKNOWN并考虑局部基线和额外非侵入信号。**目前只是下一阶段提案，不是已授权的Codex执行任务。** 用户此前要求进入G2、故障注入、原发Rank定位必须获明确批准；不得擅自进行任何此类实验或创建可执行任务。共享H800上做故障注入须另核实隔离独占窗口和共租安全。

主Codex保持当前main/PR/CI清晰、留存和脱敏规则，不在G1反复测试、不改生产模型/PyTorch/NCCL核心、宿主驱动/全局依赖或他人GPU工作。下一次新窗口先读此文件、[STATUS](STATUS.md)、[ROADMAP](ROADMAP.md)按需查证细节即可。
