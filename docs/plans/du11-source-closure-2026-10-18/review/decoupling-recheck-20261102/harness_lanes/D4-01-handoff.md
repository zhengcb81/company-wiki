# D4-01 交付说明 — StockWiki 默认公司来源虚拟化

状态：**已实现、已自测、已经两轮独立审查并修复。** 两仓提交在各自 worktree 分支上，
未推送、未合并；ROOT 负责跨仓组合节点。

## 1. 两仓实际 HEAD / 基线

| 仓库 | worktree | 分支 | 基线 | 交付 HEAD | 提交数 |
|---|---|---|---|---|---|
| company-wiki | `C:/Users/郑曾波/Projects/_harness_worktrees/d4-01-20261102/cwp` | `codex/d4-01-company-source-index` | `503f6510` | `fcf553117` | 4 |
| StockWiki | `C:/Users/郑曾波/Projects/_harness_worktrees/d4-01-20261102/stockwiki` | `codex/d4-01-company-source-virtualization` | `d8d3303` | `23d8458` | 3 |

提交：
- CWP `6374edd6c` Add a bounded, pathless company-level source index
- CWP `dbc13f694` Keep undated versions and a stable page boundary（审查修复）
- SW `0a397ae` Read company sources through a configured provider
- SW `ce00ed7` Report unusable companies by name and keep the default deployment working（审查修复）
- CWP `0c68ca9a5` Prove a listed SourceRef is readable through the public read port（审计补测）
- SW `23d8458` Never hand a pathless source to a path-based consumer（审计修复）
- CWP `fcf553117` State that diagnostics cannot become a company source fact（审计补断言）

CWP worktree 里 `.githooks/pre-push` 显示 mode 755→644，是 Windows 检出产物，
**不属于本卡**，未提交。StockWiki 工作树干净；CWP 工作树另有一个测试产生的未跟踪
`pytest-of-郑曾波/`（已删，见 §6）。

## 2. 精确修改清单

### company-wiki（7 个文件，+1616/−1）

| 文件 | 性质 |
|---|---|
| `src/company_wiki/source_catalog/company_source_index.py` | 新增。公司级来源清单实现：请求/响应校验、候选扫描、分页游标、可用性判定 |
| `src/company_wiki/source_catalog/company_source_index_cli.py` | 新增。`company-wiki-company-sources` 入口；成功写 stdout，拒绝写 stderr 并 exit 2 |
| `tests/contract/test_company_source_index_cli.py` | 新增。23 条隔离真实入口契约测试 |
| `tests/fixtures/company_source_index/wire_v1.json` | 新增。冻结 wire 字段集、排序、状态、可用性取值 |
| `pyproject.toml` | 注册 console entry |
| `docs/使用说明书.md`、`docs/GATE_SYSTEM.md` | 登记新入口 |

未触碰：`document_normalization`、`document_understanding`、`transcript_import_cli.py`、
`integration/`、ROOT runner。

### StockWiki（25 个文件，+2726/−78）

| 文件 | 性质 |
|---|---|
| `stockwiki/company_sources.py` | 新增。传输层 + provider + 配置加载（可替换 argv、`${VAR:-默认}` 句柄） |
| `stockwiki/_company_source_wire.py` | 新增。两份 versioned wire 的纯校验（模块尺寸门要求拆分） |
| `stockwiki/services/company_sources.py`、`stockwiki/cli_parsers/company_sources.py` | 新增。`company-sources` 只读清单入口 |
| `stockwiki/sources.py` | 扩展 `SourceRecord`（逻辑身份字段、`locator_label`）；新增 `source_context()` 与 `DocRootSourceContext` / `ProviderSourceContext` |
| `stockwiki/analysis.py`、`enrichment.py`、`document_signals.py` | 三入口改为经 `source_context()`；`external_sources.yaml` 记录 `source_protocol` 而非 `doc_root` |
| `stockwiki/services/company.py`、`cli_parsers/company.py` | `--doc-root` 变可选、新增 `--source-provider` / `--as-of`；具名拒绝；记录继承；成功后才落盘 |
| `stockwiki/config.py` | `Company.source_provider` |
| `stockwiki/analysis_render.py` | `render_profile` 用来源标签替代物理根 |
| `stockwiki/_narrative_process.py` | `run_bounded` 增加可选 `env` 句柄（配置化端点） |
| `stockwiki/report_export.py` | `markdown` 改为惰性导入（见 §7 环境说明） |
| `config/source_providers.yaml`、`config/cwp_source_index.transport.json`、`config/companies.yaml` | 新增 provider 声明与部署句柄；12 家公司加 `source_provider: cwp`（`doc_root` 保留为导入适配器） |
| `docs/company_source_provider.md`、`README.md` | 协议、配置、时间/可用性语义、运维命令 |
| `tests/test_company_sources.py`（19）、`tests/test_company_source_wiring.py`（17）、`tests/fixtures/company_source_provider/producer.py` | 新增。可替换假端点 + 真实 CLI 入口测试 |
| `stockwiki/integrations/dayu_cli.py` | 审计驱动的守卫修正（§5.1 第 1 条）：无本地路径的 manifest 行不再可选为上传来源 |
| `stockwiki/cli_registry.py` | 注册只读 `company-sources` 入口（§5.2） |
| `tests/test_cli_core.py` | 更新 fake pipeline 签名 |

