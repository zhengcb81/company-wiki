# 当前行动计划（2026-10-23恢复）

**唯一入口：** [CURRENT_STATUS](CURRENT_STATUS.md)。用户2026-10-23“继续”已恢复实施，原生目标active；整体计划未完成。以下历史记录不覆盖入口。

## Next Step

ROOT继续定位W08真实249页年报两条业务30%事实的候选资格/排序/父级保留根因，原96/48000/16M上限不变；两份外包卡W09-RF-RESEARCH与W11-CWP-SOURCES已准备，可现在并行启动，不等W08。ROOT不再同时施工其独占写集。

W08公开cache、跨列/缺页父级和通用事实误判的有限工程独审已绿：15上下文+36事实反控及1正式公开cache（32.59s）；但真实249页原件oracle仍FAIL，两条30%事实未入选，未并线/安装/推送。W09已完成49项原文绑定建议及经营桥准备（42 Decimal公式/14来源加总/10作者反控）；新正式RF尚未执行。W10工程已提交安装但真实矩阵OPEN。详见review/r1-w08-resume-20261023/checkpoint.json。0新增付费/下载，预算unknown均保留。

[两份可启动施工包](harness_lanes/20261023/README.md)：RF研究和CWP官方来源离线诊断分属不同工区；ROOT保留W08/新摘要/预算/中央四审/合线。原公司复验后仍依次药明合联→Snowflake及后续清单。

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

# DU11 ROOT 剩余来源闭合实施

PLAN_ID=du11-source-closure-2026-10-18; PWF_PLAN_ROOT=docs/plans。唯一实现owner ROOT。作者工区沿用当前ROOT隔离checkout；母仓主线正常推送期间不改母仓源码/HEAD。RF/FF两DU11外包工区、Dayu/IQS不写。

## 入口与完成定义

**当前工程位置（2026-10-18）：** B1已正常发布9c681ed2，精确CI39092308121 success；RF外包已独立18项验收、main与远端f8002f5f、精确CI39092538354 success、安装6文件定点同步，旧3个assurance WIP不变。FF初审102项主链绿但4反例暴露发布日期及代码解释漏洞，隔离修后28边界＋真实HK TXT1链独审通过；待ROOT先发布CWP producer的canonical_identity可选投影，再正常发布FF，不让新flag先上线断链。

ROOT本节点是物理跨页/真实parser MIME/共享语法/因果cache以及FF reader端口完整组件，**不代表唯一/集体先行词或正式C已完成**。32ab6e06已合母仓5ad4295f/6ee5ebf1但尚未发布：正常push的全量单测在600s到约96%超时，保留原失败日志，不称已推送。现有xdist依赖用于完整unit目录的两个隔离worker，窄测/contract保持原运行方式、集合和600s期限不变；完整运行与远端CI仍待正常push验证。

新真实诊断查明paragraph_index每页重置，而ordinal为source全局位置；未知下一页底部计数块也不能抢先清掉上一页半句。修在同一native owner，未知前缀只defer而不伪造家具/正向拼接。77项相关行为通过、独立10个不同控制跨两轮通过；本次实源诊断旧t32“求的同时…”selected_matches=0，t34“该系列产品…”仍1，原件/gold不变、0API。该诊断明确不是冻结内容验收/性能收据；不得把10/10 gold命中当语义闭合通过。剩余有界先行词设计参见review/antecedent-owner-design.md。继续不读作者密钥、不写原件/gold/生产配置。

母计划 document-understanding-2026-10-13 为总控。前置代码9eff4ee7随e33d40ed已正常发布：6741PASS/24SKIP/580.05s和142独立合同PASS/37.31s；精确CI39090720114 success。母仓后续文档0099dd5d已正常推送，未触发新的行为CI。剩余真实CN断句/指代见 ../du11-source-quality-2026-10-18/closure-investigation/findings.md；具体20源码接口调查见 ../du11-source-tail-geometry-2026-10-18/review/remaining-closure-design.md/json。

