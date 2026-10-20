# HANDOFF — Greenhound Online

> 跨 ChatGPT / Codex 窗口的**简短入口**，不是历史手册。以 [GitHub main](https://github.com/Zwhao0/GREYHOUND_online) 及当前 Issue/PR 为准；草稿 PR 不算已合并。仅按任务需要展开其他文档。

## 当前快照（2026-10-20，Asia/Shanghai）

- **项目**：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public）；main HEAD / 新 PR / CI 均应实时回读，不把本文 SHA 当实时事实。
- **Gate**：G0 **PASS（限定范围：单节点观测可行性）**；G1 **IN_PROGRESS、未通过**；G2/G3 未授权。
- **唯一任务**：[G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)（OPEN）：升级到两台 H800 **实际兼容的较新官方 PyTorch/CUDA/NCCL/Profiler 组合**，最小单机 smoke 后继续**两节点健康 dense DDP 的被动 NCCL 事件采集及跨 Rank 对齐**。不新增升级 Gate、不重验 G0。
- **执行状态**：本轮新软件栈升级和双节点 GPU 实测均 **NOT_RUN**；Codex 尚无 G1-01 执行 PR。以当前 GitHub 为准复核。

## 关键证据与边界

- G0-02：[PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)，NCCL 微基准 2.28.3 / Profiler v4、2 Rank 的 87 对 AllReduce（PARTIAL 已接收）。
- G0-03：[PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8)，真实单节点 2×H800 DDP，Torch 2.7 / NCCL 2.25.1 / Profiler v2、94 对 Collective、40 step 计时（PASS）。旧版本实验**不能证明新版/双机兼容**。
- **未证实**：双机跨 Rank 事件、跨节点时钟、Proxy、精确丢失、原发/等待因果归因、长期低开销/fail-open；不得写 PASS。
- **用户授权**：可在**本项目两台 H800 测试资源**的隔离容器/私有目录选择和升级 PyTorch、CUDA 用户态、NCCL、Profiler，必要时使用已许可的 Docker/sudo 客户端；先核实节点与共租安全。**不得**擅自改宿主驱动/全局依赖、重启、影响他人训练、注入故障、开发根因定位或进入 G2。Public 仓库不得提交私有主机/网络/日志/密钥；GREYHOUND detector 许可证不明，不复制源码。

## 下一步（只做这一件）

- **Codex 主窗口**：执行 [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 的版本预检→隔离升级→单机兼容 smoke→两节点健康 DDP+Profiler→事件对齐；提交**一个 Draft PR**，含脱敏 GPU/CI 证据，并在同一 PR 更新本文件与 STATUS；停止待 ChatGPT 审核。
- **子智能体**：简单重复任务用 GPT 6 luna max；难题或其不能完成者用 GPT 6.1 sol medium。主 Codex 负责权限、集成和 GPU 真实性（见 [AGENTS.md](AGENTS.md)）。
- **ChatGPT 新窗口**：读取**本文、[STATUS](STATUS.md)、[当前 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)及实际开放 PR/CI**；只在需要技术判断时打开其他文档，独立验收，不擅自跨 Gate。

## 按需查询（不全部预读）

- [STATUS.md](STATUS.md)：当前 Gate / 验证状态 / 证据导航；[AGENTS.md](AGENTS.md)：长期规则 / 子智能体。
- [ROADMAP.md](ROADMAP.md)：阶段入口与出口；[docs/DECISIONS.md](docs/DECISIONS.md)：长期决策；[docs/MEASUREMENT_CONTRACT.md](docs/MEASUREMENT_CONTRACT.md)：字段/时钟语义。
- [docs/G0-01-AUDIT.md](docs/G0-01-AUDIT.md)、[G0-02 证据](docs/evidence/g0-02-summary.json)、[G0-03 证据](docs/evidence/g0-03-summary.json)：详细历史和真实数据。**不要把其全文复制进交接文件**。
