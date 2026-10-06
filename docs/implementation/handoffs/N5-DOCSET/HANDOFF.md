# N5-DOCSET — 多文档类型真实质量基准 交接

- **Lane**：N5-DOCSET（独立包，未改任何既有 tests/src/scripts/CI/配置）
- **分支**：`codex/n5-document-quality` ｜ **基线**：`e46108b4f30d5b7e47bfc712e360f173c00b702c`
- **交付提交**：`9ff251ec9ce5b29b294477d66f84336a464fc29c`（本文件随下一次提交入库）
- **规模**：15 个新增文件，7,164 行，约 350 KB（≤2 MiB；不含任何原件、PDF、绝对源路径）
- **预算**：0 模型调用 / 0 provider HTTP / 0 下载；全程只读源仓

## 1. 交付了什么

`benchmarks/narrative_document_types/`（说明见同目录 `README.md`）：

| 文件 | 内容 |
|---|---|
| `samples.json` | 9 份真实原件登记：类型、语言、SHA-256、byte_size、root key + 相对路径、parser 选项、`metadata_is_fixture` |
| `local.json` | 本机只读根绝对路径（**git-ignored，不入库**） |
| `golden.json` | 86 个实读标注点（每份 8–12 个）：主题、正/负例、required/optional、角色、情态、locator、短引文 + `quote_sha256`、选择理由、`read_scope`（读了哪些页/行、未覆盖范围、歧义） |
| `evaluator.py` | 评估器 + 报告校验器，schema `narrative-document-quality/1` |
| `run_benchmark.py` | 跑批 CLI：解析 → 选择 → locator 回放 → 引文定位核验 → 评估 → 自校验 → `report.json` |
| `report.json` | 一次真实运行结果（source-only） |
| `tools/extract_pages.py` | 标注期只读抽页工具（不属于评估链路） |
| `tests/` | Unit 22 + Integration 6 + E2E 1 = 29 |
| `.planning/n5-document-quality/` | 本线独立 PWF（task_plan/findings/progress） |

样本覆盖：年报 S01、半年报 S02、季报 S03、招股书 S04、增发募集说明书 S05、可转债募集说明书 S06、
有价值 IR S07、程序性/套话 IR S08、英文电话会 S09（≥8 份，类型全齐；S01/S04/S07/S09 即既有四样本对照）。

## 2. 基准结果（`report.json`，`schema narrative-document-quality/1`）

总量：9 份 / 86 个 golden 点 / 712 个被选 span，**locator 回放 712 通过、0 失败**，耗时 260.8 s，临时峰值 152,604 B。

| 指标 | 结果 | 分母（报告内逐行写明） |
|---|---|---|
| required 覆盖率 | **0.3333**（11/33） | 已定位核验的 required 正例 |
| optional 覆盖率 | 0.2353（4/17） | 已核验的 optional 正例 |
| selected 噪声率 | 0.0833（2/24） | 落在标注范围且可被 golden 判定的被选 span |
| duplicate ratio | 0.0674（48/712） | 全部被选 span |
| 角色混淆 / 情态混淆 | 0 / 0 | 有匹配的 golden 点 |

分样（required；噪声；重复）：

| 样本 | 状态 | required | 噪声 | 重复/被选 | 候选/被选/截断 |
|---|---|---|---|---|---|
| S01 年报 | partial | 1/5 | 2/3 | 1/96 | 182 / 96 / 86 |
| S02 半年报 | partial | 1/4 | 0/4 | 4/96 | 105 / 96 / 9 |
| S03 季报 | selected | 3/4 | 0/5 | 0/15 | 15 / 15 / 0 |
| S04 招股书 | partial | 1/3 | 0/2 | 5/160 | 416 / 160 / 256 |
| S05 增发 | partial | 2/3 | 0/5 | 24/160 | 845 / 160 / 685 |
| S06 可转债 | partial | **0/4** | 0/0 | 14/160 | 183 / 160 / 23 |
| S07 有价值IR | needs_review | 3/4 | 0/4 | 0/11 | 11 / 11 / 0 |
| S08 程序性IR | needs_review | **0/1** | 0/0 | 0/0 | **0** / 0 / 0 |
| S09 英文电话会 | selected | **0/5** | 0/1 | 0/14 | **14** / 14 / 0 |

指标定义、负例类别、locator 约定（PDF 页序号可能与印刷页眉差 1）见 `README.md`。

