# CWP1 法律形式名称误合并复查 — 2026-11-15

## 当前状态

`INDEPENDENT_REVIEW_PASS`。这是 CWP 内身份匹配的增量复查，不代表跨仓 M3 关闭。修复位于 `security_identity.py` 和该模块的合同测试；没有改 Security Master 数据、生产目录、原件或其他仓库。

复查代码提交：CWP `master@5ae4a60b6fc883a73c198fb706a5b6979352dd29`。独立复核已按最终提交和文件 SHA 完成；ROOT 又在该精确代码提交上复跑六文件定向集合。当前 Git 工作区里这两个代码文件已提交，剩余改动仅为 PWF 记录：

| 文件 | SHA-256 |
|---|---|
| `src/company_wiki/source_catalog/security_identity.py` | `f2badf20d076c24754647210880bafccf244dd91067a111e74480dd783d79830` |
| `tests/contract/test_source_catalog_security_identity.py` | `30c8484bde3fcab13fcc1dae9864c820ba639390ea0acb0083d3ae497f0ade11` |

## 根因与复现

CWP1 为跨市场精确名称匹配加入后缀归一化时，把不同法定形式分组成同一等价类：`PLC/AG/SE/NV/SA`、`LP/LLP` 以及有限责任公司与股份有限公司名称。合成的单条 Security Master 记录即可复现：`Example Holdings AG` 被查询 `Example Holdings PLC` 命中为 `resolved / one_verified_exact_identity / official_name_exact`；LP/LLP 和不同中国公司类型也有相同误判。

把不同形式从 exact 等价类移除后，仍有第二条自动误选路径：唯一高分 fuzzy 可以自动 resolve。独立审查者用较长公司名、canonical 名末尾为 `AG`、唯一 alias 省略法定形式、查询末尾为 `PLC` 的内存样本复现，分数 `0.9744`，仍返回 `one_unique_strong_fuzzy_identity`。因而只收窄 exact normalization 不够，fuzzy 冲突判断必须查看候选记录本身。

## 设计决定

- ASCII exact 归一只保留同一名称后缀的缩写/展开：`Ltd/Limited`、`Inc/Incorporated`、`Corp/Corporation`、`Co/Company`。
- `PLC`、`AG`、`SE`、`NV`、`SA` 保持彼此独立；`LP` 与 `LLP` 保持独立。法定形式不同且无精确 alias 的高分 fuzzy 保留候选并返回现有 `fuzzy_candidates_require_user_selection`，不增加状态、reason 或 schema 字段。
- 中国《公司法》第七条规定同一类型名称的法定替代写法：有限责任公司可用“有限责任公司”或“有限公司”；股份有限公司可用“股份有限公司”或“股份公司”。代码按这两类分别 canonicalize；有限责任公司与股份有限公司仍是不同类型，不互相匹配。法条来源：[国家市场监督管理总局发布的《中华人民共和国公司法》](https://www.samr.gov.cn/xyjgs/flfg/art/2024/art_d4e84936a8a744f8928ac7aec7594345.html)，第七条。
- Fuzzy guard 按 market、exchange、security_id、source_record_id 找回候选记录，并检查其 `canonical_name` 及全部 aliases 中是否有与查询冲突的法定形式。精确匹配到明确 alias 的路径保持原行为。
- 不改已登记名称、别名、security master、跨市场 issuer-link、provider、目录或下载行为。

其他官方法源用于确认不同形式不是通用缩写：英国《Companies Act 2006》第 58/59 条分别规定 public company 名称以 `plc` 结尾和 private company 名称以 `limited/ltd` 结尾；EUR-Lex 将 SE 定义为欧盟法下的独立公司形式；荷兰政府将 NV 与 BV 列为不同公司形式：

- [UK Companies Act 2006, section 58](https://www.legislation.gov.uk/ukpga/2006/46/section/58)
- [UK Companies Act 2006, section 59](https://www.legislation.gov.uk/ukpga/2006/46/section/59)
- [EUR-Lex: European Company (SE)](https://eur-lex.europa.eu/EN/legal-content/glossary/european-company.html)
- [Business.gov.nl: Dutch legal structures](https://business.gov.nl/running-your-business/legal-forms-and-governance/business-structures-in-the-netherlands-overview/)

## TDD 与验证

1. **RED 1**：新增七组不同形式合同（PLC 对 AG/SE/NV/SA、LP 对 LLP、股份有限公司对有限责任公司/有限公司）；旧实现先在 `Example Holdings AG` / `Example Holdings PLC` 例上返回 `RESOLVED`，测试失败。
2. **GREEN 1**：移除跨形式 exact equivalence，并在 fuzzy 唯一自动解析前检测不同法律形式冲突；七组例子转为 `AMBIGUOUS`、保留 `strong_fuzzy` 候选。
3. **RED 2**：独立审查提供 canonical `AG` + 无后缀 alias + 查询 `PLC` 的长名称反例；修复前仍自动 resolve，新增专门用例失败。
4. **GREEN 2**：冲突检测改为检查候选记录的 canonical 名和全部 aliases，而不只看 fuzzy 最佳 `matched_value`；长名反例转为 `AMBIGUOUS`。
5. **中文类型正反控**：不同有限责任/股份公司类型不自动互认；《公司法》第七条列明的同类替代写法可 exact 匹配。
6. 最终定向集合：

   ```powershell
   python -m pytest tests/contract/test_source_catalog_module_contracts.py tests/contract/test_source_catalog_security_identity.py tests/contract/test_ff1_ensure_catalog_repair.py tests/contract/test_ff1_import_published_date.py tests/contract/test_ff1_operation_candidates.py tests/contract/test_ff1_unknown_date_classification.py -q
   ```

   ROOT 在上述最终代码 SHA 下结果 **69 passed / 20.62 秒**；两个受影响文件 Ruff **All checks passed**；`git diff --check` 通过。提交钩子 Ruff、覆盖 490 个源文件的 mypy 与 config doctor 均通过。短路径 pytest 临时目录 cleanup 收据为 `removed=true`。

7. **独立最终复审**：复核绑定 `master@5ae4a60b6fc883a73c198fb706a5b6979352dd29` 与上述两个精确 SHA。审查员重跑三个关键回归 **3 passed**，Ruff 通过；确认 fuzzy guard 检索候选记录后检查 canonical name 与全部 aliases，且发生在 strong fuzzy 自动解析之前。审查结论 **PASS，无阻断问题**。

## 发布界限

- 代码/测试提交 `5ae4a60b6fc883a73c198fb706a5b6979352dd29` 已推送；Git 服务端确认 `e74840d22..5ae4a60b6 master -> master`。push 固定 fast smoke **18 passed / 6.23 秒**；提交钩子 Ruff、mypy 与 config doctor 通过。GitHub 完整 CI 尚未核验。独立复审 PASS。CWP 当前源代码边界状态绑定此版本；跨仓 M3 仍等待 FF、RF、StockWiki 各自 owner 对齐公开接口调用结果、canonical PWF 与精确 refs。
- 本次没有调用 provider、网络下载、LLM 或收费 API；没有读取或写入生产财务数据。
- CWP M3 整体仍等待 FF、RF、StockWiki 各自 owner 对齐各自的公开接口调用结果、canonical PWF 与精确 refs。此 CWP 修复只完成本仓可独立推进的代码缺口，不提前关闭 M3。