完成要求：所有可证明的跨页原support和有限明确先行词context可复现；缺证/多义/超过原上限仅该卡defer，不创造事实；正式三供应商摘要、真实收费/activation恢复、同/跨run缓存和FF/RF消费均通过且有独立内容审查。金标命中/元数据/局部测试不替代完整内容质量。

## 阶段A — 先写端到端依赖行为与纯反例（IN PROGRESS）

1. 用现unit IR/观察/结构/SourceOperatingSession，不新增parser/store/第二预算。先写新公司名通用fixtures：两物理页原句切断、明确同列/同scope和真正running furniture，输出一个多原span support，禁止伪造跨页native_page_view。
2. 缺上一页/列未知/真实页眉证据缺失/TOC/表格/QA/新project或section/source/font/frame/页序不匹配/下一页独立新断言为反控。只知道block_char_start=0不能宣称语义闭合；也不能把所有singleton判残缺重演HK0/7。
3. 唯一/集体产品先行词(简繁/EN)跨窗口；明确列举的A/B/C仍集体，不把每个成员各宣称验证成功。两个竞争series、普通章标题、另一公司或问题、前文缺失及预算不容纳均defer。
4. typed summary/public-context链检查target与context refs同数值offset也不混映、原文SHA/locator/parser/否定/计划/日期/单位原样、所有支持与上下文事先计入同budget。重复page pdf_block号码必须按(source,page,block)计，不得低估。
5. 真实问题与新组合先RED留证。无需每小步人审/签收。

## 阶段B — 现source owner生产接线

### B1 完整组件：共享预算与线性metadata索引（已正常发布、精确CI绿）

不与B2混签：B1只包含已完成的test_source_metadata_budget.py九项及两owner改动，当时跨页RED仍隔离。包external-context只索引一次、exclusions只union一次；每个实际member/context fanout、section heads×body和排序在扩展前扣现WorkBudget。几何局部200K只是同parent嵌套上限，不克隆余额；预算不足在source owner返回有限partial，不能释放半句。

独审两个预遍历遗漏先写反例，RED7PASS/2FAIL，修后集中739PASS/50.52s。之前733PASS/4FAIL是新测试未定义fixture及deepcopy不兼容不可变MappingProxy，已改为正确source_case及递归全字段快照；保留失败日志，不修改生产IR迁就pickle。两预遍历修复为headings在prose成功后单独预扣；native sections先按len预扣再chain，预算0时真实ID访问0。

### B2 剩余物理与指代闭合（OPEN）

物理组件现30行为反控/8依赖与性能控制/既有states及cache集中219PASS10.11s；最终不同agent27有限PASS8.51s（含5个逐owner CRLF等价反控）已签精确5源码/2测试SHA的PASS_PHYSICAL_BUDGET_CACHE_COMPONENT，自有Temp删除。不能忽略实源接线：真实PDF IR此前mime_type=None，已先RED后在唯一PDF parser声明实际格式；全source coverage_complete含细表deferred，不能因此全局关闭物理处理再让半句退回singleton。现按完整coarse正文和pair实际opaque/deferred状态判断，pair未知只defer该pending依赖；页9缺细表不能禁页7→8已观察的延续。复用同account，当前未知column不伪造证明。

共享statement边界复用operating_states脚本/issuer/NP/aux grammar，修繁体新issuer及English新产品主语；首个真实predicate只扫描subject一次，不能遍历每个后续predicate形成N²或借object当subject。Inventory1.8补实际5个共享grammar/matching/兼容owner源字节hash，不仅依赖import方偶然变化。

真实最新0收费三源仍10/10、7/7、8/8 source及canonical；实际parent work6106955/12820408/7975948未超16M，原件/gold不变、0copy/0POST、自有Temp删除。历史第一次physical回放的PDF MIME和全局coverage使新flow未生效，保留该收据，不把它代签当前实际路径，也不称全部语义质量绿。

