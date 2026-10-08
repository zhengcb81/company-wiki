# R6-FORMAT HANDOFF — HTML/PPTX 确定性规范化与定位回放

## 1. 修的共用机制、原实测问题 / 最小 RED

**共用机制**:canonical Worker 之外的纯解析与回放层——任何 HTML/PPTX 原件字节 →
带版本化 locator 的 NarrativeUnit 集 + 具名图片/图表缺口 + 严格资源上限 + 精确回放。

**原实测问题**(root_cause_remediation.md P1 CWP 格式规范化组):SEC HTML 与图片型
PPTX 字节可读,但 `automation/narrative_select.py:300` 只接受 `application/pdf`,
CWP 没有任何 HTML/PPTX 解析能力;研究者侧 BS4/看图是临时人工行为。

**最小 RED**:`python -B -m pytest tests/document_normalization -q -p no:cacheprovider`
在移除新包(即基线 eaad25a4 状态)下 exit=4
(`ModuleNotFoundError: No module named 'company_wiki.document_normalization'`)。
语义反例由 64 个机制测试覆盖(所有权双计、隐藏泄漏、空成功、回放冒用等),
不是逐公司补丁;Worker 接线本身属 MAIN(见 §6)。

## 2. 公共接口

导入路径:`company_wiki.document_normalization`(src 布局,零新第三方依赖;
bs4/lxml/python-pptx 均已在 requirements)。

```python
from company_wiki.document_normalization import (
    normalize_document, replay_unit, NormalizationLimits, NormalizedDocument,
    OpaqueAsset, NormalizationLimitError, UnsupportedFormatError,
)

limits = NormalizationLimits()          # 或按部署资源自定义;全部严格正整数
doc = normalize_document(
    original_bytes,
    source_id="urn:company-wiki:source:sha256:<sha>",
    source_sha256="<sha>",
    mime_type="text/html",
    limits=limits,
)
unit = doc.units[0]                      # NarrativeUnit(现有 DTO)
text = replay_unit(original_bytes, source_sha256="<sha>", unit=unit, limits=limits)
span = unit.to_evidence_span(topics=["revenue"], selection_reasons=["..."])
```

与卡片的差异:**无**。签名逐字一致;`limits` 在 `normalize_document` 可省略
(默认 `DEFAULT_LIMITS`),`replay_unit` 的 limits 为必填关键字,均与卡片签名兼容。
版本常量:`PARSER_NAME="cwp_document_normalization"`、`PARSER_VERSION="1.0.0"`、
locator schema `cwp-html-dom/1` / `cwp-pptx-shape/1`、metadata
`normalization_schema="cwp-document-normalization/1"`。

字段要点(完整合同见各模块 docstring 与测试):
- `NormalizedDocument.structure: DocumentStructure`;`opaque_assets: tuple[OpaqueAsset,...]`;
  `format_name`/`parser_name`/`parser_version` 显式。
- `OpaqueAsset`: `slide_number`(1起,HTML 为 None)、`shape_path`(DOM/shape 路径)、
  `media_sha256`(按实际字节验证)、`mime_type`、`byte_size`、`original_bytes`
  (仅内存,repr/log 排除)、`gap_reason` 具名常量。
- `NormalizationLimits`: 源字节/ZIP累计解压/文本输出/unit/页/媒体累计 + 绝对
  monotonic deadline;ZIP 成员数固定上限 10,000;超限抛
  `NormalizationLimitError(limit_name, limit_value)`,不截断。
- 表格:HTML cell 稳定 `table_index/row_index/column_index`(0-based,页 1-based,
  与现有 PDF 解析一致)+ `table_class`(financial/unknown,附依据词)留给 MAIN 路由;
  PPTX cell 同构。cell 内 `<p>` 等包装并入 cell 文本,不拆段。
- QualityFlag 只用现有枚举(encoding_repaired 等);不识读内容用
  opaque asset/coverage 表达,不加枚举。
- HTML 覆盖:`line_count=有效 unit 数`,无 html 根/无可见块记 errors
  (`no_html_root`/`no_visible_text_blocks`),coverage False;PPTX:
  `page_count/pages_read/opaque_pages`,无文本页(整页图)→ opaque + coverage False。

## 3. Git

