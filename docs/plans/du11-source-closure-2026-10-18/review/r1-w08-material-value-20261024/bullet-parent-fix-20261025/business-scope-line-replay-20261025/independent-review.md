# 独立复审：annual14 具名业务线范围识别

结论：**PASS**。本复审为只读代码与证据审查，没有重新运行测试。

## 绑定版本

- 审查时 HEAD：`f7492b68fc12003a22c89e4c82a75bbe890ae383`
- `src/company_wiki/source_catalog/narrative_business_disclosures.py` SHA-256：`6a40e4771e7622c688a8361274b2edadd328b645db2520c41db6d0d397a31eb7`
- `tests/unit/document_understanding_selection/test_reading_material_value.py` SHA-256：`5dc47f1ff137457e8f9087aae1274123af9d35cfe6915ab733ea5530f116cd5f`
- 回放收据：`replay-receipt.json` SHA-256 `0f36c386bb404a15e59d384acd741d92cd382f15935373e1c860a865cb653e51`

## 审查结论

- 中文新增识别必须先满足现有收入/业务类型来源锚点，再同时看到具名业务线、经营动词和范围描述；英文规则要求收入来源句、具名业务线、运营动词和范围表达。没有公司名、页码或行业特例。
- 新增的通用套话反例不会取得 `business_scope` 标签；中英文正例覆盖换行和跨多行的业务范围描述。未发现阻止合并的误判问题。
- 年报真实回放在原有112片段上限下选入第119页化学业务范围片段；ST-A01/ST-A11既有检查点继续通过。回放工作量为11,027,878/16,000,000，未耗尽。`READING_DISCLOSURE_SCAN_PASSES`从4调到6，与两类新增有界规则相符。
- 回放仍报告`coverage_complete=false`、`whole_content_pass=false`、`content_quality=not_regraded`。这项结果只验证来源分类和选材，不构成内容评分通过。

## 限制

英文新增规则当前覆盖“收入主要来自以下业务线”这一明确句式；其他措辞变体可能仍未命中，应由后续跨市场真实样本发现和验证。本次不调整预算上限，也不改变既有内容评分。
