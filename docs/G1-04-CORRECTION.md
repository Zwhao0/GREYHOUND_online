# G1-04 — 启动编排纠错与真实 Host 包络补证

2026-10-21（Asia/Shanghai），[Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)、[同一 Draft PR #22](https://github.com/Zwhao0/GREYHOUND_online/pull/22)、[独立审核与一次 GPU 纠错授权](https://github.com/Zwhao0/GREYHOUND_online/pull/22#issuecomment-6308753247)。**启动问题已解决；本次达到提交 G1 限定 Host 映射审核的证据条件，Gate 仍 IN_PROGRESS，等待 ChatGPT 裁决。** 没有进入G2、故障注入或Rank归因。

## 失败记录与修复

1. [首次健康GPU运行](G1-04-RESULTS.md)的控制地址误配、280事件全UNSAFE，保留[原始脱敏摘要](evidence/g1-04-summary.json)，字节不变；不覆盖旧私有日志或G1-01/03证据。
2. 纠错时显式分开 `DDP_MASTER_ADDR`（node-a）和 `CONTROL_SOURCE_ADDR`（node-b），两节点接口归属经只读检查吻合。但第一次纯CPU/TCP预检仍失败，client拒绝/server接收超时，**没有启动GPU**。保留[本次失败证据](evidence/g1-04-correction-preflight.json)。用户随后明确要求继续定位并解决问题。
3. 同一控制机文件记录揭示启动竞态：client日志在source启动约53.136秒后、source命令完成约21.951秒后才创建；source总等待只有30秒。该记录仅解释编排问题，**不是跨节点时钟校准**。改为[同一控制进程的有界屏障](../tools/g1_04_coordinate.py)：启动source → 确认指定地址/端口监听 → 立即启动client，避免模型/工具回合插在两次启动之间。成功预检中监听确认到client启动仅0.154083ms（同一控制机单调时钟）。
4. 第二次不占GPU的真实两节点TCP短窗完成 **2373对四时戳、两端exit0**，完整身份/双端t1,t2,t3/序号/单调性/单位/源码指纹通过[独立核验](../tools/g1_04_preflight.py)。[脱敏预检证据](evidence/g1-04-network-pass.json)明确 `training_calibration=false`，不能替代训练期间的证据。
5. 预检通过后等待共享卡从高负载回落，连续两次只读资源检查满足低负载/显存条件；才启动新的连续侧车。两端首次有效应答的原子就绪文件、run/epoch、boot/time/pid namespace、**当前PID incarnation/start ticks与存活**、collector及时间戳辅助文件SHA均验证后，启动**唯一一次追加**健康4Rank训练。源端监听就绪与双端数据就绪是不同屏障。

[侧车模板](../tools/g1_04_sidecar.sh)按source地址精确bind，拒绝覆盖旧会话；[训练wrapper](../tools/g1_04_run.sh)在任何GPU读取或Torch启动前强制验证预检凭据及当前侧车就绪。失败即拒绝启动训练；不修改防火墙/网络策略或停止他人任务。冻结的 `g1_04_causal.py` 与审核HEAD `9339bd2` **SHA相同、无算法变更**。新增的是启动、预检、身份/存活屏障及报告证据。

## 唯一一次追加 GPU / MULTINODE 运行

固定Torch **2.14.1+cu130** / NCCL **2.30.7** / CUDA runtime **13.0.96** / driver **580.178.04**，原Profiler **v4** DSO与原合成DDP脚本不变。每机暴露原2张共享H800、OMP=1、Torch allocator上限1%，5warmup+30steps；无baseline重跑、无额外训练world collective、无每step同步。未升级软件、未重编译插件、未改生产/框架/NCCL核心。

[本次完整脱敏JSON](evidence/g1-04-correction-summary.json)含280个真实Host begin事件、逐事件ns区间/误差半宽/证据索引/状态、所用原始四时戳、输入指纹及逐Rank实际加载DSO。Profiler DSO SHA仍 `06740a4ea051720ca974a22a6f448bcacb5648e7a9c4a928e81e043ad88dcf54`；原负载SHA仍 `6f9e20bf32b93731808abd1ec304a29da1f043add1202f77e5c22006271823b5`。实际训练PID和audit/trace绑定4/4；软件/库文件指纹同既有审核证据，完整列表见JSON。

- 两训练launcher、两侧车均exit0；70个4Rank实例匹配（1个AllGather、69个连续AllReduce），全部280个Host begin事件纳入统计。
- 侧车按90秒目标、110秒deadline、120000样本、0.5ms最小请求间隔、64MiB文件预算运行，实际 **106637对四时戳**，正常duration结束。采样包络严格覆盖4/4 Rank的origin至active-until审计窗口。
- 全采样reference-send间距p50/p95/max **0.844908 / 0.868316 / 20.001149ms**；source-receive为 **0.844608 / 0.870102 / 20.024210ms**。最大间隙不被忽略：若事件落在过宽包络，算法仍会拒绝。实际所有观察事件的包络如下。
- 新任务残留0，两节点各8个原有GPU应用数量保留；私有capture目录分别约16.8MB/13.7MB，原插件未变。未测他人服务延迟，不宣称零影响。共享环境净额外开销 **INCONCLUSIVE**；沿用G1-01历史p50 **+6.1%～7.5%** 风险，不宣称≤2%或长期SLA。

## 真实事件的因果误差半宽与覆盖

这里是由真实四时戳构造的**不确定度区间半宽**，不是相对独立真值测得的时钟残差。source事件完整表示区间按冻结算法严格夹在已接收/待发送控制戳之间；没有漂移拟合、offset插值或对称网络假设。参考节点的4µs仅是本地数值表示界，不是物理时钟准确度。

| Rank / 域 | 事件数 / 1ms内BOUNDED | 半宽p50 / p95 / max（ms） | 1 / 5 / 10ms预算覆盖 |
| --- | --- | --- | --- |
| 0 / reference | 70 / 70 | 0.004 / 0.004 / 0.004 | 100% / 100% / 100% |
| 1 / reference | 70 / 70 | 0.004 / 0.004 / 0.004 | 100% / 100% / 100% |
| 2 / source | 70 / 70 | 0.511304 / 0.525694 / 0.583573 | 100% / 100% / 100% |
| 3 / source | 70 / 70 | 0.511334 / 0.526649 / 0.583173 | 100% / 100% / 100% |
| source合计 | 140 / 140 | **0.511319 / 0.526649 / 0.583573** | **100% / 100% / 100%** |
| 全体（含reference本地界） | 280 / 280 | 0.053183 / 0.524646 / 0.583573 | 100% / 100% / 100% |

**映射不可用比例：0/280=0%**；无身份/序号/本地回退、超预算或无包络拒绝。连续完整4Rank、1ms内合格AllReduce为 **seq0～68，共69个**，高于建议至少10个。只是这次完整观察序列，不建立step→Coll标记或从seq推断时间顺序。

**严格时间顺序未知比例：196/280=70%**。每个匹配实例有4个跨节点Rank-pair，合计280对；reference严格在source之前16对、之后68对，另外196对区间重叠，保持 `OVERLAP_OR_UNKNOWN`。区间有界并不意味着每一对先后可判；不能按中点排序或据此定位原发/等待Rank。差值若需报告也必须用区间相减、误差界相加。

完整活动窗被采样夹住只证明存在因果包络，**不证明整个90秒或任意未观察时刻都≤1ms**；全采样存在约20ms间隙。上述覆盖率的分母是所有实际观察到的280个事件，不是全时间轴或NCCL全集。没有跨GPU时钟同步证据。

## 验收建议与边界

**建议提交G1限定Host时间映射Gate审核**：代表性健康4Rank合成DDP的全部观察Collective均有来源明确的因果区间，69个连续实例满足1ms半宽预算；原先“训练期间无有效控制证据”的阻断已补齐。**这只是审核候选，Codex不判G1 PASS，不合并、不关闭Issue、不进入G2。**

保留的缺口：上游共同未回调/端到端全集loss、GPU timer ring覆盖、原example的生产fail-open、跨GPU绝对时间、step→Collective、生产/长期精度与低开销均UNKNOWN。本次callback级计数/导出自洽和已计数drop/reject为0不扩展为端到端零drop。控制失效与就绪故障只在CPU fixture验证；没有现场故障注入。

DOC/CPU覆盖屏障时序、预检双端一致性、旧marker、PID incarnation、namespace/源码变化、首包就绪、冻结因果反例及公开真实数据独立复算。最终项数与HEAD CI见PR/STATUS。luna max负责fixture/证据核对，sol medium独立复算了全部280个区间与69实例、审查了数学边界；主Codex负责集成与唯一追加GPU运行。

## 可重复模板与回退

在新的私有目录复用既有venv/DSO/负载，将地址通过环境注入，**不要使用示例中的占位值**：

```sh
export DDP_MASTER_ADDR=REFERENCE_PRIVATE_ADDRESS
export CONTROL_SOURCE_ADDR=SOURCE_PRIVATE_ADDRESS
export CONTROL_PORT=DEDICATED_PORT
# 协调器将server/client命令分别异步派发到对应节点的新私有目录，
# 预检参数CONTROL_DURATION_S=2、CONTROL_TIMEOUT_S=30。
# 不可在终端先阻塞运行server、等它退出后才运行client。
python3 g1_04_preflight.py verify --client PRIVATE_CLIENT.json --server PRIVATE_SERVER.json \
  --client-exit PRIVATE_CLIENT_EXIT --server-exit PRIVATE_SERVER_EXIT \
  --ddp-master-addr "$DDP_MASTER_ADDR" --control-source-addr "$CONTROL_SOURCE_ADDR" \
  --collector-source g1_04_control.py --output PRIVATE_PROOF.json
# 只有完整PASS且资源安全后，创建新的capture会话；两侧car ready均验证后，
# start_training_pair(verify_complete_preflight, both_live_sidecars_ready,
#                     start_reference_training, start_source_training)
```


协调器的传输适配器在私有环境绑定正确节点；公开屏障的实际调用形状如下（`remote_start`/`source_listener_is_ready` 为私有SSH适配器）：

```python
from tools.g1_04_coordinate import start_control_pair, start_training_pair
source, reference = start_control_pair(
    lambda: remote_start("source", ["bash", "g1_04_sidecar.sh", "server", source_dir, run, epoch]),
    source_listener_is_ready,
    lambda: remote_start("reference", ["bash", "g1_04_sidecar.sh", "client", reference_dir, run, epoch]),
    timeout_s=8,
)
# 等两端正常退出，下载并独立核验全部四时戳。通过后在新capture会话中
# 重新调用同一屏障；两端数据就绪、PID/clock-domain/SHA验证后才启动训练。
reference_training, source_training = start_training_pair(
    verify_complete_preflight, both_live_sidecars_ready,
    start_reference_training, start_source_training,
)
```

私有SSH凭据/地址适配器与实际协调脚本不公开；公开屏障模块相同，协调器实际执行SHA与单机单调事件记录在JSON。复算本次结果：

```sh
python3 tools/g1_04_report.py PRIVATE_CAPTURE_ROOT --private-manifest PRIVATE_MANIFEST.json \
  --output docs/evidence/g1-04-correction-summary.json \
  --network-proof docs/evidence/g1-04-network-pass.json \
  --controller-events PRIVATE_CONTROLLER_EVENTS.json \
  --controller-source PRIVATE_CONTROLLER.py --initial-summary docs/evidence/g1-04-summary.json
python3 -m unittest discover -s tests -v
python3 tools/validate_docs.py
bash -n tools/g1_04_run.sh tools/g1_04_sidecar.sh
```

首次失败摘要的复算使用审核HEAD `9339bd2` 对应分析器；不把新版启动代码指纹冒充首次执行版本。停止使用新wrapper即可回退，旧安装/DSO未改；任务已退出，不为回退额外运行GPU。私有失败与成功raw均保留至独立审核完成后7天内手动清理，禁止公开PID、boot/ns、IP、主机、UUID和未脱敏日志。

**停点：等待ChatGPT在同一Draft PR独立审核最终HEAD/CI与本次真实证据。** 不追加GPU实验。
