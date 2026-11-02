# D3 解耦独立验收（2026-11-02）

**工程验收通过；提交、推送及远端 CI 由 ROOT 按实际版本补记。** 本审查未实施生产改动，未调用收费服务，未见未关闭的生产 P1/P2。验收覆盖当前公开的来源、采集、读原文、读摘要和消费者接口。

| 验收点 | 已核对结果 |
|---|---|
| 依赖边界 | RF 80、FF 19、StockWiki 213、AUDIT 19 个当前运行 Python 文件静态检查，无 `company_wiki` 或 `company_wiki.*` 实现导入。FF 六操作通过统一连接适配器；RF 原文与摘要命令分别可替换。 |
| 本仓隔离 | RF 712 通过；FF 946 通过、76 子测试；StockWiki 110 通过；AUDIT 43 通过、56 子测试；ET 95 通过。FF 三项 skip 是冻结现场 master 样本及 Windows symlink，StockWiki 一项是 Windows 不适用的 POSIX detached-session；这些 skip 未计入组合通过。 |
| 当前组合 | ROOT 39 通过，零失败、零跳过，pytest 124.35 秒，临时根已恢复。含当前 CWP golden 与上一 RF 便携示例的双消费者反例、三进程复用、真实 ET worker 与假 HTTP、真实入库和 verified-open，以及不同 cwd 和命令位置下的原文/摘要替换。 |
| 预算与协议 | 显式 22 MiB 允许大于 17 MiB 原件，真正 16 MiB 超额受控。复用不重下载；本地入库不重复扣网络额度。业务非零返回与未完成 stdin 分开。取消 JSON 重编码一致性检查；实际字节 SHA/大小、身份、期次和核心版本依然验证，可选 `extensions` 不升级来源证据。 |
| 真实只读 | 已有 A 股半年报原件 1,216,470 字节通过 RF 公共 reader 实读，SHA/期次匹配；该探针的配置和库 hash 前后一致，无下载、无模型调用。 |
| 部署 | canonical 定点安装 RF 6、FF 8 个选定文件至三个逻辑入口，别名物理去重，配置 SHA 保留，重复 apply 零写。三个逻辑入口均在新进程中执行 RF 真 reader 与 FF 显式连接，零 provider 下载，临时根恢复。 |

初审发现的缺失 helper、残留 FF 真 CWP 测试、Windows `sh` 执行环境异常、仅使用 RF 便携 golden 四项均已复核关闭。RF 25 个整文件搬迁前后的全部断言 AST 内容和顺序一致（共 487 条）；当前节点在 ROOT 实际执行，旧 canary/观察窗/签收断言留作显式历史重放。常规 CI 独立运行；ROOT 组合有单独入口，无需每次提交重复运行多仓链。

版本绑定已复核 `version-supplement.json`：39 例通过后的工程观察补齐了 StockWiki 应用目录和安装说明/工程配置覆盖，未更改已测生产行为。本报告的机器记录附三项 StockWiki 实际源码 SHA，以及所读测试/部署证据 SHA。已有 WIP 字节与模式得到保留：RF `daily_alert.jsonl` 的起始 8,007 字节 SHA 匹配，旧任务另外追加 264 字节，未恢复或暂存该文件。其余四个 WIP 保持原样。

RF 当前技能、计算入口、提交钩子、推送钩子和 CI 不以该旧 daily canary 作为运行或发布许可。历史定时诊断仍在运行，可能追加告警，并通过旧观察器维护其历史周期账本；这是单独的历史调度残留，未宣称已退休。

T4/SEM、RF ghost/期次、AUDIT attempt、真实摘要/缓存恢复/RF采用及公司循环仍按 PWF 后续推进；本次没有用架构通过替代这些业务验收，也未提前派发模块施工包。
