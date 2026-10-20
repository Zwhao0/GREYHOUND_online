# HANDOFF — Greenhound Online（新窗口唯一入口）

> 最新项目事实以GitHub已合并 `main` 为准。任何ChatGPT/Codex新窗口先读取本文，再核对 `STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`、当前Issue及PR。Draft候选不能当作main成果。**每个阶段结束须更新本文和STATUS。**

## A. 最新快照（2026-10-20）

| 字段 | 当前值 |
| --- | --- |
| 唯一仓库 | [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public） |
| 当前 Gate | **G0 限定范围PASS → G1 IN_PROGRESS，G1未通过** |
| 活跃任务 | [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)（OPEN），目标双节点dense DDP被动NCCL事件采集与跨Rank对齐 |
| 最近完成 | G0-03 [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) PASS/MERGED；squash SHA `08731fcbcfbf3e70d930ad888424dd061933f6bc`；Issue #6 CLOSED |
| 既有结果 | G0-02 `nccl-tests` NCCL2.28.3/v4、双rank87对AllReduce；G0-03真实DDP Torch2.7/NCCL2.25.1/v2、94对Collective |
| 既有CI | G0-03 [DOC PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39445987211)，CPU归因 NOT_RUN |
| GPU/DDP/双机 | GPU与DDP **PASS仅单节点PoC**；MULTINODE **NOT_RUN**；不允许声称有Rank根因定位 |
| 当前PR/分支 | G1-01还没有执行PR；main HEAD每次实时回读。维护本次状态所用的PR若存在，也须确认merge状态 |
| 审核结论 | [ChatGPT G0-03 PASS与 G0 限定范围 PASS](https://github.com/Zwhao0/GREYHOUND_online/pull/8#issuecomment-6294245015)；G1-01已发布，权限/资源现场重新确认 |
| 权限 | 上一次Codex窗口称用户额外批准Docker/sudo+共享GPU；**不可视为后续节点或任务永久授权**。每次先确认可用测试节点和许可 |

## B. 不变产品目标

- Greenhound Online是独立项目，借鉴GREYHOUND的ACF/变点与Group筛选，融合开源NCCL观测，再做**离线先行的Rank因果归因，最后在线化**。
- V1先普通NCCL、固定dense DDP；目标两台H800，后扩DP/TP/PP，MoE非V1条件。强调**无生产训练代码修改、不暂停训练、不插入诊断collective、低开销、fail-open**。
- **GREYHOUND detector许可证未明确，禁止复制源码**；只可引用机制设计。G0只证明单节点字段可观测；完整事件、根因、网络/时间、长期生产稳定性均未知。
- ChatGPT规划/独立审核/决定Gate；Codex执行与子智能体协作，通过一个Issue→一个Draft PR交付；Codex不可自行merge或跨Gate。

## C. 已获证据和关键限制

- [G0-01审计](docs/G0-01-AUDIT.md)；[G0-02真实字段](docs/evidence/g0-02-summary.json)；[G0-03 DDP真实摘要](docs/evidence/g0-03-summary.json)；[源字段与时间语义](docs/MEASUREMENT_CONTRACT.md)。
- G0-03两rank实际DDP均加载NCCL2.25.1/官方Profiler v2，94对Collective匹配；40步训练CUDA-event p50/p95已核实。**与G0-02 NCCL2.28.3/v4不同**；v2没有GPU channel clock，Host RDTSC不可未经校准跨节点比较。
- CUDA step计时不能当单个Collective GPU kernel起止；`step→Coll`、`root Rank vs victim`、`Proxy`、`clock calibration`、`accurate drop`、`fail-open`仍UNKNOWN。单次共享GPU样本不能证明稳定≤2% SLA。
- 本仓库Public，禁止上传主机名、内网IP、用户名/凭证、GPU UUID、公司私有日志/拓扑/权重。真实私有trace仅本地受限存放。

## D. 下一项唯一行动（Codex）

**执行 [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)，不跳过该任务审核，不启动G2。**

1. Codex先核对main和Issue #9、真实双节点及Docker/GPU权限；权限不明可先完成离线小归并器/fixture准备，**不能操作GPU**，缺权限则最终BLOCKED。
2. 仅在批准的两台H800测试节点（各最多两卡），复用现有最小dense DDP+当前版本可用官方Profiler，做一次健康对照及短时被动采集，确认每Rank真实加载版本、`run/rank/comm/type/seq`及跨机Collective关联。
3. 使用最小离线归并脚本生成可审核的匹配、缺rank、重复及时间域信息；未观察到的准确性/丢失/Proxy须标UNKNOWN。**无故障注入、主动探测、Root Rank算法、训练暂停、系统升级/框架修改。**
4. 一个Draft PR + 脱敏证据 + DOC/CPU/GPU/DDP/MULTINODE真实分类，并在同一PR更新 STATUS/HANDOFF；停止等待ChatGPT审核。

## E. Codex子智能体新规则（用户 2026-10-20 明确指定）

- **GPT 6 luna max**：默认处理简单、重复、局部、可并行工作（文档、简单代码调整、fixture、静态/CI检查）。
- **GPT 6.1 sol medium**：仅针对 luna max 无法解决的任务或确有复杂难点（NCCL ABI、Communicator映射/时间语义）升级使用，不默认全部启用。
- 主Codex负责总体决策、真实GPU实验权限与安全、跨任务集成及最终提交。通常仅并行2–3个独立子任务；子智能体不直接越权访问H800或同时写STATUS/HANDOFF。
- 子智能体给主Codex**精简结论、变更、证据/失败**，不要灌入长日志/全文，减少主窗口上下文。详见AGENTS/DECISIONS。

## F. 新 ChatGPT 窗口可直接使用的交接指令

> 我们继续 Greenhound Online（唯一仓库 https://github.com/Zwhao0/GREYHOUND_online）。你担任技术负责人，规划、派发任务、技术决策和独立PR/Gate审核。先用GitHub实际读取最新main上的 HANDOFF.md、STATUS.md、AGENTS.md、ROADMAP.md、docs/DECISIONS.md，及当前Issue/PR、CI，不能从历史聊天臆测。G0-01审计PASS；G0-02 PARTIAL已审核合并；G0-03真实2GPU DDP PASS、PR #8已合并、Issue #6关闭；G0限定范围正式PASS，当前进入G1，活跃任务为Issue #9（两节点dense DDP的被动NCCL事件采集/跨Rank对齐）。已有真实DDP使用Torch2.7/NCCL2.25.1官方Profiler v2，94对Collective可关联；但双机、Proxy/GPU时钟、精确drop、原发因果、在线fail-open仍UNKNOWN，不允许宣称系统已能定位。Codex负责实现，最多合理并行2–3个子智能体，简单/重复默认GPT 6 luna max，只有其无法处理的问题升级GPT 6.1 sol medium。不得为形式化过度验证阻塞开发；先获得真实可复现证据。任何GPU/Docker/sudo/跨节点操作须核实本次权限；上轮权限不自动延续。请等待/审核G1-01的Draft，之后按Gate推进，每阶段更新STATUS和HANDOFF。

## G. 新 Codex 主窗口可直接使用的指令

> 继续 Greenhound Online，唯一仓库 Zwhao0/GREYHOUND_online。先读取最新main的 HANDOFF、STATUS、AGENTS、ROADMAP、DECISIONS和G1-01 Issue #9。G0已按限定范围PASS，PR #8已合并，G1-01已正式发布；不要重复G0-02/03。当前只执行Issue #9最小双机DDP Rank事件采集和对齐；使用前重新确认两节点GPU/Docker/sudo资源许可，没有许可就离线准备并BLOCKED。主窗口自主拆分互不冲突的工作：简单/重复交GPT 6 luna max，失败或复杂再交GPT 6.1 sol medium，子智能体仅回报精简结果；主窗口负责整合、权限、安全、GPU与Draft PR。不得故障注入、主动验证、升级NCCL、开发Root Rank定位或进入G2。交付一个Draft PR（HEAD/CI/证据/缺口）并更新STATUS/HANDOFF，停止等待ChatGPT独立审核。

## H. 每次交接必须更新的字段

```text
Updated (Asia/Shanghai):
main HEAD / current Gate / approved scope:
current Issue and intended next action:
Draft PR URL / branch / head SHA / base / merge:
DOC / CPU / GPU / DDP / MULTINODE results and evidence:
Runtime versions / profiler ABI / clock/data gaps:
Resource permission, confidentiality and license blockers:
Next single task and acceptance/abort condition:
Forbidden actions without approval:
```
