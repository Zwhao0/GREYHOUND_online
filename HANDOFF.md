# HANDOFF — Greenhound Online

> ChatGPT / Codex 新窗口简短入口（2026-10-21，Asia/Shanghai）。以 GitHub main、当期 Issue/PR 为事实源；细节按需打开，不复制历史长日志。

- **唯一仓库**：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)，Public。ChatGPT负责规划、独立审核/Gate；Codex主窗口负责实施，子智能体只处理分工任务。
- **G0 PASS、G1 `PASS_SCOPED_OBSERVABILITY`**，已经完成，不重新验收。[PR #22与独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/22)。健康两机H800 4Rank事件匹配与Host因果有界时间映射已证明；**不是**故障定位精度或生产低开销证明。时间比较70%仍UNKNOWN、GPU端时钟/全集drop/实际净开销未充分证明。
- **用户刚批准进入G2及有界测试故障注入。G2-01 OPEN / NOT_RUN**：[唯一可执行 Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24)。G2总Gate未通过；G3/G4不授权。
- **G2-01目标**：在隔离合成两机4Rank dense DDP上，先CPU+资源预检，再最多一次健康与一次含8个独立真值episode的单Rank pre-backward 20ms延迟测试。定位器不能读注入真值；冻结预测再揭盲，报告Top-1/UNKNOWN/健康误报，快速判断现有被动信号GO/NO_GO/INCONCLUSIVE。**不是完整G2 30次精度验收**。
- **授权边界**：获准两台共享H800的可安全分配测试资源、受控注入、私有venv/任务目录；不影响其他训练，不改生产训练脚本/模型/PyTorch/NCCL核心或宿主全局依赖。不新增训练world诊断collective/每step GPU同步，不泄露Public仓库敏感日志/地址/真值。主Codex先核实共租安全，安全不满足则说明阻断。
- **交付**：一个Draft PR、真实GPU证据分类、少量必要CPU反例、简洁同步 `STATUS.md`/`HANDOFF.md` 后停等ChatGPT审核；不自行合并或进入G3。子智能体 GPT 6 luna max 处理fixture/重复工作，GPT 6.1 sol medium只处理复杂因果或盲评问题，主Codex负责真实GPU/集成。

按需：[STATUS](STATUS.md) · [G2-01 Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24) · [ROADMAP](ROADMAP.md) · [AGENTS](AGENTS.md) · [G1证据](docs/G1-04-CORRECTION.md)。
