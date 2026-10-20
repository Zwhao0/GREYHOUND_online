# HANDOFF — Greenhound Online

> 简短交接入口。以 GitHub main、当前 [Issue #9](https://github.com/Zwhao0/GREYHOUND_online/issues/9) 与 PR HEAD/CI 为准；以下 G1-01 是**候选未合并**，不能当成 Gate 放行。

## 当前快照（2026-10-21，Asia/Shanghai）

- **Gate**：G0 限定范围 PASS，未重验；G1 IN_PROGRESS、待 ChatGPT 独立审核；G2/G3 未授权。
- **任务**：G1-01 已完成隔离升级、一次2-rank最小 smoke、一次4-rank baseline及一次plugin（双机各5 warmup+30 steps）。候选满足本Issue的观测/匹配目标，Issue保持OPEN。
- **分支 / PR**：`g1-01-multinode-profiler`，[Draft PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) OPEN/未合并；代码/证据HEAD `79d59354d57da391f4831501876b81aff9d877b2`，base main `6ec44426cd18342d441bf34c9eda2f3e0f22782d`。本交接提交仅更新文档，最新HEAD以PR为准。
- **实测**：Torch2.14.1+cu130 / CUDA runtime13.0.96 / NCCL2.30.7 / 官方Profiler实际v4；四Rank70个Collective实例匹配，每Rank553组GPU channel。单次短窗step p50约 **+6.1%～7.5%**，不宣称≤2% SLA。
- **测试**：本地DOC PASS；9项CPU fixture及真实trace解析PASS；GPU smoke和MULTINODE运行候选PASS；[代码/证据HEAD CI PASS](https://github.com/Zwhao0/GREYHOUND_online/actions/runs/39457160530)，仅DOC/CPU；最新交接HEAD检查见PR。主窗口已结束GPU实验，无本项目训练进程残留。
- **资源授权**：用户确认两台H800持续共享，允许本项目私有环境升级和有限测试，无需逐项重复申请。本轮只用私有venv，driver580.178.04/全局环境未改，未停止他人作业。

## 下一唯一动作

**等待 ChatGPT 独立审核 [Draft PR #13](https://github.com/Zwhao0/GREYHOUND_online/pull/13) 的最新HEAD、CI和实验报告。**不追加GPU轮次、不重验G0、不新增升级Gate、不自行merge/关闭Issue或进入G2。

审核时先读 [STATUS.md](STATUS.md)、Issue #9和实际 Draft PR/CI；需要技术证据再读 [G1-01实验报告](docs/G1-01-RESULTS.md)、[脱敏实测汇总](docs/evidence/g1-01-summary.json)、[逐键匹配](docs/evidence/g1-01-matches.json)。它们包含原始step数组、DSO/文件SHA、身份映射、资源收尾和回退，不在本文复制。

## 关键边界与导航

- 70个匹配仅覆盖观察键并集；精确drop/共同遗漏/全历史、绝对校时、step→Coll、root、原发/受害因果 UNKNOWN；Proxy未采。没有根因算法或在线服务，也未验证生产fail-open。
- 共享短窗方向性开销不等于稳定低开销；公开仅别名/统计/数组/哈希，原始私有日志按报告留存。禁止故障注入、主动诊断collective、生产改造、擅改驱动/停他人作业、发布机密或复制许可未明源码。
- 历史G0：[PR #5](https://github.com/Zwhao0/GREYHOUND_online/pull/5)微基准PARTIAL；[PR #8](https://github.com/Zwhao0/GREYHOUND_online/pull/8)单机DDP PASS/MERGED。历史版本不能当新版证据。
- 规则/阶段/技术按需读 [AGENTS.md](AGENTS.md)、[ROADMAP.md](ROADMAP.md)、[测量契约](docs/MEASUREMENT_CONTRACT.md)、[来源许可](docs/SOURCES_AND_LICENSES.md)。本轮实际使用GPT6 luna max做脚本/fixture/机械核对，GPT6.1 sol medium做ABI/映射审查；主窗口负责GPU与提交，代码预检不替代ChatGPT审核。
