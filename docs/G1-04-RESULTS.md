# G1-04 — 首次运行的连续 Host 因果包络（历史 PARTIAL）

> 本文保留首次失败事实。后续启动时序已修复且真实补证成功，当前结果与Gate建议见 [纠错报告](G1-04-CORRECTION.md)。

2026-10-21（Asia/Shanghai），[Issue #20](https://github.com/Zwhao0/GREYHOUND_online/issues/20)。**候选 PARTIAL；不具备 G1 Gate 放行证据。** 一次健康双节点 4 Rank plugin 训练退出成功，但本次控制启动配置错误，未形成训练期间四时戳证据。没有追加 GPU 轮次；CPU 逻辑通过不补足真实映射缺口。

[真实脱敏 JSON](evidence/g1-04-summary.json)保存280个实际Collective Host begin事件、逐事件拒绝原因、trace索引、来源指纹、运行库与退出状态。没有把CPU fixture、旧G1-03片段或空样本当成本次校准。

## 数学和实现（CPU）

[侧车](../tools/g1_04_control.py)复用G1-03 CLOCK_MONOTONIC、身份与TCP辅助函数，训练world之外串行采集 `(a1,b2,b3,a4)`；TCP_NODELAY，整帧收完后读时钟，所有序列化/网络/调度留在包络内。不增加训练collective、每step同步或热路径I/O。上限90秒目标、110秒总deadline、120000样本、每包16KiB、文件预算64MiB、请求间隔至少0.5ms，nice=5；外层115秒timeout与文件ulimit。原始控制文件只有成功结束才产生，失败时保留私有stderr和exit code，缺文件必拒绝映射。

[映射器](../tools/g1_04_causal.py)对事件完整表示区间 `[e−,e+]`，下界取所有 `b2 < e−` 样本中最大的 `a1`，上界取所有 `e+ < b3` 样本中最小的 `a4`。片段内部可用该片段 `[a1,a4]`；相邻片段之间使用前reference-send与后reference-recv。严格不等号避免等值读数误判先后。半宽为 `ceil((upper-lower)/2)`，超预算仍保留可审计区间但输出 `UNSAFE_TO_SUBTRACT`；缺侧证据则区间null。无offset插值、RTT对称、稳定漂移或seq推测时序假设。

绑定run/epoch、boot/time/pid namespace、CLOCK_MONOTONIC、目标训练PID/origin/active window、已知表示误差、ns单位；侧车PID与训练PID允许不同，训练事件必须匹配已验证的训练audit。原example的4000ns仅是数值表示界，不是物理准确度。控制乱序/缺失/回退或身份变化拒绝整个控制epoch。跨Rank仅在同reference clock、两个BOUNDED区间**严格不相交**时返回顺序；重叠返回UNKNOWN，不评分原发/受害Rank。参考节点本地表示区间也只有在控制session有效时参与跨节点比较。

CPU反例涵盖间隙、无覆盖、丢失/乱序、训练PID或namespace变化、局部回退、超宽、重叠/相等、单位错误、缺completion/误差来源、缩小误差和跨session比较；另有有界本机TCP测试。均非真实精度证明。

## 唯一真实 GPU / MULTINODE 实验

沿用两个已授权共享H800节点，每节点仅暴露原2张卡、OMP=1、Torch allocator上限1%、5warmup+30steps；launcher180秒、process group60秒。执行前目标卡可用内存分别约2458MiB和5200MiB，原驻留应用保留。未升级软件或重编译插件；新目录仅复制旧DSO和合成脚本、symlink旧venv。Torch2.14.1+cu130、NCCL2.30.7、旧Profiler v4、CUDA13.0.96和driver580.178.04固定。没有baseline或第二次GPU实验。

| 项目 | 本次真实结果 |
| --- | --- |
| 两节点训练launcher / 4个Rank结果 | 两launcher exit0；4个Rank均产出30个正常step结果 |
| Trace / 同PID origin | 4/4齐全；实际加载DSO、训练PID与audit匹配；本地Host表示可重建 |
| 观察Collective实例 | 70个既有规则MATCHED；280个Host begin事件，仅作为本次映射输入 |
| 控制侧车 | client exit1：ConnectionRefusedError；server exit1：accept timeout |
| 完整四时戳 / 训练交叠 | 0；无法证明交叠，样本间距p50/p95/max均UNKNOWN |
| 任务残留 / GPU应用数 | 新训练/侧车残留0；两节点各8个GPU应用，与前检查数量相同 |
| 新目录大小（压缩前） | 两节点均不足0.6MiB；旧插件指纹未变 |

**失败原因是主Codex私有启动脚本把client目标设成reference自身的rendezvous地址，而非source节点控制地址。** 不是健康训练故障，也没有证据说明因果时钟算法或网络精度不达标。server在正确source节点等待到有界timeout；训练独立完成，展示本次控制故障未阻断训练的事实，不能泛化为生产fail-open。该配置错误应在任何将来获批运行前通过独立控制连接及就绪检查发现；master地址与source控制地址必须分开指定。本次不为修复配置追加GPU轮次。

源指纹（两节点相同）：原合成脚本 `6f9e20bf32b93731808abd1ec304a29da1f043add1202f77e5c22006271823b5`；Profiler DSO `06740a4ea051720ca974a22a6f448bcacb5648e7a9c4a928e81e043ad88dcf54`，sole导出ncclProfiler_v4；实际训练PID加载NCCL DSO `618968ee277041751512e619190132a9bdf351c3ce7129c73484f6ef441ad692`、CUDA runtime DSO `96c42e418cec19054186b9429c321603cc190bf26a18104e19408117a2a817b0`。执行的侧车/辅助文件/wrapper与分析代码的完整SHA、每Rank trace/audit和失败日志SHA见JSON。保留本次逐类callback审计结果，不重复既有采集验收。

## 精度、覆盖与 Gate 建议

| 指标 | Rank0 / Rank1 / Rank2 / Rank3 | 全体 |
| --- | --- | --- |
| 实际Host begin事件数 | 70 / 70 / 70 / 70 | 280 |
| BOUNDED / 有四时戳来源映射 | 0 / 0 / 0 / 0 | 0/280 |
| 误差半宽p50 / p95 / max | UNKNOWN（无有效映射） | null / null / null；样本n=0 |
| 1ms预算覆盖率 | 均0% | 0% |
| 5ms / 10ms预算覆盖率 | 均0% / 0% | 0% / 0% |
| 无法比较比例 | 均100% | 100% |

预算覆盖率以全部实际事件为分母，表示**证据支持率**；0%不等于已测误差超过预算。280/280事件明确 `UNSAFE_TO_SUBTRACT`，源证据索引为空、reference interval为null。70个匹配实例对应的280个跨节点Rank-pair比较均UNKNOWN；连续4Rank、1ms内合格实例0，未达到建议至少10个。没有可报告的实测误差分布，也不把null写成0误差。

**建议：G1-04 PARTIAL，G1 Gate保持IN_PROGRESS，不放行。** 当前保留“身份/序号可对齐，但跨节点Host时间不可用”的受限能力。暂停现场时钟路线并停等ChatGPT独立审核；本次是启动失败，不能据此推断严格因果包络在该环境下的精度极限。是否重新授权修复配置后的单次补证或重新确定精度目标，由用户/独立审核决定，本PR不自行继续。

本次净额外开销INCONCLUSIVE：不重跑baseline，沿用G1-01历史p50 +6.1%～7.5%风险，不宣称≤2%或长期低开销。callback已计数的pool-drop/parent/guard拒绝为0仅适用于本次回调；共同遗漏、端到端全集loss、GPU timer ring覆盖、生产fail-open、跨卡GPU绝对时间及step→Coll仍UNKNOWN。没有故障注入、原发定位、G2、生产/框架/NCCL核心/宿主改动。

## 重现与回退

```sh
python3 tools/g1_04_report.py PRIVATE_ROOT --private-manifest PRIVATE_MANIFEST.json \
  --output docs/evidence/g1-04-summary.json
python3 -m unittest discover -s tests -v
python3 tools/validate_docs.py
bash -n tools/g1_04_run.sh
```

DOC/CPU只验证离线逻辑；GPU/MULTINODE仅本次健康训练通过，**本次真实Host映射FAIL**。最终CPU项数、代码提交/最终HEAD/CI见PR及STATUS。原有G1-01/03证据不覆盖。停止使用新wrapper/私有目录即可回退，原目录插件SHA仍 `3982ac146d710cfd3eca59e0c36fd1502790840211eb8f41c2d35934b51c9571`；无回退GPU重验。完整PID、boot/ns、主机/IP/GPU UUID、原始日志和私有launcher只留隔离目录，至独立审核完成后7天内手动清理；不提交公开仓库。
