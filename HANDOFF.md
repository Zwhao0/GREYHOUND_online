# HANDOFF — Greenhound Online

> 新ChatGPT/Codex窗口入口（2026-10-21，Asia/Shanghai）。唯一仓库 [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)，以main/Issue/PR事实为准，详细证据按需读。

- **G0 PASS / G1 `PASS_SCOPED_OBSERVABILITY`**，不重验。G1是健康2机4Rank NCCL实例/Host时间观测可行，不是故障原发定位。
- **G2-01 [PR #26](https://github.com/Zwhao0/GREYHOUND_online/pull/26) 已独立审核接收负结果并合并，Issue #24 CLOSED**：[审核评论](https://github.com/Zwhao0/GREYHOUND_online/pull/26#issuecomment-6311124128)。真实两机4Rank、8次20ms CPU pre-backward注入，冻结Host绝对晚到方法 Top-1 **3/8**、8个无新注入窗6个出现候选，130 CPU测试PASS；episode恢复/独立未证明。**该定位方法NO_GO，G2总Gate NOT_PASSED，G3/G4 BLOCKED**。
- **揭盲后新假设，仅探索**：同一Rank相邻Collective的本地 `source_ns` 进度差分，8个实际注入点出现该Rank约20ms新增间隔；另外seq19的3个非注入Rank也有约20ms变化（传播嫌疑）。**不能声称新算法已8/8成功**，须全新盲测。
- **唯一下一项 Codex任务：[G2-02 Issue #27](https://github.com/Zwhao0/GREYHOUND_online/issues/27)**。先用旧公开数据CPU验证机制/冻结规则，再基于**新随机隐匿真值**、完全独立预测冻结→揭盲，在获准的隔离共享H800任务最多跑一次新注入4Rank（合法健康baseline可复用）；多Rank同时突变报传播/UNKNOWN，不再按“谁最晚到”排名。一个Draft PR，更新精简STATUS/HANDOFF并停止待ChatGPT独立审核。
- **停损与安全**：如果G2-02再NO_GO，停止仅用NCCL Host精确定位路线，转向非侵入CPU/GPU/NIC额外观测或组级定位；不能无限调阈值。用户此前授权G2隔离测试，**不影响共租/生产，不改训练核心/驱动/全局依赖或进入G3**。主Codex管GPU/盲评隔离，luna max做机械任务，sol medium仅复杂因果/时间问题；子智能体短汇报。

按需：[STATUS](STATUS.md) · [Issue #27](https://github.com/Zwhao0/GREYHOUND_online/issues/27) · [旧实验](docs/G2-01-RESULTS.md) · [G1证据](docs/G1-04-CORRECTION.md) · [AGENTS](AGENTS.md)。
