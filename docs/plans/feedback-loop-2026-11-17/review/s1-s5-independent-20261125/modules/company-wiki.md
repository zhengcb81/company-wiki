# company-wiki · S1–S5 独立复审

2026-11-25。F4 记录的 CWP 运行目录为 `C:/Users/郑曾波/Projects/company-wiki`。本次读取该目录的 `master` 和本地 `origin/master`，两者均为 `c918a402e3cf5a58ed11c27413f92fd1f50ec256`。S5 源码发布点为 `88f10bf962aa03506bb210063696eba5b9f53b19`，两提交间 `src`、`tools`、`tests`、工作流和 `pyproject.toml` 无提交差异。工作树另有 `src/company_wiki/source_catalog/read_budget.py` 在途修改。实测从 `88f10bf96` 的 Git 归档启动新进程，使用 Windows Python 3.14.2、独立配置和状态根、本地合成输入。未读取生产作业或重启宿主。远端 CI 和实际排程启用来自现有收据，本次未联网重查。真实下载、模型请求、重发和费用均为零。[S5 台账](../../../s5-verification-20261125.md) · [F4 排程发布](../../../f4-rollout.md)

## 逐项判定

| 项目 | 判定 | 已复验范围与差距 |
|---|---|---|
| S1 | **部分** | 既有 F4 同步子进程错误、OCR stderr 捕获、摘要激活异常与旁路脱敏补修有定向证据。真实 AUTO spawn 的 stdout、stderr 和启动 traceback 仍能留下合成 Bearer 明文。 |
| S2 | **部分** | 正式 CLI 的装饰器提供失败轮转及 F4 引用。在真实 `source-read` 缺配时机器 stdout 为空、stderr 单回执，隔离状态可冷读原异常。普通成功、部分已封装失败、AUTO 维护、worker 领取前和定时任务无完整生命周期证据。 |
| S3 | **部分** | CWP 产品、F4 工程调度及公开跨仓资料边界在已验路径职责分明。配置入口已移入产品包，采集编排有 stages 端口，SQLite 读事务及租约共用事务层。AUTO 冷查仍可被构造器带入可写路径，来源注册和 assertions 仍直接依赖物理 SQL。 |
| S4 | **部分** | 快速 CI 实际纳入产品测试与扩展后的边界合同。新扫描器能识别已知 owner、F4、反射字面量和潜在导入环。真实同包 SQL 穿透、动态配置导入、worker 脱敏和无留痕的成功路径可以通过现有门禁。 |
| S5 | **部分** | 已发布的异常类别、F4 后台包装、轮转、边界扫描及 AUTO 抽取都有可定位的代码和回归。11 个 CLI 的历史发布证据属于进程外失败切片。现场只读复核范围内仍存在表下所列证据缺口，全入口、仓内松耦合及目标提交的宿主冷查待验。 |

## 关键发现及验收

### P1 · 开始、成功和关键步骤缺少同一运行的持久轨迹

用公开 `company_wiki.source_catalog.source_reader_cli` 读取真实登记的合成 TXT 原件。退出 0、stdout 字节与原件一致、stderr 回执为 `ok`，本地轮转、观察、诊断均为 0。换成不存在的 `--config`，退出 2、stdout 为空、stderr 保持一条 `reader_unavailable` 回执，新进程冷读得到一个 `FileNotFoundError`、原 run/attempt 和一个 ready。诊断仅含 `attempt_id, exceptions, owner, package_version, reason, run_id, step_id`，包版本为 `0.1.0`。这个失败无来源/请求/配置引用、事件时间与精确执行代码版本。轮转行头提供 UTC 时间。成功 stdout 与 stderr 由调用方保存时可以证明这一笔读取，无法从 owner 持久状态重建普通调用的步骤。

`src/company_wiki/runtime_feedback.py:249–284` 在解析前只在内存绑定身份，结束时自动记录非零和异常。 `runtime_feedback.py:288–310` 只投影失败成员。 `runtime_feedback_values.py:86–115` 固定 F4 身份与错误详情。 `source_catalog/source_reader_cli.py:67–130` 有配置加载、找引用、验真、交付字节四个实际边界。部分业务有独立的原生账本，AUTO 已领取的工作有 job/attempt 和提交后待投递行，外层 F4 `intake.run_observed` 也能为明确受监督进程写 pending。普通入口和 worker 预领取未自动获得这些证据。

验收应让公开入口在有效状态根下持久绑定 run/attempt，保存可安全引用的配置指纹、输入引用、执行版本、必要步骤和终态。测试正常读、拒绝、已知失败及入口早期强停，用公开只读路径按原编号查询。F4 继续投影已有故障协议，成功的流水留在 owner。保持历史 F4 身份和已冻结 payload 的幂等语义。