### FF/CWP 最终读取端口（已按producer→consumer顺序发布、精确CI绿、安装完成）

CWP source_reader_cli可选--include-canonical-identity，由现security_code唯一owner投影market/security_id（schema source-canonical-identity/1），manifest保持观察值。现CLI复用open_described_version一次metadata观察与字节验证，原global/source lineage指纹兼容，旧hash不作权限阻断；显式None的not-applicable scope与未观察由sentinel区分，避免重复读取。5新及既有reader/identity/CLI共59PASS37.37s；两reader最终SHA与FF跨仓独审相同。

FF当前manifest的future/invalid/None不再继承旧query资格，使用已有date primitive；provider未知不能满足显式fmp；FF严格消费CWP canonical projection、legacy严格值比对，不再抄市场normalizer。原作者工区不改，根修在ROOT独立FF工区，独审29unique跨次通过非伪造单轮全绿。

- native_continuity只负责可观察物理proof，原同页edge/native_range保持严格；跨页原多span的closure planner返回reference-only包与不足诊断，不生成新原文。
- 入口在narrative_reading._prose_reading_packages -> _candidates carrier替换之前。旧body windows由新完整group消费/替换；同unit不得多个analysis owner静默最后覆盖。独立context可共享但不能暗变第二body owner。
- 只有structure诊断REPEATED_RUNNING_HEADER等已证明的ID可跳家具；excluded_furniture union包含TOC，不能全跳。列None相等、matching margins alone、no_column_gap不是现成单列证明。
- SourceOperatingSession.groups已能暂态CJK连接并返回5类原unit refs。新增referent proof由现operating_states owner复用prepared views/NP/对象规则，不能PDF adapter再造产品词典。明确unique/collective/ambiguous/missing与真实上下文refs；context refs原始namespace不得送_original_refs当target坐标重映。
- citation_support_views/required_context_unit_ids原端口保持；project原子上下文/公共最多2视图、typed execution原上限不放宽。缺proof在现deferred/withheld通道说明，不加人工许可。

## 阶段C — 大节点验收与发布

一次集中相关unit/integration/typed-public-context + 不同agent最终源码独审，全修真实发现后正常提交并线推送并核精确CI。真实CN/HK/US0收费源检查，再按母现配置/同累计ledger依次真实供应商摘要与缓存/FF-RF C。源码变动与收据按版本绑定，不把历史成功重签新SHA；测试owned目录原样恢复，生产raw/config/gold不写。

## 资源与范围

仍同WorkBudget16M、96spans/48kchars、物理8原unit/4个(source,page,block)/2048chars、draft56KiB/summary64KiB/execution32KiB。必要先行词也计原block/unit/char，不能作为freecontext绕限。实际CN p17/9–14全纳为5blocks，若无法证明更小真实充分context则诚实defer，不升上限/猜单个产品。

先建立一次metadata索引和有界邻窗，最多常数邻居/每scope有限已读上下文；每次新观察预扣原account，耗尽不能重启balance或释放半句。原paid run/未知费用不改，当前累计742228tokens/$0.421556proxy、历史unknown7+401新hold保留；限2Mtokens/$20，供应商按真实现配置，不读/打印密钥。

### 历史 Next Step（已被当前入口取代）

RF最终pin9669c4d7精确CI已success；本次PWF汇总正常提交/推送后，不重复接收/发布这两卡。下一工程节点：按最终接口先TDD写有界先行词（非event描述同样检查）与original/analysis namespace、原始联合限额及不重复扫描反例，再在现唯一owner接线。保留原文fallback只读视图，先readiness/context后单一graph与fact；未知/多义/超过原4blocks/8units/2048chars仅该卡defer，不编公司特例/raise上限/克隆16M余额。真实三源仅在完整节点完成后回放一次并独立内容检查，随后正式三供应商摘要及收费/activation/同跨run缓存/FF-RF C；holdout/RF循环仍OPEN。

</details>
