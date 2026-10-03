# G-C 来源消费能力收尾

## 正式主线

| 仓库 | 提交/状态 |
|---|---|
| company-wiki producer | `a640400` 已发布，Actions37113358995绿/57秒；此后B1/source维护不改wire |
| StockWiki master | `ae0b3e3030d18ca619d44361b2cf673d73bb7e21`，普通三方合并`4c3334e`，无remote |
| revenue-forecast main/origin/main | `6fb2def709d13bda9cfada7ecf62bfc0e3744ae2`，普通推送/本地快进 |

RF [Actions37119502901](https://github.com/zhengcb81/revenue-forecast/actions/runs/37119502901)成功：verify **2m40s**，real-roots **1m46s**。正常pre-push快速门全部通过，无bypass。rf-impl4处已有`.planning/...`未提交文件前后完整SHA相同；fcap未修改。StockWiki其他owner W05 `aa3c6e6`是merge祖先且改动保留。

## 节点证据

- RF主节点89 passed/87.49秒，含年报P01/英文TXT T01正式producer→持久包→CWP CLI→RF CLI、原reader与失败；最终局部Windows20 passed/2POSIXskip（17.10秒）、真实Ubuntu16 passed/1Windows线程专属skip（16.85秒）、正式WinCLI3 passed（5.54秒）。六模块两平台mypy、全Ruff/host/unique与普通commit hooks通过。
- StockWiki真实节点14 passed/131.45秒，含招股P04/IR P07与迁根/hash/as-of/身份/期间/skip；P07 needs_review保留。局部Windows58 passed/1POSIXskip，真实Ubuntu42 passed/1WinSkip。一次全仓785通过收据复用，不重复跑。master合并相关回归 **172 passed/1POSIXskip，18.74秒**，Ruff通过。
- 原文SHA/mtime和生产fingerprint在真实文档节点前后一致；隔离run roots均清理恢复。合并测试根`C:\cwt\sw-gc-merge-20261003`、发布根`C:\cwt\rf-gc-publish-20261003`已删除，无本线遗留进程。

## 生命周期修正与能力边界

真实RED暴露父退出后孙持pipe造成超时失效/后台线程拖住宿主。Windows用先挂起→Job绑定→公开ResumeThread；POSIX用session/processgroup和nonblocking selector，无背景pipe线程。执行/drain共用deadline，回收一个共享1秒预算。POSIX主动setsid后代不承诺终止，但本地pipe关闭、宿主有界具名拒绝；不扫描/kill无关进程。

入口：StockWiki `source-read-narrative`→自有来源DTO；RF `scripts/narrative_source_preparation.py`→自有来源context。都显式opt-in、pathless来源引用/原语言摘要、不写研究结论/不隐式下载或LLM fallback。能力签收范围为来源消费；不代表生产模型/无限daemon/默认weekly已运行。Worker继续paused，N4尚未实施。
