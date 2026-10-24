## 2026-10-24 W08 annual14 V2 选材复核与相关测试包恢复

在不修改冻结的首轮annual14 review/gold前提下，使用新目录`review/r1-w08-crosspage-20261024/annual14-v2/`保存第二轮实际选择和复核。SourceRef原始字节SHA复验一致；一次249页回放，5,660 units/1,532 candidates，保留96 spans/7,171字符，工作8,613,643/16M且未耗尽；编译52个scoped task view，0 provider调用、0下载、0 raw副本。14项ROOT链路复核为6 pass/7 partial/1 missing，首轮3/9/2提升；A07的42万新化合物与310个R→D转换已在`t23`，A11新客和新分子收入占比分别在`t29`/`t15`且对象清楚，A14集中度、需求、监管、竞争、项目延误及汇率风险均有局部可读任务。A01/A02/A03/A04/A05/A09/A12仍partial，A13仍missing；不将fallback原文算selected或将aggregate `budget_full`猜成目标原因。

验证：相关自然包1,546 passed/34.48s；Ruff变更文件全绿；三个源码文件mypy 0错误。整包先在83%卡于既有`test_real_official_export_adapter_keeps_two_actual_parents_and_native_fields`：它使用系统默认`TemporaryDirectory`，fixture再于其内创建嵌套临时目录，本机受限Windows临时区的`mkdir`挂起。测试改用pytest `tmp_path`隔离后，单测2.35s通过，整包完整34.48s通过；生产代码和fixture事实断言未改。回执明确标明ROOT复核、不是独立签收、没有真实模型响应或摘要验收。W11-CWP-SOURCES按用户确认已A/B/C完成并推送，作为完成项不重开。

下一步：只针对仍未闭合的真实目标查候选/依赖/预算项级证据，优先A12、A13及A01/A05父级、A09跨任务关系；保持96/48,000/16M与8/4/2048不变。根修后再用一次同条件新版本选材检查14项，然后才推进摘要/cache和W12。

## 2026-10-23 预算制度根因改造与W09接收

用户明确授权累计10Mtokens/USD20，公司150k/USD1改软目标。ROOT单一config/resource_budget.yaml接入真实mother_totals，旧metadata/usage/unknown全不变，余额8,438,648tokens/19,368,041microUSD；追加新effective scope而不重写旧材料。初始独立56F/7P及母账2F留证；维度套件两次夹具错误另列，第三次才是3个真实RED。独审再查出partial耗尽漏报和缓存错误复用2F，已从共享owner修复并固化普通内存PDF回归。最终独审99P/47P，ROOT loopback恢复12P/210.70s、动态工作计量回归2P，全src类型/发布另附收据；不重复付费、不混加测试计数。

Audit low误停共因4F→58P，完整662run=660P/2skip；独立18控制通过，文档端序笔误只改文字，算法/原结果不变。待ROOT串行提交/定点同步，CWP待正常push。PWF入口/预算目标/外包整合说明已更新，源14目标和W08指引/跨页未冒充完成。

W09用户报告完成，独立只读初筛核实际eb7c2dee/clean、28交付工件和6原生capture，写集无越界，可进入ROOT内容复核；剩版本指针/最终review绑定/测试日志与体积口径小修。作者工区只读，W11未接管。

## 2026-10-22 W07真实生命周期完成，交W06阶段B

### 后续三仓根修接收与RF实际消费（20:54UTC）

W07已有65项有限独立实读复核通过，只签生命周期/公开读取，cache开始为空缺独立清单已下调表述。W06真实`consume_narrative_input`将support span→tides_base_2026_activity→native TIDES base公式绑定，随后主/共享确认压力已原生validate/compute/render/snapshot；作者正在最终字段修正/封存，尚无业务质量PASS。独立storage reviewer先读11原件并冻结源侧inventory，不先看新模型或摘要；source-index已交，catalog最后写者20:53:50UTC退出。

本地诊断CWP/FF/RF分别49/18/16独审通过（不同套件不合计）。RF10bf6111和FF7f6a9268已正常push/install，精确CI均SUCCESS；CWP27be00fb已merge69a5490b，主线→已安装FF/RF真实1例8.19s通过，旧main同例缺ownerop真RED。发现路径漏history共因已统一record_operation，永久回归保留；原资格/配额不变。既有快速smoke只增加2个owner/history控制，2.31s，无新门禁/重型跨仓测试入日常CI。ROOT自有临时根2372files/79,471,652B已恢复不存在，实际运行证据与原件保留；CWP正常发布下一步。

正常推送755e87cd：7088P/24S/271.80s，145smoke/30.31s。纯预检重分配后真实调用一次DS，17329tokens/6701microUSD；新进程/attempt/fence同paid operation原生恢复0新增POST/reservation/token，激活pending→完成、新run cache同415965Bartifact。已安装RF公开CLI退出0/完整418917Bcontext/96spans，selectionpartial/needs_review，不宣称公式/内容已验收。约610KB便携收据已归档，原件/数据库没有复制。

母账1561352tokens/631959microUSD，公司56355/16421，所有unknown保留。ROOT发现操作索引本已包含在initial639封存，误追加后已先保新引用到attempt，再按原SHA恢复原3763字节；639件实核0差异，新scope-v2和attempt索引为当前入口。研究agent继续阶段B，之后四审；FF136ab独审18P，RFdedebe作者201P1S正独审，CWP新9P加旧5真缺陷窄修继续。详见review/r1-w07-live-20261022.md/json。

## 2026-10-22 W07非作者复核、真实预检与W06资料交接

W07非作者查出未注册错误码让“可重试”实际变成DEAD_LETTER；工具改用原生IO_TRANSIENT且核实持久化RETRYABLE，产品5a1548e2经9个不同场景复核通过，正常合入9eba8c4e。两次最终版本运行合并覆盖，不宣称一次9绿。真实纯预检0POST：请求73560B、配置输出8192、保守上界81880，旧公司余量60974不足。协调员在原用户2M/$20内把自定公司累计token100k重分配150k，单请求deploy100k、公司$1、旧unknown全保留；旧scope/预检封存，后续使用新spec/effective-scope。

W03-A已正常push7083P/24S及145smoke，精确1b39032c/CI39842895271 SUCCESS。W06阶段A完成40个capture、10合格来源、8新原件10229835B，20事实/6目标；阶段B、预测、真实摘要新消费均NOT_RUN。catalog writer已退出。其H1首次复用budget_exceeded缺少owner计量，CWP/FF/RF正在隔离TDD根修，不重扫历史猜计量。母模型账仍1544023tokens/625258microUSD；下载网络未知不能写零。

## 2026-10-22 W03-A组合验收与并线

W03-A已TDD完成：同SHA可用时间证明仅进入raw narrative读取metadata；不造publication，不改frozen bundle/generation/cache，projected/3不变。CWP非作者12P、RF最终非作者58P；ROOT合并主线到已安装RF真实公开CLI与新contract共31P/0skip，mypy src366文件0错。RF正常push526P/1既有skip/+36subtests，main/remote674d08d9；consumer先发布安装（1文件×2物理副本/3逻辑入口、566其它文件元信息不变），producer后正常merge。旧b76收据和三份RF WIP保留。独立套件有重叠，不相加冒充一次总数。

W03-B真实0.9/v5、W07真实paid replay/激活恢复/cache/实际RF公式消费、W06新研究四审与HK/US仍OPEN。W07离线工具正在完善纯preview；不把预检故障native run伪称真实恢复，不为测试增加生产重试/审批链。多进程重验放integration大节点，日常unit保持快速。默认0.8、原件、旧FAIL、预算及未知hold不变，本节点0收费/0下载。详细证据：DU11 review/r1-w03-integration-20261022.md/json。

## 当前进展补充：2026-10-22 四包发布与W03-A

四包代码已正常推送三仓；CWP当前工程HEAD20a7fb0c，最终7083单测/24跳过和142独立smoke通过；FF899P/7S/+78subtests，RF477P/1S/+36subtests，安装后当前CWP→FF→RF固定35例9.88秒全绿且测试根恢复不存在。最终CI反控证实subset+follow_imports=skip漏本地跨模块类型，改为同一个缓存full-src命令；热缓存9.1秒，未增第二门禁。远端CI按精确SHA实录，不冒称pending已绿。

ROOT已固定W03-current-interface.md；两个复用自有工区分别实施CWP producer与RF consumer（同名新分支），不碰母仓/安装/配置；旧W04/W02分支保留。ROOT负责一次集中独审/组合E2E及consumer先发布。W03-B正式0.9/v5、真实paid恢复/cache/实际RF消费与研究四审仍OPEN；0新费用/0下载。

## 最新指令：2026-10-22 继续实施

用户“继续”取代本轮此前暂停要求。四包工程已独审并线，先修复/验收当前CWP CI、更新发布和PWF，再接W03→W07/W06→新公司。合并后完整src检查发现Optional pin别名类型漏检；已同变量验空根修，改既有commit钩子采用单一完整src命令（热缓存约9秒）、CI去掉重复名单步骤，不加人工门禁或每次全量commit测试。以下暂停条目为较早历史，不覆盖本段及CURRENT_STATUS。

## 2026-10-22 收尾后暂停

- W01 有界增量发现/实际范围证明/latest歧义、W02 FF/RF业务错误与companion、W04退役付费补写并恢复可证明legacy final、W05统一目标成员范围和比率量纲均完成工程修复及非作者独审。代码已整合；推送、安装和组合检查的最终结论见子计划收尾收据，工程通过不代表真实摘要/研究通过。
- 全src mypy366文件0错；独审 W01 155P+换行/变量补审7P，W02 35P，W04 19P，W05 106P+60subtests。各套件有重叠，不能相加成一次总测试数。
- 用户要求本阶段告一段落；W03/W06/W07、新收费与公司循环暂停。本轮0新收费/0新下载；母账1,544,023tokens/$0.625258，unknown完整保留。唯一入口为DU11 CURRENT_STATUS，细则为10月22日交接。

# 当前过程记录（2026-10-21）

**唯一当前状态与接手入口：** [CURRENT_STATUS.md](CURRENT_STATUS.md)。整体计划仍开放，用户已恢复R1实施。旧记录中的“当前”“待推送”“Next Step”均只适用于当时，不覆盖此入口。

## 2026-10-21 四路首审与共因设计节点

四个独立角色全部封存，73检查/26问题（15P1/11P2），原始报告小型副本已归档，完整live仍本机。数字1276独立比较0算术差错，业务/新信息/经营校准仍不通过。专家已开始共因方案，R5正常prepush7047/24skip+142smoke、CI39682544340 SUCCESS。R2零网络4RED/1控制PASS分诊已封存，未标修复。

## 2026-10-21 R5受影响契约共因修复并线

隔离分支f1dba9b7及handoff已cherry-pick，master生产提交a5214bda。195项最终全绿，独审PASS；恢复public扩列反例而非降低断言。三源码在母工作树逐字节SHA等于被测/被审版本；Git LF与Windows CRLF分别记录。正常push/CI尚待本轮结果，不把旧76a CI转签新代码。药明康德initial封存不改，继续四审。

## 2026-10-21 R1首轮封存与四路审查

首家公司封存：639工件/36,665,980B全部SHA一致，RF实际产物partial；四路审查开始。公司累计39,026tokens/$0.009720（含MiMo401 unknown全hold），母账1,544,023tokens/$0.625258。DS成功与缓存零新增收费有原生证据；最新来源/桥接/外部校准/受控恢复未完成，不能用工程通过代签。R5隔离TDD及独审并行，未写母仓代码。

## 2026-10-21 R1恢复：holdout冻结与RF循环准备

用户明确恢复实施。已读取当前PWF、安装的RF审查/RF/FF技能与真实版本；并行只读盘点候选污染、本地原件及旧审查活动。发现既有audit公司池campaign保留NVDA首轮及未完成复验责任，须衔接；DU-BENCH另有已编写gold的holdout，不能自动当作全新盲测。当前未派executor、未新增下载或收费调用。

## 2026-10-21 文档状态统一

核对已发布代码与公开CI，纠正HK独审/核心收据/补写默认关闭/推送状态的过期描述；用唯一状态页统合产品进度、类型质量节点、剩余任务与暂停状态。当前代码CI为76a9440b / run39662983951 success；本轮只改文档，发布结果以本轮Git提交与push输出为准，不重签旧运行收据。

## 历史记录（保留原过程，不作为当前待办）

<details>
<summary>展开历史计划、验证和失败记录</summary>

## 大节点完成：全仓 mypy 0 + CI 全量门禁（2026-10-21）

- `mypy src`：**335 errors / 85 files → 0 errors / 366 files**；`automation`、`source_catalog`、
  `document_understanding`、`document_normalization`、顶层/`source_contract` 全部清零。
- CI：`Strict type check on src`（`python -m mypy src`）替代原 automation-only 步骤；
  job timeout 5→10 分钟。
- 真 bug：`narrative_model_runtime` 的 `scoped.ModelResponseError` AttributeError、
  `routing` 的 `rel.name/rel.score` 字段错误、PyMuPDF `fitz` stdout 污染、
  `parity.run_parity` 的 known_bad 键类型、`reconcile_retire_state` 的 Row→dict。
- 验证：全量单测 **7033 passed / 24 skipped**；相关 contract **113 passed**；
  `ruff` 全仓干净；`compileall` 通过；远端 CI 绿。
- 交接：新增 `HANDOFF-2026-10-21.md`（给后续 harness 的详细交接）。
- 最终绿点：**76a9440b**（CI success；补充修复 Windows-only API 在 Linux 下的类型检查）。
- 质量审计基线仍在：复杂度 292/173/111、lint 扩面约 1000、覆盖率未测、4 个大模块。

---

## 暂停点（2026-10-20 23:55）

- **当前绿点**：`e1f9dc54`，远端 CI success；工作树干净（仅其他计划的 `.planning` 未跟踪文件）。
- **类型棘轮进度**：`automation` 0/57 且已加 CI 门禁；`source_catalog` **182 → 63**；`document_*` 63、其余顶层约 75 未动。
- **本会话额外修复**：PyMuPDF `<2.0` 固定（CI 红根因）、`fitz` 警告污染 stdout（改为 `pymupdf as fitz`）、密钥扫描扩到 `src/tools`、启用 B904/B018/B009/UP034/UP041。
- **恢复后的下一步**：① 清完 `source_catalog` 剩余 63（`narrative_reading`、`adapter_dispatch`、`resolver`、`extraction_quality` 等）并加包级 CI 门禁；② `document_*` 63；③ 顶层约 75；④ 复杂度预算、UP006/UP045、覆盖率基线、配置去重。
- 暂停原因：用户要求先暂停。

---

## 类型棘轮第三批：source_catalog 182 → 84（2026-10-20）

- 清零：`scanner`（15）、`cli`（10）、`assertion_service`（10），以及一批注解/收窄（`narrative_ocr_groups`、`narrative_pdf_intent`、`narrative_reading`、`official_discovery`、`observability`、`reader`、`reconcile_retire_state`、`narrative_visual_units`）。
- 关键修复：`scanner` 的 `store` Optional 用局部 `_catalog_store()` 收窄；`GroupCandidate` Protocol 改为只读 property（frozen dataclass 才能满足）；`reconcile_retire_state` 的 `Row` 显式转 `dict`；CLI 动态异常属性改 `setattr`。
- 后续同批继续清零：`lock`、`download_budget`、`security_code/identity`、`attribution`、`html_capture`、`section_chunk_fact`、`adapters/interface`、`narrative_operating_relations` 等。
- 验证：相关 81 + 68 passed；`ruff` 全仓干净；全量单测 **7033 passed / 24 skipped**；`source_catalog` 剩余 **63 条 / 24 文件**（`narrative_reading`、`adapter_dispatch`、`resolver` 等）。

---

## 类型棘轮第二批：source_catalog（三文件清零）+ stdout 污染修复（2026-10-20）

- `source_catalog` 包 **182 → 121 errors**：`narrative_pdf_candidates`（24）用 `TypeGuard` 收窄快照形状并注解列表；`official_source_flow`（22）修掉动态异常属性与重复 `capture` 变量、收据字典类型；`normalizer`（17）修 POSIX-only `os` 调用、`BaseProcess` 类型、`payload`/`manifest` 守卫。
- **真 bug**：PyMuPDF 1.28 的 `fitz` 兼容层把弃用警告 **打印到 stdout**，污染公开 CLI 的机器可读 JSON（本地干净的 HEAD 上也复现该集成测试失败）。全仓 24 个文件的 `import fitz` 改为 `import pymupdf as fitz`，警告消失，该集成测试恢复通过。
- `pyproject` 的 mypy overrides 增加 `fitz/pymupdf/openpyxl/xlrd`（可选依赖无 stubs）。
- 验证：相关 75 passed；`ruff` 全仓干净；全量单测 **7033 passed / 24 skipped**。剩余 source_catalog 121 条，下一批 `scanner/cli/assertion_service`。