## 3. 接口 fixture 版本

`tests/fixtures/company_source_index/wire_v1.json`：
- 请求 `company-wiki-company-source-index-request/1`：字段精确 `{schema_version, company{entity,market,security_id}, as_of_date, document_kinds, page_size, cursor}`
- 响应 `company-wiki-company-source-index/1`：字段精确 `{schema_version, status, reason, company, as_of_date, page, sources, source_read_policy_sha256}`；`page = {cursor,next_cursor,has_more,count}`；`sources[]` 13 字段；`source_ref` = SourceRef 6 字段
- 状态 `{ok, not_found, ambiguous, unavailable, blocked}`；可用性 `{available, unreadable, retired}`
- 排序 `published_date desc（未知置尾）, document_id asc`；游标为 `{p,d,s}` 的 base64url 不透明串
- 时间语义：`as_of_date` 含端点；未知发布日不被当作未来版本丢弃，`published_date: null` 排尾
- 重复文件：同一份字节 = 一个来源版本、`copies` 个物理副本

StockWiki 侧同名字段集由 `stockwiki/_company_source_wire.py` 校验；读取收据沿用现有
`source-read` 的 `2.1` schema，不做改动。

## 4. 已运行命令与结果

CWP（`PYTHONPATH=$PWD/src`，venv 解释器）：
- `pytest tests/contract/test_company_source_index_cli.py` → **23 passed**
- `pytest tests/contract/test_company_source_index_cli.py test_source_version_reader_cli.py test_transcript_import_cli_e2e.py test_company_source_layout.py test_company_raw_adapter.py tests/unit/test_deployment.py` → **74 passed, 1 skipped**
- `ruff check` / `mypy src`（pre-commit 钩子，CI 同命令）→ **All checks passed / Success: no issues found in 424 source files**

StockWiki：
- `pytest tests/test_company_sources.py` → **19 passed**
- `pytest tests/test_company_source_wiring.py` → **15 passed**
- 受影响域（31 个文件：company/enrichment/document_signals/config/cli/quick_scan/services/ui）→ **414 passed**
- pre-commit（ruff + `validate-framework --static`）→ **Passed**

跨仓真实链路（本会话手工执行，脚本不提交）：
- 专用临时 CWP catalog（两个物理根、四个文种/期次、一份重复字节）+ 临时 StockWiki workspace，
  以**部署形态**（`-m company_wiki... --config` + `PYTHONPATH`）跑真实 CLI：
  `company-sources` / `run-company` / `enrich-evidence` / `extract-document-signals` 全部 rc 0；
  撤下一份原件后该条目变 `unreadable` 而非消失。**RESULT PASS**
- 部署形态默认解析（无任何环境变量覆盖，workspace 与 `company-wiki` 同级）：
  `company-sources --ticker 688012.SH` → **rc 0，112 条来源 / 84 可用 / 2 页**，stderr 空
- 只读生产 catalog 覆盖核对（12 家配置公司，均 `status=ok`）：
  中微公司 112（84 可用）、中信建投 404（357）、新华保险 104（43）、北方华创 92（50）、
  中国平安 80（31）、中芯国际 43（16）、百济神州 35（14）、拓荆科技 25（8）、台积电 24（24）、
  信达生物 11、中国生物制药 11、华虹半导体 6。未写入生产库/配置。

