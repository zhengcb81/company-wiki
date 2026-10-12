# W07-FF-PERF 已接收 — ROOT 入口

本包已完成，不再开工。当前发布事实以 `publication.json` 为准：FF main/origin/main 64b4d29、精确 CI 38170433893 success；ET main/origin/main d0ac42c6，没有配置 CI workflow。company-wiki 的 PWF 在本地提交，远端仍待 W04 原有18失败修复；不绕过钩子。

## 证据

- `acceptance.json`：运行大节点快照；其中 publication_status=pending 是当时发布前事实，最终发布看 publication.json。
- `freeze.json`：只读范围、固定代码和初始 WIP/配置 metadata；真实密钥只 stat。
- `offline-evidence.zip`：两个 ROOT attempt 的合成 request/response/fixture/usage 原始留证，共490060字节。最终41PASS99.9624秒，首轮28PASS13PARTIAL由ROOT逻辑别名数过约束导致，原失败保留。
- `installation.json`：只有两运行文件×两物理副本，其他文件元数据保持；两个独立进程各5边界通过。
- `cleanup.json`：ROOT临时工区、运行副本和测试输出已清理；作者树、分支、原件和其他 WIP 保留。

## 可重复的只读证据重放

```powershell
python C:/Users/郑曾波/Projects/company-wiki/.planning/w07-ff-perf-reception/replay_evidence.py --ff-project C:/Users/郑曾波/Projects/filing-fetch
```

需运行已接受的 FF 代码及 Python；仅创建独立临时目录，按未改 oracle 验 request/response/fixture/usage 哈希，然后自动恢复。期望41 cases、finding_count=0。它重放留证，不冒充再次下载或再次打开已清理的合成原件。

其他 prepare/fix/implement/capture/finalize/sync/update/cleanup 脚本是一次性施工记录，**不要重跑**，可能依赖已清理工区、预状态断言或更新计划。不按旧作者 STOP/READY 或历史 snapshot 重新派工。

下一步在母目标恢复后做 W04 召回共因→G2真实摘要/RF消费→G4原三家四独审→G5新三家和指定公司循环；RF另有五组组合测试缺口。离线工程通过不认证真实供应商可达或研究结论质量。本包0真实 provider/LLM/费用，没有新许可/签收门。
