# HANDOFF — Greenhound Online

2026-10-21（Asia/Shanghai）。以[main](https://github.com/Zwhao0/GREYHOUND_online)和PR/CI为事实源。

- G0/G1-01限定PASS；G1-02/G1-03 PARTIAL已接收并合并（PR #16 / #19）。
- **G1-04纠错后具备限定Host映射Gate审核证据，候选未合并**：[Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)、[同一Draft PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)、[纠错报告](docs/G1-04-CORRECTION.md)、[本次真实JSON](docs/evidence/g1-04-correction-summary.json)。纠错代码/证据提交 `4deec9662ad318174cc8e656aba72c6ae4da4c50`，最终HEAD/CI见PR。
- 首次GPU控制地址误配及第一次纠错TCP预检超时均保留。定位到模型/工具回合使client晚53秒启动、超过server30秒deadline；改成同一控制进程确认source监听后立即启动client，真实CPU/TCP预检2373对戳、双端exit0。冻结因果算法SHA不变。
- 预检PASS并等到共享GPU低负载后，只追加**一次**相同栈/旧DSO/原负载健康4Rank；两训练+两侧车均exit0，106637对四时戳夹住4/4审计活动窗。280事件全部BOUNDED，1/5/10ms预算覆盖100%，映射不可用0%。source140事件半宽p50/p95/max **0.511319 / 0.526649 / 0.583573ms**；连续合格4Rank AllReduce **69个**。
- 严格跨节点顺序仍有 **196/280=70%** 因区间重叠UNKNOWN；不按中点排序/做Rank归因。约20ms最大采样间隙不构成全时间轴1ms保证。Host不是GPU时间；净开销INCONCLUSIVE，历史6%～8%风险及全集drop/GPU ring/生产fail-open等UNKNOWN保留。
- 本地DOC/100项CPU PASS，最新HEAD CI见PR；任务残留0、旧插件未变、两节点各8个GPU应用保留。首次失败摘要与私有日志不覆盖。
- **G1 Gate IN_PROGRESS，等待ChatGPT裁决；G2/G3/G4 BLOCKED。**

**唯一下一步：停止实验，等待ChatGPT独立审核PR #22最终HEAD/CI与新证据，申请限定Host映射Gate审核。** 不自行合并/关闭Issue/判Gate PASS，不追加GPU实验，不故障注入、原发Rank评分、进入G2或改生产/框架/NCCL核心/宿主/全局依赖。私有raw、启动脚本、PID/boot/ns/IP/UUID只留隔离目录，审核完成后7天内手动清理。

[STATUS](STATUS.md) · [当前纠错报告](docs/G1-04-CORRECTION.md) · [首次历史失败](docs/G1-04-RESULTS.md) · [测量契约](docs/MEASUREMENT_CONTRACT.md) · [AGENTS](AGENTS.md)。
