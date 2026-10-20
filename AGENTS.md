# Codex / 智能体工作规则 — Greenhound Online

> 本文件对主 Codex 和子智能体均生效，除非用户在当前 GitHub Issue 中明确授权更改。

## 1. 身份和仓库边界

- 唯一新工程：`Zwhao0/GREYHOUND_online`。不得修改用户的其他项目（FLASH、myflash、20261015 等）；需要阅读外部公开资料时仅做只读研究，并引用来源。
- 项目核心职责：ChatGPT 负责规划、验证设计、审查 Gate；Codex 主窗口统筹实现和验收，子智能体可承担独立代码审查/测试。用户批准跨 Gate 任务。
- 每个任务开始前依次读取：`HANDOFF.md`、`STATUS.md`、`AGENTS.md`、`ROADMAP.md`、`docs/DECISIONS.md` 和当前 Issue/任务文件。若信息冲突，停止推进并明确指出冲突。
- 除非当前 Issue 明确授权，**不得**在真实 H800 上运行操作、访问生产数据、注入故障、修改安装包或升级驱动/NCCL。

## 2. 不可变的科学和工程原则

1. 不能修改生产训练脚本、模型、框架、NCCL 源码；可评估受审查的标准插件/启动包装。
2. 禁止生产诊断流程暂停或阻塞训练、在训练 world communicator 中插入基准测试 collective、训练热路径 `cudaEventSynchronize()`。如发现现有参考代码存在这些行为，标记不符合并隔离。
3. 任何组件失效不应导致训练失败；采取有界缓冲、可见的丢失计数、明确 UNKNOWN 状态。
4. 不得把调用 NCCL API 的 Host 时间当成 GPU kernel 起始时间；不同进程单调时钟不可未经校准直接做跨节点差。
5. 不得把“通信耗时最久”直接定义为“原发故障 Rank”；需要对齐通信实例、因果/等待证据与独立验证。
6. 基线必须定义比较对象和健康窗口；缺少历史或同类 Rank 时输出 BASELINE_UNAVAILABLE；不得编造基线或以合成数据冒充真实证据。
7. Mock/fixture 只能证明逻辑，不能证明 GPU、NCCL、真实训练、精度或低开销；所有测试记录标注 `DOC`/`CPU`/`GPU`/`MULTINODE`。
8. 最终诊断允许 `ROOT_CANDIDATE`、`SUSPECT_GROUP_OR_EDGE`、`UNKNOWN`，禁止不经校准的 99% 类可信度声明。
9. 许可不明的外部源码不得复制进项目；先完善 `docs/SOURCES_AND_LICENSES.md`。

## 3. GitHub 工作流

- 原则上一个有范围的 Issue 对应一个 Draft PR；不要直接推送到 `main`（仓库初始化的第一笔提交除外）。
- 每个 PR 关联 Issue、范围、不可做事项、证据清单、测试类别、失败与未运行项、回退说明、代码 HEAD SHA。
- CI 绿不等于 GPU 验证通过；不得自行合并 Draft PR 或擅自关闭 Gate。
- 完成一个可审核里程碑时，在**同一个 PR**更新 `STATUS.md` 和 `HANDOFF.md`。`HANDOFF.md` 只放当前状态与下一步；长期设计记录放 `docs/DECISIONS.md`。
- 不得在仓库提交令牌、内网 IP、含机密的生产日志、私有模型/权重；诊断数据应脱敏、有大小和留存限制。

## 4. 跨窗口交接协议

所有 ChatGPT/Codex 新窗口启动指令：**以 GitHub 已合并内容为准**，先读取 `HANDOFF.md`。如有未合并 Draft PR，还需读取其 HEAD、Issue、CI、验证证据并明确标记“候选未合并”。

Codex 每次结束时：
- 更新 HANDOFF 的 `更新日期/当前 Gate/工作授权/提交和 PR/测试/风险/下一条动作/禁止动作`。
- 给用户可复制的交接摘要，不得将未运行的实验写成 PASS。
- 下个 Codex 窗口先核对 GitHub 状态再继续；如果工作树与 HANDOFF 不一致，停止并报告。
