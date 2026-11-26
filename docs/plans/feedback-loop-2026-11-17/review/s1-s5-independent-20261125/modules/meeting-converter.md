# MeetingConverter 独立复审

现场目录 `C:/Users/郑曾波/Projects/MeetingConverter`，HEAD 与本地 `origin/master` 均为 `fa1f840d37e91df3fc79006dff1b19e4afdd3d6b`。已存在的 `.coverage`、三份计划记录和 `.mimosa/`、`.workbuddy-ai/` 之外，状态清单无相关源码变化。两条离线对照直接执行现场源码，只在独占临时根使用合成音频字节、配置和 HTTP 替身。实际网络、模型、录音外发和费用均为零。发布和同 SHA 的 Ubuntu CI 结果来自已存台账，本轮未联网重查。 [复审口径](../review_contract.md) · [S5 台账](../../../s5-verification-20261125.md)

## S1–S5 判定

| 项目 | 判定 | 已核对范围与缺口 |
|---|---|---|
| S1 | 已验，限 S1-01 | MiMo 模块 logger 已定义。实测重试与耗尽均保留 `IncompleteRead` 归因，批处理退出 1，合成秘密未进入 stdout、stderr、F4 或本地日志。`OperationFeedback.flush()` 仅捕获 `Exception`，历史 `KeyboardInterrupt` 吞没已有回归断言。本轮未重注入中断。异常退出与重复 POST 风险见下文。 `engines/mimo.py:32,214–256`、`core/feedback.py:1079–1097`、`tests/test_s1_logging_resilience.py:16–68` |
| S2 | 部分 | 两组实际 CLI 的 F4 开始、产物/失败与终态可用原 run、attempt、step 冷查，两次返回一致。代码与现有强停回归表明引擎中强停保留 `unconfirmed`，终态后、ready 前强停仍可查成功，均保持 `cost_unknown` 且不重跑。强停用例本轮仅审源码与既有证据。此次正例没有本地日志，反例本地条目没有 step、输入引用、版本及 HTTP 尝试序号。 `core/feedback.py:984–1002,1045–1077,1261–1298`、`feedback_owner.py:174–187`、`tests/test_f4_ordinary_failures.py:631–679` |
| S3 | 部分 | 生产上下文来自 MC 的 `companies.yaml`。定位和板块同源，原 CWP `graph.yaml` 自动读取已移除。`config.py` 是默认值与配置读取 owner，旧 `translator.load_config` 是兼容导出。对外使用公开 JSONL/CLI，MC 自有 SQLite 由 `feedback_owner.py` 持有。仓内仍按具体 `FallbackEngine` 类型接收降级事件，且反馈记录、交付、启动、步骤投影集中在 `core/feedback.py`。 `company.py:14,43–62,99–128`、`config.py:80–112`、`feedback_owner.py:115–187,319–352`、`core/pipeline.py:22,340–352` |
| S4 | 部分 | 推送和主线 PR 的 CI 在 Ubuntu、Python 3.13 执行 `python -m pytest tests/`。日常选择器收集 S1、FFmpeg、配置、真实 CLI 的 F4、轮转与强停回归。CI 配置断言守住收集范围，未发现同仓依赖的结构门禁。已有 MiMo 回归只测读取结束后的坏响应，本次读取中途断流及成功的本地生命周期均未被拦截。Windows 宿主诊断隔离有已有专项证据，日常工作流没有 Windows job。 `.github/workflows/ci.yml:3–26`、`tests/test_ci_workflow_config.py:92–110`、`tests/test_s2_mimo_diagnostics.py:92–120` |
| S5-03 | 部分，原定向修复已验 | 现场 `b26707a`、`fa1f840d` 已生效。正例省略 `--engine` 时实际选择配置的 MiMo。现有公共 CLI 回归覆盖显式引擎、Whisper 模型/设备/精度和语言覆盖配置、显式 `auto`，以及坏翻译配置保留原文。按既有文档，`translate_max_retries=0` 表示首请求一次，布尔值拒绝。FFmpeg 静音检测与切片非零及空切片均抛错，原件保护和 HTTPError 退避前关闭有定向断言。完整读取坏响应只 POST 一次，读中断仍重复。 `transcribe.py:154–172,194–205`、`config.py:60–77,120–131`、`CONFIG.md:77`、`audio_utils.py:109–167`、`tests/test_config_cli.py:154–210`、`tests/test_audio_utils.py:127–151`、`tests/test_s2_mimo_diagnostics.py:92–120` |
| S5-05 | 部分，转录失败试点已交付 | `transcribe.main` 安装 1 MiB 轮转本地日志，保留两个历史文件。既有回归覆盖坏输入、目录被普通文件占据及宿主无 stderr。启动器只有转录入口接入，批处理直接调用、诊断/对账 CLI、公司管理与引擎比较均缺全生命周期本地日志。当前仓源码无独立生产 worker 入口，宿主启动/强停有 F4 证据，宿主 worker 自身的日志覆盖本轮未证。 `transcribe.py:60–67`、`core/local_diagnostics.py:24–27,58–109`、`tests/test_f4_ordinary_failures.py:205–261`、`feedback_owner.py:319–348`、`company_manager.py:188`、`compare_engines.py:101–108` |

