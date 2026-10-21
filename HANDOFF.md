# HANDOFF — Greenhound Online

> 简短跨窗口入口。以[仓库 main](https://github.com/Zwhao0/GREYHOUND_online)、当前 Issue/PR/CI 为事实源，不在此复述完整实验或长任务。

## 当前状态（2026-10-21，Asia/Shanghai）

- **G0**：单节点观测限定范围 **PASS**，不重验。
- **G1-01**：真实两机H800健康DDP采集 **限定范围 PASS**；[PR #13已合并](https://github.com/Zwhao0/GREYHOUND_online/pull/13) / [Issue #9已关闭](https://github.com/Zwhao0/GREYHOUND_online/issues/9)。
- **G1-02**：离线CaptureQuality + 四时间戳保守数学契约 **PARTIAL已接收**；[PR #16已合并](https://github.com/Zwhao0/GREYHOUND_online/pull/16) / [Issue #14已关闭](https://github.com/Zwhao0/GREYHOUND_online/issues/14)，[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/16#issuecomment-6307501674)，[最终HEAD CI 33项CPU PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39539775945)。本轮 **GPU/MULTINODE NOT_RUN**。
- **G1 Gate**：**IN_PROGRESS / 未批准**；G2/G3/G4 **BLOCKED**。
- **事实与缺口**：G1-01两机Torch2.14.1+cu130/NCCL2.30.7/v4 Profiler，4Rank已观察70个匹配Collective。G1-02复核旧trace的SHA 4/4相符、内部seq无gap，但 attempted/drop/flush、共同遗漏、active-window、跨节点Host offset/误差均 UNKNOWN；原始GPU globaltimer不能直接跨卡相减。一次共享短窗p50额外开销约6%～8%，低开销SLA未证明。

## 唯一下一任务

**Codex执行 [G1-03 Issue #17](https://github.com/Zwhao0/GREYHOUND_online/issues/17)：两节点真实 Host 校时与 Profiler 逐类采集审计。** 保持已经实测的新稳定栈，通过独立控制通道+同PID相对时钟origin建立可信Host时间误差界，并对现有v4插件做最小逐类计数/导出状态补证，至多一次有界健康4RankDDP测试及必要的同配置baseline。按Issue验收；无法安全界定时输出UNKNOWN/PARTIAL，不能硬凑PASS。提交一个 Draft PR 并在同PR更新简洁STATUS/HANDOFF，停止等待ChatGPT独立审核。

**权限**：两台已授权共享H800、隔离目录/venv、有限健康测试；执行前检查共租安全。禁止故障注入、原发Rank定位/评分、G2/G3、修改生产训练脚本/框架/NCCL核心、额外训练world collective、每步同步、驱动/全局依赖/其他作业变更、发布敏感原始数据或许可不明的GREYHOUND代码。

**分工**：GPT 6 luna max负责常规统计/fixture/机械审查；GPT 6.1 sol medium处理时钟误差界与Profiler ABI/并发安全；主Codex负责集成、现场资源与真实性。子智能体短结论即可。

## 按需读取

[STATUS](STATUS.md) · [Issue #17](https://github.com/Zwhao0/GREYHOUND_online/issues/17) · [G1-02实验报告](docs/G1-02-RESULTS.md) · [G1-01实验报告](docs/G1-01-RESULTS.md) · [测量契约](docs/MEASUREMENT_CONTRACT.md) · [AGENTS](AGENTS.md) / [ROADMAP](ROADMAP.md)（仅需时）。
