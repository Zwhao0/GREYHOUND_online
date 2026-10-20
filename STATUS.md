# STATUS — Greenhound Online

- **更新日期**：2026-10-20（Asia/Shanghai）；唯一仓库：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public），默认 `main`
- **当前 Gate：G0 PASS（范围限定：候选审计、单节点NCCL/DDP字段可行性与初步开销）→ G1 IN_PROGRESS（尚未验收）**
- **当前执行任务**：[G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)（OPEN，用户已更新授权）：**先在已授权两台H800测试环境隔离升级至兼容的较新PyTorch/CUDA/NCCL/Profiler，再在同一个G1-01继续双节点dense DDP被动采集和跨Rank匹配**。不设额外升级Gate；升级和MULTINODE仍NOT_RUN。
- **已完成**：G0-01 [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) PASS；G0-02 [PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5) **PARTIAL已接收**（单机NCCL测试87对事件，DDP没跑）；G0-03 [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) **PASS/MERGED**（`08731fcbcfbf3e70d930ad888424dd061933f6bc`），[Issue #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6) CLOSED，[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/8#issuecomment-6294245015)，[PR HEAD DOC CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39445987211)
- **程序状态**：只有最小PoC/采集字段验证及测试脚本；本项目没有生产级采集器、在线Detector或Rank因果归因器；G1的跨节点关联脚本尚未交付。
- **分类**：DOC=PASS（已完成PR）；CPU归因算法测试=NOT_RUN；GPU=PASS（G0-02、G0-03各自受限单机实验）；DDP=PASS（仅G0-03单机）；**MULTINODE=NOT_RUN**；故障注入/在线化=NOT_RUN。

## G0 三个任务的真实结论

1. **G0-01 静态审计**：借鉴GREYHOUND ACF/变点/Group设计；原profiler主动同步/暂停路径不适用；detector许可证仍未明，**禁止复制源码**。选NCCL官方原生Profiler作为首测。
2. **G0-02 GPU微基准（PARTIAL）**：单机2×H800的`nccl-tests`真正加载NCCL2.28.3和官方Profiler **v4**；两rank各87条AllReduce，87对可匹配；单次共享环境聚合平均延迟增幅+0.866%/+0.963%；该实验没有跑DDP。
3. **G0-03 真实 DDP（PASS）**：单机共享2×H800、NGC缓存PyTorch25.03镜像，真实forward/backward/SGD，两个DDP PID分别加载**Torch2.7.0a0 + NCCL2.25.1 / 官方Profiler v2**；两rank各94条Collective，94对按commHash/type/seq匹配，单侧缺项0（不等于全历史零drop）。40个测量step CUDA event p50/p95已按原始数据独立复算一致。

| Rank | 无插件 GPU step p50 / p95 | 开插件 GPU step p50 / p95 |
| --- | --- | --- |
| 0 | 1.144320 / 1.183483 ms | 1.153632 / 1.190360 ms |
| 1 | 1.151296 / 1.248669 ms | 1.154144 / 1.193533 ms |

**限制**：只有一次共享GPU短窗对照，不能宣称稳定 ≤2% 训练开销、完全非阻塞或长期fail-open。NCCL v2没有GPU channel timer，CUDA事件只是本地step区间；跨进程时钟不可直接相减，step→Collective、Proxy、精确drop、全历史完整性、跨节点匹配及原发/受害因果均 **UNKNOWN/NOT_RUN**。不能把v4的能力回填给v2。

## Gate 记录

| 阶段 | 状态 | 通过的范围 / 待解决事项 |
| --- | --- | --- |
| Bootstrap | PASS | GitHub基线 |
| G0 可观测性候选 | **PASS（范围限定）** | 单机实际字段+兼容性+初步开销已核实；生产能力未证实 |
| G1 Rank级证据采集 | **IN_PROGRESS；G1-01 OPEN/NOT_STARTED** | [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 已授权软件栈隔离升级及双机DDP/Rank-comm-op-seq匹配；真实结果未运行 |
| G2 离线因果归因 | BLOCKED_BY_G1 | 不能将最长等待判原发Rank |
| G3 在线非暂停 | BLOCKED_BY_G2 | 需真实负载、fail-open、丢失/低开销证据 |
| G4 扩展 | BLOCKED_BY_G3 | 后续DP/TP/PP，MoE可选 |

## 新增执行规则及下一步

- 用户指定Codex子智能体两级分工：**GPT 6 luna max**处理简单/重复任务；其无法处理或复杂难点再升级 **GPT 6.1 sol medium**；主Codex集成/负责关键授权与实测。详见 [AGENTS.md](AGENTS.md)、[DECISIONS.md](docs/DECISIONS.md)。
- **Codex下一唯一动作**：执行**已修订的 [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)**。用户已授权在两台H800项目测试服务器上隔离升级PyTorch、CUDA用户态、NCCL、Profiler并使用受控容器/必要的Docker客户端；无需每项常规测试反复征询。先核对两机GPU/driver并选择实际兼容的较新稳定组合，候选PyTorch2.14.1/CUDA13.0及可用NCCL，NCCL2.32.3需额外检验与Torch兼容；**新栈单机仅做最小兼容smoke，不重新验收G0**，随后完成原定双节点DDP+Profiler事件关联。
- **权限与禁止**：可在获准测试节点的**受控容器/私有目录**安装和升级用户态软件并开展G1-01双机GPU测试；必须核实机器归属与其他运行中训练的资源安全。**不批准无维护安排直接修改宿主GPU驱动、内核、系统NCCL、重启或停止他人训练**。仍禁止生产改造、故障注入/主动减速、诊断collective、GREYHOUND许可不明源码、Rank因果算法、擅自进入G2或自行合并PR；Public不得提交公司秘密。

## 2026-10-20 用户最新决定：允许升级，原G1-01继续

- **G0单节点已按先前验收PASS，不回滚/不重新验收。** G0-02/03记录仍是原版本的真实历史证据，不当成新版兼容性结论。
- **新授权**：允许本项目在两台H800测试服务器进行PyTorch/CUDA用户态/NCCL/Profiler的版本选择、隔离安装和双节点实验，并使用有权限的受控Docker/sudo客户端。优先实际可运行的**较新或最新官方稳定组合**，不是永久固定老版NCCL2.25.1/Profiler v2。使用容器/独立环境，不覆盖全局安装。
- **官方候选**：PyTorch 2.14.1、NCCL 2.32.3（截至2026-10-20）；可先测试PyTorch2.14.1+CUDA13.0及其真实打包NCCL/对应官方Profiler，若2.32.3适配且收益明确再采用；不直接硬替换PyTorch自带NCCL而不查ABI。此前Driver580.178.04只代表上一次现场测值，CUDA13.2高版本需核对驱动完整功能要求。真正选中版本、插件ABI和多机兼容性都**尚未实测**。
- **同一G1-01顺序**：两机版本/资源核对→隔离安装→仅一次新版单机DDP/Profiler兼容smoke（**不是新Gate**）→两节点各最多2GPU健康DDP无插件对照和被动Profiler采集→跨Rank事件关联→Draft PR。原定G1-01两机Collective关联是最终验收点。
- [更新后的Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 为最新授权细则；[PyTorch 2.14.1公告](https://dev-discuss.pytorch.org/t/pytorch-2-14-1-general-availability/3455)、[NCCL 2.32.3说明](https://docs.nvidia.com/deeplearning/nccl/release-notes/rel_2-32-3.html)、[PyTorch版本矩阵](https://github.com/pytorch/pytorch/blob/main/RELEASE.md)、[CUDA驱动要求](https://docs.nvidia.com/cuda/archive/13.2.2/cuda-toolkit-release-notes/index.html)。
