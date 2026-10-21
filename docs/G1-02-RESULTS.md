# G1-02 时间与采集质量边界（候选 PARTIAL）

2026-10-21（Asia/Shanghai），对应 [Issue #14](https://github.com/Zwhao0/GREYHOUND_online/issues/14)。本轮只做 **CPU 离线复核 / DOC**，输入为 G1-01 已归档的四 Rank 健康双节点真实 trace；合成 fixture 单列。本轮 **GPU / MULTINODE NOT_RUN**，没有修改采集器、包装器或运行时采样路径，没有访问远端机器，不重验 G0/G1-01，不升级软件、不注入、不做 Rank 归因、不进入 G2。

## 结论与证据能力

**G1-02 候选 PARTIAL，G1 总 Gate 继续 IN_PROGRESS，不能提交为 Gate PASS。** [机器可读质量报告](evidence/g1-02-quality.json)复核已有 70 个实例的数据边界；输入哈希对应[原实测摘要](evidence/g1-01-summary.json)，不把离线处理标成新 GPU PASS。

每 Rank 的导出数据为 AllGather seq 0（1 个）、AllReduce seq 0–68（69 个），Coll 70 对、Group 70 对、KernelCh 553 对。观察范围内没有内部 seq gap、重复 seq 或局部 b/e 配对异常。缺失槽计数为零只适用于**已导出首尾序号之间**；不证明 attempted=emitted，更不能推断 dropped=0。Group 和 KernelCh 没有独立全局 collective 序号，不能用 Coll 的连续性替它们证明无损。

| 质量层级 | 本次结论 | 不能推出的结论 |
| --- | --- | --- |
| OBSERVED | 文件可读、观察到的 b/e 和 per-op seq；原匹配报告 70 个四侧实例 | 整个训练生命周期无损 |
| MISSING | 合成反例可证明导出内部序号槽/局部一侧记录缺失；真实本窗口未发现 | 缺失原因一定是 collector drop；未采到一定未执行 |
| UNKNOWN（可能共同遗漏） | 全 Rank 一起遗漏、导出尾窗覆盖、未启用/接口未暴露事件 | 四侧匹配意味着没有共同遗漏 |
| UNKNOWN（根本未观测） | attempted、精确 dropped/overwritten、active window、flush、Proxy、未出现的 operation | 未报告计数等于0；文件 parse 成功等于 producer flush 完整 |

原采集 mask=66，仅启用 Coll/KernelCh，Group 为父链。Proxy NOT_COLLECTED；未观察的 Broadcast 不宣称零次或丢失。collector active window 没有可靠起止标记；init/finalize 与成功退出不补足逐事件采集窗口。导出的 first/last ts 只是本进程导出观察范围，不是 active window，也不是30个测量 step 的精确边界。窗口头尾的实际覆盖均 UNKNOWN。

## 时间来源与校准尝试

本轮先检查已有包装器、manifest、rank 记录及 trace：没有保留 example 的 `startTime` 与包装器时钟的同进程成对映射，没有独立控制路径四时间戳，也没有有界主机同步误差/漂移证据。因此无法离线补算跨节点 Host reference；相同 seq、日志墙钟或相近运行时间均不能替代校准。

| 输入 | 域 / 单位 | 本轮允许用途 |
| --- | --- | --- |
| Chrome `ts`，包括 cat=GPU | 每进程 CLOCK_MONOTONIC 减 example startTime，微秒 | 只描述本进程 callback 观察范围；Coll end 可能等待子事件引用归零，非独立 enqueue end |
| StartGpuClk / StopGpuClk | 每 GPU globaltimer 原始纳秒 | 同 GPU channel 原始区间；不是完整 kernel launch，不能跨卡直接相减 |
| step CUDA events | 本 GPU elapsed duration，毫秒 | 既有 step 分位数；无绝对时刻映射，step→Coll UNKNOWN |
| Host dispatch perf_counter | 本进程耗时 | 不作为 GPU 执行起止或跨 Rank 参考 |

实测跨 Rank Host/GPU 校准 **UNKNOWN**，不确定度 **UNKNOWN**，结果 **UNSAFE / UNSAFE_TO_SUBTRACT**。不同进程即使共享主机单调时钟，example 各自减去不同 startTime，仍不能直接比较。GPU 与 Host 域也无双向映射，不能把 Host 校准转移到 GPU。

新增 CPU 四时间戳契约仅验证数学和拒绝逻辑，不实现网络采样：独立控制 A发送 a1、B接收 b2、B发送 b3、A接收 a4，在同单位、正向因果、双向延迟非负及区间内偏移近似固定的声明下，B−A offset 属于 [b3−a4, b2−a1]。该区间保留 RTT/非对称不确定度，不假定上下行相等；还必须给时间戳误差、有效窗口和相对漂移界。外推增加漂移误差，窗口外拒绝；两个区间合成的不确定度超过目标比较预算时输出 UNKNOWN。合成 BOUNDED 不是实测 CALIBRATED。本轮真实输入不能安全比较，未产生跨 Rank 时间差或慢 Rank 分数。

## 采集器取舍、风险与唯一最小后继

保留已实测官方 v4 example，不为补计数重写/更换 collector。固定[源码池与 finalize 路径](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/plugin.c)没有公开累计逐事件 drop 证据；文件成功导出不证明全量无损。[导出字段](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/ext-profiler/example/print_event.c)也不提供上述校准。只读取上游源码，没有复制第三方实现。沿用[许可/ABI记录](SOURCES_AND_LICENSES.md)。

风险继续保留：静默池满/尾窗覆盖、GPU timer 采样 ring 覆盖、未观测事件类、finalize 写失败与 callback mutex、生产 fail-open 未验证。G1-01 的共享短窗 GPU step p50 +6.10%～7.53%、p95 +6.60%～7.82%仍是风险，没有达到 G3 ≤2% SLA。

**唯一最小后继方案（待审核授权，不在本 PR 执行）**：在固定栈上增加一个隔离、独立控制侧车，保留同进程 Host origin 映射与前/后四时间戳、时间戳误差和漂移界；对同一现有 v4 example 的逐事件类 attempted/drop/overwrite/export 状态做最小隔离仪表化，然后一次有界健康4 Rank验证。每类/每阶段单列，GPU timer ring 若仍无覆盖证据保持 UNKNOWN；不能把 Coll 池计数当全事件无损。仍不提供跨 GPU 绝对时刻，除非另有 GPU↔Host 有界映射。此方案需下一任务审核后决定，不能据本 PR 跳入 G2。

## 重现、测试分类与回退

私有原始输入已在本机，路径、PID、commHash、GPU UUID/内网地址不公开；公开报告仅别名/聚合/原始 trace SHA256。不新增原始日志副本，继续原归档留存规则。

```sh
python3 tools/g1_02_capture_quality.py PRIVATE_MANIFEST.json --output QUALITY.json
python3 -m unittest discover -s tests -v
python3 tools/validate_docs.py
```

CPU fixture 覆盖错误PID/communicator隔离、缺失/反向本地配对时间、内部 gap、重复、共同遗漏不可判、池计数未知、导出失败、窗口配对问题及未观测类；时钟 fixture 覆盖偏移、非对称 RTT、缺证据/超窗/漂移/不确定度预算和不同域不可比。既有9项 CPU 测试保持。本地共33项 PASS（既有9项 + 新增采集质量9项 + 时钟15项）；DOC验证与脱敏扫描通过。最终 HEAD CI 见 PR。

回退：撤销本 PR 即删除离线工具/fixture/质量报告并恢复交接文档；运行栈、采集机制与 GPU 环境无变更。只提交 Draft PR，Issue #14 保持 OPEN，停止等待 ChatGPT 独立审核。

分工记录：GPT 6 luna max 完成采集分析初稿和基础 fixture；GPT 6.1 sol medium 完成时钟数学/ABI审查和15项时钟测试；主Codex修正身份隔离、补足反例、复核私有真实输入并集成。无新增真实GPU操作。