### P1 · AUTO worker 启动原文、强停和后台轮转落差

真实 `AutomationSupervisor` 的 P1 spawn 加载本地 `module:callable` 替身。在领取前，替身 stdout 写一行合成 Authorization Bearer，随后抛带同一合成值的 `ValueError`。子进程退出 1，合成值在两个子日志中均可读，multiprocessing 的上层 stderr 也有原文。父进程只给出 `ChildProcessFailedError`。冻结的 AUTO 库含 0 job、0 attempt、0 notification，重启公开 `feedback-flush` 得到 `published=0,deferred=0,unavailable=false`。改用提前写测试标识后挂起的替身，父调用 `terminate_worker("mixed-1")` 强停，子进程退出 -15，两份尾日志均为空，同一冷查结果仍为 0。两组都发生在预领取阶段，无业务模型或费用状态。

`src/company_wiki/automation/worker_process.py:81–120,145–195,221–231` 直接编码 stdout/stderr 原文并重抛异常，未复用脱敏层。 `automation/supervisor.py:142–150,188–203,242–271` 保存进程槽、状态和退出码于内存，重启预算失败只含槽名。 `automation/worker.py:158–182,239–260` 的事务恢复从实际领取起生效。现有 F4 后台包装在带 `CWP_F4_ERROR_LOG` 时已保存目标模块导入失败、argparse 拒绝及强停前完整行，覆盖另一条启动路径。

验收用正常 supervisor spawn，保留启动身份与实际退出，喂入分片、跨行合成凭据验证任何继承 stderr 及诊断文件都无原文。分别在加载工厂前后、领取前、领取后及事务提交后强停，确认原身份可查、后置补投幂等、预算/作业计数准确。保留已领取尝试的 SQLite 回归。启动失败由运行 supervisor 的 owner 留证。

### P1 · 可读机器失败存在，原异常或介质故障仍丢失

- `narrative_batch_cli.py:52–71` 用单字符 `{` 请求触发真实 `JSONDecodeError`，退出 1，stdout 正常返回 `NARRATIVE_BATCH_INVALID_REQUEST`，数据库未创建。冷读一个 ready，理由只剩 `exit:1`，`exceptions=[]`。同文件 :73–100 的执行异常在 `except` 之后才交给使用 `sys.exc_info()` 的 `document_results`，失去异常对象。验收应在原捕获边界绑定安全链和位置，分别用不存在请求、坏 JSON、受控执行异常和合法拒绝比较冷读机器结果。
- 真实 `automation.cli feedback-flush --db <坏 SQLite>` 退出 1，stdout 回执明确 `InvalidDatabaseFileError`，原库字节一致。本地轮转、ready 和诊断皆为 0。 `automation/cli.py:137–170` 常规路径未接入运行记录。验收增加原库损坏、新进程冷查、日志失败及健康无待投递的路径，保持本有维护返回和数据库只读语义。
- 用文件阻断 `RESEARCH_FEEDBACK_OUT`、`RESEARCH_FEEDBACK_DIR` 和状态根后，坏配置 `source-read` 的退出及机器 stdout/stderr 与对照逐字节一致，stderr 仍仅有机器回执，诊断介质失效没有可用告警。 `runtime_feedback.py:60–67,192–199,219–245,263–267` 把轮转放在同一故障域，且关闭写失败 stderr。Windows 排程走 `tools/feedback_loop/install_recovery_task.ps1:15–24` 的直接 `pythonw -m tools.feedback_loop.local_host … recover --save-result`。同一模块用合成坏 settings 启动时，持久结果只有 `finished_at,error_type,errno`。再让结果路径不可替换，原退出 1 与机器流一致，持久结果与轮转均为 0。 `local_host.py:704–718,753–765` 和 `diagnostics.py:103–120` 解释了故障区。验收应验证诊断介质跨故障域或外层监督者可观察的独立中断信号，并逐字节校验只有一条 stderr JSON 的入口。

### P1 · 冷计划依赖可写构造器，来源服务依赖物理存储形状

