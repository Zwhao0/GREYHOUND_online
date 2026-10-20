# 决策记录（持续追加，不覆盖历史结论）

## DEC-001 — 2026-10-20：选择 GREYHOUND 扩展路线 B（已批准）

**背景：** 上一轮将“组定位 + 双基线 + Rank 打分”直接交给 Codex，实现遇到真实数据无法建立健康基线的问题；原 GREYHOUND Validation 会暂停训练，不能满足目标。

**决定：** 借鉴/保留 GREYHOUND 异常检测与 Group 筛选，单独评估 Probing 等现成 NCCL 观测，先建立真实 Rank 级事件和因果证据契约，做离线定位盲测，通过后才在线化。不允许照搬未验证的精度或开销数据。

**替代方案：** A 直接加规则：拒绝（证据不足风险）；C 全部重写：暂缓（成本高）。

## DEC-002 — 2026-10-20：V1 缩减范围（已批准）

普通 NCCL；先固定密集 DDP，再扩展 DP/TP/PP。MoE/DeepEP 非必需。首要研究 Fail-Slow，定位输出允许 `ROOT_CANDIDATE` / `SUSPECT_GROUP_OR_EDGE` / `UNKNOWN`。不暂停训练、不改训练脚本/模型/框架源码、保持低开销。

## DEC-003 — 2026-10-20：GitHub 和交接规则（已批准）

- GitHub 单独新工程；ChatGPT 规划审查，Codex + 子智能体执行；GitHub Issue/PR 保留可回读证据。
- 根目录 `HANDOFF.md` 是跨窗口唯一入口，`STATUS.md` 是事实状态，`AGENTS.md` 是执行边界，`ROADMAP.md` 是 Gate 定义。
- PR 不自动合并；Draft 的结果不能冒充 `main` 已具备；每个 Gate 转换需明确批准。
- GitHub 仓库默认建议 Private，公开前处理外部代码许可证和公司数据安全问题。

## DEC-004 — 2026-10-20：暂缓导入外部代码（安全门槛）

GREYHOUND detector 许可证尚未核实；暂不复制源码。可以读论文、读公开代码并自研，公开依赖需要按仓库及文件级别确认许可证和版本。

## DEC-005 — 2026-10-20：实际 GitHub 仓库与可见性（仓库事实）

- 用户实际创建了 `Zwhao0/GREYHOUND_online`，与原拟定 slug `Greenhound-Online` 不同。后续唯一仓库使用真实地址，不再新建同类仓库。
- 当前仓库为 **Public**。Bootstrap 只包含本项目原创规划/流程/任务文档与验证脚本；不导入上游 GREYHOUND 源码、不上传公司内部日志、网络地址、模型和密钥。
- 项目对外展示名仍是 **Greenhound Online**，须明确其并非原 GREYHOUND 项目官方分支。