- 基线:`eaad25a4bb2e6bbe5a8e110ec629dde4c5ddbda2`(与 worktrees.json 一致)
- 分支:`codex/cmrf-format-normalization-20261008`(独立 worktree,sparse)
- 交付提交:见 handoff.json `commits`;HEAD 同 `head`;无未提交遗留文件
  (docs 内五个文件 + 源码/测试全部入库)。

## 4. 测试账

| 命令 | 退出码 | 结果 | 耗时 |
|---|---|---|---|
| `python -B -m pytest tests/document_normalization -q -p no:cacheprovider` | 0 | 64 passed, 0 failed, 0 blocked | ~11–18s |
| 同上(移除新包 = 基线状态,RED) | 4 | collection error: 无 document_normalization 模块 | <2s |
| `python -B tests/document_normalization/run_real_originals.py --html <SEC 10-K> --html-sha256 99d6…0bbe --pptx <MSFT deck> --pptx-sha256 c02f…2cd4 --output docs/…/real_originals_report.json` | 0 | 两份真实原件只读解析 + 逐类回放 ok | HTML ~5.1s;PPTX ~0.5s |

真实原件(先验 SHA,只读,退出后复验未变):
- HTML:`companies/微软/raw/financial_reports/annual/微软_10-K_2025.htm`
  (root=company_raw;catalog locations 只读查询定位;8,158,067 B;
  `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`)→
  5,215 units(1,316 paragraph + 3,899 table cell;85 表 = 69 financial + 16 unknown,
  逐 cell 计 3,382 financial / 517 unknown)、
  coverage complete、0 errors、encoding utf8_strict。
- PPTX:`revenue-forecast/output/cross-market-rf-e2e-2026-10-08/objects/c0/c02f…2cd4`
  (retained_object;4,016,522 B)→ 22 slides 全读、0 文本 unit、22 opaque pages +
  22 image assets(media 3,954,484 B,SHA 逐一按字节验证)——**诚实 partial,
  未识图**。完整数字见 `real_originals_report.json`。

测试类型:单元/机制全部合成输入(离线);真实原件仅 run_real_originals(offline、
只读);无 fake HTTP、无网络、无模型调用。

## 5. 测试根状态

- 测试全内存,无临时目录/文件落地;subseed 确定性测试用子进程 stdin/stdout,不写盘。
- 测试根 = 本 worktree `tests/document_normalization/`;无生产配置/原件改动:
  `config/`、`companies/`、`.source_catalog/`、RF 归档 0 写入(原件 SHA 退出复验一致)。
- `__pycache__` 已清除;未提交任何 PDF/全 MD/拆页图片/虚拟环境/密钥。

## 6. 需要 MAIN 接线的事项

1. **Worker 路由**:`automation/narrative_select.py:300` 放开
   `text/html`(+xhtml)与 pptx MIME → 调 `normalize_document`
   (mismatch SHA/超限由本层抛出,Worker 透传拒绝原因)。
2. **图片处理**:opaque image assets 携带已验 SHA 的 `original_bytes`(内存);
   OCR/视觉走现有模型预算与 AUTO 选片,别把"解析通过"当作"图片正文已读"
   (PPTX 全图 deck 的 coverage 恒为 False,直到模型消费补齐)。
3. **表格路由**:cell metadata 的 `table_class=financial|unknown`(+`table_class_basis`)
   是启发式标志,选择权在 MAIN;两层都不删业务表。
4. **回放成本**:HTML `replay_unit` = 一次完整重解析(真实 10-K 实测 ~5–8s/次);
   MAIN 若要批量回放,建议一次 parse 后按 locator 匹配(语义等价,
   `_parse_for_replay` 内部即如此),或加缓存层(注意版本失效)。
5. **语言字段**:unit.language 现为 "und"(纯解析不做语言判定);若 Worker 需要语言,
   在 MAIN 层接现有语言判定,不绑进 parser_version。

## 7. 仍存在的外部限制

- 无 OCR/vision 凭证:图片正文不识读(具名 partial),这是能力边界不是缺陷;
  封存的 71 项检查 expected 未动、未伪称图片页已读。
- HTML 解析后端锁定 stdlib `html.parser`(bs4);真实 10-K 8.1MB 全链
  (parse+双回放)实测 ~18s,Worker 批处理请按此预算。
- `deadline` 检查是协作式(每节点/每 slide/预扫每成员),超长单节点内仍可能
  超时后小幅越界;上限兜底仍由字节/unit 等硬限保证。
