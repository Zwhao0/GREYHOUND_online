# G1-03 — 真实 Host 时间与逐类采集审计（候选 PARTIAL）

2026-10-21（Asia/Shanghai），[Issue #17](https://github.com/Zwhao0/GREYHOUND_online/issues/17)。**健康 GPU/MULTINODE 验证 PASS（限定本次）；G1-03 总体候选 PARTIAL，G1 Gate 保持 IN_PROGRESS，暂不足以申请 Gate PASS。** 唯一阻断项是：训练窗口缺少可用精度的连续 Host 映射；控制片段有真实有限边界，不能外推至训练事件。没有故障注入、Rank定位、G2、生产训练/框架/NCCL核心修改或软件升级。

[脱敏机器报告](evidence/g1-03-summary.json)包含四时间戳、逐类计数、源文件/输入哈希、每Rank step数组及进程内DSO。输入为本轮真实两节点数据；CPU模拟单列，绝不作为GPU真值。

## 实现与身份

沿用 Torch **2.14.1+cu130** / NCCL **2.30.7** / CUDA runtime **13.0.96** / Driver **580.178.04**。在两个新的私有测试目录复制已核对的官方 example，应用[局部patch](../tools/patches/g1-03-example.patch)与[原创audit header](../tools/g1_03_audit.h)，不修改旧目录/venv或上游核心。许可见[记录](SOURCES_AND_LICENSES.md)。

新增只有同PID origin、context内3×6个64位relaxed原子计数、finalize一次审计文件、trace open/flush/close检查和KernelCh channel上限保护；callback新增路径无I/O、分配或锁。原 example 的mutex、分配/生命周期风险仍存在，**不宣称生产fail-open或完全非阻塞**。

- `CLOCK_MONOTONIC` 的同一个timespec同时构造 `startTime` double微秒和整数ns origin；不是从Chrome ts估计。记录run/epoch、PID、comm rank/hash、node alias、time/pid namespace、boot ID、clock API/resolution和finalize结束时刻。
- origin数值转换误差保守取 **4000 ns**，仅在受检的monotonic范围 `<2^42 us` 内有效；仅包含double/文本表示，不是硬件绝对精度或跨节点误差。四Rank trace首尾重建到本地Host域后均在已记录窗口内。
- 完整init/finalize、manifest和同训练PID输出交叉核对：固定单WORLD `[0,1,2,3]`、两节点、4个不同GPU UUID（私有）。不是通用多communicator/重启映射。
- 两节点编译出的新插件 SHA256均为 `06740a4ea051720ca974a22a6f448bcacb5648e7a9c4a928e81e043ad88dcf54`。DSO仅导出 `ncclProfiler_v4`；目标PID有v6/v5查找失败后真实init/finalize与完整事件，结合nm/DSO身份确认实际v4。不是v6 collector。
- 八个baseline/plugin训练PID实际加载 `libnccl.so.2` SHA `618968ee277041751512e619190132a9bdf351c3ce7129c73484f6ef441ad692`、版本查询23007；`libcudart.so.13` SHA `96c42e418cec19054186b9429c321603cc190bf26a18104e19408117a2a817b0`、查询13000，状态均0。四个plugin PID加载上述新插件；baseline无插件映射。

## 真实 Host 校时：片段 BOUNDED，训练窗口 UNSAFE

[独立TCP工具](../tools/g1_03_host_clock.py)在训练world之外运行，node-a为reference/client、node-b为source/server。前后各8次四时间戳：a1发送前、b2完整接收后、b3回复前、a4完整接收后；所有序列化、解析与调度耗时都留在包络内。无对称路径假设、无训练world额外collective、无热路径GPU同步。单阶段8次/30秒deadline、包大小/样本数有界。两个节点原始文件交叉核对，4个训练PID的run/epoch/boot/time与pid namespace、origin及active-until均通过绑定。

**可证明的实测边界**：在每个source控制处理片段 `[b2,b3]` 内，非负路径延迟和同namespace单调性给出reference坐标包络 `[a1,a4]`；片段上offset属于 `[b2-a4,b3-a1]`。不假定漂移率或offset恒定。16/16片段在1ms比较预算内 **BOUNDED**：映射半宽 **0.378149～0.682328 ms**，只适用于这些控制片段；禁止外推。传统 `[b3-a4,b2-a1]` 也保留，但明确标为“交换期间offset恒定”的**条件式**结果，不能替代上述无漂移假设的可靠包络。

训练窗口通过pre最后一次接收与post第一次发送夹住，只有宽的单调因果包络；reference包络宽 **66.558802228 s**、半宽 **33.279401114 s**。实测连续漂移上界 UNKNOWN，不能用两组样本的差值或拟合线伪造上界；严格输出 **UNSAFE_TO_SUBTRACT / usable_for_cross_rank=false**。该有限数值界有来源，但远超1ms预算，未达到可用的训练事件Host对齐。没有实现按时间顺序定位或慢Rank评分。

GPU globaltimer保持独立ns域，CUDA event是本GPU elapsed毫秒，Chrome cat=GPU的ts仍为Host观察时刻。**Host控制片段BOUNDED不意味着GPU同步**；跨卡绝对时间、step→Coll仍UNKNOWN/UNSAFE。`resolution_ns=1`也不等于1ns准确度。

## 逐类质量与真实健康实验

现场检查两张目标卡：node-a各约2.46GiB、node-b各约5.20GiB可用，均有原有vLLM驻留。仅暴露每节点2张H800、OMP=1、Torch allocator上限1%（不含context/NCCL），5 warmup+30 measured steps；launcher180秒、process group60秒。只运行**一次无插件baseline + 一次新插件capture**；均4Rank健康dense DDP，使用未修改的G1-01独立合成负载脚本。正常DDP通信不含额外诊断collective；CUDA同步仅warmup/测量边界。

| 每Rank已订阅类别 | start callback attempted | accepted handle | own pool-drop / parent / guard reject | 成功exported header |
| --- | ---: | ---: | ---: | ---: |
| Group | 70 | 70 | 0 / 0 / 0 | 70 |
| Coll | 70 | 70 | 0 / 0 / 0 | 70 |
| KernelCh | 553 | 553 | 0 / 0 / 0 | 553 |

4Rank全部计数守恒，header计数与trace begin和配对数逐类一致。KernelCh accepted是嵌入式handle，**没有独立池**；其pool-drop=0仅表示该callback分支没有池拒绝，并非GPU ring无损。trace各文件open、fflush/ferror、fclose均成功；不含fsync，持久化状态UNKNOWN。audit文件可读且字段自洽，不声称audit自身写失败可在同文件中被完整报告；缺文件/截断由CPU读取器保守拒绝。

按run+epoch+已验证WORLD+op+seq匹配**70个4Rank实例**：AllGather seq0×1、AllReduce seq0–68×69；观察范围内缺侧、重复、metadata/配对/本地时间异常0。逐类计数只覆盖**此插件收到的start callbacks和finalize导出窗口**；NCCL是否为所有操作产生回调、共同未回调、全生命周期精确loss、尾窗/槽重用覆盖、GPU timer ring覆盖仍UNKNOWN。Proxy未启用。不能把一个类别的已知0 pool-drop泛化为全类型零丢失。

## 性能、RSS与回退

每Rank真实CUDA-event step，ms；相对变化来自同配置顺序短窗，**不是可识别的净插件开销**。

| Rank | baseline p50 / p95 | plugin p50 / p95 | p50相对变化 | baseline / plugin RSS KiB |
| --- | --- | --- | --- | --- |
| 0 | 1.782256 / 3.651424 | 0.905584 / 1.082298 | -49.19% | 1719112 / 1709556 |
| 1 | 2.095552 / 3.586480 | 0.906912 / 1.074893 | -56.72% | 1709480 / 1703736 |
| 2 | 2.070864 / 3.625362 | 0.906032 / 1.051766 | -56.25% | 1715116 / 1701032 |
| 3 | 1.782624 / 3.638381 | 0.905168 / 1.060011 | -49.22% | 1710380 / 1699712 |

共享资源/短窗/顺序运行存在明显混杂，不能把负变化称为性能改善、负开销或≤2% SLA。为遵守一轮限制，不追加调参或挑选数据。**历史G1-01 p50 +6.10%～7.53%、p95 +6.60%～7.82%风险继续保留**；本轮增量开销结论INCONCLUSIVE。

两mode两节点launcher均exit0，全部8个rank结果齐全，目标新任务/sidecar剩余进程0，两节点原有8个GPU应用仍在；未测共享服务延迟，不断言完全零影响。原目录plugin SHA仍为 `3982ac146d710cfd3eca59e0c36fd1502790840211eb8f41c2d35934b51c9571`；新venv仅symlink旧私有环境，无包/驱动变更。baseline真实验证 `NCCL_PROFILER_PLUGIN=none`，移除新目录或停止使用新wrapper即可回退；不为回退追加GPU轮次。

## CPU验证、重现与唯一后继

本地 **58项CPU PASS**：既有33项、新audit6项、真实时钟工具16项（含本机TCP loopback，非GPU证据）、公开实测数组/包络独立复算3项。CPU模拟溢出、缺计数、写失败不会在现场制造故障。DOC、shell语法、patch无fuzz应用、两节点编译与脱敏扫描通过；最终HEAD CI见PR。

固定source SHA及patch/header后，在**新的**隔离目录按原Makefile `make CUDA_VERSION=13.0`，复用既有venv和未修改DDP负载，运行 [wrapper](../tools/g1_03_run.sh) 的baseline/plugin各一次。先在source运行server、reference运行client取得pre，完成健康训练后再取post；run/epoch/node与插件环境必须一致。具体主机、路径、PID/namespace/boot/GPU标识只在私有归档。raw每节点不足64MiB，继续保留至独立审核完成，随后7天内手动清理。

```sh
python3 tools/g1_03_report.py PRIVATE_ROOT --private-manifest PRIVATE_MANIFEST.json \
  --executed-clock-source PRIVATE_EXECUTED_CLOCK.py --output PUBLIC_SUMMARY.json
python3 -m unittest discover -s tests -v
python3 tools/validate_docs.py
```

现场执行的控制文件完整SHA是 `017596c542e37b073928d844e10916b67dca3bffd16f7c381609567ec017a351`；取回后仅扩展离线verifier的因果片段逻辑，collector/serve/collect及依赖函数AST与已执行文件逐项一致。报告同时记录执行SHA与最终分析文件SHA，**不把离线新增逻辑说成现场重跑**。DDP原脚本SHA、patch/header/wrapper、输入trace/audit/control哈希可追溯。

**唯一最小后继**：待独立审核授权后，只在现有独立控制路径增加有证据支持的连续rate/漂移上界及更贴近训练窗的成对采样，使训练事件的Host映射达到预定误差预算；不扩大到GPU同步或归因。没有该界时继续UNSAFE。当前先停在Draft PR，ChatGPT裁决限定范围成果与G1 Gate，不自合并、不关闭Issue。
