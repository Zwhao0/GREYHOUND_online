# HANDOFF — Greenhound Online（唯一交接入口）

**使用说明：** 任何新的 ChatGPT 或 Codex 窗口首先阅读此文件，按下方“接班第一步”执行。它指向事实状态、设计记录和当前任务，避免依赖聊天上下文。**每次经审核的阶段变化都必须更新本文。**

## A. 当前快照

| 字段 | 当前值 |
| --- | --- |
| 更新日期 | 2026-10-20 |
| 唯一仓库 | [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public，默认main） |
| 当前阶段 | **G0 IN_PROGRESS**；G0-01 PASS；G0-02 PARTIAL/已审已合并；G0-03 PASS/DRAFT_REVIEW_PENDING；G1 BLOCKED |
| 当前 Issue | [G0-03 #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6)（OPEN）；G0-02 Issue #3 CLOSED/PARTIAL |
| PR / HEAD | [G0-02 PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5) MERGED，merge `f421fb752696d1e7f3a56344fc6e8a45c8b5d5d0`；最新 main HEAD 每次通过GitHub回读；G0-03 [Draft PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8)，分支 `g0-03-ddp-poc`；HEAD实时读取；base `67d4cd5736adfd2481eed1df803b4a573bc62ead` |
| CI | [G0-02 DOC PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39442234938)；CPU算法测试NOT_RUN；G0-03本地DOC检查，最终HEAD CI见[PR checks](https://github.com/Zwhao0/GREYHOUND_online/pull/8/checks) |
| GPU/训练/双节点 | 2×H800 nccl-tests真实微基准已跑（87对AllReduce）；G0-03真实PyTorch DDP PASS（候选待审核）；MULTINODE NOT_RUN |
| 独立审核结论 | [G0-02 ACCEPTED AS PARTIAL](https://github.com/Zwhao0/GREYHOUND_online/pull/5#issuecomment-6293707808)；仅 G0-03 Issue #6 范围获授权，须重新确认GPU资源许可；G1/G2/G3、双机和注入均未授权 |

## B. 已批准的方向（不得在交接中重新解释）

1. V1 目标：**不中断训练的 Fail-Slow 检测与分层 Rank 归因**。从固定密集 DDP 开始，再到 DP/TP/PP，普通 NCCL；MoE 后续可选。
2. 设计路线 B：GREYHOUND 的 ACF/BOCD 检测和可疑 Group 缩小范围 + 复用开源 NCCL/系统观测 + 新的离线先行 Rank 归因 + 最后在线化。
3. 双基线只做有数据前提的辅助校验；缺少真正可比的健康历史/Peer 就输出不可用，不得臆造。
4. 不修改生产训练脚本/模型/框架/NCCL 源码；不暂停、不在训练世界通信组插入验证 collective；重采样和热路径开销必须实测；组件 fail-open。
5. 不复制许可证尚未核实的 GREYHOUND detector 源码；外部项目须先记录来源和再利用许可。
6. ChatGPT 负责规划与独立审核；Codex 负责执行和整理证据；用户批准 Gate 的转换。

## C. 立即下一步（只做这一件）

**停止执行，等待ChatGPT独立审核G0-03 Draft；G0总Gate仍开放，G1 BLOCKED。**

- [G0-03证据](docs/evidence/g0-03-summary.json) / [记录](docs/G0-01-AUDIT.md) / [最小DDP脚本](tools/g0_03_ddp_poc.py)。本轮PASS：真实forward/backward/SGD，两rank实际Torch2.7/NCCL2.25.1、官方profiler v2加载，94对Collective可关联，已记录40步CUDA-event p50/p95。没有重跑nccl-tests。
- 接入基于用户后续补充的所有资源/权限授权：sudo仅访问已有Docker daemon，容器普通UID/GID；使用已缓存镜像，不拉取、不改Docker权限/系统包，不碰他人训练。单节点共享GPU0/1空闲5200/5202MiB，主测试前后已有占用未变。
- 只跑一次无插件、一次插件各5 warmup+40步，停用后2步烟测全部退出0，任务容器自动删除。无每步/Profiler热路径同步；只在计时窗口边界同步。DOC本地检查；CPU算法NOT_RUN；GPU/DDP PASS（候选）；MULTINODE NOT_RUN。
- v2不提供GPU channel timer，step GPU时钟由CUDA events独立采；step→Coll UNKNOWN，不按跨进程绝对时间匹配。精确drop、全历史、Proxy、通用多PG、长期fail-open和因果仍未知。本轮不是G0总PASS。
- 下一动作：ChatGPT按Draft HEAD/CI/真实证据审核，再另行确定最小任务。不得自行继续双机/注入/生产/G1、实现定位算法、merge或关闭Issue。

## D. 接班第一步：每个新 ChatGPT / Codex 窗口

1. 以 GitHub 仓库 **真实可访问的内容**为准读取 `HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`。仓库已创建；新窗口应从实际 main 和 Draft PR 的真实状态继续。
2. 检查当前 Issue、Draft PR、PR HEAD SHA、base、最新 CI 与真实实验报告；区分 `MAIN` 和 `DRAFT`。
3. 简要复述：当前 Gate、已有证据、尚未批准的事项、**下一项最小任务**。若状态冲突先指出，不盲目继续。
4. 每个执行窗口结束前更新本文（若未授权写入 GitHub，给出建议变更，不擅自将其标为已提交）。

## E. 当前需关注的风险

- 本次DDP实际NCCL2.25.1/v2与nccl-tests的2.28.3/v4不同；版本能力不可相互回填，v2没有GPU channel时间。
- 单次共享GPU的NCCL平均延迟变化约+0.87%/+0.96%，不能当真实DDP step性能证明；共享环境干扰未知。
- 宿主Torch环境入口失效；本轮用户补充权限后复用现有Docker缓存镜像取得DDP证据。此接入授权不代表允许修改Docker权限、系统升级或扩大后续Gate。
- 官方example仍有静默drop和尾窗限制，精确drop/完整性、长期非阻塞/fail-open与原发Rank证据尚缺；不得编造。
- GREYHOUND原profiler含强制CUDA同步及暂停/主动验证路径，detector许可证未明确；不可复制/沿用。
- Pubic仓库禁止主机、内网地址、凭证、公司日志、模型权重等敏感资料。

## F. 当前交接给 ChatGPT 新窗口的完整指令

> 继续Greenhound Online，唯一仓库Zwhao0/GREYHOUND_online。先读最新main、HANDOFF/STATUS/AGENTS/ROADMAP/docs/DECISIONS及Issue #6、当前Draft HEAD/CI。G0-01已PASS；G0-02已按PARTIAL合并；G0-03本轮候选PASS已交付但未合并：用户补充权限后复用已有NGC镜像，单机共享2×H800真实DDP，Torch2.7/NCCL2.25.1+官方profiler v2，两rank94对Collective可关联并有40步GPU p50/p95。当前只做ChatGPT独立审核，不重复实验；整个G0未过，G1、双机、注入未放行。

## G. 当前交接给 Codex 新窗口的完整指令

> 你是Greenhound Online主Codex。首先核对唯一仓库最新main、当前G0-03 Draft HEAD/CI、Issue #6与交接文件。G0-03执行已结束，等待ChatGPT独立审核；读取docs/evidence/g0-03-summary.json与docs/G0-01-AUDIT.md。不得沿用旧NOT_STARTED指令重复实验或把Draft当已合并。本轮DDP实际NCCL2.25.1/v2，不是上轮微基准2.28.3/v4；step→Collective、精确drop、长期fail-open仍未知。未经下一步授权，不继续GPU、双机、注入、生产或G1/Rank算法，不自行merge/关闭Issue。

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
