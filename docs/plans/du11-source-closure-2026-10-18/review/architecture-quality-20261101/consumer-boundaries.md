# 消费边界与架构约束独立审查

- 日期：2026-11-01；CWP HEAD：`d38613bc926e6c95c9009971576af81978a59234`。
- 范围：CWP 公开 SourceRef / reader / export CLI；filing-fetch、revenue-forecast、StockWiki 当前 CWP adapter；相关架构测试和 CI 选择。不是兄弟仓整仓审计。
- 操作：只读源码、CodeGraph、少量标准库 AST / 内存诊断；未运行 skill、采集、模型、数据库、公司任务、全量测试或安装。仅新增本报告。
- 索引限制：CWP CodeGraph 返回 3,524 个 Python 文件，包含 `.planning` 历史复制件；StockWiki 图返回实际已不存在的 v1 adapter，RF 图未找到当前存在的 `verify_artifact_reads`。因此先使用 CodeGraph 获取上下文，再在具体已知文件和陈旧/缺失条目上只读源码/AST。没有重建索引。下面均引用当前工作树行号。

## 结论

当前 RF 正式入口和 StockWiki v2 消费者已经实行路径无关的版本化读取：没有在所审生产消费链中发现消费者直接写 CWP 数据库、跨仓写 StockWiki 研究状态、企业答案特判或新增人工许可链。FF 的旧 path-bearing v1 兼容入口确实仍有物理路径/原件验证，但 v2 和 RF 正式入口不走它，不能把兼容代码当作当前主线违规。

确定的问题主要是：通用架构测试不能保证其名称暗示的依赖边界，StockWiki 的公开字节读取在全部缓冲后才检查输出上限，以及 CWP reader CLI 将错误请求混同为服务不可用。后三仓测试主要验证固定实例成功/拒绝，不能替代通用依赖约束和运行时资源上限验证。

## 发现

### CB-01 / P2：现有通用架构检查有可证明漏检、误报，且不在当前 CI fast contracts 中

**事实与位置**

1. `src/company_wiki/source_catalog/architecture_gate.py:43–62` 的 `source_catalog_does_not_import_prohibited_modules` 逐行匹配 `import {mod}` / `from {mod}`，`54–56` 跳过全部 `__*` 文件。它既不是 AST 导入分析，也不解析依赖方向。
2. 当前调用是 `tests/contract/test_architecture_gate.py:4–9`，仅扫描当前树并断言通过，没有该检查器的导入变体负例。
3. `.github/workflows/ci.yml:57–76` 运行全部 `tests/unit` 和 `tools/pre_push_gate.py --fast-contracts-only`；后者 `FAST_CONTRACT_CASES`（`tools/pre_push_gate.py:90–125`）没有 `test_architecture_gate.py` / `test_fc1201_root_hardcode_gate.py`。Ruff 对 contract 文件的扫描不是执行这些 contract 测试。这里不要求把全部历史 contract 加回日常流程。
4. 根特判检查 `architecture_gate.py:165–185` 是四个旧 root token 的全文搜索，并按 basename 免检。`tests/contract/test_fc1201_root_hardcode_gate.py:119–131` 的负例只有一个新模块直接写 `dayu_portfolio`。因此不能用该测试通过证明企业、ticker、页码、宿主绝对路径或新的 root 名不会进入共享实现。

**无副作用诊断**

只从该文件 AST 提取相关常量/函数，传入内存假文件，不导入项目、不落盘：

| 输入 | 现有结果 |
|---|---|
| `import auto_synthesis` | 拒绝（正控制） |
| `from ..auto_synthesis import main` | 通过 |
| `import scripts.auto_synthesis` | 通过 |
| `__import__('auto_synthesis')` | 通过 |
| `__init__.py` 内 `import auto_synthesis` | 通过 |
| 只有注释 `# import auto_synthesis` | 拒绝（误报） |
| 只有注释 `# Dropbox is configured externally` | root 检查拒绝（误报） |
| 新企业条件 `if entity == 'ExampleIssuer': result = 10` | root 检查通过（其有限范围不覆盖此类） |
| basename 为 `config.py` 的新文件中新增 `dropbox_stock` 分支 | root 检查通过（整文件白名单） |

**触发与影响**：未来导入改为限定名/相对形式，或通过包入口引入跨层依赖时可以绕过检查；说明文字反而可能触发拒绝。当前快测没有执行这些旧 contract，更不能把它们当作持续约束。以上证明的是检查器缺陷和覆盖缺口，**不是声称当前生产已经调用投资 writer**。

