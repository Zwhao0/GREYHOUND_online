# STATUS — Greenhound Online

- 更新日期：2026-10-20
- 项目：Greenhound Online
- 唯一仓库：[`Zwhao0/GREYHOUND_online`](https://github.com/Zwhao0/GREYHOUND_online)（Public）
- 远端仓库：**CREATED**（main Bootstrap 文件已上传并回读）
- 当前阶段：**BOOTSTRAP PASS**；G0-01 静态审计已交付待审核（本分支候选，未合并）
- 下一阶段：`G0`，候选工具可用性与真实观测可行性评估
- 本项目代码实现：NOT_STARTED
- 真实 H800 训练实验：NOT_RUN
- 真实开销测量：NOT_RUN
- GPU/Rank 故障定位准确率：UNKNOWN / 尚无本项目实验依据
- GitHub Issue：[G0-01 #1](https://github.com/Zwhao0/GREYHOUND_online/issues/1)（OPEN）；Draft PR：`g0-01-static-audit`（URL随创建回填）；main DOC [PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39423999157)，本分支 DOC 以 PR CI 为准
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
5. GPU 和双机实验资源访问授权及数据留存策略：未确认。

## Gate 记录

| Gate | 状态 | 证据 | 放行人 |
| --- | --- | --- | --- |
| Bootstrap | **PASS** | main 文件、Issue #1 已回读，文档 CI 已通过 | ChatGPT / 2026-10-20 |
| G0：候选/可观测性 | STATIC_AUDIT_DELIVERED / REVIEW_PENDING | [静态报告](docs/G0-01-AUDIT.md)，候选未合并；尚无 GPU 证据 | — |
| G1：Rank 级证据采集 | BLOCKED_BY_G0 | 无 | — |
| G2：真实数据离线归因 | BLOCKED_BY_G1 | 无 | — |
| G3：在线非暂停模式 | BLOCKED_BY_G2 | 无 | — |
| G4：DP/TP/PP 扩展评估 | BLOCKED_BY_G3 | 无 | — |

> 只有有可检查的 GitHub 证据且获得 ChatGPT/用户审查批准后，才能升级状态；不得用“文档完成”替代真实功能测试。

## G0-01 候选结论（等待 ChatGPT 独立审核）

- 首测 A：NCCL 原生 Profiler example 短窗口字段 PoC；备选 B：Probing 单独受控试验。Inspector 仅兼容版本摘要，不能代替原始事件完整性。
- 证据：[来源/许可](docs/SOURCES_AND_LICENSES.md)、[最小契约](docs/MEASUREMENT_CONTRACT.md)、[结论/阻断/PoC](docs/G0-01-AUDIT.md)。尚无完整生产非暂停采集器通过证明。
- DOC：本地现有脚本和 diff 检查，CI 以 Draft PR 实际记录为准；CPU=NOT_RUN；GPU=NOT_RUN；MULTINODE=NOT_RUN。
- 下一动作：ChatGPT 独立审核本 Draft；之后由用户单独授权隔离单节点无注入 PoC。禁止服务器访问、GPU实验、故障注入、算法实现、升级和自行合并/跨 Gate。
