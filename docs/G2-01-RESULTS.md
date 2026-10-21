# G2-01 — 单 Rank Fail-Slow 独立真值盲测先导

2026-10-21（Asia/Shanghai），唯一任务 [Issue #24](https://github.com/Zwhao0/GREYHOUND_online/issues/24)。本文件记录小样本工程先导，不授予 G2 Gate PASS 或 G3 权限。

## 固定协议与盲测边界

[预登记](evidence/g2-01-registration.json) 在真实 GPU 启动前提交到 GitHub `37d543258c1e1b10933d9b5575650fba031770f7`。私有随机顺序含 8 个 episode、4 Rank 各 2 次，20ms CPU sleep 位于本项目合成 DDP 的 loss forward 后、backward 前；5 warmup + 40 measured steps。另有预定 8 个健康窗口，每两个注入间保留 3 步，无额外训练 world collective 或每 step GPU 同步。

私有带 nonce 计划 SHA256：`4321cddc032d0551e0a4cb3de19d769c240feda63b4a2fca3a7841af71d592fc`。计划、seed、真值、step 边界和训练日志从未交给定位器子智能体；生成计划后不根据实测调参。定位器进程仅显式打开两个脱敏事件文件，字段白名单拒绝真值或 step 字段。主窗口实验角色生成计划并操作 GPU，独立评分脚本在预测及输入文件哈希冻结后才加载计划和实际 sleep/step 真值。此为可审计的信息隔离，不声称 OS 级密封执行或外部第三方见证。

预先限定全部 AllReduce（包含 warmup），依据 operation type 排除启动 AllGather/Broadcast，排除数量另报。复用 G1 manifest、comm/type/seq 匹配、审计、独立时钟侧车及严格因果映射。健康基线必须另一次运行，比较相同 Rank 与完整 collective 元数据、实际运行库/脚本/NCCL 配置及物理 GPU 映射哈希。

定位器要求候选 Host COLL begin 区间严格晚于每个 peer，保守 arrival lag 下界超出同 Rank 同类健康最大上界再加固定 10ms；区间重叠、缺失、质量异常或基线不可比均 UNKNOWN。它不按通信持续时间排名，不把 Host callback 当 GPU kernel 开始。有限健康基线和共同调度延迟仍限制因果归因。

评估器在每个预定 step 内以各 Rank 本地单调时间边界关联匹配实例，不把边界反馈给定位器。同一窗口的 ROOT_CANDIDATE Rank 并集恰有一个则为候选；无候选或冲突则 UNKNOWN。UNKNOWN 计未命中，映射缺失或注入不能确认则 INCONCLUSIVE。GO 门槛只为 7/8 Top-1、健康误报最多 1/8、实际注入与隔离有效。

## 真实运行及结果

**操作性停损：`NO_GO_FOR_CURRENT_SIGNAL`；独立 episode 可识别性：`INCONCLUSIVE`。** 当前冻结的被动 Host arrival 比较器不建议直接进入正式 ≥30 次精度评估。

| 预登记指标 | 本次结果 |
| --- | --- |
| 注入实际生效 | 8/8，本地单调时钟 sleep 20.060–20.070ms |
| Top-1（UNKNOWN 计未命中） | **3/8 = 37.5%** |
| 注入窗口 UNKNOWN | **0/8** |
| 预定无新注入窗口告警 | **6/8**；健康 UNKNOWN 2/8 |
| 全部分析实例 UNKNOWN | 23/89（25.84%）；其余 66 为候选 |
| 每个评分窗口可关联实例 | 全部 16 个窗口各 2 个四 Rank AllReduce |
| 真实运行次数 | 健康 1 次、注入 1 次；没有追加 GPU 轮次 |

完整逐 episode 真值/候选与 sleep 记录见[评分](evidence/g2-01-score.json)，事后 step→实例关联见[揭盲映射](evidence/g2-01-evaluation-map.json)。预测与全部输入已经在 GitHub `0f87ac33f0bc4d0a777d9689360f4fe1ef3f8b91` 提交后才执行独立评分。冻结 manifest SHA256：`c0e96ab4a39fd486bc99d5fa54d59fe9cc3b66b3da41c9dce3b07d0b818bdadf`。原始计划 nonce 与本地真值仍私有，仅公开评分所需的事后标签和实例关联。

**解释范围：** seq 25–88 连续 64 个实例都将 Rank 1 判为候选，跨越后续不同 Rank 的注入与无新注入窗口。Rank 1 的 Host 相位延后持续存在；拖尾/持久相位偏移是一种可能解释，不能据此断言物理根因。虽然计划中 episode 相隔 4 步、各 sleep 均已独立记录，**未证明恢复到健康状态或统计独立**。因此 6/8 应称“预定无新注入窗口告警”，不能当作干净独立健康特异度；3/8 也不是总体定位精度。原始预登记评分保留 NO_GO，同时对“8 个隔离 episode 的可识别性”结论为 INCONCLUSIVE。详见 [sol medium 事后公开证据审阅](G2-01-INDEPENDENT-REVIEW.md)，仍须 ChatGPT 外部独立审核。

资源安全检查沿用 G1 许可范围与小负载，每机只暴露原 GPU 0/1。启动前两次低负载快照通过（node-a 每卡空闲 2458MiB，node-b 5200MiB，util=0%），阈值分别 ≥2400/4800MiB 且 util≤10%。Torch allocator 上限 1%，实际 reserved 每 Rank 111149056 bytes。两轮远端训练/侧车退出均为 0，收尾各节点本任务残留 0、原有 GPU 应用各 8 个，原 DSO 哈希未变。不宣称已测得共租服务零影响或净开销 SLA。

两轮各 90/90 实例匹配，分析范围 89 个 AllReduce，排除 1 个 AllGather。各 356/356 已观察 Host begin 区间 BOUNDED。健康/注入的最大半宽分别 674436ns / 542602ns；本地表示误差界 4000ns。跨节点对严格先后分别 46/356 和 250/356，其余重叠/UNKNOWN。已计数 callback 的 accepted/exported 守恒、drop/reject 为 0，**上游未回调全集 loss、GPU timer overwrite 仍 UNKNOWN**。两机时钟因果界不扩展为 GPU kernel 绝对时间同步。

失败记录：私有收集脚本最初使用本机 Python 3.9 不支持的 tar `filter=` 参数；修正本地解包兼容性后收集原有归档，无重跑。注入运行本地主控 SSH 会话未报告结束，远端完成凭据已经为 0；核实远端文件与零任务残留后中断了仅本地控制进程（退出 130），保留记录，不能伪称本地主控正常完成。远端硬超时 180s、kill-after 10s、单文件大小上限 64MiB 保持有效。旧 TCP 预检凭据做启动校验，新运行各自有 45s 当前侧车采样；没有重验 G0/G1。

完整脱敏数据：[健康输入](evidence/g2-01-healthy.json)、[观测输入](evidence/g2-01-observed.json)、[冻结预测](evidence/g2-01-predictions.json)、[冻结哈希](evidence/g2-01-freeze.json)、[资源与运行汇总](evidence/g2-01-summary.json)、[健康质量](evidence/g2-01-healthy-quality.json)、[注入质量](evidence/g2-01-observed-quality.json)。

## 验证与后续建议

DOC 验证、CPU 全套 **130 tests PASS**（含定位负例、注入边界、评分冻结篡改与公开证据复算）。GPU/MULTINODE 结果只来自上述两次真实运行；CPU fixture/CI 不冒充 GPU 验证。GPT 6 luna max 完成注入 helper/fixture/评分负例；GPT 6.1 sol medium 完成区间因果定位、adapter 与盲评科学审阅；主窗口完成集成、真值承诺与隔离、真实 GPU、冻结/揭盲及唯一 PR。

下一步只提交审核建议：先区分持久 Host 相位偏移与本地新增 pre-backward 延迟，可考察不增加 world collective/热路径同步的本地 Rank 时间基线或被动 GPU 遥测，并预先定义恢复/无拖尾判据。需先经 ChatGPT 规划和用户授权后才考虑新一轮 G2 设计；本次不实现、不追加运行、不进入 G3。

## 回退与保留

停用 G2 wrapper/不传 `--g2-plan` 即关闭注入。旧 venv、Profiler DSO、宿主与生产依赖未修改。只在新私有任务目录中运行；沿用 G1 Torch 2.14.1+cu130、NCCL 2.30.7、Profiler v4。原始数据只保留在私有任务目录，审核结束后 7 天内手动清理，不公开地址、PID、UUID、nonce 或原始日志。

## 停点

唯一 Draft PR 交 ChatGPT 独立审核；不自行合并、追加 GPU 轮次、开展完整在线系统或进入 G3。