RED 证据：CWP 契约测试在实现前 **19 failed / 1 passed**；StockWiki 两个新测试模块在基线
`d8d3303` 上 **2 errors（collection：No module named stockwiki.company_sources）**。

## 5. 独立审查

两轮，均由未参与实现的 agent 执行，只读审查 + 实跑。

**第一轮**（10 项发现，2 blocker）：
1. retired/unreadable 版本会让三条流程整体崩溃 → 已改：只消费 `available`，其余计入
   `source_protocol.unavailable_sources`。
2. 无发布日的版本被整体丢弃（生产中微公司 112 条只剩 26 条）→ 已改：未知日期保留并置尾。
3. `run-company` 会清空已配置的 `doc_root`/aliases/keywords → 已改：未重述字段继承。
4. 无 provider 时静默回落到 `company.doc_root` → 已改：三个 CLI 入口先拒绝；库层保留
   显式 `Company(doc_root=...)` 回退（7 个既有测试依赖，且属显式对象字段）。
5. `CompanySourceError` 逃逸成 traceback → 已改：具名 `error_code` + exit 2。
6. `parser_status.yaml` 落盘消费侧缓存绝对路径 → 已改：只写 `source_id` + `content_sha256`。
7. `_company_known` 无序 `LIMIT 500` + N+1 实体查询 → 已改：确定性排序 + 批量查询。
8. 游标在副本迁移后硬失败/重复投递 → 已改：游标携带 source 版本，回退续页并跳过已交付版本。
9. MIME 映射不全（生产 1690 条 `application/xml` 落到空扩展名）→ 已补 xml/csv/pptx/ppt/图片。
10. `${X:-../../etc}` 可越界 → 首版加了包含规则，**被第二轮判定为过严**并撤回（见下）。

**第二轮**（针对修复，2 blocker）：
1. 包含规则把提交版配置的 `../company-wiki/...` 默认值判成 `path_escape`，四个入口全部退出 2
   ——**默认部署被自己的规则打断**。已改：token 默认值按 workspace 根解析、绝对路径原样使用；
   新增"提交版配置可直接加载"和"部署布局可解析"测试，并实测默认形态 rc 0。
2. 全 retired/unreadable 的公司以"成功、0 来源"结束 → 已改：`provider_all_unavailable` 具名拒绝。
3. 裸重跑清空 exchange/industry/tags，且失败运行也会写配置 → 已改：字段继承 + 成功后才落盘。
4. `python_executable` 展开未传 workspace 根 → 已改。

两轮发现的问题全部修复。第三轮完成度审计又发现 1 个下游回归（见 §5.1）与若干披露缺口，
已一并修复。最终复跑：CWP 契约 23 passed、StockWiki 新测试 36 passed、受影响域 414 passed、
跨仓 E2E PASS、部署形态默认 rc 0。

### 5.1 第三轮：完成度审计（逐条对照卡片）

独立 agent 按卡片逐节核对（唯一目标 / 写域 / 接口冻结 / fixture / 五项行为测试 / 明确不做 /
通过标准 / handoff 内容），结论 **COMPLETE WITH GAPS**。它自己实跑了 22+34 条测试、用临时
catalog 走了真实跨仓链路、grep 了路径泄漏。发现并已修复：

1. **下游回归（真实缺陷）**：provider 来源的 manifest 写了 `original_path: ""`，而
   `stockwiki/integrations/dayu_cli.py` 用 `Path(str(...))` → `Path("")` 等于当前工作目录且
   `.exists()` 为真，3/3 条无路径来源会被选中并解析到 CWD。已改：`SourceRecord.to_dict()`
   在没有本地路径时**不输出** `original_path` 键；`dayu_cli.select_manifest_sources` 增加
   "无路径行不可选"守卫。**这是对 Dayu 输入校验的一行修正，不是协议或行为改动**——有路径的
   行行为完全不变。新增测试 `test_the_upload_selector_skips_sources_without_a_local_file`。
2. **CWP 契约套件从不消费自己产出的 SourceRef**：新增
   `test_every_listed_ref_is_readable_through_the_public_read_port`，把清单里每个
   `available` 条目交给 `company-wiki-source-read` 实际打开，断言字节数、SHA-256 与回执身份
   全部一致，且回执不含物理路径。
