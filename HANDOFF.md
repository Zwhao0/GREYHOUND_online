# HANDOFF — Greenhound Online

> 当前快照：2026-10-21（Asia/Shanghai）。以 GitHub main、当期 Issue/PR 为准；本次 G2-01 内容为候选未合并。

- **唯一仓库**：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)。G0 PASS、G1 PASS_SCOPED_OBSERVABILITY 已完成，不重新验收。
- **授权**：[唯一 Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24) 的隔离合成 DDP 受控注入已执行；没有进入 G3。主窗口负责 GPU/集成，luna max 负责 fixture，sol medium 负责因果/盲评审阅。
- **提交与 PR**：唯一 [Draft PR #26](https://github.com/Zwhao0/GREYHOUND_online/pull/26)，分支 `g2-01-blind-failslow`；代码/计划承诺冻结 `37d5432`，真实预测先提交 `0f87ac3` 再揭盲。最终 HEAD 与 CI 见 PR，不把未合并内容当 main。
- **结果**：真实健康 1 次 + 注入 1 次；8 次 sleep 有效。Top-1 **3/8**、注入 UNKNOWN **0/8**、无新注入窗口告警 **6/8**。预登记停损 **NO_GO_FOR_CURRENT_SIGNAL**；episode 恢复/独立未证明，隔离故障可识别性 **INCONCLUSIVE**，G2 总 Gate 未过。
- **测试与风险**：DOC/CPU 130 tests PASS；GPU/MULTINODE 远端训练和侧车全 exit0，各运行 90 实例匹配，356 个 AllReduce Host begin 有界。两节点任务残留 0、原有应用各 8 个；本地注入主控未正常收尾，远端凭据及故障记录保留。Host 相位持续偏移导致后续错误归因；全集 loss/GPU 绝对时钟/净开销未证明。
- **唯一下一步**：停止，等待 ChatGPT 独立审核同一 Draft PR。下一轮若获准，应先审查本地进度/恢复证据与无拖尾判据，不直接启动 ≥30 次评估。
- **禁止动作**：不自行合并、追加 GPU、自动进入 G3、修改共租/生产任务、泄露私有原始日志或计划 nonce。私有证据审核结束后 7 天内手动清理。

导航：[STATUS](STATUS.md) · [G2-01 详细实验](docs/G2-01-RESULTS.md) · [公开证据审阅](docs/G2-01-INDEPENDENT-REVIEW.md) · [G1 已验收证据](docs/G1-04-CORRECTION.md)。