---

## 类型棘轮第一批：automation 包清零（2026-10-20）

- `mypy src/company_wiki/automation`：**15 errors → 0**（57 文件）。修复全部是真问题：
  - `narrative_model_runtime` 用 `scoped.ModelResponseError`，而该模块只在函数内导入它 → 该分支会抛 `AttributeError`（**潜在线上 bug**），改为 `legacy.ModelResponseError`。
  - `narrative_model_caller` 的闭包/恢复路径对 `_paid_responses` 的 None 收窄失效；改为局部绑定 + 显式守卫。
  - `narrative_run_store` / `narrative_model_caller` 对 `paid_response_json` 的 None 直接 `from_json`；补显式守卫。
  - `narrative_selection_generation` / `narrative_generation` 的 sha256 校验、`narrative_model_extractive` 的 `reading_context` 与 `seen` 类型、`narrative_transport` 的 receipt 字典、`cli` 的 events 元组、`supervisor` 的 Job|None、`worker_factory` 的 kwargs 展开。
- CI 新增 `python -m mypy src/company_wiki/automation` 步骤，job 超时 5→10 分钟以容纳它。
- 验证：相关单测 **193 passed**；`ruff` 全仓干净；全量单测 **7033 passed / 24 skipped**。
- 剩余规模（本轮实测）：`source_catalog` **182 errors / 43 files**、`document_understanding + document_normalization` **63 / 14**，其余顶层/`source_contract` 约 **75**。下一批从 `source_catalog` 开始。

---

## 全项目代码质量审计：基线、已修与路线图（2026-10-20）

### 基线（未做过的部分）
- **Lint 策略**：`ruff` 之前只用默认 `E4/E7/E9/F`；扩到 `B/SIM/UP/C4` 有 **1022** 条（主要是 `UP006/UP045/UP035` 类型现代化）。
- **复杂度**：按默认阈值统计 **C901 292、PLR0912 173、PLR0915 111**（这些规则此前未启用）。
- **类型检查**：CI 只查 45 个契约模块；全 `src` **mypy 335 errors / 85 files**。
- **大模块**：`narrative_evidence` 109KB、`resolver` 100KB、`narrative_batch` 100KB、`scanner` 98KB。
- **安全扫描盲区**：CI 的硬编码密钥 grep 只覆盖 `scripts/ tests/`，不含 `src/ tools/`。
- **依赖**：运行时依赖无上限（PyMuPDF 2.0 正是因此破坏 CI）；`pyproject` extras 与 `requirements.txt` 双份维护。

### 本轮已修
- `PyMuPDF>=1.23.0,<2.0` 同步到 `pyproject` 的 `pdf/catalog/all` extras。
- 密钥扫描范围扩到 `src/ tools/`。
- 修复 **21 处 src** 与 **7 处 tests/scripts/tools** 的 B904/B018/B009/UP034/UP041；在 `pyproject` 启用这些规则，`ruff` 全仓干净。
- 验证：受影响用例 **131 passed**；`compileall` 通过；全量单测 **7033 passed / 24 skipped**。

### 后续路线（按性价比）
1. **类型棘轮**：按模块组清零 mypy（automation → source_catalog → document_*），零后把全 `src` 加入 CI。
2. **复杂度预算**：先重构 top 20 函数，再启用 `C901` 阈值（如 20），禁止新增超标。
3. **大模块拆分**：`narrative_evidence/resolver/narrative_batch/scanner` 按稳定接口拆包。
4. **Lint 扩面**：`UP006/UP045`（类型注解现代化）与 `SIM/ARG/B905` 分批 + 计数棘轮。
5. **依赖治理**：为 CI 生成 constraints/lock，或给已验证大版本加上限。
6. **配置去重**：让 `scripts/config.py` 复用 `company_wiki.model_config`，去掉第二份 yaml 解析。
7. **覆盖率**：先测基线，再设 `src` 覆盖率下限。
8. **异常卫生**：非边界的 `except Exception` 逐步收窄并加日志/测试。

---

## CI 红根因：PyMuPDF 2.0 破坏 PDF 文本/表格提取（2026-10-19）

- 用 WSL + Python 3.12 + `pip install -r requirements*.txt`（与 CI 同依赖）稳定复现 3 个 PDF 失败，报错是**文本/表格提取结果变化**：`'Storesbyoperatingmodel'`（空格丢失）、列号 `{0,2}` vs `{0,1}`、缺 `-1,200` 单元格。
- 依赖里 `PyMuPDF>=1.23.0` 未设上限，CI 装到 **2.0**；本地 1.28.2 与 WSL 1.27 均通过。把 2.0 降回 1.28.2 后，同环境 3 个 PDF 用例 + 入口用例 **79 passed**。
- 根因修复：`requirements.txt` 固定 `PyMuPDF>=1.23.0,<2.0`（2.x 的文本提取语义变化需 parser/收据重新验证后再放开）。
- 入口用例在干净环境通过；此前 WSL 用 user-site 安装时失败，判断为环境污染，待 CI 复验。

---

## 模型配置单一化：config/models.yaml（2026-10-19）

- 新增 `config/models.yaml`（schema `company-wiki-models/1`），每个 provider 的 `model` / `base_url` / `api_key_env` 只在这里定义；`config.yaml` 只选 provider（仍可逐项覆盖）。
- MiniMax 模型统一改为 **`MiniMax-M3.1-Flash`**（active config / code / tests / docs）；历史日志、历史 plan、收据不改。
- 移除三处硬编码表：`src/company_wiki/config.py` 的 dataclass 默认值、`scripts/config.py` 的 `provider_defaults`、`scripts/llm_client.py` 的 env/model/url 三张表；两个配置数据类用 `__post_init__` 从单一模型表解析。
- 新增 `src/company_wiki/model_config.py`（加载/校验）与 `tests/unit/test_model_config.py`；`config.yaml` 的 model/base_url 覆盖已删除，单一源生效。
- 验证：affected 45 + 52 + 27 全过；全量单测 7032 passed / 24 skipped（唯一失败是旧断言读 `config.yaml` 的 model，已改为读模型表并复跑通过）。

---

## 远端 CI 红：4 个 PDF/入口测试（2026-10-19 排查）

- `origin/master` 在 `f9d528eb`/`01baa010`/`0bbd2e4a` 三次 CI 均失败，注解固定为同一组：
  `test_shared_reading_pdf_table_policy::test_actual_store_matrix_discovery_does_not_require_recent_event_word`、
  `test_shared_reading_pdf_layout::test_find_tables_and_extract_are_reused_once_and_cells_have_real_separate_columns [unknown_error]`、
  `test_legacy_entrypoint_simplification::test_permanently_retired_entry_exits_before_initialization[batch_ingest.py-plain]`、
  `pdf_table_observations.test_7_real_pipeline_pdf::test_real_parse_produces_observations_that_bind_and_slice_back`。
- 本地（Windows/3.13）四文件 **151 passed**；WSL（Linux/3.12）同组用例 78 passed（仅 1 条因 WSL 缺 `opencc` 失败）。`ef3f3d1c` 的 CI 在同一条代码血缘上成功。
- 已试把 runner 固定到 `ubuntu-24.04`：同样 4 条失败，已 revert；`ubuntu-latest` 的迁移通告不是充分解释。
- 结论：判断为**环境/PDF 栈**问题（pymupdf/字体/磁盘），非本次改动；需要认证日志看断言才能继续定位。CI 恢复前不宣称绿。

---

## 质量审查与临时物清理（2026-10-19）

- **静态检查**：CI 同范围 `ruff` 全通过；CI 列出的 45 个契约模块 `mypy` 无问题；`compileall` 通过；src/tests/tools 无 `breakpoint`/`pdb`/`TODO`/`FIXME` 遗留。
- **P2 质量根因修复**：`ZipInfo.create_system` 在 Windows 默认 0、Unix 默认 3，导致同一夹具跨平台哈希不同；已固定为 0。`test_fixtures_manifest` 原来每次运行都重写已提交夹具（违反“测试目录原样恢复”），已去掉写入，改为只做字节相等断言。
- **WSL 下 9 个 P2 失败**：定位为 WSL 系统 Python 缺 `python-pptx`（`dependency_unavailable`），不是代码缺陷；CI 安装依赖后全绿。
- **清理**：删除 `.mypy_cache`/`.pytest_cache`/`.ruff_cache`/`__pycache__`、`.tmp`、`.tmp-e2e`、`.tmp_du5`、`tmp/`（约 78 MB）；`.planning/shared-reading-production/du11` 的 62 个 live 运行目录裁到 5 个（CN b2v3w/b2v4e/b2v5i、US b2v3、HK deepseek），账本 `usage.jsonl` 与 metadata 保留；`.gitignore` 补上三个缓存目录。
- **注意**：本地跑测试需要 `C:\Users\郑曾波\Projects\cwp-temp` 作为 TEMP/TMP；删掉它会让 `test_w04_source_transport` 报 `unable to open database file`，已重建为空目录。
- 全量单测：**7029 passed / 24 skipped**（唯一一次失败是该临时目录被删导致，重建后该用例 18 passed）。

---

## P3 两条 Linux 失败已修，远端 CI 绿（2026-10-18）

- 复现：WSL Ubuntu（Python 3.12.3，与 CI 同版本）跑两条用例 → 稳定失败，断言差异是 `catalog/catalog.sqlite3-shm`。
- 根因：fixture 目录库是 WAL 模式；Linux 上审计子进程的只读打开会创建 `-shm`，被“除 out 文件外不得写任何东西”的断言抓到（Windows 上该文件由写连接常驻，故不可见）。
- 修复：`tests/unit/test_identity_audit/p3_fixtures/sidecar_catalog.py` 在建好 fixture 后关闭写连接、切 `journal_mode=DELETE` 并清理 `-wal/-shm`。
- 验证：WSL 3.12 两条用例 **2 passed**、P3 全 lane **50 passed**；Windows 本地 P3 lane **50 passed**。
- **exact CI**：`ef3f3d1c`，run 374（id 39164683463），**success**。

---

## CI 命令恢复绿：fixtures 包冲突已修（2026-10-18）

- 根因：`tests/unit/test_identity_audit/fixtures`（常规包，原名 `fixtures`）与共享的 `tests/fixtures`（命名空间包）同名；谁先被导入谁占住 `sys.modules['fixtures']`，另一侧就 15 个 collection error。
- 修复：P3 的包改名为 `p3_fixtures`（含契约测试断言），并加 lane conftest 固定 `tests/` 在 `sys.path[0]`。
- 结果：`python -m pytest tests/unit`（Miniconda，CI 命令）**7030 passed, 24 skipped**，exit 0。

---

## 内容验收口径更新：数字可以近似，但不能错（用户，2026-10-18）

- 用户明确：精确数字丢失问题不大（例：写“超过 7,500”可以），但**不能写错**（例：写“少于 7,000”不允许）。
- 按此口径重评：HK（DeepSeek）由 5/7 改为 **7/7、critical 6/6 通过**——两处“PARTIAL”都只是近似（7,500+/近4,400/超過3,100），没有一条与金标矛盾，也没有触发 must_not_assert。
- 剩余缺口性质变化：CN（8/10）缺的是**两条完整事实**、US（2–8）缺的是多条事实，不是“数字写错”。下一步应针对“漏事实”（表格事实单独任务/补写），而不是精度。

---

## 两个长期失败测试已按用户决定删除（2026-10-18）

- 删除 `tests/contract/test_fresh_cache_behavior_receipts.py`（parser pin 缓存前提与现行“按源字节复用”语义不符）与 `tests/integration/test_shared_reading_production_e2e.py` 中 `test_official_projection_...`（LOCATOR_REPLAY_FAILED；同文件其余 4 例保留）。
- 两者均未被 CI workflow 或队列表引用；删除目的是解除 pre-push 阻塞，不改变产品行为。

---

## P1–P4 施工包已由 ROOT 接收（2026-10-18）

- 四包全部合入本地 `master`：P1 `09a8dded`（40 tests，ruff/mypy 干净）、P4 `626eb32f`（fixtures catalog 下 34 passed，无 env 时 34 skipped 按设计）、P2（70 passed，独立复审 PASS）、P3（50 passed，独立复审 REJECT→APPROVE）。P1 接收时把重名的 `synth.py` 改为 `p1_synth.py`。
- 合并后全量单测：**6910 passed, 24 skipped**（687s，Miniconda 解释器）；`origin/master` 仍停在 `ccc5bc7e`，推送仍被两个既有失败测试挡住。

---

## C 内容按 8/10 收尾（用户决定，2026-10-18）

- 用户确认：C 内容按 **CN 8/10** 收尾，不再为最后 1–2 条事实继续烧真实调用。
- 已交付：B2 最终复审 PASS；**exact CI 仅覆盖 `2a80acf6`**（`b2-final3-20261018/ci-39139605025.json`，B2 唯一精确 CI）；三源回放绑定当前代码；C 工程侧 receipt/恢复/缓存/FF-RF 证据在**工作区** `.planning/shared-reading-production/du11/`（未入 git，fresh clone 不可复核）。
- **交付状态须知（2026-10-18）**：本地 `master` 领先 `origin/master`（`ccc5bc7e`）**7 个提交、未推送、无 exact CI**；`origin/master` 仍是无条件补写版（"默认关闭"只在本地未推提交，本地开关另推在分支 `du11-repair-flag`）。P1–P4 四张施工卡已在本地 `codex/p1..p4-*` 分支实现完毕，状态为 **IMPLEMENTED_PENDING_ROOT_RECEPTION**，不是 READY_TO_DISPATCH。
- 已知缺口（如实交接）：CN required 8/10（critical 5/7）、US 2–4/8；**HK 已于 2026-10-18 用 Windows 用户环境变量的有效 DeepSeek 密钥跑通**（1 次 POST、16,813 tokens / $0.00742、activation recovery PASS、receipt PASS）；独立内容复审 **5/7 required、critical 4/6 → CONTENT_FAIL**（无 VIOLATED；门店合计 7,504/内地 4,386/海外 3,118 被写成标题与约数，未落精确值）。覆盖修复（两次调用）为实验性、默认关闭。
- **模型评估计划（后续独立课题）**：① 先换有效 DeepSeek 密钥，用同一协议跑一次 CN；② 用同一份请求对照一个更强模型，区分“任务形状”与“模型能力”；③ 多模型只用于审计（查漏/查引用），不交叉生成摘要；④ 固定验收矩阵：严格 JSON 成功率、claims 数、required 覆盖、单位/期间错误。

---
## 覆盖修复（A）：两次调用已跑通，卡在 activation-resume 的预约冲突（2026-10-18）

- 修了三个真问题：`HandlerResult.result` 是不可变 Mapping（`isinstance(dict)` 永假，导致补写退化成重发全量请求）；prior 摘要 wire 需转 plain 容器；phase C 的 `gold_observation` 只接受全量 material，补写子集被 AssertionError 挡下。
- 实测（`CW_SUMMARY_COVERAGE_REPAIR=1`）：CN **两次 POST**（28,045 tokens / $0.005134），摘要成功、run 进入 `activation_pending`，说明补写链路本身工作。
- 但 `activation-resume` 复跑时 `ReservationConflictError`：重试 attempt 的 reservation 与恢复路径重新计算的请求哈希冲突。
- 补写默认关闭**仅存在于本地未推提交**；`origin/master`（`ccc5bc7e`）仍无条件执行补写（覆盖不全时多两次调用）。C 内容仍 8/10。下一步：让 resume 复用/跳过已结算的补写 attempt，或允许同一 attempt 的相同请求哈希复用。

---
## B2 定稿：最终复审 PASS（2026-10-18）

- 最终复审 `b2-antecedent-final-review-20261018-v3.md`：**PASS（代码层），无 P1**；两个复审 P1（长名称截断、截断误判为 missing）已修并各带回归测试。
- `tests/unit/du11_source_closure` **110 passed**；ruff 通过。
- 三源回放绑定当前代码：CN 10/10（`b2-final3-20261018`）、HK 7/7、US 8/8（`b2-real-sources-final2-20261018`）；work 6,133,095 / 13,157,181 / 7,989,484；原件/gold 未变、0 API。
- CI `2a80acf6` success，收据 `b2-final3-20261018/ci-39139605025.json`。

剩余唯一未完成项：**C 内容验收**（产品决策 A 二次调用 / C 换模型）。

