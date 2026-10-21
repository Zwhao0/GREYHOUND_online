# STATUS — Greenhound Online

更新：2026-10-21（Asia/Shanghai）；唯一仓库 [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)。以 GitHub main / 当前 Issue/PR/CI 为准。

| 阶段 | 审核状态 | 证据或下一步 |
| --- | --- | --- |
| G0 | 限定范围 PASS，不重验 | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) |
| G1 | PASS_SCOPED_OBSERVABILITY，不重验 | [PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)；限定 Host 事件可观察性 |
| G2-01 | **候选未合并 / 实验完成 / 待独立审核** | [Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24)；唯一 [Draft PR #26](https://github.com/Zwhao0/GREYHOUND_online/pull/26) |
| G2 总 Gate | **NOT_PASSED** | 先导操作性 NO_GO；隔离 episode 可识别性 INCONCLUSIVE |
| G3/G4 | **BLOCKED** | 未授权在线化或生产部署 |

## G2-01 测试事实

- DOC/CPU：130 tests PASS，文档检查 PASS；最终 HEAD/CI 见唯一 Draft PR。两次真实 GPU/MULTINODE（一次健康、一次注入）均完成，远端训练/侧车 exit 0；没有追加运行。复用 G1 Torch 2.14.1+cu130 / NCCL 2.30.7 / Profiler v4 与严格 Host 因果时钟界。
- 8 次实际 sleep 20.060–20.070ms；冻结预测后揭盲：**Top-1 3/8、注入 UNKNOWN 0/8、预定无新注入窗口告警 6/8**。持续 Rank 1 Host 延后跨越后续窗口，未证明 episode 恢复/独立，不能把 6/8 当干净健康特异度或 3/8 当总体精度。
- 各运行 90/90 通信实例匹配；分析全部 89 个 AllReduce，各 356/356 已观察 Host begin 有界。计数内 drop/reject 0；全集 loss、GPU 时间同步、生产 fail-open/净开销仍 UNKNOWN。两机原有 GPU 应用各 8 个、本任务残留 0；本地注入主控会话中断收尾，远端完成凭据保留。
- [详细结果与失败记录](docs/G2-01-RESULTS.md)、[脱敏汇总](docs/evidence/g2-01-summary.json)、[预登记](docs/evidence/g2-01-registration.json)、[事后因果审阅](docs/G2-01-INDEPENDENT-REVIEW.md)。不复制大日志。

## 唯一下一动作

停止等待 ChatGPT 对同一 Draft PR 的 HEAD、CI、冻结/揭盲证据独立审核。建议先设计本地进度/恢复证据，再决定后续 G2；本次不实现后续设计、不合并、不重跑、不进入 G3。
