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
| **G1-02 时钟与采集质量** | **候选 PARTIAL / 待独立审核** | [Issue #14](https://github.com/Zwhao0/GREYHOUND_online/issues/14)；[本轮报告](docs/G1-02-RESULTS.md)；仅 CPU 离线复核 |
| **G1 总 Gate** | **IN_PROGRESS / 未批准通过** | 事件完整性、时钟可比较性仍未充分建立 |
| G2 / G3 / G4 | BLOCKED | 不允许故障注入、原发 Rank 定位或在线化 |

## G1-01 已确认的事实

- 两台获授权 H800、私有 venv，Torch **2.14.1+cu130** / CUDA runtime **13.0.96** / NCCL **2.30.7** / 官方 example 实际协商 **Profiler v4**；宿主 Driver 580.178.04 未修改。对两个节点的包校验及目标训练进程实际 DSO/ABI 身份见[结果报告](docs/G1-01-RESULTS.md)。
- 新栈 **GPU smoke PASS**（单机2 Rank），健康 **DDP/MULTINODE 候选实验获限定验收**（两机4 Rank，baseline和plugin各5 warmup+30 steps）；观察到的 **70 个4 Rank Collective 实例匹配**，每 Rank 553 组GPU channel timer。该结论基于Codex实测归档与独立公开数据审查，**不是ChatGPT重新执行GPU实验**。
- DOC / CPU：最终 [HEAD CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39457361258)，9项 synthetic fixture PASS；公开 step 数组/匹配输出经独立复算。验收后 squash merge commit `1c2ef7f491d5979f1d7e3a55a54bd4d537e7b77c`。
- 一次共享资源对照GPU step p50 **+6.10%～7.53%**、p95 **+6.60%～7.82%**；**不是**长期低开销SLA。仅匹配观察窗口：共同遗漏、精确drop、Proxy、跨节点/GPU时钟校准、step→Coll与原发/受害因果 **UNKNOWN**。离线匹配脚本是PoC，不是生产检测/定位器。
- [脱敏统计及step数组](docs/evidence/g1-01-summary.json) · [70实例明细](docs/evidence/g1-01-matches.json)；历史G0源证据保留，不跨版本混用。

## G1-02 候选事实（未合并）

- DOC / CPU：新增 CaptureQuality 离线工具、时钟质量契约与 synthetic 反例；本地33项 PASS（既有9项不回归）。真实输入来自 G1-01 私有归档，公开[质量报告](docs/evidence/g1-02-quality.json)记录源 trace 哈希及保守边界；不是新 GPU 实验。
- 每 Rank AllGather seq0、AllReduce seq0–68，Coll/Group 各70对、KernelCh553对；本导出窗口内部 gap/重复/配对异常0。attempted/drop/overwritten/flush、窗口头尾与共同遗漏仍 UNKNOWN；连续seq不证明全量无损。
- Host 相对时钟缺 origin 映射/独立校准，GPU globaltimer 与 step CUDA event 无跨域映射。实测跨Rank **UNSAFE_TO_SUBTRACT**，uncertainty UNKNOWN；合成四时间戳 BOUNDED 只证明 CPU 逻辑。
- 本轮 **GPU / MULTINODE NOT_RUN**：采集器/包装器/采样路径均未变，没有远端操作。G1-02 **PARTIAL**，不能提交 G1 Gate PASS；保留既有6%～8%开销风险。

## 唯一下一步与权限

**停止，等待 ChatGPT 对 G1-02 Draft PR 独立审核。** Issue #14 保持 OPEN，G1 Gate IN_PROGRESS。后继最小侧车/逐类计数补证方案仅记在[报告](docs/G1-02-RESULTS.md)，未经审核不执行。不合并 PR、不注入、不做原发 Rank 定位、不进入 G2/G3。
