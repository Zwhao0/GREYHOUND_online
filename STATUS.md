# STATUS — Greenhound Online

- 更新日期：2026-10-20
- 项目：Greenhound Online
- 唯一仓库：[`Zwhao0/GREYHOUND_online`](https://github.com/Zwhao0/GREYHOUND_online)（Public）
- 远端仓库：**CREATED**（main Bootstrap 文件已上传并回读）
- 当前阶段：**G0 IN_PROGRESS**；G0-01 静态审计 **PASS / MERGED**；G0-02 单节点字段 PoC **OPEN / NOT_STARTED**
- 当前下一任务：[G0-02 Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3)：隔离单节点 2×H800 NCCL Profiler 真实字段 PoC；整个 G0 Gate 未通过，G1 未授权
- 本项目代码实现：NOT_STARTED
- 真实 H800 训练实验：NOT_RUN
- 真实开销测量：NOT_RUN
- GPU/Rank 故障定位准确率：UNKNOWN / 尚无本项目实验依据
- GitHub Issue：[G0-01 #1](https://github.com/Zwhao0/GREYHOUND_online/issues/1) **CLOSED**，下一项 [G0-02 #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3) **OPEN**；[PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) **MERGED**（合并提交 `c73d552eb14695fa9e02247193fd8e6465b863d5`）；[对应 HEAD 文档 CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39438158278)
- 原 GREYHOUND detector 许可证：UNVERIFIED，禁止复制或声称已获商用授权

## 已经批准的产品范围

- [x] 用户选择方案 B：保留/借鉴 GREYHOUND 检测与 Group 筛选，复用可兼容的开源 NCCL 观测能力，新增离线先行的 Rank 因果归因，再在线化。
- [x] V1 先支持普通 NCCL、密集模型、固定 workload DDP → DP/TP/PP。
- [x] 不暂停训练、不改训练脚本/模型/框架源码，低开销、fail-open。
- [x] MoE/DeepEP、恢复/迁移和精确物理链路定位不作为 V1 Gate 前提。
- [x] 使用 ChatGPT 策划/独立审核 + Codex 主窗口/子智能体实现 + GitHub Issue/PR 审核 + HANDOFF 持续交接。

## 未关闭的前置问题

1. 实际仓库为 Public；严禁上传公司内部数据、凭证、网络拓扑信息和许可不明的外部源码。
2. 当前训练进程实际 `torch`、CUDA、NCCL 版本与动态链接方式：未核实。过去其他项目的记录不可替代。
3. GREYHOUND 改造的源码许可、可用性与可能的强制同步：静态审计已定位同步/暂停路径；许可仍 UNVERIFIED，禁止复制。
4. Probing/NCCL Profiler 与训练版本 ABI 和 Rank 事件覆盖：已审查上游接口；运行时 ABI、精确丢失统计、阻塞开销仍需验证。
5. G0-02 已发布技术授权边界，但现场必须确认用户许可的隔离测试节点/资源后才可运行 GPU；无现场许可则只能准备并标 BLOCKED。双机测试、故障注入及数据留存需另行审查。

## Gate 记录

| Gate | 状态 | 证据 | 放行人 |
| --- | --- | --- | --- |
| Bootstrap | **PASS** | main 文件、Issue #1 已回读，文档 CI 已通过 | ChatGPT / 2026-10-20 |
| G0：候选/可观测性 | G0-01 STATIC_AUDIT_PASS / G0-02 READY；G0 总 Gate 未通过 | [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) 已合并；[Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3) 已创建；GPU 尚无证据 | ChatGPT / 2026-10-20（仅 G0-01） |
| G1：Rank 级证据采集 | BLOCKED_BY_G0 | 无 | — |
| G2：真实数据离线归因 | BLOCKED_BY_G1 | 无 | — |
| G3：在线非暂停模式 | BLOCKED_BY_G2 | 无 | — |
| G4：DP/TP/PP 扩展评估 | BLOCKED_BY_G3 | 无 | — |

> 只有有可检查的 GitHub 证据且获得 ChatGPT/用户审查批准后，才能升级状态；不得用“文档完成”替代真实功能测试。

## G0-01 静态审核通过 / G0-02 启动记录（2026-10-20）

- 首测 A：NCCL 原生 Profiler example 短窗口字段 PoC；备选 B：Probing 单独受控试验。Inspector 仅兼容版本摘要，不能代替原始事件完整性。
- 证据：[来源/许可](docs/SOURCES_AND_LICENSES.md)、[最小契约](docs/MEASUREMENT_CONTRACT.md)、[结论/阻断/PoC](docs/G0-01-AUDIT.md)。尚无完整生产非暂停采集器通过证明。
- DOC：PR #2 已合并且该 HEAD CI PASS；CPU=NOT_RUN；GPU=NOT_RUN；MULTINODE=NOT_RUN。静态字段存在不代表本项目 GPU 兼容与低开销已通过。
- 下一动作：Codex 执行 [G0-02 #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3)：先核实许可隔离的测试资源和真实动态库，再做最多单节点 2×H800、无注入、短窗口字段 PoC；若无资源许可，准备后标 BLOCKED。禁止双机、生产、注入、升级与算法开发；不得自行跨 Gate。
