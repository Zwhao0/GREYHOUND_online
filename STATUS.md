# STATUS — Greenhound Online

2026-10-21（Asia/Shanghai）。[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)，以main / PR / CI为事实源。

| 阶段 | 状态 | 证据 |
| --- | --- | --- |
| G0 / G1-01 | 限定PASS，不重验 | PR #8 / #13 |
| G1-02 / G1-03 | PARTIAL已接收并合并 | PR #16 / #19 |
| **G1-04** | **纠错补证完成，限定Host Gate审核候选，未合并** | [Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)、[Draft PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)、[报告](docs/G1-04-CORRECTION.md)、[真实JSON](docs/evidence/g1-04-correction-summary.json) |
| **G1 Gate** | **IN_PROGRESS，等待ChatGPT裁决** | 不能由Codex自行通过 |
| G2 / G3 / G4 | BLOCKED | 未获授权 |

G1-04首次控制地址错误、第一次纠错TCP预检的启动竞态均保留独立失败证据。用户要求继续定位后，确认client因模型/工具回合晚于source deadline；同一进程编排与监听屏障修复，真实两节点CPU/TCP预检2373对四时戳核验PASS，非训练校准。`g1_04_causal.py`冻结未改。

经[独立审核授权](https://github.com/Zwhao0/GREYHOUND_online/pull/22#issuecomment-6308753247)、预检PASS及共享资源低负载检查，**只追加一次**健康两节点4Rank plugin：原Torch2.14.1+cu130/NCCL2.30.7/Profiler v4 DSO与原合成5warmup+30steps负载不变。两训练launcher/两侧车均exit0；106637对四时戳覆盖4/4审计活动窗；70实例、280个真实Host begin事件。

**280/280 BOUNDED，1/5/10ms预算覆盖100%，映射不可用0%；source140事件因果半宽p50/p95/max 0.511319/0.526649/0.583573ms；69个连续4Rank AllReduce满足1ms。** 跨节点严格先后仍196/280=70%区间重叠UNKNOWN。区间半宽不是独立真值误差；全窗被夹住不等于全时间轴≤1ms（最大采样间隙约20ms）。

DOC/CPU本地100项PASS，最终HEAD CI见PR；CPU fixture及真实事件由指定luna/sol分工独立核对。GPU/MULTINODE：本次健康DDP及观察事件Host包络限定验证完成，不代表GPU同步。任务残留0、旧插件指纹未变、两节点各8个GPU应用保留。仅callback级已计数drop/reject为0；全集loss/GPU ring/生产fail-open等UNKNOWN。无baseline重跑，净增量开销INCONCLUSIVE，保留历史p50 +6.1%～7.5%风险。

**建议提交G1限定Host映射Gate审核；当前仍IN_PROGRESS。唯一下一步：停止实验，等待ChatGPT独立审核PR #22。** 不自行合并、关闭Issue、判G1 PASS、追加GPU轮次、故障注入、原发定位或进入G2。