**统一 owner 与改法**：由 CWP architecture/test owner 维护一个小型、纯 AST 的依赖规则表，按完整仓内模块路径识别层和允许的公开端口，包含 `__init__`、别名、相对 import 和常量动态 import；不要给整个 basename 永久豁免。对公司/路径特判需要区分“配置数据/平台实现”与“共享业务条件”，避免关键词全禁。可复用本仓已有 `tests/unit/test_source_reading_layers.py:19–83` 的 AST 识别方式；扩充它的模块覆盖，而不是建立新审批/注册系统。

**测试设计**：在 unit 中放轻量通用边界测试，CI 自然覆盖；对上表每项做参数化正反例；新增模块自动按路径归层，无法分类时给明确待归类输出。针对外部 consumer，仅测试公开 wire/CLI，不通过拼接邻仓源码/数据库来补能力；移位根、别名公司、同形新 ticker 和页序变体以行为测试约束。平台文件的明确路径分支和配置中的实体别名应有正例。

**相关但不能混称为活跃 CI 漏检**：`architecture_gate.py:65–85` 的 `llm_summarizer_rejects_investment_content` 从不增加 violations，任意 summarizer 都返回 `(True, [])`；内存例 `def summarize(): return 'SOTP'` 通过。当前搜索只有定义/`__all__`，没有测试或生产调用，因此这是**未使用的失真 helper / P3 清理项**，不是“当前 CI 执行恒真检查”。应删除该虚假保证，或在真正源码摘要出口用任务边界行为测试；不能以原文包含 `SOTP` 就拒绝来源材料。

**为什么宿主硬编码未必被发现**：`scripts/host_assumption_guard.py:309–318` 明确仅在 `in_tests` 时检查绝对路径与能力调用；生产实现中绝对路径不会被此规则拒绝。这是该脚本自己声明的范围，不等于新的生产代码已获许可。应补特定共享运行层的移位测试/静态规则，不把此测试可移植性检查当作生产泛化证明。

### CB-02 / P2 / StockWiki owner：verified-open 输出上限在全部缓冲后才生效

**真实调用**：`stockwiki/services/source_reader_v2.py` 的 `run_source_read_v2` 调用 `VerifiedOpenTransport.open_verified`；实现位于 `StockWiki/stockwiki/_source_reader_v2_transport.py:115–153`。

**事实**：`129–135` 用 `subprocess.run(stdout=PIPE, stderr=PIPE, timeout=...)` 收集完整两路输出；`149–150` 在进程退出后才检查 `len(data) > max_stdout_bytes`，stderr 没有资源限额。这对最终结果作拒绝，不能限制读取期间的内存。`tests/test_source_export_v2_cli.py:246–256` 只检查一个会结束的超量子进程最终返回 `stdout_over_limit`；`309–320` 检查休眠 timeout；两者均不证明超量时即时终止。

**触发与影响**：源文件比配置上限大，或配置 reader/异常子进程在截止时间内连续写 stdout/stderr 时，消费者可以先承受远高于配置上限的内存负载，再得到拒绝；这破坏了同一公开 transport 的 bounded 语义。没有运行超量进程，本结论来自调用 API 的确定语义，不声称实际发生过 OOM。

**统一 owner 与改法**：StockWiki transport owner 将 source-export reader 复用其已有有界子进程读机制/端口，读取时计数并在超过任一路限额时终止和回收进程树；保持业务 adapter 只接收 bytes+receipt。不要为了复用直接 import CWP 私有 process 模块；接收方验证字节 hash/长度仍然保留。

**测试设计**：小上限的持续输出子进程分别覆盖 stdout/stderr；验证达到 limit+固定读取块即停止、未等总 timeout、无孤儿进程且无成功 receipt。保留现有 hash、manifest、receipt 不一致测试。此修复属于兄弟仓 owner，本轮不修改。

### CB-03 / P3：CWP reader CLI 把请求格式错误与存储故障折叠为同一诊断

**位置与触发**：`source_reader_cli.py:33–35` 将 argparse 错误转换为 `ValueError`；`44–68` 解析参数和 `query_ref`；`107–114` 同时捕获 `CatalogConfigError`、`CatalogReaderUnavailable`、`OSError`、`sqlite3.Error` 和 `ValueError`，一律输出 `unavailable/reader_unavailable`。例如漏传 `--source-id`、非法 SHA-256（`source_reader.py:234–237`）和真实目录不可用不可区分。相比之下 `source_export_v2_cli.py:109–114` 区分 unavailable 与 blocked/invalid_request。

**影响**：消费者无法准确决定“改请求”还是“恢复环境”；这不是吞错后成功或静默 fallback，失败 exit=2 和无成功 receipt 仍保持。

