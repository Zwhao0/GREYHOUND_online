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

## DEC-005 — 2026-10-20：实际仓库已创建且为 Public

- 唯一仓库是 `Zwhao0/GREYHOUND_online`（用户创建，Public），与原拟定的 `Greenhound-Online` slug 不同。项目名称仍为 **Greenhound Online**，不是上游 GREYHOUND 官方项目。
- 此次 Bootstrap 仅上传项目原创规划、任务、约束和文档验证脚本；引入上游实现需单独确认许可证并遵守公司信息安全限制。
- 首项任务 [G0-01 #1](https://github.com/Zwhao0/GREYHOUND_online/issues/1) 目前只允许静态审计，未经授权不运行 H800。

## DEC-006 — 2026-10-20：G0 有限范围通过，进入 G1（已批准）

**事实**：G0-01源码静态审计PASS；G0-02单机NCCL微基准PARTIAL（两rank各87条事件匹配）；G0-03真实单机2×H800 PyTorch dense DDP PASS，分别取得两个Rank的94条可关联Collective和40步CUDA Event计时。G0-03执行期间所用版本为Torch2.7.0a0/NCCL2.25.1、Profiler v2，与G0-02的nccl-tests NCCL2.28.3/Profiler v4不同。参阅[PR #8审核](https://github.com/Zwhao0/GREYHOUND_online/pull/8#issuecomment-6294245015)。

**决定**：ROADMAP G0“候选/观测可行性、真实GPU小样本、初步开销”Gate **限定范围PASS**；同意进入 [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 的最小两节点Rank证据采集。G0 PASS不代表生产级长期低开销、fail-open、跨节点匹配、原发Rank因果或v4 GPU channel证据，均须在后续Gate以真实数据验证；**G1/G2尚未通过**。

**权限边界**：G0-03 Codex报告曾获用户在其窗口追加访问既有sudo Docker daemon许可，与原Issue禁止权限使用有差别；审核保留此偏差，不能将该授权自动延伸到G1，下一次须重新确认每台测试节点/共享GPU/容器权限。禁止修改系统NCCL/框架与生产任务。

## DEC-007 — 2026-10-20：Codex 双层子智能体分工（用户明确批准）

主Codex负责方案整合、实际GPU操作和最终PR/证据；可以并行委派任务以减少主窗口上下文。**GPT 6 luna max**优先执行简单、机械、重复任务；仅在其失败或任务确有复杂性时升级 **GPT 6.1 sol medium**；主窗口可决定是否需要子智能体，避免为了分工制造额外工作。子智能体回报简短结论、变更与证据，遵守AGENTS授权与安全规则，不得自行跨Gate、GPU越权或同时修改HANDOFF/STATUS。
