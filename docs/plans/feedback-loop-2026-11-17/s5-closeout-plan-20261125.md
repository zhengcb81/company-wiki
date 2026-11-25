# S5 · S1–S4 复审余项收口

> **状态：实施中。** 2026-11-25 用户确认按 S5 逐项核实、修复，各模块可并行。
> **调查依据**见[复审报告](../module-boundaries-2026-11-11/review/s1-s4-post-rollout-12-module-audit-20261125.md)。[逐项验证台账](s5-verification-20261125.md)保留当前版本、复现、适用范围、修复与发布记录。静态统计用于定位，具体运行行为以复现和回归为准。

## 一、通用规则（所有包适用）

1. **责任仓单写**：每项代码、测试和实施证据归所属仓。总控协调独立工作区，并走公开接口组合复验。发布和部署按各仓正式入口执行，保留在途修改。
2. **先核实再修**：可重现缺陷保留失败用例并修复共用原因，随后复跑受影响范围。已经修复、不能复现或属于历史版本的观察，记录现场对照和适用范围，避免重复修改。
3. **不改预算与权限**：不放宽下载/token/费用/时间上限，不改全局 ACL 或完整性标签，不绕过平台拒绝。涉及全局技能同步按 AGENTS.md 的 Windows 部署运行时规则，用标签正常的宿主 Python 执行 canonical 安装器。
4. **不泄密**：测试用合成凭据；收据、日志、PWF 中不得出现真实密钥。
5. **一次发布一次部署**：先修复并发布到该仓正式发布线，再对齐 F4 运行目录与全局技能，避免同一仓部署两遍。
6. **独立审查**：在责任仓发布和总控组合等关键节点独审。审查绑定发布源码；测试证据可复用，同一用例无须逐层重复运行。
7. **证据回写**：每包完成后在本仓 PWF 记：提交 SHA、RED 输出摘要、GREEN 命令与结果、独审结论、同版 CI 链接（仓内无 CI 的写明“无 CI”，不得写成通过）。

## 二、证据记录

| 编号 | 判定项 | 通过标准 | 不通过的典型表现 |
|---|---|---|---|
| G1 | 缺陷复现 | 按当前正式版和实际运行版记录适用范围、复现和原因 | 把静态计数或历史快照直接当作现场故障 |
| G2 | 修复生效 | 单元测试固定原因，关键链路走真实 CLI/HTTP/worker | 只验证替身，漏掉实际调用的入口 |
| G3 | 无回退 | 复跑受影响回归。过时的用例说明其替代依据和保留的行为 | 删除有效断言或跳过失败换绿 |
| G4 | 发布一致 | 对照审查记录与发布源码。有 CI 的仓记录同版结果 | 审查和发布对应不同源码 |
| G5 | 现场一致 | 独立记录受影响 F4 运行目录和技能受管文件的版本，还原原作业 | 只查目录是否存在 |
| G6 | 业务正确 | 保持业务协议及原作业计费语义。意图内修正的失败码记录正反对照 | stdout 被诊断污染或重复发起付费请求 |

## 三、实施包

### P0 组（先做：安全、正确性、CI 假绿）

**S5-01 StockQAbyLLM：Bearer 脱敏与环境注入回归**
- 缺陷：①`quick_scan_owner_research.py:42`、`quick_scan_owner_budget_permissions.py:23`、`quick_scan_work_decision_authority.py:32` 的 `_STDERR_REDACT_RE` 遇 `Authorization: Bearer <token>` 只替换 `Bearer`；②`quick_scan_owner_research.py:477-479` 读 stderr 头 8KB 而非尾部；③`_quick_scan_owner_refresh_port.py:398` 仍读 `_environment`，而 `quick_scan_owner_refresh.py:148` 已改为 `_process_env`。
- RED：①输入 `Authorization: Bearer SECRET123`，断言输出不含 `SECRET123`；②构造 >8KB stderr，断言末尾 traceback 出现在日志；③传入 `process_env={"X":"1"}` 且宿主 `os.environ` 含不同值，断言 `subject_dispatch_setup()` 返回的环境取前者且不含宿主独有变量。
- 修复要点：脱敏规则覆盖 `Bearer/Basic <token>`、`api_key=`、URL 查询参数；三处共用同一实现，避免三份拷贝；读取尾部；端口层改走公开的 `subprocess_env()`，不再 `getattr` 私有名。
- 验收：三个 RED 用例转绿；`test_quick_scan_module_boundaries.py` 等既有回归全绿；把 `test_s1_p0_provider_and_subprocess_logging.py` 加入 `scripts/checks.py:DAILY_TEST_TARGETS` 并实际被执行（用 `--list` 或收集数确认）。
- 依赖：无。风险：脱敏过宽误伤正常日志，需加合法文本不被改写的对照用例。