## 关键发现与验收

### P1 · MiMo 已返回 HTTP 200 时，正文截断导致同一上传提交三次

正常入口为 `transcribe.py` → `run_batch()` → `transcribe_one()` → 真实 `MiMoEngine` 和输出 writer。复现时把配置和公司 YAML 指向临时根，用合成 `.wav`、配置 `transcription_engine=mimo`、`--no-translate`。仅替换时长探测、退避与 `urllib.request.urlopen`，后者在两组均返回状态 200 的响应上下文管理器。对照 `read()` 返回合法识别 JSON，反例在 `read()` 抛出 `http.client.IncompleteRead`。替身记录请求方法和去标识化的相同载荷计数。两个已退出的子进程分别用公开 `feedback_owner.py --db <临时库> --sidecar-dir <状态根>/observations reconcile` 以原 `action-started` 发起两次独立进程冷查。

| 对照 | 转录退出 | 替身 POST | 原文与 F4 | 冷查两次 | 本地轮转文件 |
|---|---:|---:|---|---|---|
| 完整 200 | 0 | 1 | 原文存在，`published_current`，ready 存在 | `succeeded / cost_unknown` | 无文件 |
| 200 后 `IncompleteRead` | 1 | 3，三份载荷一致 | 无原文，`transcription_failed`，ready 存在 | `failed / cost_unknown` | 三条 `mimo_request / IncompleteRead`，一条 `batch / EngineError` |

冷查沿用原 step，两次机器 stdout 字节一致，未创建回执库，也未新增请求。反例的最后失败收据和原因正常，风险出在一次业务执行内。`response_received` 在 `resp.read()` **之后**才置真，故本应按已发出/费用未决处理的读取错误被当作可重试，最少形成两次额外提交。实际供应商计费未知。验收应在公开 CLI 固定已收到响应头后分别注入正文截断与超时，断言同一请求仅提交一次、原因可冷查、用量继续未知。已有完整坏响应的一次提交和经确认能安全重试的故障应继续通过。 [MiMo 判定分支](<C:/Users/郑曾波/Projects/MeetingConverter/engines/mimo.py:209>) · [F4 冷查](<C:/Users/郑曾波/Projects/MeetingConverter/feedback_owner.py:174>)

### P1 · 轮转日志无法单独还原成功或中断前的外部动作

本地 handler 延迟打开且仅接 `record_failure()`。正常运行的开始、成功、输出提交和中途强停只依赖 F4 或进程 stdout，批次中同一 run/attempt 的多份输入无法凭本地失败记录定位到各自 step。F4 `note_engine_started()` 的观察进入缓冲，强停时的持久 `action-started` 只能证明原操作开始，无法区分是否已开始 HTTP 传输。FFmpeg 两阶段错误把退出码写入 `EngineError` 文本，本地投影只留下类型、因果和源码帧，结构化阶段与子进程退出码仍缺。反馈 recorder 外层的异常分支还经根 logger 记录完整 traceback，普通 CLI 根 logger 指向 stdout。此分支的路径/异常文本暴露为源码发现，本轮未额外注入。

验收应从实际入口读回同一 run/attempt/step 下的开始、关键步骤、已知外部动作和终态。加入多文件批次、HTTP 替身强停、FFmpeg 非零、日志及反馈写失败的代表性场景。保持业务输出、退出与公开对账的机器 stdout，按实际可知的派发/用量状态冷查。公司管理、比较和反馈控制等当前入口需各自验证其日志接入。 [日志写入器](<C:/Users/郑曾波/Projects/MeetingConverter/core/local_diagnostics.py:70>) · [引擎观察缓冲](<C:/Users/郑曾波/Projects/MeetingConverter/core/feedback.py:854>) · [反馈异常分支](<C:/Users/郑曾波/Projects/MeetingConverter/core/feedback.py:1088>) · [CLI 根 logger](<C:/Users/郑曾波/Projects/MeetingConverter/transcribe.py:114>)

### P2 · 备用引擎具体类型依赖仍可漏报降级

`_drain_engine_events()` 先做具体类检查。另一种实现即使提供同形的 `drain_engine_events()` 和主引擎失败事实，只要未继承该类型，成功产物也会丢失已发生的降级及其原因。现行生产工厂返回原 `FallbackEngine`，因此该缺口属于替换实现的实际行为边界，当前默认工厂路径仍会投影降级。验收使用经公开转录流水线注入的同形引擎，验证仍出现 `published_degraded` 与主失败归因，同时保留无事件引擎的正常发布。 [类型分支](<C:/Users/郑曾波/Projects/MeetingConverter/core/pipeline.py:340>) · [生产工厂](<C:/Users/郑曾波/Projects/MeetingConverter/engines/factory.py:58>) · [降级状态回归](<C:/Users/郑曾波/Projects/MeetingConverter/tests/test_f4_ordinary_failures.py:498>)