---
## C 第九轮：4.0.8 覆盖指令回归，已回退（2026-10-18）

- 第四轮 CN 复审（4.0.8，14 条 claims）：required **6/10**、critical **4/7**。上一轮缺的 30%/60% 已关闭，但 InP、SiC 回归缺失，PD5 仅 partial 且与 gold 的 must_not 冲突，另有一条 claim 文本损坏（“上\nte海临港”）。
- 结论：4.0.8 的“必须包含覆盖率/多年目标”指令压缩了其他更新，整体变差 → 已 **revert**（`46ffee41`），恢复 4.0.6（22 条、8/10）。
- 单次调用路径的最佳记录仍是 4.0.6 的 **8/10**；继续 prompt 微调只会换一条漏项，且已两次引入回归（72 条超限、6/10）。

**Next Step：** 需要产品决策：A（覆盖修复二次调用，改 paid-admission）、C（换模型）、D（调整验收标准）。不再做 prompt/上限类实验。

---
## C 第八轮：section 任务合并实测失败并回退（2026-10-18）

- 实现：把相邻同页同节的 citation view 合并为至多 5 个成员的任务（CN fixture 64→40），所有 96 个 span 仍恰好定义一次，support/context partition 校验通过；103 个 scoped 测试绿。
- 实测：两次 CN live 均 `MODEL_RESPONSE_INVALID`（模型返回畸形 JSON，119 bytes 级），说明多成员任务的 parts/support_parts 结构反而让 MiMo 失稳。
- 处置：`4a983c98` 推送后按规则 **revert**（`12914f62`），恢复 40 任务 + prompt 4.0.6 的已知稳定行为；不保留未验证的合并路径。
- 结论：B 路径（任务合并）在当前模型上不可行；剩余只有 A（覆盖修复二次调用，需改 paid-admission）或 C（换模型）或 D（调整验收标准）。

---
## C 第七轮：菜单排序/截断不能消除覆盖缺口（2026-10-18）

- 业务优先排序 + 截断 36：28 条，覆盖 30%/60%、PD5、Micro-LED、Preciomo、众硅，仍缺 InP——材料序里 InP 任务排第 40 位，被截断。
- 截断 40（含 InP 任务）：21 条，**仍缺 InP**——模型自己只写 21 条并跳过该任务，不是菜单位置问题。
- 结论：单次调用下 MiMo 写 20–28 条、MiniMax 写 5–8 条，模型自行选择任务；`NarrativeModelCaller` 的契约是 “exactly one model attempt”，二次补写需要改 paid-admission 架构。仅靠 prompt/上限/排序已无法稳定覆盖 10 条 required。
- 用 MiMo 跑 US 的诊断被 runner 的 `PREPARATION_FINGERPRINT_CHANGED`（gold/hk-annual.json）拒绝，未执行，未产生费用。

**阻塞点：** C 内容验收的最后 1–2 条 required 需要产品决策（二次调用 / 换模型 / 调整验收标准）；单次尝试架构下继续调参只能得到 8/10 且缺口每次不同。

---
## C 第六轮：CN 8/10；单次调用的覆盖存在方差（2026-10-18）

- 第三轮内容复审：**CN required 8/10、critical 5/7**；上一轮 5 个 P1 全部关闭（PRISMO PD5、InP、三条 claim 质量），只剩未来五年 60%/70% 与当前 30% 两条——它们在**同一段 t13**。
- 方差实验（均真实计费，全部已回退到 HEAD）：target 15 覆盖 30/60 但缺 InP；40 上限（已推送的 b2v3w）22 条、8/10、缺 30/60；业务优先排序 26 条、覆盖 30/60+InP+Micro-LED、缺 PD5；上限 60 只写 21 条、覆盖 PD5+30/60、缺 InP。
- 结论：单次调用下模型自行选择约 20–30 个任务，**覆盖的 required 子集每次不同**；把上限从 40 提到 60 并不增加产出量。稳定 10/10 需要“覆盖修复”的第二次调用（只对未覆盖任务再问一次并合并），或换用产出更完整的模型。
- **US（MiniMax）**：同一 prompt 只写 5–8 条（MiMo 20–30 条）；提高上限、加强“每 task 必须一条”的措辞（曾致 MiMo 72 条超限）都无效；两次调用是唯一可行路径。

**Next Step：** 产品拍板 ① 覆盖修复二次调用（保留三供应商，需扩展计费/缓存）或 ② US 换 MiMo；之后重跑 CN/US 并做最终内容复审；HK 等 DeepSeek 密钥。

---
## C 第五轮：40 条预算生效，CN 覆盖关键事实；US 模型产出过低（2026-10-18）

- 发现并修复一个 live 专属回归：把 `MAX_SUMMARY_CLAIMS` 传进 `compile_scoped_model_view` 会改变 task-plan binding 标记，worker 在模型调用前以空消息 `HANDLER_EXCEPTION` 死信（0 tokens）。绑定标记保持 20（wire 兼容），**有效预算走 `output_plan.max_claims=40` 与解码器**。
- **CN（MiMo）**：PASS，1 POST，15,970 tokens / $0.002968，**22 条 claims**；已覆盖 PRISMO PD5、InP/磷化铟、Micro-LED、Preciomo Udx、众硅/CMP。
- **US（MiniMax）**：PASS，1 POST，19,115 tokens / $0.009165，但**只写 5 条**，Azure consumption、RPO 375B/368B/40% 仍未覆盖。同一 prompt 下 MiniMax 的产出量（5–9 条）远低于 MiMo（22–30 条），属模型遵从度差异。
- 结论：CN 已接近内容验收；US 需要在“换模型 / 二次补写调用 / 接受部分覆盖”之间做产品取舍（见上一节四选项）。

**Next Step：** 第三轮内容复审确认 CN 覆盖；US 取舍拍板后执行；HK 等 DeepSeek 密钥。

---
## C 第四轮：scoped 摘要 claim 上限 20→40，CN 覆盖全部关键事实（2026-10-18）

**取舍与理由：** 64 个候选任务组配 20 条 claim 预算时，真实模型只能覆盖部分关键事实；历史上覆盖最好的 22 条版本（CN 8/10）被旧上限整单拒绝。将 **scoped 路径**（v4/v5）的 `MAX_SUMMARY_CLAIMS` 提到 **40**、`target_claim_count=36`；v1–v3 legacy 仍保持 20，不受影响。

- **CN（MiMo）：PASS**，30 条 claims，15,746 tokens / $0.002893；已覆盖 PRISMO PD5 阶段、InP/磷化铟、Micro-LED、Preciomo Udx、众硅/CMP 收购、当前 30%、五年 60%/70%。
- **US（MiniMax）：PASS 但只写 8 条**，Azure consumption、RPO 375B/368B/40% 仍缺；同一 prompt 下 MiniMax 的产出量显著低于 MiMo，属模型遵从度差异，待第三轮内容复审确认后再决定（换模型或分块二次调用）。
- 触发点：`validate_against` 等共享校验不设 20 上限；scoped 解码器与请求构建统一用 `MAX_SUMMARY_CLAIMS`。

**Next Step：** 第三轮内容复审（CN 预期接近 10/10，US 仍不足）→ 决定 US 的处理方式 → HK 等密钥。

---
## C 第三轮配置：全量视图 + target 15；内容覆盖仍是瓶颈（2026-10-18）

- 第二轮内容复审（view 收敛到 20 个任务时）：CN required **2/10**（critical 2/7）、US **4/8**（critical 4/8），均 CONTENT_FAIL。复审明确指出 20-task 位置抽样把上一轮已覆盖的 f-five-year-target、f-current-coverage、f-cmp-acquisition、f-microled-sample 等又丢了——**位置抽样不可用**。
- 已回退“按位置抽样”的视图收敛；恢复全量 64 个任务，改为：schema 每 task 至多 2 条、prompt `4.0.5` 要求 `target_claim_count=15`（给 20 条硬上限留 5 条余量，因为 MiMo 在 target 18 时仍输出 21 条）。
- 最新 CN（`live-cn-h1-b2v3r-20261018`）**PASS**：1 POST，15,382 tokens / $0.002772，15 条 claims；已覆盖 CMP 收购、当前 30%、五年 60%/70%、Micro-LED、Preciomo Udx；仍缺 InP 与 PRISMO PD5。
- 结论：**工程验收已稳定，内容验收未达成**。20 条 claim 上限对 64 个候选任务组，模型实际只写 15–22 条，且每次覆盖的 required 子集不同；这是“预算 vs 候选集 vs 模型遵从度”的结构问题，继续微调 prompt 的收益在递减。

**Next Step（需产品取舍）：** ① 提高 claim 上限（20→24/28）；② 为 selector 增加可传递的值分数，按分数而非位置选视图；③ 换用能稳定遵从 20 条上限的模型；④ 接受部分覆盖并在收据里显式列出未摘要任务。选定后重跑 CN/US 并交内容复审。

---
## C 第二轮：模型视图收敛到 20 个任务，CN/US 再次 PASS（2026-10-18）

**根因：** 任务计划有 64 个 citation view，却只有 20 条 claim 预算。真实模型因此出现三种失败：只写 8 条（覆盖不足）、写满 64 条（`CLAIMS_LIMIT`）、把 task-local part key 串错（`EVIDENCE_REFERENCE`）。

**修复：** 模型视图只暴露 **20 个任务**（按文档位置均匀抽样，避免摘要压缩在开头章节）；完整 plan 仍保留 64 个任务供覆盖统计；prompt `4.0.3` 要求约 18 条、每 task 至多 1 条。

- **CN（MiMo）：PASS**，1 POST，9,843 tokens / $0.001798，13 条 claims；InP/磷化铟已覆盖，PRISMO PD5 阶段仍缺。
- **US（MiniMax）：PASS**，1 POST，10,829 tokens / $0.005353。
- 第二轮内容复审进行中（上一轮 11 条 P1 逐条复核）。
- HK 仍被无效 DeepSeek key（401）阻塞。

**Next Step：** 内容复审结论 → 关闭剩余 P1 → US/CN 定稿；HK 密钥轮换后补跑。

---
## 正式 C 内容审查：CN/US 均 CONTENT_FAIL；两处根因已修（2026-10-18）

独立内容审查（非作者，只读）：**CN CONTENT_FAIL**、**US CONTENT_FAIL**。

- CN：required 命中 8/10（critical 5/7），缺 PRISMO PD5 阶段与 InP 起步；另有 3 条 claim 质量问题（“该新产品”未闭合、源句截断、从句中起头）。
- US：required 命中 2/8，缺 6 个 critical（Azure consumption-based、三段结构、2024-08 分部重组、RPO 375B/368B 与 40% 前瞻）；8 条 claim 本身逐字、数字正确。
- 两者：无评级/目标价/估值，语言保持 zh/en，未发现数字或单位换算错误。报告：`review/c-content-review-20261018.md/json`。

**根因与修复：**

1. 任务计划有 **64 个 citation view** 对 20 条 claim 预算，模型只写 8 条；schema 每 task `maxItems=1` 进一步压制覆盖。已把 per-task 上限做成动态值并在 4.0.2 指令中要求“每个有直接支持的 task 输出一条，直到预算”。
2. MiMo 某次把 clause 输出成 **JSON 字符串数组**（双层编码），被判 `CONTRACT_INVALID`；解码器现在容忍一层编码并保留全部合同校验（新增 transport 控制测试）。
3. 曾尝试按 `max_claims` 截断任务计划，但违反既有合同“claim limit never silently drops source tasks”，已回退（160+ 任务测试保持绿）。

最新一次 CN 重跑因 `MODEL_TIMEOUT` 失败（provider 延迟），不是合同问题；US 待用 4.0.2 重跑。HK 仍等 DeepSeek 密钥轮换。

**Next Step：** 用 4.0.2 重跑 CN/US → 再次独立内容审查 → HK 密钥修复后重跑 → holdout。

---
## 正式 C：CN(MiMo) 与 US(MiniMax) 真实 PASS；HK(DeepSeek) 被无效密钥阻塞（2026-10-18）

**根因修复（摘要 claims 上限）：** `max_claims=20` 只写在自然语言指令里，而响应 schema 的每个 task 数组允许 20 条，模型按 schema 输出 22 条 → `SUMMARY_INVALID / CLAIMS_LIMIT`。修复：`output_plan.max_claims_per_task = 20 // task_count`，响应 schema 的 `maxItems` 改为该动态值，prompt 版本升到 `reading-source-scoped/4.0.1` 并在指令中引用；新增 3 个控制测试。

**CN（MiMo `mimo-v2.6-flash`）：PASS。** 1 次 POST，15,394 tokens / $0.002783；`activation_recovery.status=PASS`（同 attempt、无新增 charge）、`cross_run_zero_POST=true`、exact-ref PASS，artifact `fe70c9f0…`。收据：`live-cn-h1-b2v3i-20261018/receipt.json` 与 `overall.json`。

**US（MiniMax `MiniMax-M3`）：PASS。** 1 次 POST，18,093 tokens / $0.007782；同一恢复/缓存链 PASS，artifact `fb73610d…`。收据：`live-us-10k-b2v3-20261018/`。

**HK（DeepSeek `deepseek-flash`）：BLOCKED。** 真实调用返回 `MODEL_HTTP_CLIENT_ERROR` 401；直接探测确认 `DEEPSEEK_API_KEY` 无效（API 原文 “Authentication Fails … ****449c is invalid”）。未替换 provider、未伪造数据；需要轮换该密钥后重跑 HK。

