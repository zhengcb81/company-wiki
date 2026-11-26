# StockInfoDLSimple 独立复审

2026-11-25，Windows。受审运行目录为 `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`，分支及本地远端跟踪引用均为 `v2-clean-rewrite@9b0c07c91a76789a09b458aaa796d8dfd2d1957a`。`src/`、`main.py`、`tests/`、`.github/` 和 `config.json` 无跟踪文件差异。已有未提交跟踪改动位于 `docs/plans/mb11-sid-2026-11-11/` 的三份规划文件。以下 `src`、`tests` 和 `main.py` 行号均指该 SID 检出。CWP 当前配置用 `-m src.company_wiki_adapter_cli` 消费 CN 公告，F4 实际设置在同一工作目录用 `-m src.feedback_owner` 执行 owner 操作。独立浏览器下载走 `main.py`。[CWP 采集配置](../../../../../../config/source_acquisition.yaml) · [S1 台账](../../../s1-p0-blackhole-plan.md) · [S2 设计](../../../s2-unified-logging-plan.md) · [S3/S4 台账](../../../../module-boundaries-2026-11-11/s3-s4-owner-rollout-20261125.md) · [S5 台账](../../../s5-verification-20261125.md)

| 项目 | 判定 | 核对范围 |
|---|---|---|
| S1 | **部分** | 独立入口配置文件日志已实际写入。既有测试证实 `get_current_page_info()` 的非预期异常会记录堆栈，并通过 `BrowserError.__cause__` 保留原错误。真实独立入口仍可把前向翻页异常当作正常末页，丢失根因并把截断结果结为成功，见 SID-01。 |
| S2 | **部分** | 独立入口有带 UTC 时间及 run/attempt 的启动和终态回执，F4 有请求始末与结算。适配器有稳定请求步骤、正常与错误投影、单次原业务输出及已有重投通道。正常内部步骤与副作用仍难按同一运行冷查，适配器预读或日志介质全失也有空窗，见 SID-02。 |
| S3 | **部分** | CWP 的版本化 JSON 子进程和 SID 的 API/浏览器运行边界成立。标题匹配已共享。仓内浏览器到下载 owner 的分页、下载返回值仍压平不同状态，已影响主入口结算，见 SID-01、SID-03。 |
| S4 | **部分** | 发布分支已有 Ubuntu/Python 3.10 快速 CI。名单覆盖旧分页读取、普通配置错、适配器单 JSON、预算和 owner 反馈。未覆盖真实独立入口的前向翻页按钮抛错、同 run 步骤串联、Windows 多进程轮转。 |
| S5 | **部分，定向修复已验** | `9b0c07c9` 与运行目录一致，S5 台账记录正式远端同版 CI、58 项定向及独审 9 项。本轮 Windows 复跑 S1/S5 共 9 项通过，包括实际子进程配置日志、拒写回退、单 JSON、消除根 logger 回落、旧流关闭、单进程轮转与脱敏。S5 文件回归成立，启动全链与故障旁路全失仍有 SID-02 所列缺口。 |

## SID-01（P1）翻页异常被结算为正常成功

- **复验方法。** 在两个独占临时根分别启原生 Python 子进程，调用正式 `main.main()`、`StockDownloader.download()` 和真实 `PlaywrightBrowser.go_to_next_page()`。配置为单证券、无栏位限制、`max_pages=2`、`max_retries=0`、文件日志 DEBUG。映射和启动、导航、链接、下载 I/O 使用本地替身，两页各给一个不同链接，落入临时输出的合成 PDF 均超过最小字节数。下一页 DOM 在第 2 页显式 disabled，失败组只把第 1 页 next 控件的 `click()` 换成抛 `PaginationClickError(RuntimeError)`。两个运行分别设置 `RESEARCH_FEEDBACK_RUN_ID=sid-pagination-ok / sid-pagination-fail`、`RESEARCH_FEEDBACK_ATTEMPT_ID=try-1`，另设隔离 `RESEARCH_FEEDBACK_STATE_ROOT` 和 `RESEARCH_FEEDBACK_DIR`。
- **观察。** 正常组落两份 PDF，故障组仅一份，两个原命令均 exit 0、stdout 0 字节，stderr 均含 `All tasks completed`。故障组的 stderr 和 DEBUG 文件都没有原异常类型，日志只打印第 1 页。以原根在新进程执行 `python -B -m src.feedback_publish reconcile --json`，两组均冷读原 run/attempt 的 `all_completed` / exit 0，pending 0。冷读已发布 sidecar 可见同一请求的 `action-started → ordinary-download-task=completed`，结算详情均为 attempted 1、succeeded 1、failed 0。独立入口没有机器 JSON，以上回执是公开冷读命令与 F4 投递证据。
- **根因。** `src/browser.py:545–555` 对末页控件不可用和抛异常都返回 `False`，异常没有日志。`src/downloader.py:515–529` 当作正常循环结束，`src/downloader.py:367–393,666–698` 只验已选中的文件与已登记的候选失败。第一页已有有效文件，足以通过此验收。`main.py:243–271,514–535` 按 owner 返回结算，于是错误传播成成功回执。源码还显示反向路径忽略 `go_to_last_page()` 的布尔失败，分页读超时继续使用一页默认值。两项是本轮未另跑的分支。位置见 `src/browser.py:570–591,644–650`、`src/downloader.py:531–547`。
- **后续验收。** 同一离线夹具分别覆盖明确末页、触达配置上限和次页控件抛错。异常组保留已落原件，结果表达覆盖不完整，原进程非零并冷查同一尝试的原错误类型、页号及当时已经执行的下载数。反向跳转须验证确实抵达计划页；检查重试或重投不重复已确认的副作用。

