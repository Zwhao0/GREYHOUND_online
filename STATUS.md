# STATUS — Greenhound Online

- 更新日期：2026-10-20
- 项目：Greenhound Online
- 唯一仓库：[`Zwhao0/GREYHOUND_online`](https://github.com/Zwhao0/GREYHOUND_online)（Public）
- 远端仓库：**CREATED**（main Bootstrap 文件已上传并回读）
- 当前阶段：**G0 IN_PROGRESS**；G0-01 静态审计 **PASS / MERGED**；G0-02 单节点字段 PoC **PARTIAL / DRAFT_REVIEW_PENDING**
- 当前任务：[G0-02 Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3)：隔离单节点 2×H800 NCCL Profiler 真实字段 PoC；整个 G0 Gate 未通过，G1 未授权
- 本项目代码实现：仅最小NCCL复现shell入口；无采集器/定位算法开发
- 真实 H800 实验：共享单节点2 GPU官方NCCL微基准PASS；dense DDP NOT_RUN
- 真实开销测量：一次对照/插件聚合均值已采；step p50/p95 NOT_AVAILABLE，非独占SLA
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
2. 本次目标NCCL进程实际加载2.28.3 DSO与v4插件已核对；Torch/DDP未使用，不能替代生产训练运行时核验。
3. GREYHOUND 改造的源码许可、可用性与可能的强制同步：静态审计已定位同步/暂停路径；许可仍 UNVERIFIED，禁止复制。
4. Probing/NCCL Profiler 与训练版本 ABI 和 Rank 事件覆盖：本次官方example实际v4加载成功；Probing未运行，精确丢失、长期阻塞/fail-open与DDP开销仍未知。
5. 用户本轮明确允许共享GPU后已执行单机微基准；设备非独占，性能受共租干扰。后续Torch入口、DDP/双机/注入仍需独立授权。

## Gate 记录

| Gate | 状态 | 证据 | 放行人 |
| --- | --- | --- | --- |
| Bootstrap | **PASS** | main 文件、Issue #1 已回读，文档 CI 已通过 | ChatGPT / 2026-10-20 |
| G0：候选/可观测性 | G0-01 STATIC_AUDIT_PASS / G0-02 PARTIAL / DRAFT_REVIEW_PENDING；G0 总 Gate 未通过 | [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) 已合并；[真实摘要](docs/evidence/g0-02-summary.json)；本次NCCL字段/加载/回退成功，DDP未验证 | ChatGPT / 2026-10-20（仅 G0-01） |
| G1：Rank 级证据采集 | BLOCKED_BY_G0 | 无 | — |
| G2：真实数据离线归因 | BLOCKED_BY_G1 | 无 | — |
| G3：在线非暂停模式 | BLOCKED_BY_G2 | 无 | — |
| G4：DP/TP/PP 扩展评估 | BLOCKED_BY_G3 | 无 | — |

> 只有有可检查的 GitHub 证据且获得 ChatGPT/用户审查批准后，才能升级状态；不得用“文档完成”替代真实功能测试。

## G0-01 静态审核通过 / G0-02 启动记录（2026-10-20）

- 首测 A：NCCL 原生 Profiler example 短窗口字段 PoC；备选 B：Probing 单独受控试验。Inspector 仅兼容版本摘要，不能代替原始事件完整性。
- 证据：[来源/许可](docs/SOURCES_AND_LICENSES.md)、[最小契约](docs/MEASUREMENT_CONTRACT.md)、[结论/阻断/PoC](docs/G0-01-AUDIT.md)。尚无完整生产非暂停采集器通过证明。
- G0-02候选：首测A官方example得到两rank各87个可对齐Collective、1392对GPU channel事件；实际NCCL2.28.3 + 插件v4；B未启用。一次平均延迟变化约+0.866%/+0.963%，不作SLA结论。
- DOC：本地静态检查，最新HEAD CI见[PR checks](https://github.com/Zwhao0/GREYHOUND_online/pull/5/checks)；CPU=NOT_RUN；GPU=PASS（仅共享单机NCCL微基准）；DDP=NOT_RUN；MULTINODE=NOT_RUN。
- G0-02 Draft PR：[PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)，分支 `g0-02-profiler-poc`（候选未合并，HEAD实时读取）；[执行记录](docs/G0-01-AUDIT.md)、[脱敏事实](docs/evidence/g0-02-summary.json)。
- 下一动作：ChatGPT独立审核本Draft；后续先明确现有Torch环境及资源条件，再单独授权dense DDP/step分位数。禁止自行合并、G1、双机、注入、升级或算法开发。