- 公开 `automation.cli plan --db <不存在于已有父目录>` 标称只读，实测退出 0、`events_planned=0`，并创建 SQLite。正控为同一未建路径上的 `feedback-flush`，返回 `automation_database_missing`、退出 1、零写。 `src/company_wiki/automation/cli.py:53–68` 把只读规划交给默认迁移构造器，见 `automation/store.py:697–723`。运维可把错误路径当成合法空任务库。让公开查阅使用明确已有库或只读输入，验收空库、缺库、老库、错库的区别及零写。
- `source_catalog/canonical_writer.py:396–418,776–822` 调 `catalog.store` 并直接按 `documents`、`locations` 表与状态更新和查找，`source_catalog/assertion_service.py:401–424,470–481,543–555` 在服务层编写写入投影与恢复 SQL。字段、索引或存储后端演进需要跨写入/恢复调用方同步修改。保留注册后重放、断点恢复、同一事务与并发验证，将物理查询和校验收敛至具名存储端口。对真实 `canonical_writer.py` 跑当前扫描器得到 0 违规，说明这条责任分界需要行为测试或更细的 owner 声明。
- S5 已抽出 `automation/store_transactions.py` 的公共租约/行解码，`narrative_run_store.py:26–27` 经它取 gate 与 attempt，`store.py:1315,1333` 仍在共享事务内调用叙述投影。共用 SQLite 原子性是既定业务约束。余项包括 `narrative_run_store.py:514–528` 依赖 `migrations._open_connection`，以及 `narrative_model_extractive.py:180,221` 与 `narrative_model_scoped.py:252,298–305` 的实际私有调用。DU 的 geometry 指纹在读取组装层完成，`document_understanding/structure/relations.py:247,307–344` 的 `builder._budget` 是结构域内文件实现，和宣告独立职责的反向导入影响不同。
- 正式公告 CLI 由 source_catalog 拥有。历史 `source_contract/announcement_collector.py:23–38` 仅在请求旧收集函数时加载真实实现，纯 receipt 值仍独立。它具名列在兼容白名单。F4 `host/intake/local_host` 是包含同机捷径的潜在运行图，`host.py:23–52` 的延迟本机路径实际需要另一层配置；当前证据只证明依赖链，未复现导入时崩溃。

### P2 · 当前 CI 和扫描器能防住部分退回

`.github/workflows/ci.yml:30–42,65–82` 在 Ubuntu/Python 3.12 运行 `tests/unit` 和快速合同，`tools/pre_push_gate.py:88–113` 列出边界合同。独立 Windows 定向复验覆盖源读故障、F4 目标导入/强停、轮转和分诊异常类别。既有 worker 用例覆盖原 lease/恢复和尾段上限；`tests/unit/test_automation_supervisor.py:76–107` 的尾段用例没有标准流凭据和领取前强停断言。

运行 `LayerBoundaries(src, feedback_root=tools/feedback_loop).runtime_import_cycles()`，本版扫描 535 个模块、16 组潜在 SCC，含 source_catalog 两组各 9 文件、叙述模型四文件、公告兼容三文件、DU 结构八文件及 F4 三文件。取同一个共享模块路径供扫描，`importlib.import_module("company_wiki.source_catalog.store")` 被报告为共享层访问运行 owner，`importlib.import_module(os.environ["CWP_AUDIT_MODULE"])` 无边和无违规。扫描器明确限于静态可解析名称，真实 `worker_process.py:221–229` 的配置信任边界需要业务合同。SCC 用例检验排序与类型依赖排除。扫描器既有覆盖及差距来自 `tests/support/layer_boundary_scan.py:161–215,370–408` 与 `tests/contract/test_layer_public_boundaries.py:379–395,416–486`。潜在 SCC 有延迟和兼容分支，不能等同 16 处运行事故。

## 复验条件

- 上述模块命令在 `88f10bf96` 归档中执行，`PYTHONPATH` 指向归档的 `src` 和 `tests`。两类状态环境都指向独占夹具，清除继承的 `RESEARCH_FEEDBACK_*` 和 `CWP_F4_*`，再显式给定测试 run/attempt。原件复用 `tests/support/sr_cwp_fixtures.py` 的 `build_catalog` 注册 `annual-report.txt`，以其 `document_id/source_id/content_sha256` 调读。配置损坏单用不存在路径或合成坏 JSON。阻断写入用普通文件替代目录或用目录替代应被替换的结果文件。
- Worker 通过 `AutomationSupervisor(SupervisorConfig(..., profile="P1", runtime_factory_path="audit_worker:crash", runtime_options_json="{}", compute_job_types=("audit.compute",), model_job_types=("audit.model",), max_restarts_per_slot=0))` 启动。工厂只打印合成头并抛错，或者在领取前触碰隔离标记并等待强停。通过 `children()`、子日志与新进程 `python -B -m company_wiki.automation.cli feedback-flush --db <隔离库>` 比对。测试父脚本需用 `if __name__ == "__main__"` 保护 Windows spawn。
- pytest 复验覆盖 `test_s1_p0_logging_blackholes.py`、`test_owner_runtime_feedback.py`、`test_layer_public_boundaries.py`，以及 `test_feedback_local_host.py` 的后台导入和强停、argparse、跨进程轮转、原生异常分诊四组。初次隔离归档漏带 `pyproject.toml` 导致 CLI 注册断言失败。补齐同版本文件后，重新收集 144 项，142 项通过，2 项因本机符号链接不可用跳过。