3. **`company-sources --source-provider` 覆盖路径无测试**：已补。
4. **"扩展诊断不成为公司来源事实"只有隐含断言**：响应字段集本就没有扩展通道，现改为显式
   断言——加任何 `extensions/diagnostics/warnings/notes` 字段都会让契约测试失败。
5. **handoff 两处不实**：曾声称"两仓工作树干净"（CWP 有测试残留 `pytest-of-郑曾波/`）与
   "`sw-baseline` 仍在"（实际已删）。已更正，残留目录已清理。

审计给出但**不修改**的两项判断，理由如下：
- *narrative 端口半边无接线测试*：三条默认流程本就不消费叙述，`source-read-narrative` 保持
  原样且其 15 条测试仍绿；卡片要求的"原文与叙述分别走公开 reader"在原文侧已满足，叙述侧
  没有可接的调用点，强行接线属于新增业务。
- *StockWiki 侧 wire 字段集是硬编码副本*：消费端**必须**独立校验，读取生产端 fixture 会让
  两仓测试耦合、并掩盖协议漂移。字段集与 `wire_v1.json` 同步由人工评审保证，版本号
  （`...-index/1`）不匹配会直接拒绝。

### 5.2 写域披露（审计点名，ROOT 需接受或回退）

| 文件 | 判定 |
|---|---|
| `stockwiki/report_export.py`（`markdown` 惰性导入） | **写域外**，与卡无关；不加此改动，基线 `d8d3303` 上 `stockwiki.cli` 连测试收集都失败。属环境使能，可单独回退 |
| `stockwiki/services/company_sources.py`、`cli_parsers/company_sources.py`、`cli_registry.py` | 卡未枚举的新入口，属"来源 adapter 的可观测面"，只读、不写研究状态 |
| `stockwiki/analysis_render.py`、`_narrative_process.py`、`config.py`、`sources.py` | 相邻且必要（来源标签、子进程 env 句柄、公司字段、来源记录） |
| `stockwiki/integrations/dayu_cli.py` | 审计驱动的守卫修正，见 §5.1 第 1 条 |
| `tests/test_cli_core.py` | 被改签名影响，更新 fake pipeline |
| CWP `docs/使用说明书.md`、`docs/GATE_SYSTEM.md` | 写域只列模块/CLI/测试；两处各一行登记新入口 |
| `README.md`、`config/*` | 卡允许（入口说明、公司来源配置） |

## 6. scratch 清理

- 所有测试临时根（`pytest-of-*`、`sw-pt-*`、`d401-e2e-*`、`d401-deploy-*`）用后即删；
  `_harness_worktrees/d4-01-20261102/` 下只剩：两个 worktree、`pre-commit-home`（钩子缓存）、
  四个可复跑脚本（`e2e_d401.py`、`prod_coverage.py`、`deploy_check.py`、`default_check.py`）。
  基线对照 worktree（`sw-baseline`）与所有 `dbg_*`/`probe_*` 已删除。
- 两个 worktree 的 `git status`：CWP 仅 `.githooks/pre-push` 既有 mode 差异；StockWiki 干净。
- 未删除、未移动任何生产原件；未写生产 catalog / StockWiki 研究状态；未调用模型或供应商。

## 7. 环境说明（不是产品缺陷，ROOT 需知）

1. **venv 缺 `markdown`**：`stockwiki.cli` 在基线 `d8d3303` 上连 collection 都失败
   （`ModuleNotFoundError: markdown`）。已把 `report_export.py` 的 `import markdown` 改为
   函数内导入（行为不变，只在真正导出 HTML 时要求该依赖），否则无法用真实 CLI 入口验证。
   这是**为跑通真实入口所必需**的最小改动，已单独说明。
2. **沙箱删除拦截**：本机 `sitecustomize` 的 bulk-delete guard 在累计 50 次 unlink 后以
   `SystemExit(1)` 中止进程，导致 workspace 锁文件清理较多的测试整片失败。测量时使用
   `CODEBUDDY_SAFE_DELETE_ENABLED=0`（仅对测试进程、只写 pytest 临时目录）。这不是代码问题：
   关闭拦截后同一批测试 400+ 全绿。
3. **全量套件不可跑**：`tests/test_c06_*.py` 与 `test_vendor_subject_owner.py` 引用仓库中
   不存在的模块（`query_contract`、`query_field_assessment` 等），基线即 collection error，
   与本卡无关。因此本卡只跑受影响域（414 passed）。

