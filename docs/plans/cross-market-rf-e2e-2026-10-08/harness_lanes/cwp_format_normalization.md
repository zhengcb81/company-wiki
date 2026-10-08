# R6-FORMAT：HTML/PPTX 确定性规范化与定位回放

## 任务与开工

这是较大的共用解析任务，可以立即独立启动。工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/cwp-formats`，分支 `codex/cmrf-format-normalization-20261008`。精确基线见同目录 worktrees.json。不要在 canonical company-wiki 目录修改代码。

阅读本卡、同目录 README.md / handoff_interface.md、上级 root_cause_remediation.md / follow_up_plan.md / findings.md，以及仓内 AGENTS。参考现有 `source_catalog/narrative_document.py`、`narrative_evidence.py`、`narrative_replay.py`、`source_contract/evidence_span.py`。结构问题先 CodeGraph，实际文件以清单为准。

实测根因：原 SEC HTML 和图片型 PPTX 字节可读，但 canonical Worker 仅接 PDF/TXT；研究者 TEMP BS4/看图不能证明 CWP 有此能力。仅放开 MIME 会遗漏回放、表格、隐藏重复和图片覆盖。本线负责**纯解析与回放**；MAIN 负责现有 Worker/AUTO/选片/预算模型/公开读取的接线。

## 独占写入目录

仅允许新增/修改：

- `src/company_wiki/document_normalization/`
- `tests/document_normalization/`（包含小 fixtures 和手动真实原件入口）
- `docs/implementation/cmrf-format-normalization-20261008/`

不改现有 `source_catalog/`、`automation/`、`source_contract/`、config、CI、依赖文件和共享 PWF；这些可只读 import。不得下载、联网、调用模型、翻译、写 DB 或永久落盘全文 MD/拆页图片。需要新增第三方依赖，先在交接注明交 MAIN；优先使用现有 bs4/lxml/python-pptx/标准库。

## 冻结的接入接口

入口 `company_wiki.document_normalization` 导出：

```python
normalize_document(original: bytes, *, source_id: str, source_sha256: str,
                   mime_type: str, limits: NormalizationLimits) -> NormalizedDocument
replay_unit(original: bytes, *, source_sha256: str,
            unit: NarrativeUnit, limits: NormalizationLimits) -> str
