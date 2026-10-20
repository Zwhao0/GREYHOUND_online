# 观测和验收数据契约 v0（待 G0/G1 验证）

这是**待验证的字段需求**，不是宣称真实系统已经能采到每一项。

## 1. 运行与拓扑标识（必须明确来源）

- `job_id`/`run_id`、节点标识、PID、GPU UUID、global/local rank、rank epoch（重启不可复用旧身份）。
- NCCL communicator 稳定身份、group membership、TP/PP/DP 角色（可 UNKNOWN）、建组/销毁时间。
- operation / algorithm（若支持）、message bytes、seq / local seq、peer、stream、source version 与 profiler ABI。

## 2. 时间来源必须分开

- `host_enqueue_ts` = Host 发起时间；**不等于 GPU 端执行时间**。
- `gpu_start_ts` / `gpu_end_ts` = 若确实采到的 GPU 端事件；说明采样、同步和开销。
- `proxy_send_wait` / `proxy_recv_wait` / `network_progress` = 仅插件确实支持时记录。
- 所有时间须声明时钟域、单位、偏移估计、误差界；跨节点未经校准的单调时钟不可直接相减。
- 原始证据需保留覆盖/丢弃/缓冲溢出/采集状态。每种缺项标注 `UNKNOWN`。

## 3. 定位和基线

- 对同一通信实例跨 Rank 匹配，证明哪一侧是晚到、等待、真正执行慢。
- 历史基线限于**同一个 Rank 的可比阶段、消息大小、拓扑和配置**下经健康验证的窗口；故障时冻结更新。
- Peer 基线限于**同角色、同工作量且非共同受影响**的 Rank，不存在则 BASELINE_UNAVAILABLE。
- 输出包括 rank/group、归因证据、反证、未观测字段、UNKNOWN 理由；禁止无验证的精确物理根因。

## 4. 测试类别和独立真值

- DOC：文字、模式、schema、静态规则。
- CPU：解析/匹配/模拟合成数据的单测；不能证明在线可用性。
- GPU：单节点真实训练观察和故障实验。
- MULTINODE：真实 NCCL 跨节点及故障实验，含通信路径与时钟问题。
- 注入标识与参数存放在测试方私有证据中，**不能传给算法**；评估时统计 Top-1、Top-k、UNKNOWN、误报、召回、检测/定位延迟、正常迭代 p50/p95 开销。
- 所有数据收集必须在用户许可的隔离窗口，禁止在生产任务注入故障。

## 5. G0-01 最小事件契约（静态候选，2026-10-20）

`SUPPORTED` 仅表示固定上游接口/实现存在；`UNKNOWN` 表示未证实或未采集；`UNSUPPORTED` 表示该来源不提供。**所有本项目运行时字段、完整性和开销均 UNKNOWN，GPU/MULTINODE NOT_RUN。** 固定源码依据见 [来源矩阵](SOURCES_AND_LICENSES.md)，实验门槛见 [G0-01](G0-01-AUDIT.md)。

