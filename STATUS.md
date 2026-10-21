# STATUS — Greenhound Online

更新：2026-10-21（Asia/Shanghai）；[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)，Public。以实时 main / Issue / PR / CI 为准。

| 阶段 | 经过审核的状态 | 证据 |
| --- | --- | --- |
| G0 | **限定范围 PASS**：单节点可行性，不重验 | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8)，历史PR #2/#5 |
| G1-01 | **PASS / MERGED**：新栈两机健康4Rank的Collective匹配 | [PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13)，Issue #9 CLOSED |
| G1-02 | **PARTIAL已接收 / MERGED**：CPU采集质量/时间语义 | [PR #16](https://github.com/Zwhao0/GREYHOUND_online/pull/16)，Issue #14 CLOSED |
| G1-03 | **PARTIAL已接收 / MERGED**：逐类callback审计、真实Host片段 | [PR #19](https://github.com/Zwhao0/GREYHOUND_online/pull/19)，Issue #17 CLOSED |
| G1-04 | **限定范围 PASS / MERGED**：训练期间Host因果区间 | [PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)，[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/22#issuecomment-6310090904)，Issue #20 CLOSED |
| **G1 总 Gate** | **PASS_SCOPED_OBSERVABILITY** | 已证实**固定两机健康 dense DDP** 的Rank/Collective实例对齐、可追溯的被动Host事件采集和事件级有界时间区间；**不是故障定位或生产级验收** |
| **G2/G3/G4** | **BLOCKED_PENDING_EXPLICIT_USER_APPROVAL / NOT_STARTED** | 不允许自动故障注入、Rank原发归因或在线化 |

## G1 最终客观证据和边界

- 两台共享 H800，Torch **2.14.1+cu130** / NCCL **2.30.7** / 官方example实际 **Profiler v4**；真实4Rank健康DDP；固定单WORLD，观察到的 **70个4侧匹配Collective**。G1-03逐Rank已回调的Group70/Coll70/KernelCh553计数自洽，仅callback内部已计数drop/reject=0，**不等于上游全集零丢失**。
- G1-04第一次启动控制地址错误、第一次CPU纠错预检启动竞态，均留[失败报告](docs/G1-04-RESULTS.md)与[纠错报告](docs/G1-04-CORRECTION.md)。随后已授权的一次纠错GPU实验，侧车与DDP退出0；106637组真实双端四时间戳，观察的280个Host begin事件全部具有 **≤1ms区间半宽** 的可追溯时间包络，source半宽p50/p95/max **0.511319/0.526649/0.583573ms**；69个连续4Rank AllReduce满足预算。[公开逐事件证据](docs/evidence/g1-04-correction-summary.json)。
- 独立审核重算了140个source事件所引用的four-stamp因果上下界、各Rank半宽统计与280次跨节点区间排序：**16 BEFORE / 68 AFTER / 196 OVERLAP_OR_UNKNOWN**（70%先后不确定）。**1ms是包络半宽上界，不是独立真值残差；仅覆盖实际观察事件，不保证整个时间轴。** Host callback不是GPU kernel执行/完成。
- G1-04最终 [DOC/100项CPU CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39557871658)；本阶段真实GPU结果基于Codex可追溯归档而非ChatGPT在H800上独立重跑。
- **尚未解决**：原发Rank/受害Rank可区分性、真实注入定位精度、step→Coll、跨GPU绝对时钟、共同漏采/上游事件缺失、GPU timer ring、长期生产fail-open及真正的低开销SLA。G1-01单次共享窗口p50曾额外+6.1%～7.5%；后续实验混杂，当前开销 INCONCLUSIVE，不能宣称≤2%。

## 下一动作

**不再追加G1/G0验证。** 建议转为G2独立真值的少量盲测先导实验，以快速证伪“原发Rank可由已有观测信号区分”的假设；但用户此前明确要求 **未批准不得进入 G2、故障注入或原发Rank定位**。因此**当前没有获授权可运行的G2任务**，需用户明确批准且隔离独占测试安全条件满足后才能创建并执行G2 Issue。Codex仅保持仓库与私有证据安全，不得自行开始实验。