**S5-02 revenue-forecast：CI 假绿与 S1 回退**
- 缺陷：①`tools/pre_push_gate.py` 的 `CI_TESTS` 不含本轮新增的 10 个测试文件；②`scripts/filing_fetch_client.py` 在 `1b471df4` 删了 S1 的 `_logger` 与 stderr 摘录。
- RED：①写一个契约测试，枚举 `tests/` 下 S1–S4 新增文件（用提交范围 `db4f8c7a..b9e59db4` 的新增/修改测试列表），断言每个都在 `CI_TESTS` 或明确的豁免清单中——当前应失败；②子进程以 `PermissionError` 非零退出时，断言 RF 抛出的错误或本地日志含脱敏后的 stderr 尾段，且 stdout 机器 JSON 不变。
- 修复要点：补入 `CI_TESTS`（先本地跑通，确认不因时长超限）；恢复脱敏 stderr 本地记录，并保持 S2 已有的 `ImportError` 摘要行为。
- 验收：本地 `python tools/pre_push_gate.py --ci` 的用例数增加量等于新增文件的测试数；远端同版 CI 日志中能看到这些测试名；两个 RED 转绿。
- 风险：补进后可能暴露此前未被 CI 覆盖的失败，需逐个归因，不得删断言。

**S5-03 MeetingConverter：配置优先级与校验**
- 缺陷：`transcribe.py:85-88,152-187`：`--engine` 默认非空导致 `config.json` 的 `transcription_engine` 不生效；`{**cli_defaults, **raw}` 让配置文件覆盖命令行；`normalize_config()` 绕过 `_validate()`；`audio_utils.py:137-153` 不检查 `ffmpeg` 退出码；`engines/mimo.py` 捕获 `HTTPError` 后不 `close()`。
- RED：①`config.json` 设 `transcription_engine=whisper`、命令行不传 `--engine`，断言选用 whisper；②命令行传 `--model large-v3`、配置写 `small`，断言用 `large-v3`；③`translate_max_retries=0` 或布尔值写进整数字段，断言抛 `ConfigError` 而不是运行中途 `TypeError`；④让假 `ffmpeg` 返回非零，断言报错而不是产出 0 字节切片；⑤模拟 `HTTPError`，断言响应被关闭。
- 修复要点：CLI 参数默认值用 `None`，优先级 命令行 > 配置 > 默认；所有运行入口走同一个带校验的加载函数；`_validate` 拒绝 `bool` 冒充 `int`。
- 验收：五个 RED 转绿；现有 365 项测试不减；用真实 CLI + 假引擎复验默认与显式两条路径。
- 风险：优先级改变会改变既有用户行为，需在 PWF 写明变更并保留 `--engine auto` 的旧语义。

**S5-04 旁路写失败与诊断误导（跨仓，各仓独立包）**
统一验收口径：注入“侧车目录不可写”，断言 ①业务结果与退出码不变；②stderr 出现一行脱敏告警（含失败类型，不含路径与凭据）；③stdout 机器协议不变。
- **S5-04a revenue-forecast-audit**：`audit_delivery.py:130-144` 在 `exported_without_journal` 时也要把 `failure` 写到可被 `reconcile` 读取的位置。RED：让 `_journal` 抛 `sqlite3.Error`，随后调用 `feedback_owner.py reconcile <id>`，断言不是永久 `unknown`。
- **S5-04b investment-dashboard**：`request_feedback.py:325-329` 写失败时不得把不可查的 `correlation_id` 当作已记录；至少 stderr 告警，并在响应中区分“已记录/未记录”。RED：只读目录下发请求，断言 `get-diagnostic` 结果与响应声明一致。
- **S5-04c company-wiki**：标准库异常及已有公开错误类型进入分诊结构，其他可信形状使用通用类别，原始类名与脱敏因果链留在本地。RED：`.diagnostic.json` 含 `sqlite3.OperationalError`，断言分诊输入里 `exceptions` 非空，同场检查非业务标签不进入外发内容。
- **S5-04d filing-fetch**：`ff_scheduled_windows.py:152-170` 对非内建异常至少保留类名与末帧位置。RED：子进程抛自定义异常，断言失败记录含类名。
- **S5-04e industry-research**：`deepseek_client.py:107-140` 将 HTTP 200 的 JSON 解析失败与网络错误分开，不重试付费调用；最终一次 429 不再空等 15 秒。RED：用假服务返回 200+坏 JSON，断言请求次数为 1。
- **S5-04f invest-quick-scan**：`provider_transport.py:27-53` 把 `Request` 构造放进 `try`，并捕获 `http.client.HTTPException`；同阶段去重键加入题目标识。RED：构造非法 URL 与截断响应，断言返回 `(0, {"error":"transport"})` 而不是抛出；两题不同故障断言产生两条记录。
- **S5-04g earnings-transcripts**：`scraper.py:1790-1791` manifest 写失败应置失败退出码；`transcript_feedback.py:1439` 收窄为 `Exception`；worker 诊断在 worker 启动前崩溃时仍有可读痕迹。RED：manifest 目录只读，断言退出非零；向旁路写入注入 `KeyboardInterrupt`，断言不被吞掉。
- **S5-04h StockWiki**：`complete()` 的提交顺序改为可重入或先 `scan.sqlite` 后 `identity_receipts.sqlite` 且失败可重试。RED：在 `confirm_public_resolution` 注入失败后重跑，断言能完成而不是卡死。该包涉及事务设计，先出设计说明并独审再改代码。

