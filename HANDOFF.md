# HANDOFF — Greenhound Online

> 跨 ChatGPT/Codex 的简短入口（2026-10-21，Asia/Shanghai）。GitHub main 和 Issue/PR/CI 为事实源；详细科学证据只在实验文档。

## 当前快照

- G0 单节点限定 PASS，不重验。G1-01 [PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) 真实健康双节点4Rank采集 **scoped PASS**；G1-02 [PR #16](https://github.com/Zwhao0/GREYHOUND_online/pull/16) 离线质量/时钟契约 **CPU PARTIAL接收**。
- G1-03 [PR #19](https://github.com/Zwhao0/GREYHOUND_online/pull/19) 已独立审核 **PARTIAL接收并合并**；[Issue #17 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/17)，[审核结论](https://github.com/Zwhao0/GREYHOUND_online/pull/19#issuecomment-6308132405)，[最终CI 58项CPU PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39544013660)。本轮两台H800健康4Rank baseline+新插件测试均exit0；受控插件逐类 callback/导出 Group70/Coll70/KernelCh553，自有池drop计数0，观察70实例对齐。
- 实测独立Host控制**16片段**各有界（误差半宽0.378～0.682ms），但全训练窗未获得漂移误差界：**33.279s，UNSAFE_TO_SUBTRACT**。仅控制片段可比较，Host不等于GPU同步。全集drop/共同遗漏/GPU ring/生产fail-open保持UNKNOWN。
- 共享短窗口性能对照混杂，净开销INCONCLUSIVE；保留G1-01历史 +6%～8% p50风险。G1总Gate **IN_PROGRESS**，G2/G3/G4 **BLOCKED**。

## 唯一下一步

**Codex执行 [Issue #20：G1-04 健康训练期间跨Rank Host有界时间映射与最终Gate证据](https://github.com/Zwhao0/GREYHOUND_online/issues/20)**。复用已实测Torch2.14.1+cu130/NCCL2.30.7/v4、G1-03局部仪表化官方example、同PID origin与独立TCP侧车；通过训练期间相邻四时戳构造可验证的事件时间因果包络，不凭空假定连续漂移率、不把GPU globaltimer跨卡相减。仅一次有界健康双节点实验，必要的CPU反例与质量/精度覆盖统计；提交一个 Draft PR，同步简洁STATUS/HANDOFF，等待ChatGPT审核 **G1 Gate 是否具备限定范围放行条件**。不自动通过、**不进入G2或故障注入**。

**权限**：用户已批准的两台共享H800隔离健康测试，主Codex先核实共租状态；无宿主/全局依赖升级、无生产训练或NCCL核心改造、无额外训练world collective/热路径同步、无根因打分、不泄露主机/PID/内网/UUID/私有日志。子智能体优先 GPT 6 luna max 做fixture/证据，GPT 6.1 sol medium处理时钟数学/ABI，主Codex负责现场测试与集成；不要重复加载全部文档。

## 按需阅读

[STATUS](STATUS.md) · [G1-04 Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20) · [G1-03实验报告](docs/G1-03-RESULTS.md) · [G1-03脱敏实测](docs/evidence/g1-03-summary.json) · [测量契约](docs/MEASUREMENT_CONTRACT.md) · [AGENTS](AGENTS.md)。
