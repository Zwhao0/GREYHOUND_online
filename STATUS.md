# STATUS — Greenhound Online

- 更新日期：2026-10-20
- 唯一仓库：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public）；默认分支 `main`
- 当前阶段：**G0 IN_PROGRESS**；G0-01 静态审计 **PASS**；G0-02 NCCL 微基准 **DELIVERED / PARTIAL / MERGED**；G0-03 真实 DDP PoC **OPEN / NOT_STARTED**
- 当前任务：[G0-03 Issue #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6) — 单节点许可环境下真实 PyTorch dense DDP + NCCL Profiler 字段/step 时延 PoC
- 状态变更：[G0-02 PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5) 已由 ChatGPT 独立审核后合并，squash SHA `f421fb752696d1e7f3a56344fc6e8a45c8b5d5d0`；[Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3) **CLOSED / PARTIAL_DELIVERED**
- 实测：[G0-02 脱敏证据](docs/evidence/g0-02-summary.json)；[执行记录](docs/G0-01-AUDIT.md)；[最终 HEAD DOC CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39442234938)
- 目前系统代码：尚无在线检测/Rank 定位系统；仅有微基准复现脚本
- 实测分类：DOC=PASS；CPU算法测试=NOT_RUN；GPU=PASS（仅单节点 2×H800 nccl-tests）；**DDP=NOT_RUN；MULTINODE=NOT_RUN**
- 真实开销：共享GPU下一次NCCL microbenchmark均值增幅约 +0.866% / +0.963%；DDP step p50/p95 **NOT_AVAILABLE**，不可宣称生产 ≤2% 开销、非阻塞或 fail-open
- 故障原发Rank定位准确率：UNKNOWN；尚无真实注入、因果归因和在线服务证据

## 已批准产品约束

1. 路线B：借鉴 GREYHOUND ACF/变点及 Group 筛选，先复用兼容的开源 NCCL 观测并验证真实Rank证据，再做离线归因、最后在线化。
2. V1先固定 dense DDP、普通 NCCL、两台 H800，后续DP/TP/PP；MoE/DeepEP/恢复不作第一版强制条件。
3. 不修改生产训练/模型/框架/NCCL源代码，不暂停、不插入诊断collective，低开销与fail-open必须实测。
4. GREYHOUND detector 许可证仍 UNVERIFIED，禁止复制。仓库Public，禁止发布公司主机、内网、密钥、私有原始日志及权重。
5. ChatGPT规划/独立审核，Codex执行并以Draft PR交付；跨Gate及双机/注入实验须另行明确授权。

## 阶段验收

| Gate | 状态 | 可核查的证据 |
| --- | --- | --- |
| Bootstrap | PASS | 初始化与文档CI |
| G0-01 静态审计 | PASS / MERGED | [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) |
| G0-02 单机 NCCL microbenchmark | **PARTIAL / ACCEPTED / MERGED** | [PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)；2rank各87条AllReduce，87对可关联 |
| G0-03 单机 PyTorch DDP | **OPEN / NOT_STARTED** | [Issue #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6) |
| G0 总 Gate | **IN_PROGRESS / NOT_PASSED** | DDP缺证据；低开销长期性/丢失/因果均不支持宣称 |
| G1 Rank级跨节点数据 | BLOCKED_BY_G0 | 无 |
| G2 离线因果归因 | BLOCKED_BY_G1 | 无 |
| G3 在线非暂停 | BLOCKED_BY_G2 | 无 |
| G4 DP/TP/PP扩展 | BLOCKED_BY_G3 | 无 |

## 下一步及真实缺口

- **已验证**：目标 `nccl-tests` 进程真实加载 NCCL 2.28.3 + 官方 v4 Profiler；同commHash的两rank各87条AllReduce事件可匹配，原始GPU channel clock可见。仅一次共享GPU环境的方向性开销样本；未证明全历史完整、精确drop、原发/等待或长期fail-open。
- **G0-03**：上轮宿主默认Python无Torch、普通用户无Docker权限。先在重新确认许可的资源/目录找可用Torch运行环境；如有，最小2-GPU DDP baseline+plugin一次短窗，记录实际DDP进程NCCL/ABI/collective及step p50/p95。如无可用环境，快速BLOCKED，明确用户需要提供的受授权Torch入口。不能通过重跑nccl-tests代替。
- **禁止**：未经许可操作共享GPU或生产环境、sudo/Docker越权、系统升级、双机、故障注入、Rank算法、主动验证和自行跨Gate。
