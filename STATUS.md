# STATUS — Greenhound Online

更新：2026-10-20（Asia/Shanghai） · 唯一仓库：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public）。当前状态以 GitHub main / Issue / PR 实时信息为准。

**当前行动**：[G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) — 用户已授权在两台 H800 测试环境中**隔离升级** PyTorch、CUDA 用户态、NCCL、Profiler；新版单机只做兼容 smoke，然后继续原定两节点 DDP NCCL Rank 事件采集/对齐。**不是新 Gate，不重新验收 G0。**

| 阶段 / 验证 | 当前状态 | 证据 |
| --- | --- | --- |
| G0-01 静态方案 | PASS | [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) |
| G0-02 NCCL 微基准 | PARTIAL / 已接收 | [PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)：单机2Rank、87对 AllReduce |
| G0-03 真实 dense DDP | PASS / 已合并 | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8)：单机2×H800、94对Collective、40 step |
| **G0 总 Gate** | **PASS（仅单节点可行性）** | G0-01/02/03；不证明生产级能力 |
| **G1-01 新栈+两节点** | **OPEN / NOT_RUN** | [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)；尚无对应升级/双机实测 |
| **G1 总 Gate** | **IN_PROGRESS / 未通过** | 双机 Rank 证据、完整性/时间来源待验证 |
| G2 离线归因 / G3 在线化 | BLOCKED | 尚无因果定位或在线运行证据 |

## 已核实、未证实

- G0-02 微基准：目标 NCCL **2.28.3 / Profiler v4**，87 对事件；[脱敏证据](docs/evidence/g0-02-summary.json)。
- G0-03 DDP：目标 Torch **2.7.0a0 / NCCL 2.25.1 / Profiler v2**，94 对事件、真实 step p50/p95；[脱敏证据](docs/evidence/g0-03-summary.json)。**版本不同，不能混用其能力或推断新版兼容性。**
- GPU/DDP：**PASS 仅指上述单节点 PoC**；新版本 GPU/双机 MULTINODE：**NOT_RUN**；精确 drop、跨节点时钟、Proxy、Rank 原发/等待归因、严格开销 SLA、长期 fail-open：**UNKNOWN**。
- 系统仍只有 PoC/脚本，没有在线检测器或 Rank 根因定位器；本项目 Public，原 GREYHOUND detector 许可未确认，禁止复制。

## 当前权限与收尾

用户批准 G1-01 使用**本项目两台 H800 测试资源**及受控容器/私有目录内升级 PyTorch/CUDA 用户态/NCCL/Profiler（必要时已许可 Docker/sudo）。不得改变宿主驱动/全局依赖或影响他人训练；禁止故障注入、训练暂停、主动诊断 collective、生产代码修改或提前进入 G2。选用版本与实际 ABI **只能在新实验完成后记录**。

下一动作与验收以 [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 为准；Codex 提交**一个 Draft PR**、真实测试分类与脱敏证据，并同步更新 [HANDOFF.md](HANDOFF.md) 和本文件；ChatGPT 独立审核后才推进。
