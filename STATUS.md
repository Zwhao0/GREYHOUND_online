# STATUS — Greenhound Online

2026-10-21（Asia/Shanghai）；[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)。以main、当前Issue/PR和CI为事实源。

| 阶段 | 正式状态 | 证据 |
| --- | --- | --- |
| G0 | 限定范围 PASS，不重验 | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) |
| G1 | PASS_SCOPED_OBSERVABILITY，不重验 | [PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22) |
| G2-01 | **NO_GO_FOR_CURRENT_SIGNAL / MERGED；Issue CLOSED** | [PR #26](https://github.com/Zwhao0/GREYHOUND_online/pull/26)、[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/26#issuecomment-6311124128)、[Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24) |
| **G2-02** | **AUTHORIZED / OPEN / NOT_RUN** | [唯一下一任务 Issue #27](https://github.com/Zwhao0/GREYHOUND_online/issues/27) |
| G2 总Gate | **NOT_PASSED** | 不允许用先导小样本冒充精度验收 |
| G3/G4 | **BLOCKED** | 尚未授权在线化/生产化 |

**真实 G2-01 结论**：两机4Rank的1次健康+1次注入均远端正常结束；8次pre-backward 20ms sleep执行，冻结原发候选盲评仅 **3/8 Top-1**，预定8个无新注入窗中**6个出现候选**；130 CPU CI PASS。Rank1累计Host晚到持续占据seq25–88，episode恢复/独立未证实；因此**停止基于绝对Host晚到量的原发Rank定位方法**，G2没有通过。[失败与真值证据](docs/G2-01-RESULTS.md)、[评分](docs/evidence/g2-01-score.json)。

**揭盲后的探索性发现（不算新验证）**：独立从已公开健康/注入轨迹的同Rank本地 `source_ns` 计算相邻Collective间隔增量；8个已知注入位置的Rank均有约20.05–20.68ms突变，另有seq19的3个其他Rank出现约20ms后续突变（疑似等待传播）。**不得报成8/8盲测或据此通过G2**。GPU kernel时间/精确根因/端到端丢失/低开销SLA依旧未证实。

**下一步**：Codex只执行 [Issue #27 G2-02](https://github.com/Zwhao0/GREYHOUND_online/issues/27)：冻结“Rank本地进度增量+多Rank传播UNKNOWN”最小方法，用**新的隐藏随机真值**做至多一次新注入GPU盲测（健康baseline优先复用已有合法数据）。如再次NO_GO，停止仅依赖NCCL Host的精确原发Rank路线，评估额外非侵入CPU/GPU/NIC证据或组级定位。只交一个Draft PR及简洁STATUS/HANDOFF，待ChatGPT独立审核。