**统一 owner 与改法**：CWP 公共传输 owner 在解析/输入校验边界明确返回 pathless `invalid_request`，保持存储错误 unavailable；避免把内部异常原文直接泄漏成路径/凭据诊断。

**测试设计**：缺参数、非法 digest、不可读配置、不可读 catalog 四项应有区分的稳定 reason，全部 stdout 无源字节。不要把正常质量拒绝更名为人工 approval。

## 已做对的边界与保留理由

| 边界 | 当前证据 | 结论 |
|---|---|---|
| CWP 公开身份与实际打开分离 | `source_reader.py:78–84` 的 SourceRef 不含路径；`226–258` 精确 document/source/hash 查询；`source_reader_cli.py:62–95` owner 打开后输出 bytes+receipt | 保留。变更目录不应让消费者获知/猜测物理布局。 |
| RF 正式消费入口只有 v2 | `revenue-forecast/scripts/source_preparation.py:399–433` 明确只有 SourceRef v2、兼容 flag 为 no-op、缺 config 失败；`SKILL.md:184–188` 旧两步入口已 deprecated | 未发现正式链回落到 canonical_path。 |
| FF v2 的职责边界 | `filing-fetch/scripts/fetch_filing.py:1201–1205` 拒绝用 v2 请求走旧 local 模式；`1245–1259` 单一 v2 dispatcher；`1384–1404` v2 仅 metadata 检查、owner 最终 open 决定物理资格 | 合法薄 adapter。identify/market/provider 路由不是企业答案特判。 |
| FF 的路径型旧入口 | `filing_contracts.py:620–732` 做旧 root policy containment / 文件 hash；`fetch_filing.py:1395–1404` 仅 legacy 分支调用；FF `SKILL.md:16` 声明 1.1/1.2 是 legacy | 有重复 owner 工作但有明确兼容边界；不作为当前 v2 生产违规计数。未来只做定点退役，不再扩展。 |
| RF 本地旧 helper | `company_wiki_source.py:115` 导入 CWP 内部 artifact DAG、`278–301` 读取 artifact path、`445–454` 重算原件；`source_preparation.py:305–306` 注明离线历史夹具用，新代码不得调用 | 不应误报“当前 RF 主线直接读 CWP”。建议长期隔离至 compat/test 支持，但本轮不改。 |
| StockWiki pathless 接口 | `source_reader_v2.py:1–17`；`_source_reader_v2_transport.py:117–127` 仅 ID/hash/purpose；`200–221` 两路 receipt/bytes/manifest 交叉核对 | 无运行时 CWP Python import/DB/物理根解析；自身 wire DTO 是跨进程合同投影，不是第二个 source identity owner。 |
| 接收方重算 hash | CWP `source_reader_cli.py:3–5` 明确消费者检查 exit、receipt、自身收到的 bytes hash；StockWiki `210–221` 实施 | 必要传输完整性校验，不等于重新做源身份/period/物理根政策。不可在“去重验证”名义下删除。 |
| 无逐材料人工门禁 | `source_reader.py:601–619` 把 review 作为可选诊断；缺少/失效记录得到 not_reviewed；`source_preparation` / FF 文档继续既有下载意图 | 保留诊断、不新增审批链。当前 roots/bytes/identity/as-of/预算校验有实际数据责任，不是多余人工 gate。 |
| 已有轻量 AST 边界测试 | `tests/unit/test_source_reading_layers.py:19–83` 识别相对/别名/常量动态 imports；`107–132` 真实绕过负例和合法 port 正例 | 是可延伸的有效基础；当前只覆盖命名 PDF/financial-statements seams，不能推论全 source_catalog 解耦完成。 |
| relocation 行为测试 | `tests/contract/test_architecture_quality_storage.py:23–103` 验证已登记根移位、撤根、相对路径逃逸、原件 hash 不符 | 是必要来源校验。跨仓正式接口回放也应沿用这种可移位夹具，不依赖当前宿主目录。 |

## 审查边界和下一步

没有扫描密钥或生产配置内容；没有修改 .githooks、外来 hookmode、RF assurance、Dayu/IQS/Dashboard，也未调用其测试。未对所有 CLI 子命令、数据库 writer、PDF/LLM selection 内部逐一证明；这些由其它审查分工负责。未发现不代表全仓不存在。

建议先由 CWP owner 收束 CB-01 的“可执行而且轻量”的跨层边界约束，同时保留已有真实端口行为/移位测试；CB-02 交给 StockWiki transport owner；CB-03 在 reader 协议维护时修正。无需新建许可、receipt 注册或逐案例 canary；不建议把所有历史 contract/跨仓 E2E 放回每次提交。
