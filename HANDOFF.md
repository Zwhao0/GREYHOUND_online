# HANDOFF — Greenhound Online（新窗口唯一入口）

> 最新项目事实以GitHub已合并 `main` 为准。任何ChatGPT/Codex新窗口先读取本文，再核对 `STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md`、当前Issue及PR。Draft候选不能当作main成果。**每个阶段结束须更新本文和STATUS。**

## A. 最新快照（2026-10-20）

| 字段 | 当前值 |
| --- | --- |
| 唯一仓库 | [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public） |
| 当前 Gate | **G0 限定范围PASS → G1 IN_PROGRESS，G1未通过** |
| 活跃任务 | [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)（OPEN，按用户最新授权已修订）：**先升级两机兼容的较新PyTorch/NCCL/Profiler，再继续原定双节点DDP跨Rank事件对齐**；尚未执行新环境实验 |
| 最近完成 | G0-03 [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) PASS/MERGED；squash SHA `08731fcbcfbf3e70d930ad888424dd061933f6bc`；Issue #6 CLOSED |
| 既有结果 | G0-02 `nccl-tests` NCCL2.28.3/v4、双rank87对AllReduce；G0-03真实DDP Torch2.7/NCCL2.25.1/v2、94对Collective |
| 既有CI | G0-03 [DOC PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39445987211)，CPU归因 NOT_RUN |
| GPU/DDP/双机 | GPU与DDP **PASS仅单节点PoC**；MULTINODE **NOT_RUN**；不允许声称有Rank根因定位 |
| 当前PR/分支 | G1-01还没有执行PR；main HEAD每次实时回读。维护本次状态所用的PR若存在，也须确认merge状态 |
| 审核结论 | [ChatGPT G0-03 PASS与 G0 限定范围 PASS](https://github.com/Zwhao0/GREYHOUND_online/pull/8#issuecomment-6294245015)；G1-01已发布，权限/资源现场重新确认 |
| 权限 | **用户本轮已明确批准G1-01使用两台H800测试资源及升级PyTorch/CUDA用户态/NCCL/Profiler**；可用受控容器/私有环境及必要的已有Docker/sudo客户端，无需每个常规动作重复申请。但必须核实节点属本项目/共享GPU资源安全；不擅自更改宿主驱动/系统依赖或停止现有训练 |

## B. 不变产品目标

- Greenhound Online是独立项目，借鉴GREYHOUND的ACF/变点与Group筛选，融合开源NCCL观测，再做**离线先行的Rank因果归因，最后在线化**。
- V1先普通NCCL、固定dense DDP；目标两台H800，后扩DP/TP/PP，MoE非V1条件。强调**无生产训练代码修改、不暂停训练、不插入诊断collective、低开销、fail-open**。
- **GREYHOUND detector许可证未明确，禁止复制源码**；只可引用机制设计。G0只证明单节点字段可观测；完整事件、根因、网络/时间、长期生产稳定性均未知。
- ChatGPT规划/独立审核/决定Gate；Codex执行与子智能体协作，通过一个Issue→一个Draft PR交付；Codex不可自行merge或跨Gate。

## C. 已获证据和关键限制

- **本轮最新授权（2026-10-20）**：G0单节点结果已PASS，不重做；新软件栈升级属于G1-01内部准备环节。允许在两台H800授权测试环境隔离升级PyTorch/CUDA用户态/NCCL/Profiler，升级后继续同一Issue #9的双节点采集验收，不新增升级Gate。旧的“不得升级/每次重复申请”文字由Issue #9新描述取代。

- [G0-01审计](docs/G0-01-AUDIT.md)；[G0-02真实字段](docs/evidence/g0-02-summary.json)；[G0-03 DDP真实摘要](docs/evidence/g0-03-summary.json)；[源字段与时间语义](docs/MEASUREMENT_CONTRACT.md)。
- G0-03两rank实际DDP均加载NCCL2.25.1/官方Profiler v2，94对Collective匹配；40步训练CUDA-event p50/p95已核实。**与G0-02 NCCL2.28.3/v4不同**；v2没有GPU channel clock，Host RDTSC不可未经校准跨节点比较。
- CUDA step计时不能当单个Collective GPU kernel起止；`step→Coll`、`root Rank vs victim`、`Proxy`、`clock calibration`、`accurate drop`、`fail-open`仍UNKNOWN。单次共享GPU样本不能证明稳定≤2% SLA。
- 本仓库Public，禁止上传主机名、内网IP、用户名/凭证、GPU UUID、公司私有日志/拓扑/权重。真实私有trace仅本地受限存放。

## D. 下一项唯一行动（Codex）

**继续 [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)；同一任务先升级再双节点验证，不返回G0或新开升级Gate。**

1. 用户已批准两台H800**项目测试资源**与隔离安装/升级PyTorch、CUDA用户态、NCCL、官方Profiler。主Codex核对本次实际节点、Driver、GPU可用容量，优先选择官方较新/最新稳定且实测兼容的组合。候选PyTorch2.14.1 + CUDA13.0；NCCL2.32.3是官方更高候选，**只有在实际Torch兼容/加载验证通过后才能选用**。不得为版本号盲改PyTorch绑定的NCCL ABI，也不在共享机器擅自改驱动、重启或覆盖全局包。
2. 在隔离环境中新版本单机只做**一次最小DDP+Profiler兼容smoke**，核对真实PID加载的libnccl、Profiler ABI和非空事件。**这不是G0重测，G0已PASS。**
3. 立即按原G1-01做两节点各最多2×H800的健康dense DDP无插件对照+官方Profiler采集。报告跨Rank成员、commHash、type、seq与元数据对齐、Host/GPU/Proxy时钟域、事件缺项和方向性step p50/p95；不计算未经证据支持的原发Rank。
4. 只交一个Draft PR，脱敏实测版本/DSO/插件/CPU/GPU/DDP/MULTINODE证据，**同PR更新 STATUS/HANDOFF**并停止等待ChatGPT审核。不做故障注入、生产任务改动、根因算法、G2或其他阶段。
5. 子智能体分工保留：GPT 6 luna max做简单/重复工作，确有复杂疑难再升级GPT 6.1 sol medium；主Codex负责真实机器、兼容性决策和集成。
## E. Codex子智能体新规则（用户 2026-10-20 明确指定）

- **GPT 6 luna max**：默认处理简单、重复、局部、可并行工作（文档、简单代码调整、fixture、静态/CI检查）。
- **GPT 6.1 sol medium**：仅针对 luna max 无法解决的任务或确有复杂难点（NCCL ABI、Communicator映射/时间语义）升级使用，不默认全部启用。
- 主Codex负责总体决策、真实GPU实验权限与安全、跨任务集成及最终提交。通常仅并行2–3个独立子任务；子智能体不直接越权访问H800或同时写STATUS/HANDOFF。
- 子智能体给主Codex**精简结论、变更、证据/失败**，不要灌入长日志/全文，减少主窗口上下文。详见AGENTS/DECISIONS。

## F. 新 ChatGPT 窗口可直接使用的交接指令

> 继续Greenhound Online，唯一仓库 https://github.com/Zwhao0/GREYHOUND_online。你是技术负责人，首先通过GitHub读取main上HANDOFF、STATUS、AGENTS、ROADMAP、docs/DECISIONS、当前Issue #9与Draft PR/CI。此前G0-01静态PASS、G0-02微基准PARTIAL已审核、G0-03真实单机PyTorch DDP PASS，故**G0已按限定范围PASS，不再重新做单节点Gate**；G1正在执行但尚未验收。**用户2026-10-20新决策：授权使用本项目两台H800测试资源、升级PyTorch/CUDA用户态/NCCL/官方Profiler，不必固定旧Torch2.7/NCCL2.25.1/v2；选择两机真正可兼容的最新或较新官方稳定组合，保留隔离回退，不干扰共享训练，勿无计划升级宿主GPU驱动。** 已原地更新G1-01 Issue #9：升级为当前任务的环境准备，升级后继续原定两节点健康DDP被动NCCL Rank事件采集和跨Rank对齐；新版单机只做简短兼容smoke，不新增升级Gate。官方候选PyTorch2.14.1/CUDA13.0与适配NCCL/Profiler，NCCL2.32.3仅实际兼容后采用，须看目标PID真实加载库而不能单看版本号。双机、跨节点时间、精确drop、原发因果、在线化均尚无新版本证据。Codex主窗口负责执行，可用GPT 6 luna max完成简单重复任务、GPT 6.1 sol medium处理疑难。后续审核一个Draft PR，严格不将未跑的升级/双机实验写PASS，最终更新STATUS/HANDOFF。
## G. 新 Codex 主窗口可直接使用的指令

> 继续Greenhound Online（Zwhao0/GREYHOUND_online），先核查GitHub最新main的HANDOFF/STATUS/AGENTS/ROADMAP/docs/DECISIONS和**已修订G1-01 Issue #9**。G0单节点Gate已PASS，旧Torch2.7/NCCL2.25.1/v2无须保留为新版本。用户明确授权本项目两台H800测试环境及隔离升级PyTorch、CUDA用户态、NCCL、Profiler；使用许可Docker/必要sudo客户端可按Issue执行，不必每项都请示，但不干扰其他运行任务、不替换宿主驱动或重启。先核对官方稳定组合和两机实际driver，用隔离镜像或任务目录装较新/最新可用版本，验证真实NCCL/Profiler ABI（优先PyTorch2.14.1+CUDA13.0适配版本；只有兼容才采用NCCL2.32.3）。新版单节点最小smoke之后**继续当前G1-01双节点4rank健康DDP+被动Collective采集与Rank关联**，不设升级Gate，不重复G0。优先把版本清单、脚本适配和普通fixture分派给GPT 6 luna max，疑难再用GPT 6.1 sol medium；主窗口集成、操作GPU、提交一个Draft PR并更新STATUS/HANDOFF。禁止故障注入、主动通信探测、根因Rank打分和提前进入G2。
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