### P1 组（日志与可追溯）

**S5-05 全入口本地轮转日志（按仓分包，先做试点再推广）**
- 范围：CWP、FF、RF、Audit、StockWiki、IQS、Dashboard、IR、MC、ET、StockQA；SID 另含 `company_wiki_adapter_cli.py` 与 `setup_logger` 句柄泄漏。
- 设计要求（先写设计、独审后实施）：每仓一个启动函数；轮转文件、默认级别、日志目录来自本仓现有状态根；格式化器复用各仓已有脱敏实现；绝不写 stdout；日志写失败不改变业务结果。
- RED（每仓一条）：用坏输入调用真实主入口，断言日志文件存在，含异常类型和 `run_id`；断言 stdout 机器输出与修复前逐字节相同。
- 验收：11 个仓各自通过上述用例；SID 的 `setup_logger` 连续换文件后旧句柄已关闭（Windows 上可删除旧文件）。
- 说明：这是原 S2 第一层目标，工作量最大，建议拆成按仓独立的小包分批发布，不要一次完成。

**S5-06 `from None` 前置日志**：只处理用户确认要求覆盖的入口（建议先 CWP 的 98 处未记录点中位于 CLI 边界的那些），不按语法统一拒绝；以“真实故障入口能冷查出原因链”为验收，不以计数下降为验收。

### P2 组（结构与门禁）

**S5-07 跨仓残留 3 处**：FF `seed_batch.py:32`/`cli_main.py:107`、IQS `legacy_oracle.py:3,7`、RF `slo_probe.py:25`。RED：全目录扫描式 AST 测试（FF 边界测试改为 `MATRIX.glob("*.py")`，并对内联脚本字符串另做检查）先失败。验收：扫描 0 命中，原功能用公开 CLI 复验。

**S5-08 仓内破环**（每项独立设计、独审后实施，不并行改同仓）：StockQA 的 `quick_scan_work_store.py` 分层；CWP `source_catalog` 的 SCC 与 `_LEGACY_EDGES`；RF `report_catalog*`；StockWiki Store 绕过；Dashboard `adapters/*` 私有导入。验收用“环数/私有导入数不增加的棘轮”加上业务回归，**不以一次清零为目标**。

**S5-09 静态门禁与 CI**：修复 `layer_boundary_scan.py` 六个盲区（每个盲区一条 RED：对应反例必须被扫描器报出）；为 ET、SID、IQS、Dashboard、IR 补最小 CI（跑本仓现有快速测试即可）。验收：反例被报出，合法对照不被误报。

### 现场对齐包（每仓在其修复包发布后执行）

**S5-10 F4 运行目录与全局技能对齐**
- 清单：FF、RF（`report`/`reconcile` 统一）、IQS、StockQA、IR、Audit（补 `.codex` 副本）、Dashboard 主仓。
- 步骤：①记录当前 F4 运行路径与 HEAD；②用 canonical 安装器同步全局技能（按 AGENTS.md 用标签正常的宿主 Python）；③切换 F4 `settings.json` 指向，改动前备份并记字节 SHA；④新进程冷查一次已有原动作。
- 验收：逐文件 SHA 比对表（路径、发布 SHA、实际 SHA）全部一致；重复安装零写；冷查原动作得到与切换前相同的终态；新增下载、转录、模型请求、费用均为 0。
- 约束：不改全局 ACL；`settings.json` 属于总控配置，改动前须明确是否由本仓 owner 执行；若平台拒绝，写明被拒动作并停止。

## 四、建议顺序

1. 先 S5-01、S5-02、S5-03（用户可见的正确性与安全，且彼此独立，可并行）。
2. 再 S5-04a–h（各仓独立，可并行，StockWiki 先设计）。
3. 每包发布后立刻做对应的 S5-10。
4. S5-05 先选 CWP、SID 做试点，验证设计后再推广。
5. S5-07 随后；S5-08、S5-09 最后，且按仓串行。

## 五、实施口径

1. 按 S5 保留编号和审计原条目。确认已修、发现误报或现场另有前提时，记录具体证据和适用范围。
2. 优先覆盖采集、研究、服务、后台和分诊的公开入口。共用日志由运行边界初始化，失败原因在本仓落盘，保证机器 stdout 不变。只对已复现的边界行为补测试，动态依赖的数量和语法计数用于调查。
3. 责任仓交付代码、最小测试包和实际入口。总控核对现场路径，切换经核实的运行引用。历史记录按其原接口保留；主工区有在途工作时使用专用检出。
4. 优先消除触发实际错误的私有依赖、存储绕过和调度环路。跨仓调用经公开入口验证，低风险结构清理独立记录。

## Next Step

并行复现 StockQA 子进程脱敏与环境、RF 远端 CI 日常测试清单及 stderr、MC 配置及公开 CLI。总控先修 CWP 分诊证据的异常类别缺失，再复现后台启动与并发日志。