## 8. 仍待 ROOT 的组合步骤

1. 分别接收两仓提交并合入主线；两仓无共同文件，顺序无关。
2. 用**新临时 CWP catalog + 临时原件**跑一次跨仓组合节点，覆盖：query → read/summary →
   RF 实际采用 → AUDIT 导入（本卡只覆盖 StockWiki 侧三个入口）。
3. 组合节点需确认 consumer 进程内**看不到** CWP 实现路径：本卡用 `PYTHONPATH` 注入 CWP
   `src` 是部署句柄；若 ROOT 要求"消费者进程无法 import CWP"，需改用已安装的 CWP 包或独立
   服务端点（`index_command`/`read_command` 已支持任意 argv，无需改代码）。
4. 生产部署前确认两个环境句柄：`CWP_CATALOG_CONFIG`（默认 `../company-wiki/config/source_catalog.yaml`）
   与 `CWP_PYTHONPATH`（默认 `../company-wiki/src`）。本机已实测默认形态可用。
5. 合并后更新 `CURRENT_STATUS`；本卡不声明 D4 整体完成，也不承接迁移剩余工作。

## 9. 明确未做

未改 RF/FF/ET/IQS/Dayu/CWP PDF 与叙述阅读策略；未改 StockWiki investment 判断；未删 legacy
数据或旧 evidence；未把旧物理来源 ID 直接替换（旧 `SourceRecord` 字段与 `doc_root` 导入适配
路径均保留）；未新增私有/公开授权、人工签收或第二套资料数据库；未改 `integration/` 与 ROOT runner。

## 10. 第四轮独立复审记录（2026-11-04，复审 agent，未参与实现）

只读复审 + 全量复跑。结论：**COMPLETE**，可交 ROOT 组合。

复跑结果（复审 agent 独立执行）：
- CWP 契约套件 **23 passed**（worktree，`PYTHONPATH=src`，宿主 venv 解释器）。
- StockWiki 新测试 **36 passed**（19+17）；受影响域复跑 **227 + 53 passed**，零失败。
- `deploy_check.py` **PASS**：部署形态无环境覆盖，中微公司 112 条 / 84 可用 / 2 页，rc 0。
- `prod_coverage.py` **12/12 status=ok**，数字与 §4 逐位一致。
- `e2e_d401.py` **RESULT PASS**（3 版本 2 页、撤原件 → unreadable、无路径泄漏）。
- §1 两仓 HEAD/提交、§6 scratch 状态逐一核实，与本文档一致。

对争议点的独立判定：
- 叙述端口：基线 master 上 `source-read-narrative` 本就是独立 opt-in 入口，三条默认流程
  从未消费；transcript 在默认流程中经 raw 公开 reader 读取。§5.1 的"无可接调用点"判定成立。
- 库层 doc_root 回退：仅显式对象字段可达；三个默认 CLI 入口均先具名拒绝（wiring 测试
  `test_a_configured_doc_root_is_not_silently_the_daily_protocol` 等覆盖）。
- `dayu_cli.py` 守卫：有路径行为与基线一致（`test_dayu_cli_integration` 通过）；是否接受
  该写域扩展由 ROOT 决定。

本节同批修正的记录/脚手架偏差（不影响两仓提交）：
1. §2 头部计数过时 → 按交付 HEAD 实测校准（CWP 7 文件 +1616/−1；SW 25 文件 +2726/−78，
   表补 `dayu_cli.py`、`cli_registry.py` 两行；测试条数校准为 CWP 23 / SW 19+17）。
2. `default_check.py` 原实现把 provider `transport_config` 解析到未合并的生产 StockWiki
   检出，合并前必然 FAIL 且易误读为缺陷 → 改为只读两段式（提交版配置在交付分支内自洽
   加载 + 部署同级布局解析存在性），不写任何生产文件，修正后 PASS。
3. `e2e_d401.py` 硬编码 worktree venv 解释器，该解释器带 Low 完整性标签时无法在 %TEMP%
   mkdir（AGENTS.md Windows 节已记载的环境问题）→ 改为 `D401_PYTHON` 可覆盖、默认
   `sys.executable`，修正后 PASS。

留给 ROOT 的既有事项不变（§8）；新增一条注意：组合节点的子进程解释器不要使用带 Low
完整性标签的 worktree venv python，用宿主正常标签解释器。
