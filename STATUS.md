# STATUS — Greenhound Online

2026-10-21（Asia/Shanghai）；[唯一仓库](https://github.com/Zwhao0/GREYHOUND_online) Public。**G1-01结果为本 Draft 候选未合并，G1总Gate仍 IN_PROGRESS。** 具体执行和证据放[实验报告](docs/G1-01-RESULTS.md)，下一动作见[HANDOFF](HANDOFF.md)。

## 阶段与测试事实

| 阶段 | 当前状态 | 证据 |
| --- | --- | --- |
| G0-01 | PASS | [PR #2](https://github.com/Zwhao0/GREYHOUND_online/pull/2)静态审计 |
| G0-02 | PARTIAL / 已接收 | [PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)：单机NCCL2.28.3/v4，87对 |
| G0-03 | PASS / MERGED | [PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8)：单机Torch2.7/NCCL2.25.1/v2，94对/40steps |
| G0 Gate | **限定范围PASS** | 单节点可行性；本轮未重复完整验收 |
| G1-01 #9 | **候选完成、OPEN待审** | 新稳定栈+真实双节点4Rank被动事件/实例匹配 |
| G1 Gate | **IN_PROGRESS，未由ChatGPT验收** | 当前Draft不可当已合并或自动Gate PASS |
| G2 / G3 / G4 | BLOCKED | 无原发因果、在线化或扩展验收 |

| 本轮分类 | 结果 | 范围 |
| --- | --- | --- |
| DOC | 本地PASS；[代码/证据HEAD CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39457160530) | `python3 tools/validate_docs.py` |
| CPU | PASS，9项synthetic fixture+真实trace解析 | fixture只证明逻辑 |
| GPU smoke | PASS，新栈兼容 | 一次2Rank，1 warmup+2 steps；各6 Coll/81 GPU channel |
| DDP / MULTINODE | 四Rank运行/匹配候选PASS，待独立审核 | baseline一次+plugin一次，各5 warmup+30 steps；launcher均exit0 |
| 故障注入 / 根因 / 在线化 | NOT_RUN | 未进入G2/G3 |

## 新栈与观测事实

- 两机私有Python3.12 venv，**Torch2.14.1+cu130 / CUDA runtime13.0.96 / 配套NCCL2.30.7 / 官方example实际v4**。30包/机SHA与pip check通过；10个训练PID的CUDA/NCCL DSO及同DSO版本查询、6个plugin PID的插件SHA/ABI日志一致。Driver580.178.04未改。
- **每Rank70 Coll，70个四Rank实例匹配**（1 AllGather、69 AllReduce）；观察键并集中缺侧、重复、metadata/成员冲突0。每Rank553组正序非零GPU channel。完整init/finalize、WORLD成员、launch身份和私有GPU UUID交叉核对，NCCL报告nNodes2、network IB。
- 一次共享GPU顺序对照，step p50变化 **+6.10%～7.53%**，p95 **+6.60%～7.82%**。仅方向性证据，不宣称稳定≤2%；不为数字追加轮次。收尾本项目训练进程0，原有各8个GPU应用仍在。
- 精确drop/共同遗漏/全历史、未观察操作、绝对校时与误差界、step→Coll、root、原发/受害因果 UNKNOWN；Proxy未采。只有最小DDP负载、启动包装、离线manifest/匹配脚本，无生产采集器、通用comm重建或根因定位器。

[实测汇总/原始step数组与SHA](docs/evidence/g1-01-summary.json)；[70实例逐键结果](docs/evidence/g1-01-matches.json)；[版本锁](tools/g1_01_pylock.toml)。旧G0证据原样保留，不能混用版本能力。

## 候选提交与收尾

- 分支 `g1-01-multinode-profiler`，[Draft PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) OPEN/未合并；代码/证据HEAD `79d59354d57da391f4831501876b81aff9d877b2`，base main `6ec44426cd18342d441bf34c9eda2f3e0f22782d`，实验开始基点`f455125`。交接提交仅文档变更，最新HEAD/CI回读PR。
- 用户已确认两机持续共享及隔离升级。本轮未改驱动/内核/全局包/生产任务，旧环境保留；停用插件已在新栈baseline实测。私有原始数据与回退细节见报告。
- **下一动作**：停止执行，等待ChatGPT审核本Draft的最新HEAD/CI与实验报告；不自行merge/关Issue/判Gate PASS、不重验G0、不新增升级Gate或进入G2。
