# HANDOFF — Greenhound Online

> 跨 ChatGPT / Codex 窗口的简短入口。以 [GitHub main](https://github.com/Zwhao0/GREYHOUND_online)、当前 Issue/PR 为事实源，不复制历史实验全文。

## 当前状态（2026-10-21，Asia/Shanghai）

- **G0**：单节点限定范围 **PASS**，不再重复验收。
- **G1-01**：[Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) **CLOSED / scoped PASS**，[PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) 已独立审核并合并（squash `1c2ef7f491d5979f1d7e3a55a54bd4d537e7b77c`）；[审核记录](https://github.com/Zwhao0/GREYHOUND_online/pull/13#issuecomment-6306390974)、[最终CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39457361258)。
- **G1 总 Gate**：**IN_PROGRESS**，未批准通过；G2/G3 BLOCKED。
- **已得证据**：在两机H800私有Torch 2.14.1+cu130 / NCCL 2.30.7 / 实际Profiler v4上，健康4 Rank DDP短窗观察到70个四Rank Collective匹配。仅观察窗口内一致；精确drop/共同遗漏、跨GPU/节点校时、step→Coll与原发/等待因果 UNKNOWN。单次共享资源GPU step p50相对增加6.1%～7.5%，并非低开销达标。

## 唯一下一步

**Codex 执行 [G1-02 Issue #14：跨 Rank 时间可信度与事件采集质量边界](https://github.com/Zwhao0/GREYHOUND_online/issues/14)**。复用本次已经实测的新稳定栈；不另做软件升级Gate，不重验G0/G1-01。优先CPU离线质量/时钟分析及fixture，最小补证，只有采集或采样路径变化才追加一次有界健康双节点实验。交一个 Draft PR，更新 STATUS/HANDOFF 并停止待ChatGPT独立审核。

**权限边界**：沿用已批准的两台共享H800隔离测试、私有venv和有限健康采集；主Codex确认资源归属和共租安全。禁止故障注入、原发Rank推理/评分、G2、生产训练/模型/框架/NCCL核心源码修改、训练world诊断collective、宿主驱动与全局依赖变更、停他人任务和公开敏感原始日志。

**分工**：GPT 6 luna max优先做机械式数据/CPU fixture/文档；GPT 6.1 sol medium处理时钟误差/ABI难题；主Codex负责真实GPU、整合与权限。避免并行改交接文档。

## 按需查阅

- [STATUS.md](STATUS.md)：Gate状态和真实测试分类。
- [G1-01实验报告](docs/G1-01-RESULTS.md)、[脱敏汇总](docs/evidence/g1-01-summary.json)、[匹配证据](docs/evidence/g1-01-matches.json)：上轮详细依据。
- [AGENTS.md](AGENTS.md)、[ROADMAP.md](ROADMAP.md)、[MEASUREMENT_CONTRACT.md](docs/MEASUREMENT_CONTRACT.md)：规则、出口和时钟/完整性契约。仅用到时再展开。
