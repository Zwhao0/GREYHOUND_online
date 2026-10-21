# STATUS — Greenhound Online

2026-10-21（Asia/Shanghai）。[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)，以main / PR / CI为事实源。

| 阶段 | 状态 | 证据 |
| --- | --- | --- |
| G0 / G1-01 | 限定PASS，不重验 | PR #8 / #13 |
| G1-02 / G1-03 | PARTIAL已接收并合并 | PR #16 / #19；G1-03最终CI 58项CPU PASS |
| **G1-04** | **候选PARTIAL，未合并** | [Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)、[报告](docs/G1-04-RESULTS.md)、[真实JSON](docs/evidence/g1-04-summary.json)；[Draft PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)；代码/证据提交 `bd6757c4bf3606e86eac1fa90496208f2ef74255`，最终HEAD/CI见PR |
| **G1 Gate** | **IN_PROGRESS，不建议放行** | 本次训练期间Host控制采样失败 |
| G2 / G3 / G4 | BLOCKED | 未获授权 |

G1-04：复用Torch2.14.1+cu130/NCCL2.30.7/Profiler v4旧DSO与原合成负载，**只运行一次**两台共享H800健康4Rank plugin（5warmup+30steps），两launcher exit0。4份trace/audit/Rank结果齐全，70实例匹配、280个实际Host begin事件；这些仅是映射输入，不重验既有采集功能。

主Codex私有launcher把client控制地址设为reference自身而非source，client连接拒绝、server接收超时，两侧车exit1，完整四时戳0。**280/280 UNSAFE_TO_SUBTRACT，1/5/10ms预算证据覆盖率0%，无法比较100%；误差p50/p95/max均UNKNOWN（null），连续合格实例0。** 不把启动失败解释为已测精度差；不追加GPU轮次。严格因果包络及异常处理仅有CPU验证。

GPU/MULTINODE：健康训练限定PASS，真实Host映射FAIL；DOC/CPU本地76项PASS，最终HEAD CI见PR。任务残留0、两节点各8个GPU应用、旧插件指纹未变。仅本次callback级已计数拒绝/drop为0；端到端loss/GPU ring/生产fail-open仍UNKNOWN。无baseline重跑，净增量开销INCONCLUSIVE，沿用历史p50 +6.1%～7.5%风险；GPU绝对跨卡时间/step→Coll UNKNOWN。

**唯一下一步：停止，等待ChatGPT独立审核Draft PR。** 建议PARTIAL接收、不放行G1 Gate，暂停现场时钟路线。是否重新授权修复配置后的单次补证或调整精度目标，由用户/独立审核决定。不得自行合并、关闭Issue、故障注入、原发Rank定位、进入G2或改动生产/宿主/全局依赖。
