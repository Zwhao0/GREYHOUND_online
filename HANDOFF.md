# HANDOFF — Greenhound Online

> 跨 ChatGPT / Codex 窗口的简短入口。以 [GitHub main](https://github.com/Zwhao0/GREYHOUND_online)、当前 Issue/PR 为事实源，不复制历史实验全文。

## 当前状态（2026-10-21，Asia/Shanghai）

- **G0**：单节点限定范围 **PASS**，不再重复验收。
- **G1-01**：[Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) **CLOSED / scoped PASS**，[PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) 已独立审核并合并（squash `1c2ef7f491d5979f1d7e3a55a54bd4d537e7b77c`）；[审核记录](https://github.com/Zwhao0/GREYHOUND_online/pull/13#issuecomment-6306390974)、[最终CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39457361258)。
- **G1 总 Gate**：**IN_PROGRESS**，未批准通过；G2/G3 BLOCKED。
- **已得证据**：在两机H800私有Torch 2.14.1+cu130 / NCCL 2.30.7 / 实际Profiler v4上，健康4 Rank DDP短窗观察到70个四Rank Collective匹配。仅观察窗口内一致；精确drop/共同遗漏、跨GPU/节点校时、step→Coll与原发/等待因果 UNKNOWN。单次共享资源GPU step p50相对增加6.1%～7.5%，并非低开销达标。

## G1-02 本轮候选（未合并）

- [Issue #14](https://github.com/Zwhao0/GREYHOUND_online/issues/14)：**PARTIAL，等待独立审核**。新增 CPU CaptureQuality 与时钟反例，G1-01真实归档离线复核；[详细报告](docs/G1-02-RESULTS.md)、[脱敏质量数据](docs/evidence/g1-02-quality.json)。Draft PR / 最终 HEAD / CI 以本轮 PR 为准。
- 真实每 Rank Coll70/Group70/KernelCh553对、AllReduce seq0–68、AllGather seq0；内部gap/重复/配对异常0，仅导出窗口。精确drop、共同遗漏、active window/flush仍 UNKNOWN；跨Rank Host/GPU均 UNSAFE_TO_SUBTRACT。
- **本轮 DOC/CPU；GPU/MULTINODE NOT_RUN**。未改采集/运行路径、未访问远端、未升级。合成时钟区间不等于现场校准。G1总Gate仍 IN_PROGRESS，保留共享短窗6%～8%开销风险。

## 唯一下一步

**停止，等待 ChatGPT 独立审核本轮 Draft PR。** 不合并、不关闭 Issue #14、不自行提交 G1 Gate PASS；G2/G3 BLOCKED。报告中的最小后继方案待审核后另行授权。本轮已有授权工作至 Draft PR 为止。

**权限边界**：禁止故障注入、原发Rank推理/评分、生产/框架/NCCL核心改造、训练world诊断collective、宿主/全局包变更、共租抢占和公开敏感日志。未来如需现场有限健康测试，由主Codex核对资源与明确任务授权。

## 按需查阅

- [STATUS.md](STATUS.md)：Gate和真实测试分类。
- [G1-02结果](docs/G1-02-RESULTS.md)：质量契约、时间来源、反例、风险与回退。
- [G1-01结果](docs/G1-01-RESULTS.md)、[原汇总](docs/evidence/g1-01-summary.json)、[70实例](docs/evidence/g1-01-matches.json)：历史真实采集依据。
- [AGENTS.md](AGENTS.md)、[ROADMAP.md](ROADMAP.md)、[数据契约](docs/MEASUREMENT_CONTRACT.md)：规则与阶段边界。
