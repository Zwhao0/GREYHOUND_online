# HANDOFF — Greenhound Online

2026-10-21（Asia/Shanghai）。以[main](https://github.com/Zwhao0/GREYHOUND_online)及PR/CI为事实源。

- G0/G1-01限定PASS；G1-02/G1-03 PARTIAL已接收并合并（PR #16 / #19）。
- **G1-04候选PARTIAL，未合并**：[Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)、[报告](docs/G1-04-RESULTS.md)、[真实脱敏JSON](docs/evidence/g1-04-summary.json)。[Draft PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)；代码/证据提交 `bd6757c4bf3606e86eac1fa90496208f2ef74255`，最终HEAD/CI见PR；不是main已验收事实。
- 严格单调因果包络实现及CPU反例已完成，本地DOC/76项CPU PASS，无漂移假设。一次共享双节点健康4Rank plugin训练两launcher exit0，旧栈/DSO/负载不变；70匹配实例、280个实际Host begin事件。
- **主Codex控制启动地址配置错误**：client连到reference自身，连接拒绝；source server接收超时，侧车均exit1。训练期间完整四时戳0；280事件全部UNSAFE，1/5/10ms覆盖0%、无法比较100%，误差分布UNKNOWN。不重复GPU实验。
- 任务残留0，原插件指纹未变；真实Host映射FAIL，健康GPU/MULTINODE仅限定PASS，CPU通过不补足真实映射。净开销INCONCLUSIVE，历史6%～8%风险及全集drop/GPU ring/fail-open UNKNOWN保留。
- **G1 Gate IN_PROGRESS，不建议放行；G2/G3/G4 BLOCKED。**

**唯一下一步：停止，等待ChatGPT独立审核Draft PR。** 暂停现场时钟路线；本次失败不能推断因果包络精度极限。任何修复配置后补证或精度目标调整须由用户/审核重新决定。不得自合并、关闭Issue、放行Gate、注入故障、原发Rank评分、进入G2、改生产/框架/NCCL核心/宿主/全局依赖或公开私有数据。

[STATUS](STATUS.md) · [G1-04报告](docs/G1-04-RESULTS.md) · [测量契约](docs/MEASUREMENT_CONTRACT.md) · [AGENTS](AGENTS.md)。私有raw/失败日志/launcher保留至独立审核完成后7天内手动清理；旧G1-01/03证据不覆盖。