## SID-02（P1）已有请求回执与正常、启动失败的步骤链尚未连通

- **独立入口。** `main.py:441–457` 在解析参数前创建运行身份。实际正常对照从新进程找到了原时点和终态，独立侧车另有相同键的 task started/completed。真实页、链接和下载主要是 `src/downloader.py:231,288–310,519–527,577–628` 的文本日志，正常对照的文件中没有 run ID。并行或重试时无法仅用原 run/attempt/step 区分页和下载。F4 事件的 version 为普通入口 `ordinary-cli-1.0` 或适配器 `1.3.0`，所查日志及回执没有发布 Git 标识。`main.py:205–228` 在受保护的下载步骤及其启动事件前构造 downloader，`src/downloader.py:46–49,204–205` 初始化重试日志会建立目录。该目录拒写即可让任务在启动回执之后抛出，属源码分支，未另做故障注入。
- **CWP 适配器。** 当前 `config.json` 未提供 `logging`，生产配置也未传 `--config`，实际走默认 INFO、`logs/downloader.log`（相对 SID 工作目录）。明确 `log_to_file=false` 会保留机器静默行为，相关拒绝应由 owner 的投递或运行回执承担查询。已配置日志目的地打不开时改用 SID 状态根的 `logs/adapter.log`，但双根都打不开时静默返回。文件处理器运行时的写失败告警在 `console=False` 时亦关闭；反馈写错若也无可用介质，不会产生可见本地诊断。原 JSON 和退出仍独立保留。位置见 `src/config.py:11–28,48–52,99–109`、`src/company_wiki_adapter_cli.py:266–315`、`src/logger.py:78–89,140–161,188–212`。
- **启动与主要副作用。** 适配器先读取配置并启动日志，再读 stdin，等解析出请求或 JSON 拒绝才写 `action-started`。stdin 自身读失败会以 `unbound` 进入适配器异常日志，原身份未被绑定；若在此前被强停，也没有这条 owner 启动事件。正常仅有请求始末，能从侧车看到候选 ID、取件状态及条件性预算汇总，稳定合成请求键可以和错误对照。身份解析、各 API 页、传输及暂存的关键结果没有各自同身份的步骤事实。公开 `feedback_publish reconcile` 只读运行回执和待投条目，适配器的 `command_sink` 未建立 `runs/` 回执。强停在启动前或目录投递成功后，仅靠该命令无法重建此入口。位置见 `src/company_wiki_adapter_cli.py:309–376,391–429,482–525`、`src/feedback_publish.py:198–218,516–523,599–622,804–845`。本段为限定源码判断，未另行执行强停。
- **后续验收。** 复用已有 owner 启动及回执机制，在读输入前建立原身份，按同一键记录适用的身份解析、各页覆盖、外部调用与暂存结算，保留配置或安全请求引用及版本。以公开冷读验证正常、首阶段强停和日志拒写，区分已尝试、已落地及未知效果。保留显式禁用文件日志及原 stdout/stderr 协议，同时能检出持久化失败、继续原业务并按原身份补投。

## SID-03（P2）跨仓边界已立，内部传输契约仍需补型

- **已成立。** CWP `JsonCommandAdapter` 使用配置目录中的 SID 子进程，严格检查子进程的 JSON、schema 及 adapter name/version，拒绝时消费稳定代码和可重试字段。SID `_build_adapter` 实际创建 `StockInfoCompanyWikiAdapter(None)`，用 `OrgIdResolver` 和 `CninfoAnnouncementClient`，没有启动 legacy downloader、Playwright 或 CWP Python/SQLite。适配器的 `StockDownloader` 注解及可选 `downloader.cleanup()` 属类型与兼容路径。两端标题匹配共用 `disclosure_matching`。位置见 CWP `src/company_wiki/source_catalog/adapter_process.py:376–405,471–531`，SID `src/company_wiki_adapter_cli.py:107–130`、`src/company_wiki_adapter.py:23–27,283–392,394–410,513–567` 和 `src/downloader.py:15–17`。
- **剩余具体耦合。** 上层验证依赖浏览器给出的布尔值。SID-01 已验证 `False` 可丢失页状态，`src/browser.py:516–541` 的下载失败也经 `src/downloader.py:624–644` 成为通用 `download_file returned False`。父子之间无可传递的原操作、异常类型和代码位置。另有 `main.py:29–30` 单仓路径插入，普通 script 入口仍在本仓内，当前未观察到跨仓导入后果。可用上述浏览器夹具和现有纯 API 正常/异常收据对照验收 owner 边界，两条实际入口分别保留各自既有输出。

## S4/S5 验证范围

发布 CI 使用显式测试列表，包括 `test_s1_logging_and_browser_errors.py`（直接调分页信息读取）、`test_s5_adapter_logging.py`、adapter CLI 与 budget、feedback observation/owner、旧清理 stderr 顺序和独立配置异常。清单不含本轮发现的两页真实调用链或同仓状态边界静态约束，Ubuntu 也无法证明 Windows 文件占用和并发轮转。现有用例确实保留旧错误格式和换文件的旧流关闭，单进程轮转归档受限。先把 SID-01 的实际入口对照纳入 CI，并对 SID-02 的原身份冷读/诊断失败补行为验收，再评价全入口覆盖。现有 `RotatingFileHandler` 的 Windows 双进程争用未在本轮验证。位置见 `.github/workflows/ci.yml:3–35`、`tests/unit/test_s1_logging_and_browser_errors.py:13–48`、`tests/unit/test_s5_adapter_logging.py:20–54,58–159`。[同版 CI](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/45699176729)

离线复验和 9 项定向测试只使用独占临时根。未启动真实浏览器、访问 API、下载原件或修改 SID 的代码、配置、运行数据与 Git 状态。