## 3. 验收命令与结果

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:CW_BASETEMP_FALLBACK_ROOT="$PWD\tmp"
python -m pytest -p no:cacheprovider --basetemp tmp/n5-docset-test `
    benchmarks/narrative_document_types/tests -q
# => 29 passed, 1 warning in 37.62s（Unit 22 / Integration 6 / E2E 1）

ruff check benchmarks/narrative_document_types
# => All checks passed!

python benchmarks/narrative_document_types/run_benchmark.py `
    --output benchmarks/narrative_document_types/report.json --overwrite
# => {"schema_version": "narrative-document-quality/1", "samples": 9, ...}

git diff --check   # clean
```

- **Unit**：评估器反例先行（页码偏一、相似段落误命中、未知 golden 引用、错误 SHA、
  无标注范围、角色/情态错配、篡改引文哈希、抬高覆盖率分子、删 golden 点、缺 scope 分母）；
  首轮 RED（11 failed / 22 collected，夹具与校验器缺陷），修复后 22/22 GREEN。
- **Integration**：用真实 parser/selector 跑 S03/S07/S09 子集并校验报告；原件
  SHA/size/mtime 前后一致；改 SHA 的样本被 `run_benchmark._run_sample` 拒绝。
- **E2E**：独立 catalog（SQLite 在本线 tmp 根内）+ **半年报/季报/增发**三份原件副本，
  走 `SourceVersionReader.open_version(purpose="narrative_derivation", expected_read_policy_sha256=...)`
  正式只读接口 → 解析 → 选择 → `verify_pdf_evidence_spans_bytes` 真实回放
  （96+15+160 = 271 span 全通过），`finally` 关闭 catalog、删除 tmp 根、断言原件指纹与
  tmp 目录集合恢复原状；36.69 s。

> basetemp 说明：本 worktree cwd 57 字符，任何 `--basetemp` 后缀都会触发仓库的短 basetemp
> 重定位规则，因此用 `CW_BASETEMP_FALLBACK_ROOT="$PWD\tmp"` 把回落根钉在本 worktree `tmp/` 内；
> pytest 退出时按约定删除该根（日志 `CW-BASETEMP-CLEANUP ... "removed": true`）。

## 4. 保护与清理

- 原件：跑批与测试前后均核对 SHA-256 / byte size / mtime；**未删除、未移动、未硬链接、未入 Git**。
- 生产状态：未写任何生产 catalog、索引、配置、数据库；E2E 只用自建 catalog。
- 所有测试 DB/WAL/复制件/度量文件都在本线 `tmp/` 短根内，运行结束为空。
- `local.json` 被 `benchmarks/narrative_document_types/.gitignore` 排除；跟踪文件中无机器绝对目录。

## 5. 移交 MAIN 的 open_items（产品缺陷，外线不自行改主线）

1. **required 覆盖率 33%**：主要来自预算截断（S04 截断 256、S05 截断 685、S01 截断 86）与候选规则漏打分
   （S06 四条 required 全 miss，但同页单位已成功解析）。建议按 `report.json` 的
   `golden_results[].locator` 逐条复核后决定是调预算还是补候选信号。
2. **英文电话会候选极稀**：S09 498 个 unit 只产出 14 个 candidate（0/5 required），
   管理层 prepared remarks 大面积未进入候选；这是 recall 侧最集中的缺口。
3. **程序性 IR 无法干净 skip**：S08 0 candidate、状态 `needs_review`——
   `_EMPTY_SKIP_KINDS` 不含 `investor_relations`，与“无事实进展的程序性文档允许 skip”的目标不一致。
4. **QA 表格单元 locator 标记 `locator_unstable`**：S07/S08 因此落到 `needs_review`，
   下游是否接受该状态需要确认（不影响回放：回放全部通过）。
5. **电话会解析起始行之前的内容不解析**：S09 高亮摘要区（第 26–60 行，含 G-S09-01）位于
   `Full Conference Call Transcript` 之前，属解析 scope，不是 selector 决策；已在 golden 中
   用 `parser_region=before_transcript_start` 标注。
6. **跨文本块句子被截断**：如 S03 G-S03-03，前半块被选中、后半块（含 224.23% 增长句）被丢弃，
   输出中只剩半句。
7. **重复段落噪声**：整体 duplicate ratio 6.7%（S05 24/160、S06 14/160），多为募集说明书的重复承诺段。

## 6. 未做/不承诺

- 未修改 selector/Worker/公共合同/阈值；报告如实保留非全绿结果，未“修到全绿”。
- 标注为定向精读而非逐页穷尽（每份 `read_scope.uncovered` 写明）。
- 不产生任何投资评价、评级、目标价或结论；`report.json` `output_scope: source-only`。
- 本包只覆盖本卡范围，不代表整个项目完成。
