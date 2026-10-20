# HANDOFF — Greenhound Online（唯一交接入口）

**使用说明：** 任何新的 ChatGPT 或 Codex 窗口首先阅读此文件，按下方“接班第一步”执行。它指向事实状态、设计记录和当前任务，避免依赖聊天上下文。**每次经审核的阶段变化都必须更新本文。**

## A. 当前快照

| 字段 | 当前值 |
| --- | --- |
| 更新日期 | 2026-10-20 |
| 项目名称 | Greenhound Online（不同于上游 GREYHOUND） |
| GitHub 用户 | `Zwhao0` |
| 实际仓库 | [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public） |
| 远端状态 | **CREATED / BOOTSTRAP PASS**（15 个文件已上传 GitHub main 并回读） |
| 默认分支 | `main`（每次交接需回读最新 HEAD） |
| 当前 Gate | **G0 IN_PROGRESS**；G0-01 静态审计 PASS/MERGED；G0-02 PARTIAL / DRAFT_REVIEW_PENDING（NCCL字段成功，DDP未运行）；G1 BLOCKED |
| 当前 Issue | [G0-02 Issue #3](https://github.com/Zwhao0/GREYHOUND_online/issues/3)（OPEN；隔离单节点 2×H800，无注入）；G0-01 #1 CLOSED |
| 当前 PR / HEAD | [G0-01 PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) 已合并；squash SHA `c73d552eb14695fa9e02247193fd8e6465b863d5`；最新 main HEAD 请 GitHub 实时回读；G0-02 [Draft PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)，分支 `g0-02-profiler-poc`，本分支HEAD实时读取；base `4d8a49c71f1dc24d7252f7ce21b56d06c9a9b225` |
| CI | G0-01 [DOC PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39438158278)；CPU/GPU/MULTINODE NOT_RUN；G0-02本地DOC静态检查，最新HEAD CI见[PR checks](https://github.com/Zwhao0/GREYHOUND_online/pull/5/checks)；GPU仅NCCL微基准PASS，DDP未运行 |
| GPU / 双机真实实验 | GPU=PASS（共享单节点NCCL微基准）；DDP=NOT_RUN；MULTINODE=NOT_RUN |
| 独立审核结论 | [G0-01 STATIC PASS](https://github.com/Zwhao0/GREYHOUND_online/pull/2#issuecomment-6293155716)；仅 G0-02 单节点隔离测试按 Issue #3 条件授权；双机、注入、G1/G2/G3 均未授权 |

## B. 已批准的方向（不得在交接中重新解释）

1. V1 目标：**不中断训练的 Fail-Slow 检测与分层 Rank 归因**。从固定密集 DDP 开始，再到 DP/TP/PP，普通 NCCL；MoE 后续可选。
2. 设计路线 B：GREYHOUND 的 ACF/BOCD 检测和可疑 Group 缩小范围 + 复用开源 NCCL/系统观测 + 新的离线先行 Rank 归因 + 最后在线化。
3. 双基线只做有数据前提的辅助校验；缺少真正可比的健康历史/Peer 就输出不可用，不得臆造。
4. 不修改生产训练脚本/模型/框架/NCCL 源码；不暂停、不在训练世界通信组插入验证 collective；重采样和热路径开销必须实测；组件 fail-open。
5. 不复制许可证尚未核实的 GREYHOUND detector 源码；外部项目须先记录来源和再利用许可。
6. ChatGPT 负责规划与独立审核；Codex 负责执行和整理证据；用户批准 Gate 的转换。

## C. 立即下一步（只做这一件）

**G0-02候选已交付，停止执行，等待ChatGPT独立审核；G0仍开放，G1未授权。**

- [执行记录](docs/G0-01-AUDIT.md) / [脱敏事实与原始字段样例](docs/evidence/g0-02-summary.json)。用户发现设备占用后明确允许共享GPU；仅第二候选节点GPU0/1运行，未停止现存进程，非独占隔离性能基准。
- 一次无插件+一次官方v4 example采集+2次迭代停用烟测全部退出0；两实际目标PID加载NCCL2.28.3与v4插件，87对Collective跨rank对齐，GPU原始channel timer可见。无生产脚本/框架/运行库修改，无root。
- 本轮结果PARTIAL：宿主无Torch、普通用户Docker不可访问，复用现有官方NCCL测试。dense DDP及step p50/p95未验证；Proxy、精确drop、完整历史、因果、长期fail-open未知。平均延迟仅方向性样本。
- DOC本地检查；CPU NOT_RUN；GPU PASS仅限上述微基准；DDP/MULTINODE NOT_RUN。PR未合并，整个G0未通过。
- 下一动作由ChatGPT审核；若继续，先明确可用Torch入口及共享/独占资源条件，再单独授权dense DDP/step分位数。不得擅自重跑、合并、关闭Issue、双机、注入、升级或进入G1/算法。

## D. 接班第一步：每个新 ChatGPT / Codex 窗口

1. 以 GitHub 仓库 **真实可访问的内容**为准读取 `HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`。仓库已创建；新窗口应从实际 main 和 Draft PR 的真实状态继续。
2. 检查当前 Issue、Draft PR、PR HEAD SHA、base、最新 CI 与真实实验报告；区分 `MAIN` 和 `DRAFT`。
3. 简要复述：当前 Gate、已有证据、尚未批准的事项、**下一项最小任务**。若状态冲突先指出，不盲目继续。
4. 每个执行窗口结束前更新本文（若未授权写入 GitHub，给出建议变更，不擅自将其标为已提交）。

## E. 当前需关注的风险

- GREYHOUND 原 profiler 路径调用 `cudaEventSynchronize()`；直接继承可能破坏低开销/非阻塞目标。
- 原组定位对“仅一个可比组”会转入主动验证。两台 H800 下要允许定位到可疑组但暂不精确归因。
- 原始 NCCL Host enqueue 时间不等于 GPU 实际执行时间，跨节点 monotonic 时间未经校准不能直接相减。
- 本次NCCL微基准实际NCCL2.28.3 + v4插件已核对，不能推广为Torch训练兼容性；精确drop与长期开销仍未知。
- 没有足够真实证据之前，不能要求 Codex 制造健康双基线或高精度 Top-1 结果。

## F. 当前交接给 ChatGPT 新窗口的完整指令

> 继续 Greenhound Online 项目：唯一仓库 Zwhao0/GREYHOUND_online。先通过 GitHub 阅读 HANDOFF、STATUS、AGENTS、ROADMAP、docs/DECISIONS 和当前 Issue/PR，回读最新 main HEAD/CI。G0-01 静态审计已经 PASS，PR #2 MERGED，Issue #1 CLOSED；G0-02 Issue #3 OPEN，本次共享单节点NCCL字段采集成功但整体PARTIAL，dense DDP和step分位数未运行；先审核当前Draft，不继续实验。不要把该 PoC 当成全部 G0 Gate 通过。ChatGPT 负责审核，Codex 执行。严格禁止未经许可的服务器访问、生产注入、改训练/框架/NCCL及跳到 G1。

## G. 当前交接给 Codex 新窗口的完整指令

> 你是 Greenhound Online 主 Codex，唯一仓库 Zwhao0/GREYHOUND_online。先核对最新 main、HANDOFF、STATUS、AGENTS、ROADMAP、docs/DECISIONS、docs/MEASUREMENT_CONTRACT 与 G0-02 Issue #3。G0-01 PR #2 已通过并合并。仅执行 Issue #3 授权范围：已获用户许可的隔离节点最多 2×H800、无注入短时间 DDP + NCCL 原生 Profiler 的加载/字段 PoC；若资源许可无法确认，只做准备并报告 BLOCKED。首轮勿增加无意义的多轮测试或平台化工作，不升级环境、不改生产训练、绝不执行双机/故障注入/Rank 因果归因。本轮已完成共享GPU上NCCL微基准、两rank字段与回退，整体PARTIAL；先读取当前Draft HEAD/CI/脱敏实测证据，停止并等待独立审核，不因本段旧范围重复执行。

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
