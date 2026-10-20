# Greenhound Online

**项目状态：Bootstrap / 尚未在真实训练环境中验证。** 这是一项独立的新工程：借鉴 GREYHOUND 的低开销异常检测与组级筛选，研究在**不中断训练**的条件下，将可疑通信组进一步归因到 Rank / GPU / 通信端点，并提供可核验的证据。

> **名称区别：** 本项目名为 **Greenhound Online**，原研究项目名为 **GREYHOUND**。名称相近不代表与原作者有隶属、授权或代码继承关系；导入 GREYHOUND 代码前必须核实许可证。

## V1 范围（2026-10-20 决策）

- 优先部署环境：两台各 8× H800（之后扩展 3 台）；**实际运行环境必须重新核实**。
- 通信后端：普通 NCCL 集合通信。先使用固定输入、密集模型的 DDP 验证，之后扩展 DP/TP/PP；V1 不要求 MoE/DeepEP。
- 首要场景：Fail-Slow 检测及原发 Rank 归因；Hang/Fail-Stop、网络物理根因和恢复动作列为后续增强。
- **无代码修改：** 不修改生产训练脚本/模型/框架/NCCL 源码。允许启动前配置、环境变量、标准 profiler 插件或受审查的 launcher；运行时侵入式注入不作为 V1 必需能力。
- **不暂停：** 任何常驻诊断不得暂停训练、插入需要所有训练 Rank 参与的测试 Collective、阻塞训练热路径或调用会等待 GPU 完成的热路径同步。
- **低开销、高可信：** 先取得可归因的真实证据，不能根据不充分数据强行输出坏 Rank。工具或观测链失败不得使训练失败（fail-open）。

## 候选路线（已批准，未实现）

保留或借鉴 GREYHOUND **ACF/BOCD 异常检测 + 组级可疑范围筛选**；评估 Probing 等开源组件的 NCCL 事件采集和等待分解，设计独立的 Rank 级离线归因算法；**离线真实证据验证成功后**再在线化。双基线是辅助校验，不是凭空制造定位信息。

## 项目控制台：从这里开始

1. **[HANDOFF.md](HANDOFF.md)**：唯一跨 ChatGPT/Codex 窗口的交接入口，包含当前工作授权和下一步。
2. **[STATUS.md](STATUS.md)**：事实状态、已验证证据、Gate 结果、未关闭风险。
3. **[AGENTS.md](AGENTS.md)**：Codex/子智能体工作约束与 PR 提交要求。
4. **[ROADMAP.md](ROADMAP.md)**：分阶段目标、验证准入与退出条件。
5. **[docs/DECISIONS.md](docs/DECISIONS.md)**：架构决策记录，避免交接中发生漂移。
6. **[tasks/G0-01.md](tasks/G0-01.md)**：已创建对应 Issue 的静态源码审计任务；H800 操作须另行授权。

## 当前事实

- 已在实际仓库 `Zwhao0/GREYHOUND_online` 的 main 分支初始化文档，首个任务见 [G0-01 Issue #1](https://github.com/Zwhao0/GREYHOUND_online/issues/1)。代码实现和 H800 实验均尚未开始。
- **代码和 GPU 测试：NOT_RUN**；不能把以前其他项目的 H800 测试当作本项目已通过的结果。
- 许可风险：原 GREYHOUND detector 的明确再利用授权尚未确认。许可确认前只可参考其论文和对公开源码的分析，不能直接复制进本项目。

## 实际仓库

- [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（main）。
- 仓库目前是 **Public**；禁止上传公司机密、训练日志或许可证不明的第三方源代码。
- 本项目展示名 Greenhound Online，并非上游 GREYHOUND 的官方实现。

## 开发原则

**有观测才有算法；真实证据优先于 mock；不确定则明确 UNKNOWN；每阶段独立审核，未经批准不得进入下一阶段。**
