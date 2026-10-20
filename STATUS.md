# STATUS — Greenhound Online

- **更新日期**：2026-10-20（Asia/Shanghai）；唯一仓库：[Zwhao0/GREYHOUND_online](https://github.com/Zwhao0/GREYHOUND_online)（Public），默认 `main`
- **当前 Gate：G0 PASS（范围限定：候选审计、单节点NCCL/DDP字段可行性与初步开销）→ G1 IN_PROGRESS（尚未验收）**
- **当前执行任务**：[G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)（OPEN）：两节点真实dense DDP的被动NCCL Rank事件采集与跨Rank匹配。Issue已发布；尚未实测；跨节点/GPU/sudo/Docker权限需要当次明确确认。
- **已完成**：G0-01 [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2) PASS；G0-02 [PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5) **PARTIAL已接收**（单机NCCL测试87对事件，DDP没跑）；G0-03 [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8) **PASS/MERGED**（`08731fcbcfbf3e70d930ad888424dd061933f6bc`），[Issue #6](https://github.com/Zwhao0/GREYHOUND_online/issues/6) CLOSED，[独立审核](https://github.com/Zwhao0/GREYHOUND_online/pull/8#issuecomment-6294245015)，[PR HEAD DOC CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39445987211)
- **程序状态**：只有最小PoC/采集字段验证及测试脚本；本项目没有生产级采集器、在线Detector或Rank因果归因器；G1的跨节点关联脚本尚未交付。
- **分类**：DOC=PASS（已完成PR）；CPU归因算法测试=NOT_RUN；GPU=PASS（G0-02、G0-03各自受限单机实验）；DDP=PASS（仅G0-03单机）；**MULTINODE=NOT_RUN**；故障注入/在线化=NOT_RUN。

## G0 三个任务的真实结论

1. **G0-01 静态审计**：借鉴GREYHOUND ACF/变点/Group设计；原profiler主动同步/暂停路径不适用；detector许可证仍未明，**禁止复制源码**。选NCCL官方原生Profiler作为首测。
2. **G0-02 GPU微基准（PARTIAL）**：单机2×H800的`nccl-tests`真正加载NCCL2.28.3和官方Profiler **v4**；两rank各87条AllReduce，87对可匹配；单次共享环境聚合平均延迟增幅+0.866%/+0.963%；该实验没有跑DDP。
3. **G0-03 真实 DDP（PASS）**：单机共享2×H800、NGC缓存PyTorch25.03镜像，真实forward/backward/SGD，两个DDP PID分别加载**Torch2.7.0a0 + NCCL2.25.1 / 官方Profiler v2**；两rank各94条Collective，94对按commHash/type/seq匹配，单侧缺项0（不等于全历史零drop）。40个测量step CUDA event p50/p95已按原始数据独立复算一致。

| Rank | 无插件 GPU step p50 / p95 | 开插件 GPU step p50 / p95 |
| --- | --- | --- |
| 0 | 1.144320 / 1.183483 ms | 1.153632 / 1.190360 ms |
| 1 | 1.151296 / 1.248669 ms | 1.154144 / 1.193533 ms |

**限制**：只有一次共享GPU短窗对照，不能宣称稳定 ≤2% 训练开销、完全非阻塞或长期fail-open。NCCL v2没有GPU channel timer，CUDA事件只是本地step区间；跨进程时钟不可直接相减，step→Collective、Proxy、精确drop、全历史完整性、跨节点匹配及原发/受害因果均 **UNKNOWN/NOT_RUN**。不能把v4的能力回填给v2。

## Gate 记录

| 阶段 | 状态 | 通过的范围 / 待解决事项 |
| --- | --- | --- |
| Bootstrap | PASS | GitHub基线 |
| G0 可观测性候选 | **PASS（范围限定）** | 单机实际字段+兼容性+初步开销已核实；生产能力未证实 |
| G1 Rank级证据采集 | **IN_PROGRESS；G1-01 OPEN/NOT_STARTED** | [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9)，需真实双机DDP/Rank-comm-op-seq匹配/缺失记录 |
| G2 离线因果归因 | BLOCKED_BY_G1 | 不能将最长等待判原发Rank |
| G3 在线非暂停 | BLOCKED_BY_G2 | 需真实负载、fail-open、丢失/低开销证据 |
| G4 扩展 | BLOCKED_BY_G3 | 后续DP/TP/PP，MoE可选 |

## 新增执行规则及下一步

- 用户指定Codex子智能体两级分工：**GPT 6 luna max**处理简单/重复任务；其无法处理或复杂难点再升级 **GPT 6.1 sol medium**；主Codex集成/负责关键授权与实测。详见 [AGENTS.md](AGENTS.md)、[DECISIONS.md](docs/DECISIONS.md)。
- **Codex下一唯一动作**：执行 [G1-01 Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 的许可确认与两节点2×H800/节点健康DDP被动采集；先做可分配的脚本/解析准备；无资源授权就BLOCKED，不能运行GPU。
- **禁止**：擅自sudo/Docker越权、生产训练/修改框架与NCCL、故障注入/主动减速、诊断collective、GREYHOUND不明许可证代码拷贝、Rank因果结论、自动进入G2或自行合并PR。Public仓库不得泄露公司机器/网络/私有日志/权重。
