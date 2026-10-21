# STATUS — Greenhound Online

更新：2026-10-21（Asia/Shanghai）。[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)，Public；实时状态以 GitHub main、Issue 和 PR 为准。

## 阶段状态

| 阶段 / 测试 | 状态 | 证据与边界 |
| --- | --- | --- |
| G0-01 静态审计 | PASS | [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) |
| G0-02 NCCL 微基准 | PARTIAL（已接收） | [PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5) |
| G0-03 单节点 DDP | PASS / MERGED | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) |
| **G0 Gate** | **限定范围 PASS** | 单节点观测可行性；不再重验 |
| **G1-01 双节点采集** | **限定范围 PASS / MERGED** | [Issue #9 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/9)；[PR #13 MERGED](https://github.com/Zwhao0/GREYHOUND_online/pull/13)；[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/13#issuecomment-6306390974) |
| **G1-02 时钟与采集质量** | **OPEN / NOT_RUN** | [下一唯一任务 Issue #14](https://github.com/Zwhao0/GREYHOUND_online/issues/14) |
| **G1 总 Gate** | **IN_PROGRESS / 未批准通过** | 事件完整性、时钟可比较性仍未充分建立 |
| G2 / G3 / G4 | BLOCKED | 不允许故障注入、原发 Rank 定位或在线化 |

## G1-01 已确认的事实

- 两台获授权 H800、私有 venv，Torch **2.14.1+cu130** / CUDA runtime **13.0.96** / NCCL **2.30.7** / 官方 example 实际协商 **Profiler v4**；宿主 Driver 580.178.04 未修改。对两个节点的包校验及目标训练进程实际 DSO/ABI 身份见[结果报告](docs/G1-01-RESULTS.md)。
- 新栈 **GPU smoke PASS**（单机2 Rank），健康 **DDP/MULTINODE 候选实验获限定验收**（两机4 Rank，baseline和plugin各5 warmup+30 steps）；观察到的 **70 个4 Rank Collective 实例匹配**，每 Rank 553 组GPU channel timer。该结论基于Codex实测归档与独立公开数据审查，**不是ChatGPT重新执行GPU实验**。
- DOC / CPU：最终 [HEAD CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39457361258)，9项 synthetic fixture PASS；公开 step 数组/匹配输出经独立复算。验收后 squash merge commit `1c2ef7f491d5979f1d7e3a55a54bd4d537e7b77c`。
- 一次共享资源对照GPU step p50 **+6.10%～7.53%**、p95 **+6.60%～7.82%**；**不是**长期低开销SLA。仅匹配观察窗口：共同遗漏、精确drop、Proxy、跨节点/GPU时钟校准、step→Coll与原发/受害因果 **UNKNOWN**。离线匹配脚本是PoC，不是生产检测/定位器。
- [脱敏统计及step数组](docs/evidence/g1-01-summary.json) · [70实例明细](docs/evidence/g1-01-matches.json)；历史G0源证据保留，不跨版本混用。

## 下一步与权限

**Codex 只执行 [G1-02 Issue #14](https://github.com/Zwhao0/GREYHOUND_online/issues/14)**：优先离线补证事件采集质量、序号间隙与时钟比较的可靠边界；仅在新采集路径需要时运行短窗口、健康、隔离的两节点验证。保留已授权两机共享环境的保护措施；不得修改驱动/全局依赖、影响其他任务、注入故障、研发原发Rank评分或擅自进入G2。提交一个 Draft PR，更新 STATUS/HANDOFF，停止待ChatGPT独立审核。
