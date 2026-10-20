# STATUS — Greenhound Online

- 更新日期：2026-10-20
- 项目：Greenhound Online
- 唯一仓库：[`Zwhao0/GREYHOUND_online`](https://github.com/Zwhao0/GREYHOUND_online)（Public）
- 远端仓库：**CREATED**（main Bootstrap 文件已上传并回读）
- 当前阶段：**BOOTSTRAP PASS**；G0-01 静态审计 READY / NOT_STARTED
- 下一阶段：`G0`，候选工具可用性与真实观测可行性评估
- 本项目代码实现：NOT_STARTED
- 真实 H800 训练实验：NOT_RUN
- 真实开销测量：NOT_RUN
- GPU/Rank 故障定位准确率：UNKNOWN / 尚无本项目实验依据
- GitHub Issue：[G0-01 #1](https://github.com/Zwhao0/GREYHOUND_online/issues/1)（OPEN）；PR：NOT_CREATED；文档 CI：[PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39423267555)（Bootstrap 提交；最新 HEAD 的运行仍须核查）
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
3. GREYHOUND 改造的源码许可、可用性与可能的强制同步：需要专门审核。
4. Probing/NCCL Profiler 与训练版本 ABI 和 Rank 事件覆盖：需要验证。
5. GPU 和双机实验资源访问授权及数据留存策略：未确认。

## Gate 记录

| Gate | 状态 | 证据 | 放行人 |
| --- | --- | --- | --- |
| Bootstrap | **PASS** | main 文件、Issue #1 已回读，文档 CI 已通过 | ChatGPT / 2026-10-20 |
| G0：候选/可观测性 | STATIC_AUDIT_READY / NOT_STARTED | Issue #1，尚无 GPU 证据 | — |
| G1：Rank 级证据采集 | BLOCKED_BY_G0 | 无 | — |
| G2：真实数据离线归因 | BLOCKED_BY_G1 | 无 | — |
| G3：在线非暂停模式 | BLOCKED_BY_G2 | 无 | — |
| G4：DP/TP/PP 扩展评估 | BLOCKED_BY_G3 | 无 | — |

> 只有有可检查的 GitHub 证据且获得 ChatGPT/用户审查批准后，才能升级状态；不得用“文档完成”替代真实功能测试。