**临时目录根因：** Python 子进程在本机 `%TEMP%` 和 `C:\` 根目录创建目录被 ACL 拒绝（WinError 5），`tempfile.mkdtemp` 因此反复重试——这就是此前多次 C 卡在 preparation 的原因。改到 `C:\Users\郑曾波\Projects\cwp-temp`（仓库外、可写）后全部通过；未改生产配置。

**累计账：** ledger **44 个唯一 attempt，900,711 tokens / $0.238405**（去重口径，核对于 2026-10-18；不含 metadata 记录的历史基线）。HK 的 401 没有结算发票，但有一条 **69,046 tokens / $0.031208 的 unknown 预算占用（hold）**，按规则不能计为零。

**Next Step：** CN/US 摘要交独立内容审查（关键事实、指代、主体、单位/期间、当前/未来）；HK 等密钥轮换后重跑；之后 holdout 与 RF 审查循环。

---
## B2 性能修复已发布；正式 C 受本机负载阻塞（2026-10-18；优先于上一节）

- `6a2ee853` 已推送：声明回看改为 64 字有界窗口 + 按原文缓存，单次 26ms → 3.7ms（缓存命中约 0）；CI `39123679375` success。105 测试与三源召回不变。
- 正式 C 共尝试 5 次：第 1 次跑完选择→真实 POST→activation 恢复→cache→cross-run→read→reference 全链，但 `TEMP` 未设置使临时湖建在仓库内，收尾断言失败、receipt 未写出（真实计费 15,141 tokens / $0.002722，重复 ledger 行按 attempt 去重）。第 2–5 次均在 preparation 阶段超过 15 分钟只有 `preparation.json`；py-spy 显示卡在 `tempfile.mkdtemp`，且本机另有两个 agent 各占约 1,500s CPU。第 5 次改用收窄 root + `C:\cwp-temp` 干净临时目录仍无进展。
- 结论：**C 仍 OPEN**，当前具体阻塞是本机资源争用/临时目录，不是 B2 语义；已停止所有未完成的付费 run，未再产生费用。
- 本地门禁仍被两个非 CI 范围的测试挡住（`test_fresh_cache_behavior_receipts`、`test_official_projection_...`），shim + runner 守卫保存在 parked patch，未推、未绕 hook。

**Next Step：** 等机器空闲窗口重跑 cn-h1 live（干净临时目录、narrowed root）；同时定位两个合同测试；之后再推 shim/guard。

---
## B2 三审：中文泛称与 head 匹配已修（2026-10-18；优先于上一节）

三审仍判 **REJECT**（工程 7/10、合同 5/10）：v2 的 P1-B、P2-A、P2-D 关闭；P1-A 只修了拉丁泛称，另发现新 P1（head 不比较）。已修：

- **P1-A 中文泛称**：声明改为“先找 head、再向前取专名”，并剥离 公司/推出/开发/销售 等前缀；加入技术描述词与产品 head 黑名单、计量词/指代词拒绝。`公司主要产品系列`、`各类产品`、`所有系列`、`上述系列产品`、`前道集成电路设备产品`、`可覆盖存储器件` 均不再成为声明。
- **P1-B head 匹配**：series 指代只接受 series 声明，device 只接受 device；泛称 `these products` 仍接受任意产品声明。`Omega设备` 不再闭合 `该系列产品`。
- **P2-A 专名形态**：支持 `iPhone 15系列`、`Model 3系列`、`3M系列`、`Preforma uniflash系列`、`小米系列产品`（系列后缀从名字挪到 head）。
- **P2-B 前置枚举**：新增 `包括A、B在内的X系列` 这一形态；同句客户列举不再误挂。
- **P2-C 归属**：`公司客户…` → quoted；`公司表示客户…` → issuer。
- **P2-D 泛称英文**：`products or services`、`internal control`、`accounting systems` → not_applicable，US 未闭合从 11 降到 6。

测试 **105 PASS**；selection/w04 **738 PASS**。三源回放：CN 10/10、HK 7/7、US 8/8；work 6,133,095 / 13,157,181 / 7,989,484；收据 `b2-v3-20261018/`、`b2-real-sources-v3-20261018/`。

**正式 C 的进展与阻塞（如实记录）：**

- 首次 cn-h1 live（`live-cn-h1-b2v3-20261018`）跑完了选择→真实 POST→activation 恢复→cache→cross-run→read→reference 全链，但收尾断言失败：本机 `TEMP` 未设置时 `tempfile.gettempdir()` 回退到仓库目录，runner 在仓库内建临时湖，最后 `ROOT not in root.parents` 断言失败；**receipt 未写出**。真实计费已入母账（attempt `76fe00f0…`，15,141 tokens / $0.002722）。
- 母账该 attempt 出现两行重复（`append_native` 追加两次），`mother_totals` 按 `(database, attempt_id)` 去重，累计不受影响；文件保留不改。
- 第二次显式设置 temp 重跑（`live-cn-h1-b2v3b-20261018`）超过 20 分钟无产出，已停止进程；仅 preparation/harness 两文件，未写 receipt。原因待查（非网络连接态）。
- 结论：**C 仍 OPEN**；需先修 runner 的 temp 前置校验（应在付费前 fail fast），再以 loopback 验证链路耗时，然后重跑真实三源。

**Next Step：** 提交/推送本轮 B2 修复 → 修 runner temp 前置校验并补测试 → loopback 计时 → 重跑 cn-h1 live。

---
## B2 复审 v2：2 个新 P1 已修（2026-10-18；优先于上一节）

复审仍判 **REJECT**（工程 7/10、合同 5/10）：v1 的 P1-1/2/3/5 关闭，P1-4 部分关闭（furniture 邻接错误），另发现 P1-A/P1-B 与 6 个 P2。已逐条修复：

- **P1-A 泛称伪声明**：拉丁名改为“大写专名 token 序列”，CJK 名排除公司/产品/这些/计量词；`We sell products…`、`Our products…`、`公司产品系列丰富`、`这些产品线` 不再成为声明。
- **P1-B furniture 邻接**：回溯改为与“最后保留的 unit”比较，并记录被跳过的 proven furniture 数；跨页 carry 仍按真实邻居 `(p1,p2)`，错误 carry `(p1,header)` 不再接受。
- **P2-A** deictic 先识别实际 head（含系统/平台/方案），不支持的 head 回退 legacy，不再把“这些平台”当产品。
- **P2-B** collective marker 必须出现在声明之后，同句客户列举不再挂到产品系列。
- **P2-C** 客户/供应商主导句判 `quoted_related_party`（不捐赠），公司主语判 `issuer`；新增正反例。
- **P2-D** 重跑三源并绑定最终代码：bindings 含 `product_reference a1300818`、`narrative_antecedent 41d42ef7`、`relations dce431d9`、`narrative_reading ddc36db5`；`deferral_reasons` 三源均可见（CN 5、HK 2、US 11 unresolved）。
- **P2-E** 新增 9 个负例/正例：泛称句、unsupported head、同句 collective、attribution 正反、furniture carry 正反、separate-window。
- **P2-F** 同页跨窗口由 ordinal 证明；跨页只认已证明窗口边，separate-window 不桥接（有反例）。`SourcePageFlow` 只暴露汇总、不暴露边，故不接线并如实记录。

测试 `tests/unit/du11_source_closure` **99 PASS**；selection 738 PASS；全量 unit 见 progress。真实三源：CN 10/10、HK 7/7、US 8/8，work 6,133,095 / 13,157,181 / 7,993,449，0 API、原件/gold 不变。收据：`b2-v2-20261018/`、`b2-real-sources-v2-20261018/`。

**Next Step：** 三修后复审 → 提交/推送核精确 CI → 正式 C。

---
## B2 独立审查 REJECT → P1 全修（2026-10-18；优先于上一节）

独立审查（非作者 agent，绑定 family-scope 快照 SHA）结论 **REJECT**：工程完整度 6/10、合同一致性 4/10，P1×5、P2×11。已逐条修复，报告见 `review/b2-antecedent-independent-review.md`。

**P1 修复：**

- P1-1 声明上下文端到端：`_candidates` 现在把声明的原始 unit id 同时写入 budget 包与原始 eligible 包；`_context`/citation view 的 target 组变成 support=target、context=declaration（新增 `select_reading_evidence` 端到端断言）。
- P1-2 envelope 命名空间：声明按原始 id 计数，carrier 通过 `expand` 展开为全部 originals；不再拿 carrier id 查 `original_units`。
- P1-3 offset：声明/成员 ref 直接在原文上匹配（不再用压缩空白的匹配视图），CJK 换行场景新增回放断言。
- P1-4 跨页：从 continuity window 导出 `page_carries` 并传入窗口构建；未证明物理顺序 → `complete=False`/`partial`；proven running furniture 可跳过；`project_for` 与真实 section key 接线。
- P1-5 内部声明：只接受 deictic **之前**的声明；forward declaration → `missing`；两个内部 family → `ambiguous`。

**P2 修复：** 单卡 reference deferral 不再让整篇 `status=partial`/`coverage_complete=False`；unread/unproved/cap → `partial`；envelope block key 改为 `(parent, page, pdf_block)` 且 carrier 展开；坐标缺失不再借为相邻；collective members 只取声明所在句；attribution 按 role 保守判定；产品 head 词表改为 `PRODUCT_SUFFIX` 子集＋import 断言（无第二套词典）；reference deferral 前置于 128 截断；probe `source_bindings` 绑定 3 个新模块；readiness 异常统一转 `partial`。

测试 `tests/unit/du11_source_closure` **90 PASS**（新增端到端 context、forward、内部 ambiguous、换行 offset、carrier envelope、跨页 carry、文档状态、collective 负例、客户声明不可捐赠）。

真实三源（修复后，0 API、原件/gold 不变、同 16M）：CN 10/10、HK 7/7、US 8/8；work 6,133,095 / 13,157,180 / 7,987,497。CN 收据首次可见 `REFERENCE_UNRESOLVED=3`、`REFERENCE_ENVELOPE=1`；t32/t34 精确 SHA 仍 `selected_matches=0`。收据：`b2-reviewed-final-20261018/`、`b2-real-sources-reviewed-20261018/`。

仍未关闭（如实记录）：单数产品指代按计划保留 legacy admission；第三方归属只做句内启发式（`THIRD_PARTY` 出现在声明前且无 `ISSUER_WORD` 即不捐赠），不做完整引述解析；运行期 selection cache 是否因语法模块字节变化而失效未验证。

**Next Step：** 复审 → 正常提交/推送/核精确 CI → 进入正式 C。

---
## B2 有界先行词工程节点完成（2026-10-18；优先于历史）

B2 已按 `review/antecedent-source-interface-final.md` 实现，并跑通真实三源回放。状态：**ENGINEERING_GREEN（独立审查/发布进行中）**；正式内容 C 仍 OPEN。

本轮改动（只扩展现有责任层，没有第二套 detector/Store/预算/产品词典）：

- 新增 `document_understanding/operating_states/product_reference.py`：产品 deictic 与具名声明/集体枚举的纯语法；单数指代与族指代分开标记。
- `OperatingRelationSession.reference_closure()`：按 target + 有序 predecessor + window_complete 缓存，返回 `not_applicable/unique/collective/ambiguous/missing/partial`；声明 ref 保持原始 namespace。
- 新增 `source_catalog/narrative_antecedent.py`：按真实 source ordinal 的有界前驱窗口（同 source/section/project/role/kind，连续性不足即停，cap 截断标记 incomplete）＋ 联合 envelope（8 原 unit、4 个 `(source,page,pdf_block)`、2048 原文字符）。
- `SourceOperatingSession` 增加 originals 只读回退、antecedents、`reference()`；声明 ref 按自身原文校验，不经过 target offsets 重映。
- `_candidates` 把 readiness 前移到 graph 与任何 fact/cache 之前；`ambiguous/missing/partial` 只 defer 该卡（`REFERENCE_UNRESOLVED`），envelope 超限只 defer（`REFERENCE_ENVELOPE`），`unique/collective` 把声明原 unit 计入 required context。

范围收敛（详见 findings）：只有**族/系列指代**（系列、产品线、上述、前述、这些、该等、these/those/such）进入门禁；单数「该设备/该产品」保留 legacy admission，避免把没有跨窗身份主张的句子误 defer。该收敛由 4 个既有 selection 测试暴露后决定，不是放宽断言。

真实三源回放（0 API、0 原件副本、原件/gold 前后 SHA 不变、同 16M 账户）：CN 10/10、HK 7/7、US 8/8；selected 96；CN 6,141,589、HK 13,171,440、US 7,993,452 work units。t32/t34 精确 SHA `selected_matches=0`；p17「该系列设备已付运」以 `REFERENCE_UNRESOLVED/missing` 显式 defer；CN withheld 137（`REFERENCE_UNRESOLVED` 2、`REFERENCE_ENVELOPE` 1、其余为既有非可选/预算）。收据：`b2-family-scope-20261018/`、`b2-real-sources-20261018/`。

测试：`tests/unit/du11_source_closure` 78 PASS；全量 unit 结果见 `progress.md`（4 项宿主环境失败不计本节点，逐项列出原因）。

**Next Step：** 独立审查 → 修复确认项 → 正常提交/推送并核精确 CI；之后才进入正式 C（三供应商原语言摘要、付费恢复、同/跨 run 缓存、FF/RF 真实消费），不得用本节点工程绿或金标命中代替内容 C。

---
## 当前两卡接收与发布结果（2026-10-18；优先于历史）

接手下一主线时先读[DU11 当前主线接手指南](review/harness-handoff.md)；本文件后续各节定义 B2 的详细行为和测试合同。

RF/FF两张DU11卡功能工程已接收、全部交付提交进入各自主线。CWP producer先发布0ccdc689（6801PASS24SKIP346.26s＋142合同PASS48.31s，精确CI39094787278 success）；RF runtime f8002f5f（18独立行为接收、416PASS＋36子测、CI39092538354 success、6源码定点安装）；FF最终e8740748（873PASS7SKIP78subtests91.13s、精确CI39095654355 success、6物理源码依赖序原子安装，双根imports/help通过）。RF唯一兼容版本表两阶段正常更新：e7364639的wiki pin/CI39094965965 success，再9669c4d7收敛filing=e874、wiki=0cc、revenue=f800，最终416PASS＋36子测73.74s、远端一致，精确CI39095818018已completed/success，三仓本次发布CI全部绿。

正常FF发布共3次尝试=2RED+1GREEN：先修异构schema类型丢失及既有mypy hook漏掉transitive scripts依赖，再修旧“未知日期”夹具缺provider导致测试错位。保留原完整拒绝/0下载/日期资格断言，不删测试/提高阈值/跳hook。JSON stdout的GBK/UTF8根因和集中CI表漏DU11纯回归也已修并独审；最终类型delta独立公共mypy＋10有限控制通过。详细收据见review/du11-reception-closeout.md以及各publication报告。

未动生产原件/gold/配置/密钥/Dayu/IQS或作者树，没有新收费模型调用。RF旧3个assurance WIP保留，stage1曾观察weekly_manifest自然变化，不归因/不恢复旧值；stage2前后相同。一个RF外层审查Temp仍NOT_CLEAN，历史PermissionError后平台拒删，保留且不换通道重试；内部端到端原样恢复。未知发布日期的/3投影仍如实source_availability_unknown，不伪造日期或另加许可。

整体PWF仍OPEN：t32最新真实诊断不再selected；t34仍缺有界先行词。下一实现按review/antecedent-source-interface-final.md，在现source/operating唯一owner、同parent16M及8units/4原block/2048chars封闭依赖，再做正式三供应商摘要、收费/activation恢复、同跨run缓存及真实FF/RF消费C，之后holdout与RF循环。不要把工程/金标命中当内容C通过，不重做已接受DU11或新增小节点签收。

## 当前发布结果（优先于下方历史）

CWP已正常发布remote master=0ccdc6896ee58063ff827e9ceab16043c7550e0c：全量6801PASS24SKIP346.26s、独立合同142PASS48.31s，未删测/提时限/跳hook。精确CI39094787278已completed/success，匿名API核对相同HEAD。详见review/du11-cwp-publication.md/json及保留的原push日志。RF runtime已发布，集中compatibility/current.json须先更新CWP producer pin，随后正常发布FF，再同步安装源码/核精确CI。t32最新诊断不再selected；t34有界先行词及正式C仍OPEN，下一实现接口/TDD见review/antecedent-source-interface-final.md。

# Progress

## 2026-10-22 技能独立试读与公司复审进展

新增两阶段技能通过七个独立离线场景；试读发现旧记录工具只按裸问题编号归并、取最后映射，ROOT9项实际隔离回归先RED后GREEN，内部统一复审定位并保留唯一旧记录兼容。独立10个真实CLI反控通过；最终完整632测试OK（2skip）103.965s。旧故障注入依赖第三次Path.stat，在Py3.14时序失效，改为真实复制read期间源变化，原断言不放宽；不同agent在Py3.13.9/3.14.2各单独复验通过。安装工具tempfile创建阻塞另有实际trace，尚未声称同步完成。

公司storage18项9P/5F/2BLOCKED/2NA、process20项14P/3F/3NA已封存，具体问题和责任层保留各自报告；不能把摘录逐字真或算术对当业务语义通过。fetch/analyst独立进行，不共享彼此初稿。501执行工件及原件/配置由各自收据核对不变。下一步汇齐四报告再交专家共同根因，而非逐条局部补丁。

## 2026-10-22 三仓发布与新版预测封存

CWP aa2dd822正常push完成：7097单测P/24既有skip267.37s、146契约P36.11s，精确CI39854576322 SUCCESS。与RF10bf6111/FF7f6a9268的精确CI及已安装字节共同收尾本地读取诊断包，未绕钩子/删断言/加人工许可。W06最终final3已封存，ROOT实核manifest501件89,049,507B全匹配；作者1594算术不是独审。storage/process已按当前同一manifest启动，fetch/analyst待空槽；原初FAIL及639件不变，暂无新版业务PASS。审查技能源码39文件已冻结，623工程测试OK/2skip，独立七场景试读进行中。

## 2026-10-22 审查技能收尾升级（实施中）

用户增加两项最终步骤：全面代码质量/模块化/泛化与买方收入研究方法改善，以及根据当轮新问题升级审查检测。ROOT先核对审查技能源码仓 `a2f216b` 与已安装入口，工作树原本干净；独立 owner 仅改该仓 `skills/` 与专属建设 PWF，不写正在封存的真实公司运行目录。两步接在原公司复验之后，复用现有根因映射与大节点审查，不引入新状态机、额外授权或每个小提交的重测试。待独立行为试读、安装差异核对及正常提交推送；此段不是已完成声明。

## 最新：正常push超时与两个独审delta（2026-10-18）

母仓6ee5ebf1正常push未成功：完整unit约96%时达到600s，日志在母仓`.planning/shared-reading-production/du11/push-source-flow-reader-port.log`；远端仍9c681ed2。原日志保留，非断言失败证明，也不能因PowerShell尾部命令exit0误报发布。现用已声明xdist对完整unit目录启两个file-scheduled worker，不删测试/改期限，窄测和contract不增加启动开销。实现先3FAIL/1PASS，修后4新及80既有gate控制共84PASS6.44s。独立4新控制PASS4.69s，另3窄测/非零退出控制通过；真实2-worker/SQLite超时反控5s期限后20.064s返回124（既有execnet约15s关停），返回时worker均退出、gate/outer Temp均删除。完整7000组运行提速未签收，留待正常push；不增加第二进程管理框架。

源编号修复先3RED、补未知counter反控1FAIL/3PASS，再77PASS3.95s。独立新4＋自选6跨两轮10个不同控制通过，首轮9PASS/1FAIL是审查控制误要求局部拒扣后parent.exhausted=True；按既有B1语义应保留父余额，仅修外部审查控制且单跑通过，生产源码未迁就错误断言。报告精确SHA绑定见review/page-local-readiness-independent.md/json。实源诊断page-scope-after-counter-fix明确非冻结验收/计时证据：CN10/10、parent6142162、旧t32不再选中，t34仍选中，0API/原件gold不改。该剩余先行词问题不混签绿。

## 当前发布与接收（2026-10-18）

物理/cache最终独审已完成：PASS_PHYSICAL_BUDGET_CACHE_COMPONENT，27有限PASS8.51s、5源码/2测试精确SHA前后相同、两自有Temp均删除；未重跑219/763，不代签一般语义/先行词C。FF隔离根修已正常commit a9c2dcf7，等待先producer发布；新CWP test唯一静态F811以同既有pytest fixture参数noqa说明，runtime与各独审冻结一致。

B1远端9c681ed2已精确CI39092308121 success，正常push5221PASS/11SKIP517.05s，未跳hook/改deadline。RF外包已18项独立行为接收，正常main发布f8002f5f（416PASS＋36子测65.46s），精确CI39092538354 success，2物理技能目录6源码同步、原3WIP SHA不变；验收一次外层Temp被平台拒绝删除仍NOT_CLEAN，其内部E2E恢复真，未再换方式删除。

FF初审102PASS＋4实际反例发现日期/股票码根因，ROOT隔离修34PASS后不同agent28控制＋真实HK TXT1链最终复审PASS；29unique跨次通过、0ET/network/原件修改，作者树未写。仅待CWP先发布reader canonical端口，再正常FF commit/merge/push/定点同步。

物理早期763PASS45.71s后独审新发现繁体新issuer、English显式新产品主语被接到旧半句；修共享grammar后225PASS4.70s，又补source grammar缓存漏口/N²/真实parser MIME/per-pair coverage，先6FAIL及8FAIL30PASS后修，最终219PASS10.11s。最终实源零收费CN/HK/US10/7/8及canonical一致，parent work6106955/12820408/7975948，原件/gold不改、0copy/ownedTemp删除。但实际CN t32/t34仍selected，整个语义闭合/先行词及正式C仍OPEN。最后delta独审进行中，未拿旧收据重签当前源。

CWP reader新端口及同次manifest读取先3RED，第一次相关54P3F（2fixture config目录错、1暴露global pin兼容），改后4针对PASS；新filing_reuse单观察反控2FAIL3PASS指出None未观察混淆，复用scope sentinel修，最终59PASS37.37s。FF跨仓最终review绑定两reader真实源SHA，原manifest/原文不变、不新增人工门禁。

## 最新 B1 节点（2026-10-18）

最终独审PASS_B1_ENGINEERING，精确3文件SHA前后相同；独立9PASS/3.27s＋3有限控制（两入口预扣失败0访问、外部context正控不丢），自有及pytest重定位Temp均删除。真实三源budget-source-replay/receipt.json：CN10/10、HK7/7、US8/8，canonical同分；分别12.665/27.042/11.721s，同一16M账户各用5758585/12269996/7975948，无耗尽。原件/gold不变、0POST/0原文复制、ownedTemp删除。内容/C仍OPEN，不能用此工程节点代签。

现production source metadata与native continuity已复用同parent账户，移除逐member重建容器集合的N²行为。独审指出两预扣前遍历并新增CountedIds反控；RED为7PASS/2FAIL，修复后739集中PASS/50.52s。首次大组733PASS/4FAIL是四个新fixture错误，完整失败保留budget-index-full-green.log（文件名非结论）；改正后目标行为才真正执行。最终独审及真实三源回放进行中，B2物理跨页与先行词未实现，正式付费C仍OPEN。

母e33d40ed正常push6741PASS/24SKIP/580.05s+142合同PASS/37.31s，精确GitHub CI39090720114 success；文档0099dd5d已推。B1未发布前的后续记录与母结果分开。下方是历史顺序证据，不作为当前Next Step。

2026-10-18：建立ROOT后续独立包；无新生产源码改动、无API/原件写入。前置工程9eff4ee7已独审正常提交并合母e33d40ed，母正常push进行中。阶段A RED尚未实施，阶段B/C均OPEN。

## Stage A physical behavior RED

Existing production _prose_reading_packages/_candidates/finalize_selection, not a missing-module placeholder: tests/unit/du11_source_closure/test_cross_page_reference_plan.py collected15,8FAIL/7PASS4.45s. Six CN/EN × background/event/risk positive multi-original carries currently split; five distinct (source,page,block) sentence can expose right suffix; one-span budget currently exports only half a cross-page sentence. Seven unknown/changed-column/page-gap/scope/font/heading/table controls pass. No production changes yet; draft tests remain only ROOT isolated branch and are not in mother pending push. Next write furniture/independent-statement/parent-budget and antecedent cases, then shared owner implementation.

StageA expanded19cases:10FAIL/9PASS5.61s, including explicit running furniture and exhausted parent geometry scan. Root began systematic budget connection: _Analysis uses existing WorkBudget.scoped, source candidate metadata reserves before indexes, same parent flows into geometry and operating session. First zero-parent controlGREEN1PASS/102deselected4.83s: -k applied to all requested paths, so this is explicitly not103PASS. Correct explicit-node compatibility command is separately running. Full physical crosspage/antecedent implementation and independent review remainOPEN; mothere33 normalpush succeeded6741PASS24SKIP580.05s +142contracts37.31s and remote master exactlye33d40ed7688cfdcead1e02d55542f7026d0b8e5. RemoteCI352/runs39090720114 currentlyIn progress.

Metadata performance root cause reproduced on actual _prose:16/32members visited288/1088times (quadratic),2FAIL5.05s; no timing-only claim. One owner external-context index and one combined exclusion set now avoid rebuilding whole member/context sets for each paragraph. Reservations account actual membership/section/header-context edges and sort work on the same parent; _candidates returns finite partial if preprocessing cannot reserve. Concentrated88PASS5.59s covers2linear controls/2parent-budget+previous native/prose readiness controls. Source crosspage/antecedent RED remains intentionallyOPEN and unmerged. New design review approved overall owner direction but is not final implementation acceptance.

</details>

### 2026-10-21 R1 N1冻结节点完成

已固定药明康德→药明合联→Snowflake、20项通用检查、真实代码/195份安装内容SHA、母预算和首家隔离scope。配置脚本真正执行通过原生schema校验，0下载/0模型；独立agent终审PASS_PREPARATION_ONLY（r1-holdout-freeze-review-20261021），不是来源或预测通过。母账真累计1,504,997tokens/$0.615538，剩495,003tokens。下一步立即派独立executor完整RF，封存后四路独审及根因专家；旧NVDA和未来八家任务保留。

## 2026-10-21 专家封存后四线并行实施

26问题已映射11根因/7施工包，M1共用接口由ROOT一次接收；W01来源发现/时间资格、W02 FF与RF边界、W04实验补写退役与历史final恢复、W05比例/分部组已在独立工区TDD施工。方案及完整7卡的小型字节副本已收进R1 packet，原initial/四审/设计封存不改。RF两新工区采用sparse checkout各2136文件约21.8MB，未保留46969份旧.planning输出副本；临时完整检出峰值未测。当前无新增API/下载，预算及unknown不变。ROOT首轮source反例因长TEMP/父目录未建及测试冷catalog前置假设产生的环境/夹具失败已分开留证，真正2个发现机制RED与7个资格API RED已保留；75相关例已绿，新增cold/current-open和扩展resolver验证进行中。工程candidate不等于真实0.9/付费恢复/研究闭环通过。

自动审批拒绝了整子计划目录的递归暂存，理由是可能夹带无关/敏感WIP；未执行提交。ROOT改为先逐项核对本次PWF/独审/收据文件，再显式逐文件暂存；不跳过审批、不把raw、密钥或其它计划带入。


## 2026-10-22 技能最终完成与四审汇齐

审查技能源码623054c/发布收尾738d99a已本地提交，无配置远端。两目录各39包文件实核同树f50bf54...；七案独立语义试读、十CLI、632测试（630P/2skip）及独立发布字节核对通过，完整收据和旧失败均保留。三个自有测试根恢复不存在，0新收费/下载，无新审批门。母PWF记录本仓提交并正常推送，不冒称技能仓已推送。

W06四路复审全部FAIL，共14条发现出现项；索引保存各报告SHA/检查数。专家统一实读原件/代码和报告反证，再形成新的PWF；不能把14症状逐个补丁或把重叠范围重复计数。W03/W07已完成，HK/US新公司与内容质量仍OPEN。

文档汇总首次读取独审JSON误取outcome键（实际为conclusion）而退出，未写任何文件；按实际schema修正后成功。

## 2026-10-22 当前主线目标更新并启动

用户明确要求把目标更新为当前主线循环并启动。create_goal因旧目标未完成而拒绝替换；未伪报完成。官方proxy只读连接18秒超时后已关闭，改用官方文档支持的短生命周期stdio app-server get/set/get；同一线程旧目标核对后更新objective/status=active，内置get_goal再次确认active。无新thread/turn、无数据库直写、无权限或配置修改。应用目标计数实际保留，项目外部调用2M/$20及unknown账不变；收据保存前后原值。所有本次自建客户端已关闭。

专家五卡已交付，ROOT核验11份小工件SHA及14/14完整问题键覆盖，接收方案而非业务签收。W08独立只读RED/fixture/版本设计已启动，W09–W12仍planned；后续按新目标八步循环，不重做W03/W07。接收脚本初次假设四报告均有review_attempt而KeyError，未写任何文件；analyst缺字段，改用其已封存目录与四审索引显式上下文，原报告不改，不加额外身份门禁。

## 2026-10-22 当前收尾后暂停
W08候选11502372保存独立支线，公开cache/父级与数字标识误判、真实内容partial及独审未完，未并线/安装/推送。850P在类型delta前；最终185P、mypy366/Ruff绿；自有残留Temp已清。W10两轮独审六项缺陷共因根修，delta2真实41/41，完整658项656P/2skip79.153s和17边界P2.92s；71c7762代码/ae13ef7收尾，本地无remote，两安装根39MATCH。W09只完成新attempt基线和原件10页真实capture，旧501封存不变，新研究输入/native RF/真实矩阵均未作。CURRENT_STATUS/JSON、行动计划、交接及implementation-progress已统一，用户要求暂停，下一步先W08失败回归；累计预算不变，0新增模型/下载。

## 2026-10-23 恢复主线
用户“继续”已取代暂停；原生目标回读active，mother HEADa2f99db6无未提交源码，W08工区11502372干净。ROOT分两条不重叠源码owner处理上下文/cache和事实筛选；第三线仅写新attempt研究建议/经营桥，不改旧封存。预算/配置/原文及unknown保留，先RED根修再集中大节点独审，无新许可。

## 2026-10-23 工程节点与两份并行包

W08公开cache、跨列/缺页父级和通用事实误判的有限工程独审已绿：15上下文+36事实反控及1正式公开cache（32.59s）；但真实249页原件oracle仍FAIL，两条30%事实未入选，未并线/安装/推送。W09已完成49项原文绑定建议及经营桥准备（42 Decimal公式/14来源加总/10作者反控）；新正式RF尚未执行。W10工程已提交安装但真实矩阵OPEN。详见review/r1-w08-resume-20261023/checkpoint.json。0新增付费/下载，预算unknown均保留。

ROOT继续定位W08真实249页年报两条业务30%事实的候选资格/排序/父级保留根因，原96/48000/16M上限不变；两份外包卡W09-RF-RESEARCH与W11-CWP-SOURCES已准备，可现在并行启动，不等W08。ROOT不再同时施工其独占写集。 工区实际检出和独立PWF已正常提交：RF42393ea1、CWP0d7ada21；仅准备文档，不是任务已完成。两卡及共用接口由独立agent静态审查，发现空工区、输入清单漏项、交接schema冲突、测试选择漏项和无缺陷路径要求RED等问题，均已修正。

## 2026-10-23 两份外包卡已派发
用户确认W09/W11已交其他harness；登记为用户报告施工中，不冒称已观察实现或验收。ROOT不触碰其工区写集，继续W08。两项真实内容oracle曾PASS，但独审又查出模态数量/因果旁路、混合用途及表单/导航问题，保留所有初次FAIL并从共享owner修，不提前发布或新付费。

## 2026-10-23T20:07:26.112790+00:00 W08工程进展及外包边界
W08已保存隔离支线181200bc，集中992P/82.35s、RuffPASS、src mypy368/0；两路独审有限PASS。真实249页/5647units两条业务30%已各自父级通过，但原14目标PARTIAL，错父级/缺表头/跨页祖父未闭合，六项遗漏已继续逐项实际trace。未并线/安装/收费，不能重签旧四审FAIL。用户确认W09/W11两卡已交其他harness，dispatch记录为人报施工中；主线不改两包独占写集。

## 2026-10-23T20:55:52.617812+00:00 W08共用标题节点保存发布
隔离支线b6395b6c正常push，标题独审152P；负证据不再被结构fallback覆盖，最终249页p184仅p83/2财务报告和p183/7分解标题。完整gate先24Fsparse缺件，后6F含5缺件和1真预算顺序回归；分别恢复完整自有HEAD测试依赖并前移原有边预扣（不扩大额度/断言），原失败组239P，最终完整正常push结果见新收据，未绕门禁。12实际owner-byte反控进入普通单测。原14目标PARTIAL，p16三裸数行、Chemistry跨页父级及六遗漏仍开；下一步详隔离PWF。仅本会话pytest1/2和显式mypy-cache约29.2MB清除，旧pytest0/历史.planning保留。新预算消耗0，W09/W11仍外部独占。

## 2026-10-23T21:47:46.637639+00:00 W08有限节点已提交，正常推送进行中

1712ed10：两组最终独审44P/165P，原断言未改；全src369/0，RuffPASS。真实原件249页/5647units/1511candidates/96spans8156chars，20owner字节与来源/配置/库SHA稳定，work8210077/16M未耗尽；p16两选中裸数行诚实unknown、p184父级正确、whole14PARTIAL。中间1680P11skip1F与13purityF均留证根修；完整正常pre-push未结束，不宣称全量新绿。W09/W11仍外部施工，34冻结输入逐项MATCH。费用/token无新增，预算提高只是讨论未修改。Next唯一入口见CURRENT_STATUS。

### W08正常发布确认
1712ed10已正常push到既有隔离支线，本地/origin相同，tracked干净；完整7558P/24既有skip403.02s，smoke146P47.71s。不将403秒当每文档解析耗时，不将本地green冒称remoteCI成功；真实年报9.27s、工作821万/1600万，0新增模型费用。主线代码合并/安装、完整14目标、后续正式摘要仍未完成。

## 2026-10-23预算发布收尾

CWP ab95027b正常push：7165P/24既有skip294.50s，另146契约P36.56s；全src366/0。精确CI40034980056已观察in_progress，不借旧绿。Audit564f77a源码/af255d4计划收尾，无remote；两安装各39文件MATCH仅改3文件及manifest。旧账仍1561352tokens/631959microUSD，旧7+新4unknown全留；所有本节点pytest有效临时目录恢复，ROOT两缓存精确清除37,221,622B，未全仓清理。W09完整内容复核正在追历史driver正向模板与跨scenario说明共因，未代签研究PASS。

## 2026-10-23精确CI与外包新交付

预算源码ab95027b的精确CI40034980056已实查completed/success（22:42:48Z），文档fa667547已推送、普通文档gate154P/51.24s。W09有限内容独审49/49来源和22摘录实核、主/压力公式及54格/25桥/7敏感性重算无金额错；两P2和两P3为role/scope/scenario变化未原子更新平行解释，ROOT修投影不调收入迎合文案。W11用户报告A/B/C交付推送，ROOT只读初筛进行，报告陈旧不当产品缺失；实际nearest item祖先及无可见链接内嵌JSON-LD覆盖需隔离新RED核实。旧作者工区、原件、账和冻结材料均不改。

## 2026-10-23 W11正式交付接收与ROOT修复启动

用户报告W11 A/B/C完成并推送，ROOT已完成版本/测试/清理/独审收据只读初筛并接手两项共同根因；W09另两P2/两P3由ROOT独立attempt修角色/范围/场景投影，作者工区保持只读。W08预算基线接入已分配ROOT子任务，先实核并保留现有measure变更、77新增回归与guidance的7F/13P。当前预算源码精确CI成功，费用和原件无新增；未把包初筛当业务通过。本次PWF首个补丁因整行后有链接导致上下文不匹配、原子失败无修改，已用完整原行修正。

## 2026-10-24 W11工程独审通过、正式并线准备

初始ROOT13例10F/3P→相关120P；独立37例30P/7F暴露三类剩余观察缺口，ROOT在同一owner根修，新增正式unit32例先8F/24P，最终含全部作者回归/两CLI共132P/45.72s、独立同37例37P/6.73s。Ruff/相关2src类型通过，失败材料保留，专属tmp及13.46MB缓存恢复。PWF先记工程通过/发布中，不冒称新IR原件或公司PASS；源码提交及真实支线并线/正常push/精确CI由ROOT继续。

## 2026-10-24三线当前检查点

W11 ROOT修复664d3a1d及真实作者ancestry合并44b722ec正常提交完成，6份已验raw SHA不变；仅排除作者工区START_HERE bootstrap，母原本无该文件。普通Git rm先拒绝删除incoming staged新文件，核对精确路径/母HEAD不存在后只对该1445B非原件文件用rm -f，未动其他文件。正常push在跑。W09 v3已冻62P+8subtests、六native调用及126年度格Decimal0差，最高真实空间样本30.15MiB，独审启动。W0817项独审8F9P，实施者接手统一谓词/模态/时间owner；一次followup因审查child占满槽被工具拒绝，child84P收尾释放后正常派发，属于agent容量而非用户权限或产品失败。0新增下载/付费，旧原件/账/封存保持。

## 2026-10-24 W11推送前真实环境缺陷已根修

正常pre-push在Conda3.13.9挡住1F/7196P/24skip（202.23s），146smoke另通过，未推到远端。根因是BS4可选编码后端对短UTF8猜测不同；复用已有确定性HTML decoder并传播encoding repair诊断。未改旧断言，新增5编码控制；Conda37P、venv39P（含2CLI），独立原37再次37P。原失败完整日志留本地、精确SHA和紧凑失败尾部入Git，避免提交7196条冗长通过日志。两临时目录和6份142KB合并源码备份恢复，财报原件/作者历史不动。W09有限独审16P，发布任务串行分配RF写集。

## 2026-10-24 两包真实发布完成与W08有限复审

W11 ROOT修复664d3a1d、作者真实ancestry merge44b722ec、确定性解码1be42a76已正常push。首次正常prepush真实1F/7196P被拦，保留故障并复用既有HTML解码owner，从源头消除环境猜码；最终普通7202P/24skip/187.45s，另146smokeP/26.12s，精确代码CI40040509874成功。132相关P属于编码前版本，未篡称最终全套重跑。实际IR正文恢复未完成。

W09四项内容问题通过共享投影owner修复，作者真实ancestry merge9dcce304、当前RF599d17b8已push且精确CI40040969386成功，正常595P/1skip/36subtests45.28s。5运行文件同步到两个物理安装根，共10写入；103owned文件全部匹配。保留原assurance/output/作者工区。平台曾拒绝排除作者交付的操作，未执行；改为完整保留约24MB作者交付的更安全正常合线，没有换通道重复被拒绝删除，也不宣称去重已完。

W08独审17项原8F/9P暴露actual/future与收入指引重复状态根因，重构不可变PredicateObservation供二者共用。有限相关677P，独审原17不变+6真实selector/citation/model未来目标召回+1源码cache身份共24P；原77/20/24断言不改，预算独审版本保持，暂未保存merge/并母线或安装。跨页、annual14、正式摘要/缓存/RF矩阵/W12仍OPEN。

母PWF/两级Next Step/机器checkpoint/施工包总入口统一。错误读了不存在的旧dispatch路径已纠正到harness_lanes/20261023/dispatch.json；沙箱普通Git读外部linked worktree报must be run in a work tree，按既有授权使用escalated正常Git，未重置或改索引规避。0新增模型/原件下载/费用；10M/$20总额、旧unknown和原始文档/封存均保留。

## 2026-10-24 W08真实并线、发布失败根修和W11索引保存

W08正常合7b1c015b为b0344200，15源/test按review原始字节恢复（11仅LF等价），W11源和母入口不变。第一次正常prepush5F/7830P/24skip201.29s挡住；ROOT统一project词性/假设条件，正式新22例和旧套件362P4.64s，独审首轮42=34P8F保留、最终原42全P2.00s。等待正常发布，不借旧CI。跨页下一公共RED9=7F2P，结构47有限P，per-target原文依赖出口与预算fixture澄清未完。W11单次GET已正规保存486901B新索引，binary read/source SHA校验、同字节本地发现；0业务文件。临时body恢复不存在、原件/封存/配置/母模型账不变。业务材料external_limit仍开，无LLM调用。

## 2026-10-24 W08有限主线发布与下一节点分层

4e3e0231正常push成功：7857P/24skip192.88s，另146smokeP25.12s；精确CI40044921473 completed/success。原5/7830/24失败与独审8失败证据保留；同42复审通过。旧10路径只有newline/stat显示变化，逐份LF==HEAD blob、正常index刷新前后tree相同，tracked干净。下一prototype只在ROOT工区：physical47P、order170P、初版引用19P尚非一个冻结组合验收。独立复核撤回source-only家具也占模型block预算的拟新门槛，语义材料和物理证明按各责任层计量，原9与全部源/旧FAIL不改。累计外部模型账仍1561352tokens/631959microUSD；原件保留、源索引新增486901B已单列。

## 2026-10-24 W08跨页工程验收与真实内容边界

共享观察一次、唯一结构父级、per-target语义/物理职责与共用词法修复，原13独审全绿、自然2121P/11既有skip39.36s。三共因63F与英文12P1F原证据不改；源码正常保存ef49ae3e并真实合母线，待正常发布。真实249页只解析一次，96/8518、8.630449M/16M，两scopeP；完整14独审3P9partial2missing，另仅补8页10888字符，原文/旧sealed/config/db/gold不变。下一步修层级/事件时间/条件闭包、财务孤片与定额选材/分批，阶段计划见review/r1-w08-crosspage-20261024/next-source-quality.md；不是扩大额度或强迫全文切片。本节点无付费模型/业务下载；W09/W11已发布既有状态保持。

## 2026-10-24T01:37:02.500157+00:00 W08普通prepush四回归两共因已修

原4F/8052P/24skip日志保留；长英文头词扫描复用原token边界、正证家具兼容原header/footer角色。原断言未改，物理最终194P，母仓原13+原4独审17P，27实际绑定不变。只恢复既有合同，不扩预算/词典特判/人工许可。正常完整push/精确CI待后续真实观察；annual14仍3P9partial2missing，0新增模型/PDF解析/业务下载。

## 2026-10-24T01:46:21.401335+00:00 W08共享来源节点真实发布完成

源码`f2b8f2bf`已正常推送，真实合线`e09e44e1`保留`ef49ae3e`作者祖先；完整单测8056P/24既有skip/221.02s，契约smoke146P/30.52s。精确[CI40050949303](https://github.com/zhengcb81/company-wiki/actions/runs/40050949303) completed/success。原4失败、同13+原4独审17P及两处共因修复收据均保留，未改旧断言/绕hook。

先按本轮真实annual14断链冻结下一批共因反例与逐目标offer/defer诊断，再一起修源层级、事件时间/指引前提闭包、低信息财务孤片与定额选材/分批；在大节点完成后集中测试/独审，再用同一实际输出核内容。随后正式新摘要、cache恢复、W09/W10实际采用矩阵和W12四审；原公司复验后药明合联→Snowflake。

## 2026-10-24T04:01:01Z W08回归根因修复正常推送并精确CI通过

提交`87a14a8608f5bcce17e7496f43c71b43baf56ea5`已正常推送。正常pre-push通过受影响单元测试8072项、24项既有跳过，独立CI契约烟测146项；Ruff、mypy、host assumption guard、diff check均通过。精确[GitHub CI 40060222913](https://github.com/zhengcb81/company-wiki/actions/runs/40060222913) completed/success（Fast checks，4m19s）。

修复针对两个不同根因：官方JSON真实回放没有去掉三项合法的selection-only标注，误报`LOCATOR_REPLAY_FAILED`；Windows宿主不可写TEMP/TMP令大型W04 SQLite WAL回归无法建立临时存储。前者新增真实selection注释回归并通过官方JSON loopback；后者令pytest子进程统一使用hook每次调用拥有、结束自动清理的临时根，65-parent回归通过实际gate路径。Cache迁移loopback测试在受限沙箱失败是宿主网络隔离；通过常规门禁环境复测通过，没有改产品网络逻辑。

GitHub CI有一条非阻断运行时警告和一条Ubuntu 26迁移提示，记录为后续工作流维护项，不混入本轮缺陷。W11-CWP-SOURCES A/B/C交付和推送仍依用户确认及现有收据记录；真实IR正文/source recovery仍OPEN。W08 annual14仍3pass/9partial/2missing，下一步继续源层级、事件时间与指引前提闭包、定额选材/分批，测试绿不代签内容质量。

## 2026-10-24 W08公开诊断合同复核与回归

按生产链新增并验证逐目标selection trace/diagnostic公开合同。TDD先暴露`max_chars=0`诊断无法越过DTO和selected trace计数未受证据/原始单元约束；修复后又由独立只读复审补出无证据正计数、admission样本与聚合不一致、路径样式locator及诊断detail文本边界。现有owner内完成修复，trace保持有界、哈希化且不进入模型提示；不引入第二内容库或新的许可/审查门。

最终相关回归：171 PASS（unit/production selection/official JSON/selection contract），13 PASS（三组本地真实端到端，含worker、loopback、投影/summary/cache恢复）；Ruff PASS，`git diff --check` PASS。独立复审确认没有剩余blocker，提示的locator字段规范顺序/唯一性是非阻断的后续硬化项，本轮保持范围。上述测试未调用外部API、未下载真实材料。W11-CWP-SOURCES由用户重新确认A/B/C全流程交付并推送；已有W11源码1be42a76及精确CI40040509874记录仍适用。真实IR原件恢复、W08 annual14内容、正式摘要/cache和W12仍未关闭。当前代码/PWF提交推送与精确CI待做。

## 2026-10-24T01:49:23.487623+00:00 发布交接最终补正

独立文档复核发现CURRENT_STATUS正文和MAINLINE_LOOP_GOAL当前起点各一段旧prototype未发布描述，均改为f2b8f2bf/CI40050949303；其余当前字段、17P、annual14的3/9/2和无新增门禁一致。仅文档补正，不改源码、旧审查或预算。

## 2026-10-24T05:38:43Z W08 V5根因修复与14项目标独立复核

V4独审发现纯名词“收入确认、履约义务、客户控制”会把会计政策误判为经营事件。新增中英文负例先RED，修改共享source-purpose关系判断后119项聚焦回归通过；真实业务正例、确认时段及预收转收入关系保持。相关自然测试2,155 passed/11既有skip/0失败（54.08秒），Ruff与mypy通过；V5独立源安全复核没有新增blocker。

以同一真实249页来源回放V5：1,533候选、96 selected spans/7,767字符、8,845,814/16,000,000工作量；2项运行checkpoint通过，零模型调用/下载/raw copy。与checkpoint oracle分开的冻结14项清单独审7pass/5partial/2missing；55个编译任务context未见Testing/Biology兄弟业务串入。A03/A04仍missing，A01/A02/A05/A09/A13仍partial；A12前提已同任务可见，A13具体确认金额/业务期间仍缺。详细逐项状态、代码/测试哈希及准确结论见`review/r1-w08-crosspage-20261024/annual14-v5/review.md/json`；正式摘要与模型结果仍未验收。

本轮无外部模型费用、无业务文档下载、无raw copy。用户再次确认W11-CWP-SOURCES A/B/C全流程完成并推送；该交付进入PWF记录，ROOT真实IR业务材料检查仍按其独立收据状态OPEN。

## 2026-10-24T05:55:48Z W08 pre-push旧selector指纹根因修复

首次正常push被pre-push拦下：受影响unit测试6669项，6655通过、11既有skip、3失败。失败都来自`test_stage_classifier_explicit_legacy_native_fingerprint_unchanged`的0.6.0/0.7.0/0.7.1参数，期望`54c4bd…`、实际`d220d0…`。逐源反事实验证证明：仅将新增N6候选源码恢复提交父版本，三个指纹立即恢复；分别只恢复其余每个改动源码文件，指纹仍失败。根因是W08六个新N6信号被接入全版本共用detector。

生产修复明确拆开旧版检测器、旧business fact/finance-only路径和旧group join；0.6/0.7继续旧规则，0.8保留新信号。独立复审发现由“新tuple排除已知六项”生成旧集合存在未来漏隔离风险；改成显式冻结历史tuple，并以新增六facet + 历史tuple组成当前检测器。六个facet分别验证0.6.0/0.7.0/0.7.1不变、0.8启用；固定指纹及边界独立复核9P。最终9个相关测试文件357P、Ruff PASS、`mypy src` 372文件0错。未修改原金标断言、未绕过pre-push。失败提交`808fca1484b01a5f86768f79a119f28764fe143a`仍未推送；下一步提交当前修复后重跑原hook。第二次pre-push的两项失败均由当前版分组误用了旧兼容detector引起。修复后相关测试478P、Ruff PASS、mypy src 372文件0错；独立复审覆盖固定指纹及六facet边界9P。此事件不改变V5年度14目标的7P/5partial/2missing业务结论。下一步提交修正和PWF，正常重跑hook、push并查看精确CI。


## 2026-10-24T06:22:26Z W08 selector 兼容修复已推送

提交 `584c1101ec21141bca14c87cbaa3bca2769ddca6` 已正常推送。正常 pre-push：6664 passed / 11 existing skipped / 0 failed，270.68s；相关11文件478P，Ruff PASS，mypy src 372文件0错误；独立复审确认固定指纹与六facet版本边界9P。GitHub 精确 CI [40069847315](https://github.com/zhengcb81/company-wiki/actions/runs/40069847315) 已建立，观察时仍运行中，未记成功。根因分别为旧选择器共享detector污染和当前0.8 group误用兼容detector；没有修改原指纹断言或绕过hook。继续按唯一入口对annual14未闭合目标做候选/依赖/admit链诊断。


## 2026-10-24 06:26:48Z W08 selector 精确 CI 成功

精确源码 CI [40069847315](https://github.com/zhengcb81/company-wiki/actions/runs/40069847315) 已completed/success，耗时4分36秒；只有既有 Node 20 runner提醒与Ubuntu 26迁移提示。提交 584c1101ec21141bca14c87cbaa3bca2769ddca6 的远端工程验证闭环。上一份PWF状态提交 ce376d00 已推送，pre-push 154项契约烟测通过。源码选择兼容问题关闭；annual14 V5内容仍7pass/5partial/2missing，继续依据冻结14项目标扩展有界trace，逐项核candidate、admission、dependency、offer/defer和task context。

## 2026-10-24 W08 DTO/cache根修、clean Phase C端到端与正常推送

源码提交 `baa77ab6` 已绑定source proof endpoints、target-unit dependency closure与`reading-context-projection/1`缓存身份；`aade6b93`修复clean deployment与Phase C oracle对生产reading context `/3` 的适配。首次pre-push从沙箱失败后先定位两份漏带运行配置，再由最小TCP复现确认Windows `10013`禁止沙箱子进程回连`127.0.0.1`。在非沙箱运行真实本地loopback，E2E 95.42s通过；没有接触外部模型或真实付费API。聚焦selector/context/cache与Phase C 170项通过（176.56s），Ruff通过，`mypy src`372文件0错。

完整正常pre-push通过8126项/24既有skip（389.84s），独立CI契约smoke146项通过（42.09s）；commit hooks通过。`aade6b933a065fae71a14b8baf2a3b16fcbb9bb9`已推送且与`origin/master`相同；精确GitHub CI 40076059766待观察最终结论。W11-CWP-SOURCES A/B/C再次由用户确认交付并推送，关闭施工卡。

本次门禁显示完整`tests/unit -n 2`是固定push前置项，即使变化面很窄也运行全量（389.84s）；保留测试与hook，不做本次绕过。后续应单独按当前项目计划评估测试分层/执行时机，确定跨模块回归、loopback E2E、快速单测与远端全量的职责及失败反馈，不重新制造一个审批门。精确CI40076059766已success；CURRENT_STATUS/JSON、task_plan、progress与findings同步了已发布HEAD和下一步。


## 2026-10-24T08:25:44Z 三张独立施工卡准备完成

按最新PWF和RF/FF/Audit三路只读调查，选择W13-CWP-GATES、W14-RF-CLEAN-CHAIN、W15-AUDIT-PORTABLE；FF现有来源修复已交付，不强拆重复生产任务。卡/总README/INTERFACES/dispatch/交接模板和独审关闭记录位于`harness_lanes/20261024/`。三个独占worktree及各自四份子PWF已创建、commit并核tracked clean，源实现尚未开始，状态READY_NOT_DISPATCHED；启动HEAD为8746be6f、9196ef1c、b00319b。ROOT继续annual14，不写委派范围。

独立agent全面审卡后发现5项具体歧义（共享smoke会影响远端、缺runner假绿、RF生产冻结/污染反控、TXT实际消费、便携清单/退出码），全部已修并独立复审通过。每包C节点仍必须独立审实现并修完内部问题，当前卡片审查不能代替未来产品验收。

新worktree实测分别175.82/51.52/6.80MiB；W14约806MiB旧tracked.planning副本在新工区用sparse省略，原RF及Git对象不变。没有新模型/下载/生产写入。首次沙箱内git status无法读共享worktree元数据（not a work tree），按现有授权在非沙箱只读核查成功；未reset或清理旧WIP。所有bootstrap提交仅文档，未运行/声称产品测试。


## 2026-10-24 主线继续：annual14未闭目标诊断

上一goal turn完成三包/独立卡审查/独占工区/文档发布bc184b57，属于已改变权威状态的progress。本轮回到ROOT annual14七个未闭目标，W13/W14/W15写范围保留给外包。已实读最新PWF、V5 freeze/review、旧trace/编译脚本：旧trace只涵盖A12/A13，V5 selection已有public selection_trace、逐budget targets和55任务关系，应先用这些冻结材料与既有8页原文摘录诊断，避免重解析整份PDF或重复收费。当前未调用模型/下载，未声称内容缺口关闭。

## 2026-10-24 ROOT继续：修复独审剩余的判据/断言边界

上一轮仅复核并再次提供已就绪W13–W15卡，未改变产品状态，按主线no-progress处理。当前已重读PWF与源码；独审17例中2例仍失败：信用风险规则内“是否推出/能否交付”被宽动作词误认为已发生事件。下一步补入通用问句与实际事件的正反例，用共用事件断言边界修复，不对公司、页码、金额做特判；然后集中自然回归和一次真实同源选材。W13–W15委派文件不改。预算按最新已授权10M/$20，历史2M仅是旧原生目标文字。

真实SourceRef已只读重放一次：249页、1526候选、96选中/7689字符，8,845,814/16M，两个原checkpoint通过，原件/配置/DB未变。但旧trace helper采用缩进JSON，完整14项观察生成562377B超512KiB上限，诊断命令非零，不能作为完整trace验收；有效selection保留为selection.observer-overflow.json。修工程observer仅移除JSON格式空白（不删观察、不抬上限），最终源码冻结后需再读一次以取得完整目标链。新增独审发现在whether共享列表之后，明确but转折的simple-past事件不能继承question；已按语法转折重置，非公司/数据特判，待终审。

## 2026-10-24 W08 当前节点验证与真实复核

最终语序/列表/转折边界经314项独立测试通过，2302自然通过/11既有skip/51.32s，Ruff/mypy src373通过。真实14目标链成功输出468115B（原512KiB上限未提高），72个目标单元/14标签，249页1526候选、96/7689字符、8845814/16M；55编译任务，A12前提仍在同task。独立内容复审仍7P/5partial/2missing，模板位置被治理/通用战略等补上，不能把规则修复当完整内容改善。下一共因应修语义包价值/边际闭包竞争，再修父子/日期局部关系。

发布前cache依赖检查另发现新reporting_rules不在现有business_algorithms列表。新测试先因fixture缺mime得到partial（已设置实际HTML carrier），随后真实RED same!=changed，补一行现有依赖后58项库存/cache通过。该补丁在真实selection和2302自然包之后；原始SHA收据不重写冒称包含后补丁，最终正常pre-push另行验全。自有scratch精确清理；去重初版XML/重复selection后节点必要证据约1.85MiB。无原件/生产配置修改、无收费调用/下载、无外包文件写入。

### 最终字节补审与同源等价复核

最后发现纯会计方法“consists of”可触发新公开structure helper而绕过报告规则；原_business_fact本已有_OBJECT外层条件。两条英文负例先2F31P，helper补原条件后161项聚焦通过；最终独立320P/0F/0skip/5.19s，绑定4源/2作者测试。cache独立历史34P/6.64s及沙箱fixture ERROR均另存，不拿旧SHA代签。最终源码再次只读原SourceRef7.60s，全部96 EvidenceSpan/原文、task-local groups和55任务成员逐项等于内容独审材料，metadata差异保留；final-source-receipt绑定最终源摘要，内容仍7/5/2，零付费/下载/raw copy。

源码与阶段PWF已正常commit 1e5e6c1a（47个明确拥有文件），静态commit hooks全部通过。最终来源内容增量独审确认全部96 evidence、local groups及55 tasks和完整模型payload与旧内容审查相同，7/5/2可沿用但没有改善。独立budget-next设计已收齐，下一动作改为先修source价值/覆盖元数据而非重写正确的边际closure计费。当前仅待正常push/精确CI；阶段费用未增加。

正常push完成，远端精确master=f73afb89be1f4caf610432211281e07a14e58c77。最终全量pre-push8160 passed/24既有skip/409.50s，另独立146契约32.46s，无hook绕过。GitHub精确CI40081962182已确认in_progress，仍待终态，不写成成功。下一共因已留下6个中英文/繁体中性纯函数实际观察，未假称生产source session或选择测试通过。

精确GitHub CI40081962182已实查completed/success，绑定f73afb89be1f4caf610432211281e07a14e58c77（创建09:26:32、结束09:31:07）。当前机器/人读PWF、主线Next Step及发布收据已同步为已发布/CI成功；下一步是source价值和覆盖TDD，不继续等待旧CI。整体目标仍ACTIVE，正式摘要/缓存/真实矩阵与公司循环未代签完成。

## 2026-10-24 ROOT继续source材料价值与覆盖TDD

上一轮是用户状态解释，只读复核/重述不改变主线，按no-progress处理；前一实施节点源码1e5e6c1a、PWF89540df4已发布，精确CI40081962182成功。当前按现有预算共因设计开始实际TDD，保留legacy fact DTO/指纹，source owner输出既有value_band/topics，预算不读原文、不新建planner、不抬限额。先以中英文/繁体业务scope、客户地区定义、订单stock/FY转换与泛效益竞争冻结正反例。预算仍采用最新授权10M tokens/$20，旧原生目标2M文字为历史；本节点初始不调用外部模型。

source-value首批25个中性测试实际18F/7P（2.90s）后实现25P（2.18s）：业务scope、客户收入地理口径、订单stock/绝对FY转换分成固定覆盖用途；来源value不再直接等于eligible。复用原planner和value_band/topics，不改OperatingFact DTO/旧指纹。新增3组有限source关系扫描在现有session中按9×text而非旧6×text预留work，仍沿用16M限额；新模块加入既有算法cache闭包。下一步集中相关回归/独立反控后真实年报验证，不提前说14项改善。

## 2026-10-24 继续：独立反控要求关系绑定根修

上一轮为状态解释，无产品进展。最新相关回归338P/17.68s；独立21例13F/8P，生产公开selector亦复现：整句拼接让订单借员工/现金数，地域收入借差旅费地点，转换借供应商动作；普通英文地域收入漏选。当前按共享predicate_scope和对象后的直接谓词限定关系，移除reading内重复合同转换fallback；不改预算、不抬限额，不把338绿代签内容。

真实内容独审已完成：原7P/5partial/2missing改善为8P/6partial/0missing，A04订单/RPO/确认计划missing→pass，A03地区收入missing→partial，旧7pass保留。A02原增长子事实的选中支持回退已记录，不用缺表头数字冒充命名数据。最终线性版重新实读SourceRef，全部96 EvidenceSpan、task-local groups与55tasks逐项等于独审输入，8/6/0可沿用；工作9540035/16M，8109chars，0收费/下载/原件副本。Ruff通过、mypy src374文件0错；独审线性版406P，仍发现裸remaining obligations不属于客户合同的对象类型问题，需收敛词义后最终复验。自然包同一句柄仍运行，未重启或冒称通过。

最终独立工程410P/31.85s（34独立/32作者含效率与类型控制），374份源码树执行前后SHA一致，全部内部发现修完PASS。最后bare-obligations收敛后128聚焦/27.85s、Ruff和mypy374通过；真实原SourceRef又复核，全部96 EvidenceSpan、局部groups及55tasks仍等于8/6/0内容独审材料，未以旧源摘要代签。独占test scratch已恢复；ROOT只删除本轮重复的中间selection，留SHA/字节与全证据等价收据，不触碰原件。准备明确路径正常commit/push，无hook绕过。

正常commit完成c6182bc4；push被本地完整门拦住，8190P/24skip/3F，515.07秒；独立contracts146P/87.57秒。不是远端CI失败，未推送、未绕hook。失败为英文next twelve months RPO时间表达、新发布业务的source-description降权、一个真实paid-v3离线恢复首批partial。先诊断共因修复并重新验收，不能沿410绿冒称完整发布。用户新要求跨类型/市场真实样本提升已开始盘点：现单catalog24families，旧20样本17原件仍存在；将复用DU-BENCH/策略目录，补实际读取/选材/摘要不同轴，不重造路由器。

跨文种/市场初始实读完成：13份旧原件全部SHA匹配并前后不变，46个PDF指定页及HTML/TXT定向窗口（非全文召回），港股双语门店表与IPO条件/脚注两页已真实渲染目视，PNG恢复为空。类型矩阵/具体经验/缺样/后续实施写review/market-family-upgrade-20261024；现策略已实际进入reading_strategy，不能误称未接线。另9个DU5绑定均存在但尚未本轮核SHA/读，明确不算已验证，US-IPO/HK-call/US半年实样仍缺。


## 2026-10-24 最新真实样本调查及发布补审

最新状态以CURRENT_STATUS.md/json为准。13真实原件抽读与46页、2页视觉检查已留证于review/market-family-upgrade-20261024/，继续扩大不同公司/缺样并冻结源侧检查点，再按现24family单registry实测、TDD修复，不增第二router/逐材料许可。首次push三项失败已根修；最终458来源语义与30真实请求恢复分批独审通过，正常提交推送待完成。最新annual14为96/8146字符、55任务、8P/6partial/0missing，15.84%支持恢复；正式summary/cache/RF仍OPEN。未下载、未付费调用、未改原件。


## 2026-10-24 跨市场/文种样本进一步升级

首13+DU5九+补三共25真实原件SHA核验，有界页/段落/HTML研究窗口，无raw副本/模型/下载；USIPO正规FF试取0HTTP/0provider因budget_exceeded，精确限额待诊断。五family在单catalog内升级：20F层级、HK中报期后/业务root、CN/HK招股root/行业/募资、电话会条件CC；旧错误case01字节保留，新02及active引用修正。首5F/4P及IPO真4F/13P→75相关P，最终独立61P/3.71s、16被审文件SHA前后一致。中途sandbox Temp故障、ROOT错误profileid夹具、审查者漏封面夹具等失败均保留，不计产品根因。

三FAIL不是全假警报：真实漏DOCX后续计划/不确定性和EX99.1指标/指引；也有oldgold ASR/精确财务值职责/替代support错误。四份本次来源映射0遗漏；最终同样本无内容得分提升，不能说五policy匹配绿等于内容验收通过。见review/market-family-upgrade-20261024/的三份独审、strategy_upgrade_design与remaining_root_causes。旧公司formal summary/cache/RF循环仍OPEN。原source/request根修正常推送3b4110a3：8199P/24skip+146契约，精确CI40087657562 success；本轮策略组件正常发布待收。


## 2026-10-24 策略正常发布前兼容基线补审

策略提交912f6fbd的第一次正常push在本地拦下旧geometry policy全profile SHA：8215P/1F/24既有skip（279.15s），另146契约P。测试名/注释明确“only change with explicit policy upgrade”，因此未删断言或改产品，按五份已独审授权策略更新四legacy预期SHA，另11不变；old/new保留于policy-baseline-upgrade.json。ROOT109相关P；独立112P/2.57s，含Git旧catalog+旧fixture全部15反事实、当前15对齐、未授权语义仍失败与geometry-only仍通过。原16被审文件/原测试/旧case不改，自有临时目录清理。正常跟进commit/push待完成，不将一次失败push说成远端CI失败。新behavior-checkpoints.json冻结10条跨市场源侧语义检查点，明确已用于诊断不属blind holdout；其端到端检查仍OPEN。


## 2026-10-24 五family正常发布完成

源码912f6fbd及已独审兼容基线c990e389正常推送成功，未绕hook。完整8216P/24既有skip（318.17s），契约146P（36.29s）；精确CI40090199646：completed/success。见review/market-family-upgrade-20261024/publication.json。25原件有界阅读/五family组件61独审/兼容112补审的scope分别保留；四样本真实内容仍3FAIL/1PARTIAL、正式摘要/cache/RF未通过，不将工程绿当准确率提升。当前按M1–M5继续，既有raw/旧gold/旧case不改，0新模型调用/0provider下载。


## 2026-10-24 继续M1/M2共因实施

上一目标回合是实际进展：五family发布及精确CI成功、PWF收尾已推送a8386389。当前核对主线仍active，M1交原baseline独立读源专家形成新development gold作者包（不自签验收、不改旧gold），ROOT同时先TDD修DOCX/TXT原生匿名轮次观察与连续段落。真实Gbits116段/19选中、97无经营信号拒绝已实查；路由缺陷不是唯一共因，晚段计划限定仍需内容复验。预算按最新唯一config/resource_budget.yaml的10M/$20，不按目标历史2M重置。无模型/下载，其他作者范围不改。


## 2026-10-24 M1/M2实作中间证据

M1四份development新版源侧gold作者包保留47旧ID/importance及错误反例，新增至51；独审真实读源发现漏09:41“它不像”否定桥、Azure完整移出/旧新口径和totalCompany nochange等，作者已修并保留v1及逐字段历史，最终139锚点/151错误断言/85缺joint反例作者QA通过，独审仍进行中，不自签acceptance。

M2首轮真实RED7F/8P（首次错误pipeline调用夹具另留10F/5P历史）；DOCX1.2/TXT0.4共享native timestamped speaker观察、unknown机构角色、连续段落、不同source分隔、标题需真实多speaker证据已实施。首44P/4F揭示版本验证重复和旧预期，统一require_parser_version并保留旧1.0/1.1及0.3.1；57相关P。额外原生正文/inline end、trimmed offsets、空table边界3F/16P→57相关P。Ruff初1测试E702已格式化，mypy初2类型问题已修→374源文件0错。

真实吉比特：原生轮次/路由修复先单独观察19段不变；同源经营意向共因修复（无数字plan→action→business-object，未知阶段不升actual，有限grammar拒借员工/现金/邻句名词）首7F/7P→33P，另2反例已补；READING_DISCLOSURE_SCAN_PASSES 3→4用于预扣新增扫描，原16M不提高。最新真实23段/8230UTF8字节/23映射，oldgold五critical字面源锚点1→5、overall仍FAIL；新增5/6/16/89段原文实读确认未来存量运营、企稳不确定性、未落地更新和降低买量依赖均在，ASR“会不会”原话不改。不是新gold/模型/公司验收。源码和原件SHA冻结见m2-intent-real-selection/replay-binding.json。M2相关集中测试同一82717句柄仍运行；独审由未参与实现者进行，当前不写其范围。不付费/不下载/不改生产配置。


## 2026-10-24 M1验收与M2独审根因收敛

M1独立源侧审查完成：四新development gold共51事实/139原文锚点，102P，旧47ID/importance/false assertions和v1修订历史完整保留；旧输出按新gold仍PARTIAL/FAIL/FAIL/FAIL，未将金标修订当产品通过。

M2独审集中候选382P/3F，两个失败共同根因是clear重置closed导致文末附录重新获得speaker，已使物理边界仅clear active；第三项旧测试只要求限制在context，已强化成每个left的事实support及实际source card必须保留right，而非回退产品。匿名轮次、动作吞词、业务名词中心词、计划限定漏入请求、重复版本白名单均在各自共用owner修复。中文短句观察复用同一去标签substantive函数，空label/单汉字不能冒充正文。最终独审仍进行，既有失败保留。

ROOT阶段530P/11既有skip、374源文件mypy零错；其他中间RED/GREEN及独审工具夹具错误各自留证，不能累加成最终测试数。版本窄修58P证据只签actual factory→normalization→JSON/replay，完整DOCX历史/当前cache测试曾在旧1.0的本机HTTP阶段unknown reservation，现独立诊断中；不归咎费用耗尽，也不代签生命周期通过。

最终冻结源码53f891204a9cbf573fe6babb22d699a46ceba7c56a05bc0a1d2b72ff4d36f593下四真实文档回放23/30/96/7全部精确映射，原件SHA不变/0下载/0模型。Gbits旧critical源锚点5/5、叙述7/9，overall仍FAIL；HK中报/US附件缺口和稀疏季报噪声仍保留。源侧回归不是正式摘要/cache/RF验收。最终回放见m2-final-real-selection，后续若源码变动须重新绑定。


## 2026-10-24 M2最终独审与真实生命周期通过，待正常发布

最终独审386P/31.14s（47独立反控），全374源码及真实Gbits首尾SHA一致，未修内部发现0。ROOT最终Ruff通过/mypy374源文件0错。真实DOCX public-history完整CLI/worker：旧1.0正式生产、历史resume不改DB/原artifact/预算，新1.2独立generation、当前cache复用0新增调用通过（1P/43.58s，合成本机HTTP）。sandbox内旧1.0阶段unknown reservation同一测试失败保留；在标准本机loopback权限下同测试通过，具体transport异常未单独保留，不宣称费用不足/产品预算修复。此前只签factory58P的边界已补，仍不代签正式配置真实公司摘要/cache。

原生结束状态、NP head与限定事实support的最终修复已纳入此冻结版；四真实A电话会/稀疏季报、HK中报、US附件回放与独审源码文件逐SHA核对一致。原件未改，源选择oldgold状态FAIL/PARTIAL/FAIL/FAIL保留。自有三临时目录已恢复absent，详见m2-root-receipt.json。正常commit/push待执行，尚未宣称远端CI通过。


## 2026-10-24 M2正常发布被全量push总时限拦截

源码/测试/PWF正常commit65cd8f58成功。第一次正常push因动态执行变更触发全8315 Unit，跑至84%未见断言失败但600s总超时，146契约/110.81s通过；未发布，不虚构远端CI。候选源码/测试/PWF whitespace检查通过，历史失败XML保留原始输出空白，未为git diff空白提示改写已绑定证据；正常pre-commit全过。

未盲重跑同次全量。只读查W13工区HEAD=a8045416，已实现但handoff=INCOMPLETE_EXTERNAL_BLOCKER（作者未做最终独审），故母表READY_NOT_DISPATCHED已过期。ROOT另派未参与实现者从冻结Git对象隔离审查，不改作者工区/索引，不自动把草稿签PASS。通过后接收已有bounded fast push并保留full_validation_pending/完整模式/远端CI，不绕hook。M3继续只读定义/口径共因调查，产品源码暂不改动。

用M1新development gold评同一final选择另留development-gold-evaluation.json；Gbits/Proya/HK出现0值同时含quote跨fragment/缺line/scope观察信息，不能拿这些未拆解数字宣称M2退步或召回率通过；完整源侧锚点检查和真实卡片仍需对应locator/作用域复核，旧gold/旧观察不改。该诊断文件不是新验收。

## 2026-10-24 W13 ROOT 修正、独审与并线待发布

W13作者冻结候选a8045416的独立审查为FAIL：33/65/333个已关闭文件仍扩成62/94/362个pytest目标，提前输出local_fast_pass，且不列实际目标；作者handoff将Git blob前缀误标成SHA-256。ROOT在pending merge内修正为32个文件预算、宽/目录/未知整体defer到CI、先列完整目标并在成功后报告pass。独立审查绑定八个文件物理SHA，ROOT版本154P/125.60s、18独立探针P、5真实Git ref端到端检查P、Ruff PASS；不重跑8k全量。原作者候选和作者工区随后新增的未提交review分开保存，未混入接收。证据与不通过项见review/w13-root-reception-20261024/。旧19路径失败已证实是Windows路径长度（259可用、260+稳定失败），以及B10 3F/13P均未由本包修复。当前需要常规merge commit和正常push，再查精确远端CI。

M3只读真实样本调查已完成：MSFT指标定义、RPO口径、新旧/机械重列指引漏入选择；HK中报AI/CDN反向因素、单一经营分部、下半年计划、重大投资否定及编制/币种说明不完整。另有observer没有canonical span/task scope证据，因此一些旧分数不可判，不能统一当产品召回失败。neutral probe为6 RED/4 PASS。下一节点按报告在共享source-disclosure、既有predicate/time和局部依赖owner先写RED，再实现及集中实测；不抬限额、不拼全文、不新增router，不以scope观测不足宣称产品修复。报告见study/m3-discovery/report.md。

## 2026-10-24 W13 CI 根因修复与 M3 R5 验收

精确CI `40098625678` 在 W13 合并HEAD `3bcfc202e1657cdd9d5e3797c4b76cd40b8b8c57` 失败，三项 `tests.unit.test_daily_push_policy` 行为测试均指向同一Git mode 根因：hook在Linux checkout不可执行；测试fixture还用`shutil.copyfile`丢失执行位。ROOT已将`.githooks/pre-push`暂存为`100755`、fixture改`copy2`并加mode回归。隔离本地Git push E2E 4/4、mode回归1/1通过；未重复跑8k全量。正常push和精确新CI待本次提交后完成。

M3 R5独审`PASS_REVIEWED_M3_SOURCE_BEHAVIOR`，报告绑定六份当前源码SHA；五份原件与回放卡绑定一致。596项相关测试30.43秒通过，Ruff/diff-check通过。R4发现的`, which represents...`解释从句借谓词问题已由R5反例验证关闭。Proya 2026Q1原件12页，逐页文本检查并视觉核对1/3/11页；仅第3页包含对经营现金流下滑的有意义经营解释，其余以财务表/股东信息为主，现选中该解释合理。M3不代签正式摘要/cache/RF或完整业务覆盖。

## 2026-10-24 后续精确 CI 回归修复

主线`e3e7d2fb`精确CI `40109033205`报5项失败。定位后修复财务变化错误进入叙述业务、治理培训误分类及跨页未闭合后缀处理。四文件代码提交`c22a952f`通过正常提交钩子；定向unit 322项、integration4项、Ruff、diff-check均通过。复用M4真实双季报结果与SHA，不下载、不调用模型、不改原件；未重跑8k全量。PWF本轮收据待提交，随后正常push并检查新精确HEAD CI，再按顺序诊断M5预算拒绝。报告：`review/market-family-upgrade-20261024/ci-regression-fix-20261024/report.md`。

## 2026-10-24 M4 稀疏季报根因修复与复验（覆盖上面的调查中间状态）

按真PDF定位到三个共因：连续性引擎把完整句与未闭合尾巴一并延后；同页下一行实测间距1.074em超出旧1.0em阈值；法定非经常性损益补助模板误成为业务卡片。TDD先确认行距回归旧版失败，再修复为最大1.15em并保留超限拒绝；连续性改为只延后未闭合片段，避免页边界二次扩大defer；报告规则屏蔽套话。

中微公司2026Q1真实正控再次回放后22 spans/1,340字符/13可用卡+1不可用卡，8300+、300+、Angnova 140:1、Domingo >700:1、薄膜设备224.23%均有来源卡；珀莱雅2026Q1负控4 spans/87字符/1可用卡，现金流原因被保留。零下载、零模型调用、两份PDF原件SHA不变。中微仍partial，未被证明的其他内容不提升为摘要。

连续性/几何136P，当前组合346P，Ruff和diff-check通过，M4验收报告及结果JSON已保存。W13远端hook mode修复在受限环境出现4个隔离Git/sh环境错误后，正常本机Git环境该定向文件25/25通过。W13根修`4e593c71`与M3/M4源码及PWF`159770e9`已提交；现待正常推送并核对精确远端CI，未重跑8k全量。CI通过后按计划进入M5 provider启动前预算拒绝根因诊断。
## 2026-10-24 M5 观测链与二次发现根修

CWP AcquisitionCoordinator此前在本地准备阻止下载时丢弃唯一local_read_budget/1观察；新增严格operation-contract验证后将其透传，FF用现有filing-local-preparation-observation/1承接，不新建状态账本。独立真实路径E2E驱动RF→FF→CWP，设置offline socket拒绝器与marker provider；观察到source-group limit及limit+1计数，provider_started=false、0下载、marker不存在、路径不泄露。

同一回归还发现issuer layout二次发现未复用historical scope journal/已有metadata，使已知旧期来源被重新当作未分类。修复后canonical scope 22项通过；合同/历史scope/E2E最终组合46项通过，Ruff、三模块mypy、host guard（68既有违规/0新增）、diff-check通过。CWP源码commit 0f64289e已由正常pre-commit提交，尚待PWF commit、push和精确CI。

FF曾有6个pre-push测试因合成请求3秒总预算/Windows探针1秒预算被全套运行调度延迟耗尽；提高测试合成预算而保持生产deadline/清理/隔离规则后，8项聚焦回归通过，完整pre-push为933P/7既有skip/78 subtests，FF精确CI 40115441655 completed/success。旧Snowflake 2020 S-1原件目前不在公司池，未重试原请求；原历史bound仍OPEN。无provider调用、下载、模型调用、Dayu变更。本节点报告见review/market-family-upgrade-20261024/m5-local-budget-observation-20261024/report.md。

## 2026-10-24 M5 发布与精确 CI 收口

CWP源码`0f64289e`和M5 PWF收据`0acae348`均已推送；精确CI `40116401110` 绑定HEAD `0acae348484d661278faa62641ad426f2c8cf485`，completed/success。FF `e0d96426445e4b93bc6cc7a6e6014996ad0a777d`的精确CI `40115441655`也已success。M5机制验收关闭，但Snowflake 2020 S-1原件本地缺失，故旧事件的精确触发bound仍OPEN。

当前转入真实正式摘要与缓存恢复：从已经在库且原件SHA可冻结的跨市场/文种材料中选样，使用配置的共享引擎与provider，检查原语言正式摘要、引用和限定、同源缓存复用、进程中断恢复及RF实际读取；不重跑8k全量、不重复下载已存在的原件。M5本身仍为零provider请求、零下载、零模型调用，Dayu未改。

## 2026-10-24 W13/W14/W15外包包ROOT接收

三包均已按最终代码、独审绑定版本、测试结果及清理收据完成ROOT接收，具体证据：[三包ROOT接收报告](review/package-reception-w13-w15-20261024/README.md)、[机器收据](review/package-reception-w13-w15-20261024/receipt.json)、[更新后的dispatch](harness_lanes/20261024/dispatch.json)。

- W13：作者最终取消32目标保护，宽范围实测357个目标耗时628秒，触及旧600秒边界，因此ROOT不整包复制；主线保留≤32本地目标、宽/动态/目录/未知转固定smoke/CI。`67439d0ac13ddf3e3b4fa4f8ef20cf1a4e87999c`加入精确节点去重和smoke-only truthful label回归。154项定向测试、18项独立策略探针、5项真实Git push检查、Ruff通过；未跑8k全量。PWF一并正常push后等待精确HEAD CI。
- W14：RF main已快进并推送至`aa19b653da18566e582e802269f5908471c456db`；独立审查APPROVE，22项相关回归和pre-push 595 passed/1 skipped/36 subtests通过。范围只覆盖离线工程E2E，没有真实下载或公司分析；不重跑其长时端到端。RF中既有3份修改的assurance文件和untracked output未触碰。
- W15：Audit本地main接收至ROOT修复提交`37e12e6ff4674fa1989b2616cff3c31faa4d8cb0`。集成回放发现固定SHA受到Windows CRLF/LF变化影响；`.gitattributes -text`和canonical SHA修复后28项通过，adoption replay complete、8 counterexamples、cleanup_verified；14个fixture SHA均匹配。Audit无remote，因此只记录本地提交，不称已推送；不相关预算脚本未动。

三包本轮没有改原件、下载或调用外部模型。CWP W13仍需正常push并读精确CI；随后恢复正式摘要、缓存复用/中断恢复、RF实际读取、跨市场/文种真实内容与四路审查。工程施工包全部接收并未关闭整体PWF目标。


## 2026-10-24 CN H1 RF接口联调、根修与W13-W15接收更新

- W13/W14/W15均完成ROOT接收；W13精确CI `40120507146` 对HEAD `83e49a6b3a83a78726de9c7a40e4bdbc6baf52fc` success。
- 中微2026H1冻结原件与artifact在官方store隔离catalog重建，RF v3上下文真实读取、citation adapter `source_owned_views`、69/69 groups/views、112 EvidenceSpan通过；v6 0下载/0 provider调用/临时catalog删除。沙箱曾拒绝`os.link`，相同测试改在本机权限运行后通过。
- Independent review发现的v3裸诊断白名单、target used超限和schema非字符串根因在RF/CWP两端统一修复。RF commit `c48f86bd0d56f0a2be67a71348cf05d8544b6cdd`已推送并与`origin/main`一致；最终只读接口独审PASS。RF聚焦测试85P，Ruff/mypy/host guard通过，pre-push 595P/1skip/36subtests；CWP `test_narrative_reading_transport.py` 54P。
- CN H1内容仍partial/needs_review，68 claims均uncertain/needs_review。context 195,794/196,608 bytes，只余814 bytes。下一候选微软FY2025 10-K原件SHA `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`、8,158,067 bytes，原件已在本地，下一步只做零费用预算/结果边界预检，不下载。
- 本轮尚需提交/推送CWP producer检查、112财报选择上限、Phase C拒绝分类和PWF更新；整体W12内容质量审查与holdout循环保持OPEN。

## 2026-10-24 CN H1发布收口与三条独立旁线施工卡

- CWP commit ae45b49adff21a3f79bec38512b225609051b434 已正常推送。pre-push 根据宽影响范围只运行合同烟测 154 passed in 133.76s；358 个受影响目标交给远端 CI。精确 GitHub Actions run 40129398346 / check 120977676826 对应本 SHA，记录时仍 in_progress，不先行宣称通过。
- 准备三张互不重叠的外仓卡，见 harness_lanes/20261024-independent/README.md：industry-research 报告生成边界、QAbyLLM RAG 重建失败保护、MeetingConverter 三文件输出完整性。开始 SHA 与派卡时状态已冻结；MeetingConverter 既有 .coverage 修改列为保护项。
- 三卡均使用合成数据/临时根，无真实公司资料、模型/API、网络或下载。必须由未参与实现的独立 agent 审完整 diff、独立运行验收测试并添加反例；所有发现修复和复审最终 SHA PASS 后才允许交接。三卡不改变当前 company-wiki 主线，也未新建外仓 worktree 或写外仓代码。

## 2026-10-24 CI 40129398346 根因与测试合同修复

- 精确HEAD ae45b49adff21a3f79bec38512b225609051b434 的远端CI于 Unit tests 失败；公开annotations只给部分失败且JUnit unavailable，失败步骤之后的focused contract、CLI、secret scan跳过。
- 从producer diff和本地重放定位共享根因：financial-report route 有意把annual/semiannual/quarterly的默认selection_limit由96提到112；三个annual_report单测helper仍硬编码96，所有这些用例在内容断言前即被合同值断言挡住。它们是过期测试期待，并非提取结果错误。CI hook快门仅跑154项smoke，受影响unit目标转远端CI，所以pre-commit/本地push门没执行这些用例；远端CI及时抓到错配。
- 按生产route合同改三个测试helper引用FINANCIAL_REPORT_SELECTION_LIMIT，没有回退112产品上限、没有删除测试。3个受影响单测文件加routing architecture tests共143 passed/9.32s，Ruff通过；测试修复仍待正常commit/push并验证新HEAD CI。

## 2026-10-24 CI 二次失败后的测试合同补漏

CI run `40130559322` 精确绑定commit `61ecfc2b9ae33e87691e4765c36c82481959db6c`，在`Unit tests`失败。公开check-run注解定位N6的`<=96`断言和production-selection `_select` 默认仍显式传96。两者由第一轮修复未枚举全部财报默认限制假设造成；不是112路由产品逻辑错误。将前者绑定`FINANCIAL_REPORT_SELECTION_LIMIT`，后者helper改为`limit=None`，让正式路由决定默认值，显式budget测试仍显式传参。

五个相关测试文件与routing architecture测试共181 passed/36.88s；Ruff与diff-check通过。一次无basetemp的同套运行为180 passed/1环境setup error（Windows沙箱系统temp无法再创建pytest numbered directory）；该唯一用例显式使用仓库内隔离basetemp后通过，临时目录清理完成。接下来正常提交并push，等待新精确CI；通过后继续MSFT 10-K零费预检。旁线三卡已推送，卡片要求各自实现者提交后由非实现agent独立审查最终SHA并修复所有发现再交接。
