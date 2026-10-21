# STATUS — Greenhound Online

更新：2026-10-21（Asia/Shanghai）。[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)；以 GitHub main / Issue / PR / CI 实时信息为准。

| 阶段 | 当前状态 | 证据 |
| --- | --- | --- |
| G0 单节点 | **限定范围 PASS**；不重验 | PR #2 / #5 (PARTIAL) / #8 |
| G1-01 真实双节点 Rank 对齐 | **限定范围 PASS / MERGED** | [PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13)；[Issue #9 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/9) |
| G1-02 CaptureQuality/时钟契约 | **CPU/DOC PARTIAL 已接收 / MERGED** | [PR #16](https://github.com/Zwhao0/GREYHOUND_online/pull/16)；[Issue #14 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/14) |
| G1-03 Host控制片段/插件计数 | **PARTIAL 已接收 / MERGED** | [PR #19](https://github.com/Zwhao0/GREYHOUND_online/pull/19)；[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/19#issuecomment-6308132405)；[Issue #17 CLOSED](https://github.com/Zwhao0/GREYHOUND_online/issues/17) |
| **G1-04 训练窗 Host 时间有界映射** | **OPEN / NOT_RUN** | [下一唯一任务 Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20) |
| **G1 总 Gate** | **IN_PROGRESS / 未批准通过** | 训练事件跨节点Host时间差尚无可用误差预算 |
| G2 / G3 / G4 | **BLOCKED** | 尚未授权故障注入、原发Rank定位或在线化 |

## 已确认与未确认的证据

- [G1-01实测](docs/G1-01-RESULTS.md)：两台H800、Torch **2.14.1+cu130** / CUDA runtime **13.0.96** / NCCL **2.30.7** / Profiler实际 **v4**。健康4Rank短窗70个观察Collective实例跨Rank匹配，G0不重做。
- [G1-02离线审计](docs/G1-02-RESULTS.md)：33项CPU测试，观察序列内部无gap，但共同遗漏、全生命周期drop、跨GPU时间、Producer完整导出仍UNKNOWN；CPU合成四时戳不冒充实测校准。
- [G1-03实测](docs/G1-03-RESULTS.md) / [脱敏数据](docs/evidence/g1-03-summary.json)：两机一次baseline+一次instrumented官方example健康4Rank DDP均exit0；逐Rank Group70/Coll70/KernelCh553已回调并导出，已计数own pool-drop/parent/guard reject为0；观察范围内70实例匹配。仅callback级审计，**不证明**所有NCCL操作都回调、GPU timer ring无覆盖、端到端零drop或生产fail-open。
- 同PID Host origin/time namespace绑定4/4；独立TCP pre/post **16个真实控制片段**误差半宽约 **0.378～0.682ms**（限片段），但训练窗口**33.279s**且无有据漂移界：**UNSAFE_TO_SUBTRACT**。Host片段不代表GPU globaltimer/step同步，不能形成Rank原发/受害归因。
- G1-03 final-head [CI DOC+58 CPU PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39544013660)；本轮审核独立重算了公开step p50/p95、计数与片段包络，非重新操作H800。G1-03 squash `57bb5fe68e4922b04762d51f6980242706e8c831`。共享环境一次性能对照混杂，净额外开销INCONCLUSIVE，保留旧G1-01 p50 **+6.1%～7.5%** 的风险；未验证≤2% SLA。

## 下一动作与权限

Codex **仅执行 [G1-04 Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)**：延续现有独立Host控制侧车，在健康DDP**训练期间**对事件建立可审计的短包络/时钟误差界，完成一次有界双节点真实验证；之后提交一个 Draft PR 及最终G1 Gate证据建议、更新简洁STATUS/HANDOFF，停等独立审核。无需重做已通过的G0/G1-01/逐类计数，不启动软件栈升级。

沿用两台已获授权**共享H800隔离健康试验**（先检查共租安全）。不得故障注入、故意减速、原发Rank评分、进入G2、插入world诊断collective、每step同步、修改生产脚本/框架/NCCL核心/宿主驱动/全局依赖、停止他人训练或上传敏感原始日志。
