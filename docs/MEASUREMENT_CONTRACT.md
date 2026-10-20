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
