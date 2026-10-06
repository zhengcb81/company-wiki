# N5-DOCSET — 多文档类型真实质量基准

回答一个问题：**现有 parser/selector/locator 从真实资料里挑出来的，是不是真有价值的业务描述；漏了多少、夹杂了多少。**
不调模型、不联网、不下载、不产生任何投资评价；被测对象是仓库里既有的
`parse_pdf` / `parse_transcript_text` → `select_narrative_evidence` → `verify_*_evidence_spans`，
本目录不复制任何解析或选择实现。

## 文件

| 文件 | 作用 |
|---|---|
| `samples.json` | 9 份真实原件的登记：doc_type、language、SHA-256、byte_size、只读定位参数（root key + 相对路径）、parser 选项、是否 fixture |
| `local.json` | 本机只读根的绝对路径（**被 `.gitignore` 排除，不入 Git**） |
| `golden.json` | 86 个人工标注点（每份 8–12 个），含业务主题、正/负例、required/optional、角色、情态、locator、短引文与 `quote_sha256`、选择理由、实读范围 |
| `evaluator.py` | 评估器 + `report.json` 校验器（schema `narrative-document-quality/1`） |
| `run_benchmark.py` | 跑批 CLI：解析 → 选择 → locator 回放 → 引文定位核验 → 评估 → 自校验 → 写 `report.json` |
| `report.json` | 一次真实运行的结果（source-only） |
| `tools/extract_pages.py` | 标注期只读抽页工具（把原文页/行拷到 `tmp/` 供人工阅读），**不属于评估链路** |
| `tests/` | Unit（评估器反例）/ Integration（真实 parser/selector）/ E2E（独立 catalog + 正式只读接口） |

## 怎么跑

```powershell
# 完整 9 份（本机约 7 分钟，零网络/零模型）
python benchmarks/narrative_document_types/run_benchmark.py `
    --output benchmarks/narrative_document_types/report.json --overwrite

# 测试（一次性集中节点）
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:CW_BASETEMP_FALLBACK_ROOT="$PWD\tmp"
python -m pytest -p no:cacheprovider --basetemp tmp/n5-docset-test `
    benchmarks/narrative_document_types/tests
```

`local.json` 不存在时（干净 clone、无本地原件），Integration/E2E 会对缺失原件 `pytest.skip`，
Unit 测试仍全绿。

## 样本（9 份 ≥ 8，覆盖卡要求的全部类型）

| sample | 类型 | 语言 | 格式 |
|---|---|---|---|
| S01 | 年报 | zh | PDF |
| S02 | 半年报 | zh | PDF |
| S03 | 季报 | zh | PDF |
| S04 | 招股书 | zh | PDF |
| S05 | 增发募集说明书 | zh | PDF |
| S06 | 可转债募集说明书 | zh | PDF |
| S07 | 有价值 IR | zh | PDF |
| S08 | 程序性/套话 IR | zh | PDF |
| S09 | 英文电话会 | en | TXT |

S01/S04/S07/S09 与既有 G1 四样本一致（P01/P04/P07/T01），其余为本包新增（半年、季报、两类再融资、程序性 IR）。

## Golden 标注约定

- **先读原文再写标注**：用 `tools/extract_pages.py` 把页/行抽到 `tmp/` 逐页读，selector 输出只作为被测对象。
- 每份 ≥6 个点、≤15 个点；每份记录 `read_scope`（读了哪些页/行）、`uncovered`（未覆盖范围）、`ambiguities`（歧义）。
- `locator.page_number` 是 **PDF 页序号（parser/locator 用的 1-based 页码）**，可能与页面上印刷的页眉页脚差 1。
- TXT 用 `line_start/line_end` + `byte_start/byte_end`（UTF-8 字节偏移）双重定位。
- `quote_sha256` = 引文 UTF-8 的 SHA-256；评估器每次运行都会重新到原件对应位置核验引文，
  **引文无法定位的点不计入覆盖率分母**（并在行内标记 `verified: false`）。
- 负例类别覆盖：`pure_financial_table`、`table_of_contents`、`legal_boilerplate`、
  `repeated_paragraph`，另加 `procedural_form`、`static_reference`、`metadata_header`。
- 角色：`company_statement`（company_filing/management）与 `question`（analyst/investor_question）。
  情态：`actual` / `planned` / `forecast` / `negation` / `question`。
- 程序性文档（S08）只有一条事实性正例；**缺信号的季报不会被当成无价值**（S03 有 4 条 required 正例）。

## 指标与分母（report.json 每行都写明）

| 指标 | 分子 | 分母 |
|---|---|---|
| `required_coverage` | 引文完整出现在被选中且同页/同行范围内的文本里（`full`） | **已定位核验的 required 正例**（在该样本 `read_scope` 内） |
| `optional_coverage` | 同上 | 已核验的 optional 正例 |
| `selected_noise_rate` | 带负例引文的被选 span | **落在标注范围内、且能被任一 golden 点判定的被选 span**（judged） |
| `duplicate_ratio` | 归一化后重复的 span 数 | 该样本全部被选 span |
| `role_confusion` / `modality_confusion` | 匹配到的 span 角色类与 golden 期望不一致的点数 | 有匹配的 golden 点 |
| `selected_utf8_bytes` / `source_raw_bytes` | 选中文本 UTF-8 字节数 / 原件字节数 | — |

`full` 需要整句引文落入被选文本；相似但不包含的段落只能是 `partial`（≥0.6）或 `miss`，
**不会被算作命中**。`partial` 不计入覆盖率分子。

## 已知边界（诚实声明，不是免责声明）

- 标注是**定向精读**（每份读了相关页段），不是逐页穷尽；未读范围写在 `read_scope.uncovered`。
- 覆盖率低不等于“资料没价值”，只说明当前 selector 没把该引文放进输出；
  单条 miss 需要区分是预算截断（`omitted_candidate_count`）、候选规则没打分、还是跨文本块切分。
- 噪声率只在“可判定”的被选 span 上计算，未判定的 in-scope span 单独列 `unjudged_in_scope`。
- 全表扫描（`full_table_scan: true`）只用于让表格负例可判定、并让 `coverage_complete` 为真；
  生产 handler 的默认第一遍是自动表扫描、零命中时才回退全表扫描，两者差异记录在 `parser_options`。
- 本基准不调阈值迁就实现：报告如实保留非全绿结果，产品缺陷移交 MAIN `open_items`。

## 复现与保护

- 跑批前后校验原件 SHA-256、byte size、mtime；任何变化直接报错退出。
- 临时文件只写 `--temp-root`（默认 `tmp/n5-docset-run`），单个度量文件写完即删，报告记录 `temp_peak_bytes`。
- 不写生产 catalog/索引/配置；E2E 用自己的独立 catalog（SQLite 在自己的 tmp 根内），结束 `finally` 关闭并删除。
- 报告 `output_scope: "source-only"`：只有来源、解析、选择、定位与覆盖率信息。
