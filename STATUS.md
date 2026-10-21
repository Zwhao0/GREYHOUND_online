# STATUS — Greenhound Online

更新：2026-10-21（Asia/Shanghai）；唯一仓库 [Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)。以 GitHub main / 当前 Issue/PR/CI 为准。

| 阶段 | 审核状态 | 证据或下一步 |
| --- | --- | --- |
| G0 | **限定范围 PASS**，不重验 | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) |
| G1 | **PASS_SCOPED_OBSERVABILITY**，不重验 | [PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)、[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/22#issuecomment-6310090904)；固定两机健康dense DDP |
| **G2-01** | **AUTHORIZED / OPEN / NOT_RUN** | [Issue #24：单点Fail-Slow盲测先导](https://github.com/Zwhao0/GREYHOUND_online/issues/24)；用户明确批准受控合成测试注入 |
| G2 总 Gate | **IN_PROGRESS / NOT_PASSED** | 不以先导小样本冒充正式精度验收 |
| G3/G4 | **BLOCKED** | 未授权在线化或生产部署 |

## 当前事实与缺口

- G1：两台H800，Torch **2.14.1+cu130** / NCCL **2.30.7** / Profiler实际**v4**。单WORLD健康4Rank的70个匹配Collective，280/280个**已观察**Host begin事件有≤1ms半宽的可追溯因果时间界；但跨节点事件对**196/280=70%**先后仍UNKNOWN。详见 [G1-04纠错实测](docs/G1-04-CORRECTION.md)。
- 这不证明原发/等待Rank的因果区分、GPU时间同步、全集零漏采、长期fail-open或低开销SLA；G1-01一次共享短窗报告额外p50约+6%～8%，真实净开销仍INCONCLUSIVE。
- 本次用户明确授权**隔离测试任务**使用获准两机H800资源，执行有界、真实的Fail-Slow测试及离线盲评；以前“G2不允许进入”的阶段限制已被 [Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24) 取代。不得中断共租生产训练或变更驱动/系统全局依赖。

## 下一动作

Codex **仅执行 [G2-01 Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24)**：复用G1观测栈，在隔离合成4Rank DDP中最多一次健康baseline+一次有界8-episode单Rank 20ms pre-backward延迟注入；私有独立真值预提交并盲测，先冻结预测再评分。输出Top-1/UNKNOWN/健康误报及GO/NO_GO/INCONCLUSIVE，1个Draft PR更新STATUS/HANDOFF，停止待ChatGPT独立审核。不做G0/G1重复验收、完整定位平台、在线服务或G3。
