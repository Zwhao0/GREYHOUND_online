# HANDOFF — Greenhound Online（唯一交接入口）

**使用说明：** 任何新的 ChatGPT 或 Codex 窗口首先阅读此文件，按下方“接班第一步”执行。它指向事实状态、设计记录和当前任务，避免依赖聊天上下文。**每次经审核的阶段变化都必须更新本文。**

## A. 当前快照

| 字段 | 当前值 |
| --- | --- |
| 更新日期 | 2026-10-20 |
| 唯一仓库 | [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public，默认main） |
| 当前阶段 | **G0 IN_PROGRESS**；G0-01 PASS；G0-02 PARTIAL/已审已合并；G0-03 READY/NOT_STARTED；G1 BLOCKED |
| 当前 Issue | [G0-03 #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6)（OPEN）；G0-02 Issue #3 CLOSED/PARTIAL |
| PR / HEAD | [G0-02 PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5) MERGED，merge `f421fb752696d1e7f3a56344fc6e8a45c8b5d5d0`；最新 main HEAD 每次通过GitHub回读；G0-03执行PR尚无 |
| CI | [G0-02 DOC PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39442234938)；CPU NOT_RUN；GPU PASS仅单节点NCCL微基准 |
| GPU/训练/双节点 | 2×H800 nccl-tests真实微基准已跑（87对AllReduce）；PyTorch DDP、MULTINODE均 NOT_RUN |
| 独立审核结论 | [G0-02 ACCEPTED AS PARTIAL](https://github.com/Zwhao0/GREYHOUND_online/pull/5#issuecomment-6293707808)；仅 G0-03 Issue #6 范围获授权，须重新确认GPU资源许可；G1/G2/G3、双机和注入均未授权 |

## B. 已批准的方向（不得在交接中重新解释）

1. V1 目标：**不中断训练的 Fail-Slow 检测与分层 Rank 归因**。从固定密集 DDP 开始，再到 DP/TP/PP，普通 NCCL；MoE 后续可选。
2. 设计路线 B：GREYHOUND 的 ACF/BOCD 检测和可疑 Group 缩小范围 + 复用开源 NCCL/系统观测 + 新的离线先行 Rank 归因 + 最后在线化。
3. 双基线只做有数据前提的辅助校验；缺少真正可比的健康历史/Peer 就输出不可用，不得臆造。
4. 不修改生产训练脚本/模型/框架/NCCL 源码；不暂停、不在训练世界通信组插入验证 collective；重采样和热路径开销必须实测；组件 fail-open。
5. 不复制许可证尚未核实的 GREYHOUND detector 源码；外部项目须先记录来源和再利用许可。
6. ChatGPT 负责规划与独立审核；Codex 负责执行和整理证据；用户批准 Gate 的转换。

## C. 立即下一步（只做这一件）

**执行 [G0-03 Issue #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6) 的许可单节点真实 PyTorch DDP + NCCL Profiler 字段/step分位数 PoC；仍属 G0。**

- G0-02以PARTIAL审核合并：两rank的NCCL微基准各采87个AllReduce并匹配，实际NCCL2.28.3+官方Profiler v4。**没有验证PyTorch DDP和step p50/p95。**
- 上轮阻塞：宿主Python无Torch且Docker普通用户不能访问。优先复用用户许可可访问的已有Torch环境；找不到则只在任务私有目录轻量尝试已有/授权wheel；不得系统升级、root或耗时搭平台。无法轻量获取则立刻BLOCKED并只说明一条解阻条件。**绝不重跑nccl-tests替代DDP。**
- 仅在重新确认 GPU许可与空闲容量后最多单机2×H800、无注入，做一次最小dense DDP无插件对照+官方同Profiler短窗；真实训练step用明确口径给出方向性p50/p95和字段对齐。若环境或权限不符则不能运行。
- 一个Draft PR、脱敏证据、CI和同PR内STATUS/HANDOFF更新；禁双机、注入、生产服务、系统升级、定位算法、自行merge/跨Gate。

## D. 接班第一步：每个新 ChatGPT / Codex 窗口

1. 以 GitHub 仓库 **真实可访问的内容**为准读取 `HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`。仓库已创建；新窗口应从实际 main 和 Draft PR 的真实状态继续。
2. 检查当前 Issue、Draft PR、PR HEAD SHA、base、最新 CI 与真实实验报告；区分 `MAIN` 和 `DRAFT`。
3. 简要复述：当前 Gate、已有证据、尚未批准的事项、**下一项最小任务**。若状态冲突先指出，不盲目继续。
4. 每个执行窗口结束前更新本文（若未授权写入 GitHub，给出建议变更，不擅自将其标为已提交）。

## E. 当前需关注的风险

- nccl-tests的NCCL2.28.3 v4 profiler可用**不等于**PyTorch DDP实际动态库/ABI已验证。
- 单次共享GPU的NCCL平均延迟变化约+0.87%/+0.96%，不能当真实DDP step性能证明；共享环境干扰未知。
- 宿主缺Torch且无普通用户Docker访问权限；G0-03不能通过生产环境窥探、root或系统升级解阻。
- 官方example仍有静默drop和尾窗限制，精确drop/完整性、长期非阻塞/fail-open与原发Rank证据尚缺；不得编造。
- GREYHOUND原profiler含强制CUDA同步及暂停/主动验证路径，detector许可证未明确；不可复制/沿用。
- Pubic仓库禁止主机、内网地址、凭证、公司日志、模型权重等敏感资料。

## F. 当前交接给 ChatGPT 新窗口的完整指令

> 继续Greenhound Online，唯一仓库Zwhao0/GREYHOUND_online。首先GitHub读取HANDOFF/STATUS/AGENTS/ROADMAP/docs/DECISIONS及Issue/PR/CI。G0-01 PASS；G0-02的PR #5已审核以PARTIAL合并、Issue #3 CLOSED：单机2×H800 nccl-tests采87对可关联AllReduce，NCCL2.28.3+profiler v4真实加载。但PyTorch dense DDP、step p50/p95尚未运行，G0总Gate未过，G1仍BLOCKED。下一项G0-03 Issue #6在重新确认许可的资源上取得Torch入口，跑单机2GPU最小DDP+同Profiler真实字段/step分位数。禁止重复nccl-tests、root/系统升级、双机/注入、定位算法；Codex执行并提交Draft，ChatGPT审核。

## G. 当前交接给 Codex 新窗口的完整指令

> 你是Greenhound Online主Codex。唯一仓库Zwhao0/GREYHOUND_online。首先GitHub读HANDOFF、STATUS、AGENTS、ROADMAP、docs/DECISIONS、docs/MEASUREMENT_CONTRACT和G0-03 Issue #6。G0-02已以PARTIAL审核合并、Issue #3 CLOSED，单机NCCL原始事件字段87对已验证，**不必重复nccl-tests**。按照Issue #6先寻找可受权使用的Torch入口，失败则快速BLOCKED；若可用且重新确认2×H800资源许可，执行一组短时真实dense DDP baseline与同NCCL Profiler，记录目标PID加载版本、跨Rank事件匹配及step p50/p95（注意时钟语义），脱敏保存。不得碰系统环境/他人训练，不得双机、注入、Rank算法开发。完成一个Draft PR并在同一PR更新STATUS/HANDOFF，停止等待ChatGPT独立审核。

## H. 后续每次必须更新的交接字段模板

```text
Updated (UTC/Asia-Shanghai):
Repository / default branch / main HEAD:
Active Gate and approval state:
Authorized Issue and exact scope:
Draft PR URL / branch / HEAD / base / merge status:
Tests: DOC= / CPU= / GPU= / MULTINODE= (each PASS/FAIL/NOT_RUN + evidence):
Observed results and data completeness:
Unknowns, blockers, license/security concerns:
Next single action (owner + acceptance criteria):
Explicitly forbidden next actions:
```
