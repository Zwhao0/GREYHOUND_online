# HANDOFF — Greenhound Online（唯一交接入口）

**使用说明：** 任何新的 ChatGPT 或 Codex 窗口首先阅读此文件，按下方“接班第一步”执行。它指向事实状态、设计记录和当前任务，避免依赖聊天上下文。**每次经审核的阶段变化都必须更新本文。**

## A. 当前快照

| 字段 | 当前值 |
| --- | --- |
| 更新日期 | 2026-10-20 |
| 项目名称 | Greenhound Online（不同于上游 GREYHOUND） |
| GitHub 用户 | `Zwhao0` |
| 目标仓库 | `Zwhao0/Greenhound-Online` |
| 远端状态 | **NOT_CREATED — 当前仅有本地初始化项目包** |
| 默认分支 | 计划 `main`，尚未创建 |
| 当前 Gate | `BOOTSTRAP`：等待新仓库和初始推送 |
| 当前 Issue | 无（NOT_CREATED） |
| 当前 PR / HEAD | 无（NOT_CREATED） |
| CI | NOT_RUN |
| GPU / 双机真实实验 | NOT_RUN |
| 独立审核结论 | 尚无可审核代码；未授权进入 G1/G2/G3 |

## B. 已批准的方向（不得在交接中重新解释）

1. V1 目标：**不中断训练的 Fail-Slow 检测与分层 Rank 归因**。从固定密集 DDP 开始，再到 DP/TP/PP，普通 NCCL；MoE 后续可选。
2. 设计路线 B：GREYHOUND 的 ACF/BOCD 检测和可疑 Group 缩小范围 + 复用开源 NCCL/系统观测 + 新的离线先行 Rank 归因 + 最后在线化。
3. 双基线只做有数据前提的辅助校验；缺少真正可比的健康历史/Peer 就输出不可用，不得臆造。
4. 不修改生产训练脚本/模型/框架/NCCL 源码；不暂停、不在训练世界通信组插入验证 collective；重采样和热路径开销必须实测；组件 fail-open。
5. 不复制许可证尚未核实的 GREYHOUND detector 源码；外部项目须先记录来源和再利用许可。
6. ChatGPT 负责规划与独立审核；Codex 负责执行和整理证据；用户批准 Gate 的转换。

## C. 立即下一步（只做这一件）

**完成仓库 bootstrap：** 用户在 `Zwhao0` 下创建一个空的 **Private** 仓库，名为 `Greenhound-Online`，不勾选 GitHub 自动生成 README/.gitignore/LICENSE。将本项目包内容推送到 `main`，并给 GitHub 连接应用授权此仓库。

完成后需：
- 回读实际仓库 URL、默认分支和提交 SHA，填入本文件和 `STATUS.md`，将远端状态改为 `READY`。
- 创建首个 `G0-01` Issue，链接 `tasks/G0-01.md`，但**只读审计 / 实验方案阶段**，未经用户授权不得自动跑 GPU 实验。
- 开启首个 Codex 主窗口：先阅读 `AGENTS.md`、`STATUS.md`、`ROADMAP.md`、`docs/DECISIONS.md`、`docs/MEASUREMENT_CONTRACT.md` 和 G0-01 Issue。只做 G0-01，不推进 G1。

## D. 接班第一步：每个新 ChatGPT / Codex 窗口

1. 以 GitHub 仓库 **真实可访问的内容**为准读取 `HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`。如尚未建库，则用初始化项目包；不可虚构远端状态。
2. 检查当前 Issue、Draft PR、PR HEAD SHA、base、最新 CI 与真实实验报告；区分 `MAIN` 和 `DRAFT`。
3. 简要复述：当前 Gate、已有证据、尚未批准的事项、**下一项最小任务**。若状态冲突先指出，不盲目继续。
4. 每个执行窗口结束前更新本文（若未授权写入 GitHub，给出建议变更，不擅自将其标为已提交）。

## E. 当前需关注的风险

- GREYHOUND 原 profiler 路径调用 `cudaEventSynchronize()`；直接继承可能破坏低开销/非阻塞目标。
- 原组定位对“仅一个可比组”会转入主动验证。两台 H800 下要允许定位到可疑组但暂不精确归因。
- 原始 NCCL Host enqueue 时间不等于 GPU 实际执行时间，跨节点 monotonic 时间未经校准不能直接相减。
- 不知道现有训练实际动态链接 NCCL 版本；NCCL profiler 插件 ABI 兼容性待验。
- 没有足够真实证据之前，不能要求 Codex 制造健康双基线或高精度 Top-1 结果。

## F. 当前交接给 ChatGPT 新窗口的完整指令

> 我们继续全新项目 **Greenhound Online**，GitHub 目标仓库 `Zwhao0/Greenhound-Online`。请首先读取仓库根目录 `HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md` 和当前 G0-01 任务/Issue，并回读 GitHub 真实状态。若新仓库仍未创建，明确指出并从项目初始化包推进，不要假定已有 PR。用户已批准：GREYHOUND 的异常检测与 Group 筛选 + 开源 NCCL 证据 + 独立的离线先行 Rank 归因 + 最后在线化。第一版固定密集 DDP，普通 NCCL、两台 H800，之后扩展 DP/TP/PP，不强制 MoE；不暂停训练、不改训练代码。ChatGPT 规划与审核，Codex 执行。请从当前 Gate 的最小任务继续，不要跳过证据验证，不要擅自进入下一阶段。

## G. 当前交接给 Codex 新窗口的完整指令

> 你是 **Greenhound Online** 主 Codex 执行者。先从 `Zwhao0/Greenhound-Online` 读取 `HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`、`docs/MEASUREMENT_CONTRACT.md` 及已授权的当前 Issue。**以已合并 main 状态为准，Draft PR 必须另行标识。** 仅完成当前 Issue 明确授权范围，不启动未经批准的真实 GPU 操作、不复制许可不明的 GREYHOUND 代码、不自行 merge 或推进 Gate。遇到不能观测的字段请输出 `UNKNOWN`/证据缺口，不得模拟数据冒充 GPU 证据。提交 Draft PR 时提供 HEAD SHA、CI、运行证据、失败项、回退方案并更新 `STATUS.md`/`HANDOFF.md`，等待 ChatGPT 独立审核。

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