```

- 复用现有 `NarrativeUnit` / `DocumentStructure` / `EvidenceCoordinates`，不造第二套 EvidenceSpan。`NormalizedDocument.structure: DocumentStructure`；`opaque_assets: tuple[OpaqueAsset, ...]`；`format_name` / `parser_name` / `parser_version` 明确。
- `OpaqueAsset` 至少包含 `slide_number`（1起）、`shape_path`（嵌套 shape 序号路径）、`media_sha256`、`mime_type`、`byte_size`、`original_bytes`（临时内存，默认 repr/日志不包含）。图片未识读时记录 opaque，不能返回完整覆盖。非图片图表/绘图/损坏对象也有具名缺口，不能默默丢失。
- `NormalizationLimits` 是严格有限正整数：源字节、ZIP累计解压字节、文本输出字节、unit数、页/slide数、媒体累计字节；另可接受调用方传入的绝对 monotonic deadline。默认值写在 docs，可按资源选择，但绝不能无限制、超上限只静默截断。
- 每个 unit 的 metadata 包含 `normalization_schema="cwp-document-normalization/1"`、format、`source_sha256`、版本化 `source_locator`、明确 transform；表格有稳定 table/row/column 身份。unit ID 绑定 source/hash/parser版本/locator/规范化文本SHA，跨进程不受 hash seed 影响。
- HTML locator schema=`cwp-html-dom/1`：明确唯一结构路径和 text block/table cell 范围；PPTX schema=`cwp-pptx-shape/1`：slide、nested shape path、paragraph/run或table cell位置、关联 media SHA。采用结构节点索引，不依赖公司名、原文件名或绝对路径。
- `replay_unit` 重新验证实际原件 SHA、parser版本、locator及文本；错 SHA、改 locator、冒用图片 SHA 或未知版本拒绝，不能返回持久 unit.raw_text 当作回放。
- 使用现有 QualityFlag 值；未识读/歧义在 coverage/errors/metadata明确保留，不通过增加不存在的枚举改底层合同。HTML以实际有效块计数表达完整扫描；PPTX page_count/pages_read/opaque_pages正确，别让 HTML 因 line_count=0 永远不完整。

## 实施步骤

1. 在自己的 docs 建 task_plan/findings/progress，记录基线/ownership和既有能力；先建 API/语义反例，记录当前未实现或错误机制的 RED。
2. HTML：从实际 bytes 和明确编码解析，保留编码策略；不执行 JS，不联网获取 CSS/图片。分离标题/段落/列表/表格/脚注，避免父节点和子节点重复；排除 script/style/nav及明确隐藏元素/ix:hidden，inline XBRL 可见正文保留。不能用全文文本相同就去重，两个位置相同文字可能都有意义。
3. HTML 表格区分财务表和经营事实表；解析层产结构/标志，不删除用户需要的业务表。确实金融表可标 `financial_table`，模糊表标明不确定，留 MAIN 选择器处理。脚注/单位/小字和段落上下文必须能回放。HTML真实格式/未知编码/损坏输入不能空成功。
4. PPTX：稳定遍历 slide、group/nested shapes、paragraph/run、表格，保留分页和结构位置；从实际 media bytes 验 MIME/SHA。内嵌全页图片是 opaque asset，不能凭 shape 名称造文字。notes 与正式slide正文分开标志；关联关系不对/外部链接不获取。ZIP路径穿越、过多成员、超解压量/巨大XML/媒体、重复异常关系，受资源上限约束。
5. 实现精确回放和版本行为，输出只在内存；解析真实文档重复两次/换文件名/多seed一致。复用现有通用 DTO，向 MAIN 提供最小 import 调用例和 `NarrativeUnit.to_evidence_span` 成功例。
6. 一次集中责任层＋真实原件测试，最后提交自己的分支及交接。现有 Worker全链接通由 MAIN 验收，本线不伪称已完成模型识图。

## 测试包和大节点标准

测试入口：`python -B -m pytest tests/document_normalization -q -p no:cacheprovider`。另提供 `tests/document_normalization/run_real_originals.py --html <path> --pptx <path> --output <small-report>`，所有真实输入只读且先验 SHA；不要求固定本机目录才能运行。

- HTML：隐藏祖先/inline-XBRL可见与隐藏、nested节点不重计、导航/脚注/编码、经营表与财表、上下文、多相同文本不同位置、locator/tamper/错误SHA/版本、明确资源上限。
- PPTX：文本、group、表格、notes、图片整页/混合页、多图重复 media、slide排序、错误relation/linked图、非图片chart缺口、ZIP炸弹边界、replay身份；图片页应诚实 partial。
- 通用：bytes/hash/限额非法值拒绝；无网络、无 LLM、无输出目录污染；EvidenceSpan创建与回放匹配；多个 seed/重命名确定性；异常和成功都恢复测试根。
- 真实微软 HTML＋原图片 PPTX至少各一份：可从固定第一组 archive/SourceRef 经现有只读 reader定位，参考 benchmarks/cross_market_rf/cases.json / delivery_archive_index.json，不使用已删除旧 TEMP 路径。解析器测试只读这些原件，记录全文规模/有效unit/opaque/媒体字节/耗时；测试副本退出清掉。
- 无 OCR/vision 凭证或不支持页面时具名 partial；不是“测试通过，所以图片正文已经读到”。不能把已经封存的原71检查 expected 改为PASS。

## 交付

docs 内五文件遵守 handoff_interface.md；提交只带独占目录。交接写清源locator replay示例、格式/覆盖/资源限制、真实原文SHA及小结果，MAIN需要的接线动作。不改 master、不同步安装副本。原文删除0，收费调用0，缓存/全文中间件永久保留0。