| 字段/键 | 最小来源与语义 | 静态状态/缺口 |
| --- | --- | --- |
| `run_id, rank_epoch, node_id, pid` | 经审查的启动包装/运行清单；重启新 epoch；公开产物脱敏 | NCCL 不生成 run/epoch；运行清单 UNKNOWN |
| `global_rank, local_rank, gpu_uuid` | 启动器环境 + 实际 PID/GPU 映射；不能把 communicator rank 当 global rank | Profiler rank 为 comm 内 rank；GPU UUID 不在 v4 描述符，映射 UNKNOWN |
| `comm_key, comm_rank, members` | v4 init 的 commHash/nranks/rank/nNodes；汇总每 rank 的 init 与启动身份，保留原始证据 | commHash SUPPORTED；完整成员数组 UNSUPPORTED（需外部重建）；hash 不是全局唯一性证明 |
| `collective_key` | `(run_id, rank_epoch, verified_comm_key, collective_type, seqNumber)`，再核对 func/count/datatype/root、参与成员 | v4 coll.seqNumber 按 communicator + collective type 各自递增（[源码](https://github.com/NVIDIA/nccl/blob/593de54e52679b51428571c13271e2ea9f91b1b1/src/plugin/profiler.cc#L247-L270)），不可当全类型总序号；重建 comm 成员前跨 rank 匹配 UNKNOWN；不按时间最近或本地指针匹配 |
| `op, logical_message_bytes` | coll.func/count/datatype；bytes=count×类型宽度，写明每 rank 输入语义 | SUPPORTED；不是网卡传输字节；AllGather/ReduceScatter 输入/输出另标，未知类型宽度 UNKNOWN |
| `parent, channel, peer, proxy_state` | parentObj 只在同地址空间有效；ProxyOp/Step 状态链及 channel/peer | ABI SUPPORTED；PXN 跨 PID 父链可能断裂，断链 UNKNOWN，不猜关联 |
| `host_enqueue_start/end` | 插件回调时 CLOCK_MONOTONIC（example）；coll.stopEvent 仅 enqueue 结束 | SUPPORTED；不是 GPU 完成时间，也不是精确训练计算结束 |
| `gpu_channel_start/end` | v4 KernelCh pTimer / KernelChStop，GPU globaltimer；保存原始值与转换元数据 | ABI SUPPORTED；是 channel work 时间，不能把它叫完整 kernel launch 时间；实测覆盖 UNKNOWN |
| `proxy_progress_ts` | ProxyOp/Step 回调的本地 Host 时钟；区分 SendGPUWait/RecvWait 等状态 | SUPPORTED；不是硬件线上包时间；网络事件依赖 net plugin，不能从 ABI 推导实际支持 |
| `clock_domain, unit, calibration, uncertainty` | 每进程/每 GPU 独立域；example Host 微秒，GPU pTimer 原始纳秒需核对；保留转换方法 | 跨节点和跨 GPU 校准 UNKNOWN；禁止直接相减；误差大于效应则 UNKNOWN |
| `sampling, seen, emitted, dropped, overwritten, truncated, collector_health` | 每 rank/事件类/窗口的计数、容量和启停边界；区分未激活/未产生/丢失 | ABI 无通用 drop 字段；example 有界池会静默丢弃且只导出尾窗，精确 drop UNKNOWN；未报告不等于零 |

关联顺序：先用身份清单验证成员与 commHash 一致性，再按 seq + 元数据核对；每个匹配键必须在每名预期成员恰有一个 collective。channel/ProxyStep 是子事件，不是另一 collective。同类型同序号元数据冲突、缺 rank、重启复用、重复事件、PXN 断链均隔离并记原因，不做强行补齐。固定 dense DDP 的唯一 world communicator 可先测；多组/重建 communicator 和 DP/TP/PP 不得据此宣称已支持。

晚进入、通信执行久、等待的判别必须保留反例：较长 GPU 区间可能只是等待迟到 peer；较晚 Host enqueue 可能是 CPU 调度或数据准备；RecvWait 可能由远端计算、网络或本地进度线程引起。只有区间长短或 Inspector 聚合时，最多 `SUSPECT_GROUP_OR_EDGE`；缺校准/父链/完整性时 `UNKNOWN`。本阶段不产生原发 Rank 结论或实现归因算法。

采集不得要求暂停训练、额外 world collective 或热路径 GPU 同步。插件回调在 NCCL 线程执行，有界内存不等于无阻塞、低开销或 fail-open 已获证明；这些均保留为后续隔离 PoC 的验收项。

## 6. G0-02 实测覆盖（候选待审核，仅共享单机 NCCL microbenchmark）

[真实证据摘要](evidence/g0-02-summary.json)及[执行记录](G0-01-AUDIT.md#g0-02-执行记录候选未合并等待独立审核)更新的是本次运行事实，不回填为任意训练环境的保证：

| 要求 | 本次事实 | 边界 |
| --- | --- | --- |
| 实际库/ABI | 两目标PID加载同一NCCL2.28.3 DSO；官方2.27.7 example均加载v4 | 不是v5实测，Torch/DDP未使用；构建commit未知，保留二进制SHA |
| rank/GPU/comm | MPI测试自身rank→device0/1；同PID comm init rank0/1、nranks2、同commHash | 单world，无重启/多组证明，公开摘要以alias脱敏 |
| collective关联 | 87对`(run,commHash,type,seq)`，count/dtype一致；float32×2097152=8MiB | 不证明全历史/零drop；两rank键一致不代表采集无共同丢失 |
| Host时间 | Coll begin为Host回调时间；带子事件的Coll end为refcount归零时刻 | 独立Host enqueue end UNKNOWN，Chrome GPU类别ts仍是Host观察时间 |
| GPU时间 | 每rank1392组KernelCh原始StartGpuClk/StopGpuClk | GPU timer域，不作跨GPU绝对差、不等同完整kernel launch |
| Proxy/drop/因果 | Proxy未启用，精确drop和等待/原发区别UNKNOWN | 未注入、未做Rank归因；单机不能代替跨机验证 |
| 基本开销 | 一次无插件/插件平均延迟、RSS、输出量和停用烟测已记录 | step p50/p95 NOT_AVAILABLE；共享资源干扰未知，无SLA/fail-open证明 |

G0-02整体为PARTIAL：真实NCCL字段链可用，但DDP和step分位数未验证。GPU PASS仅限这次微基准，不等于完整G0或G1通过。

## 7. G0-03 实测覆盖（DDP PoC候选PASS，非Gate放行）

[真实摘要](evidence/g0-03-summary.json)覆盖一组共享单机DDP：实际Torch2.7/NCCL2.25.1/官方profiler v2，两DDP PID的DSO指纹和同进程版本查询、插件maps/ABI日志均已核对。两rank各94条Coll按run+commHash+type+seq匹配，并核对count/dtype；单WORLD PG0成员[0,1]的关联基于同PID唯一comm初始化/单commHash，不是通用PG映射；NCCL日志commId不当作CommHash。

每rank 40个真实CUDA-event step值及p50/p95已采，Host dispatch独立计时。只在warmup/测量末尾同步，无每步强制同步。v2 collector Host时钟是gettimeofday估频的RDTSC相对微秒，不能沿用v4 CLOCK_MONOTONIC假设；本次Host Coll-only不是GPU执行时间，v2 KernelCh/pTimer UNSUPPORTED。step→Coll UNKNOWN，Proxy未启用，精确drop/全历史/因果/跨机及fail-open仍未验证。原始GPU channel缺失与训练step GPU计时可用是两个不同结论。
