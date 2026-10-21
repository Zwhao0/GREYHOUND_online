# HANDOFF — Greenhound Online

2026-10-21（Asia/Shanghai）。以[main](https://github.com/Zwhao0/GREYHOUND_online)、Issue/PR/CI为事实源。

- G0限定范围PASS；G1-01 [PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) scoped PASS已合并；G1-02 [PR #16](https://github.com/Zwhao0/GREYHOUND_online/pull/16) CPU/DOC PARTIAL已接收。
- **G1-03候选PARTIAL，未合并、待独立审核**：[Issue #17](https://github.com/Zwhao0/GREYHOUND_online/issues/17)、[详细报告](docs/G1-03-RESULTS.md)、[脱敏实测](docs/evidence/g1-03-summary.json)。最终HEAD/CI见本轮Draft PR。
- 固定Torch2.14.1/NCCL2.30.7/v4；一次无插件baseline+一次仪表化example的两节点健康4Rank均exit0。callback逐类计数/导出自洽，70实例匹配；end-to-end loss/ring覆盖UNKNOWN。
- 真实Host控制片段16/16 BOUNDED（半宽0.378～0.682ms）；训练窗口半宽33.279s、无连续漂移界，**UNSAFE_TO_SUBTRACT**。Host不等于GPU同步。唯一阻断：训练窗可用精度的Host映射。
- 本地58项CPU/DOC PASS；本次真实GPU/MULTINODE健康测试限定PASS。净额外开销INCONCLUSIVE，保留历史6%～8%风险。原插件/venv不变，任务剩余进程0，原驻留GPU任务仍在。
- **G1 Gate IN_PROGRESS；G2/G3/G4 BLOCKED。**

**唯一下一动作：停止，等待ChatGPT独立审核G1-03 Draft PR。** 不自合并、不关闭Issue、不宣告Gate通过。后继最小方案在报告，未经审核不执行。

权限仍限两台共享H800隔离健康短测；禁止故障注入、原发/受害Rank评分、生产/模型/框架/NCCL核心改造、训练world诊断collective、每步GPU同步、宿主/全局包变更、抢占其他任务或公开敏感日志。

[STATUS](STATUS.md) · [采集/时间契约](docs/MEASUREMENT_CONTRACT.md) · [许可/patch依据](docs/SOURCES_AND_LICENSES.md) · [AGENTS](AGENTS.md)。私有raw按原留存规则保留至审核完成后7天内清理，不提交Public仓库。
