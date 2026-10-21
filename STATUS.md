# STATUS — Greenhound Online

2026-10-21（Asia/Shanghai）。[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online)，以 main / Issue / PR / CI 为事实源。

| 阶段 | 当前事实 | 证据 |
| --- | --- | --- |
| G0 | 限定范围 PASS，不重验 | PR #2 / #5 / #8 |
| G1-01 | 限定范围 PASS / MERGED | [PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13)、Issue #9 CLOSED |
| G1-02 | CPU/DOC PARTIAL已接收 / MERGED | [PR #16](https://github.com/Zwhao0/GREYHOUND_online/pull/16)、Issue #14 CLOSED；33项CPU |
| **G1-03** | **候选 PARTIAL / 待独立审核** | [Issue #17](https://github.com/Zwhao0/GREYHOUND_online/issues/17)、[Draft PR #19](https://github.com/Zwhao0/GREYHOUND_online/pull/19)、[实验报告](docs/G1-03-RESULTS.md)、[真实摘要](docs/evidence/g1-03-summary.json) |
| **G1 Gate** | **IN_PROGRESS / 未通过** | 训练窗口Host对齐仍UNSAFE |
| G2/G3/G4 | BLOCKED | 未授权注入、原发Rank定位、在线化 |

G1-03：固定Torch2.14.1+cu130/NCCL2.30.7/Profiler v4，两台共享H800的一次baseline+一次新插件健康4Rank测试均退出0。每Rank Group/Coll70、KernelCh553 attempted/accepted/export一致，已计数pool-drop/parent/guard reject为0；70个四Rank实例匹配。仅callback窗口，非全量无损；GPU ring/覆盖/共同未回调仍UNKNOWN。

真实Host前后16个控制片段BOUNDED，半宽0.378～0.682ms；同PID origin/namespace/window绑定4/4通过。训练窗口保守半宽33.279s，缺连续漂移上界，**UNSAFE_TO_SUBTRACT**；GPU绝对跨卡及step→Coll保持UNKNOWN。仅控制片段有界，不能外推。

DOC/CPU：本地58项PASS（含既有33项），最终HEAD CI见[PR #19](https://github.com/Zwhao0/GREYHOUND_online/pull/19)；真实GPU/MULTINODE：本次健康测试限定PASS。顺序共享短窗plugin p50相对baseline为-49.19%～-56.72%，混杂明显，净增量开销INCONCLUSIVE；保留G1-01历史+6%～8%风险，无≤2% SLA声明。详细RSS/DSO/回退及未解决项见报告。

**唯一下一动作：停止，等待ChatGPT独立审核G1-03 Draft PR。** 不自合并、不关闭Issue #17、不放行Gate或进入G2。后继只考虑有来源的连续Host漂移界，需审核后授权。
