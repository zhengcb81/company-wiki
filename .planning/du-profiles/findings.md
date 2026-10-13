# DU-PROFILES findings

## Base

- worktree `.../document-understanding-20261013/profiles`, branch `codex/du-profiles-20261013`
- base/HEAD `7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`, `git status` clean at start
- `src/company_wiki/document_understanding/` does not exist yet; ROOT owns the parent `__init__.py`
- ruff is run by CI as `ruff check src tests/unit ...` with no `[tool.ruff]` table in pyproject
  (ruff 0.15.18, default rules; E501 not enabled by default)

## Existing production behaviour that the new package must not duplicate

- `src/company_wiki/source_catalog/narrative_routing.py` is the current production router.
  `classify_document_kind` matches title regexes in order and falls back to `existing_kind`;
  budgets 96 default / 160 prospectus; only `ir_policy` + `meeting_notice` may skip an
  empty result. This package is a separate, composable layer; it must not edit that file.
- `document_kinds.py` maps declared kinds to SourceType; useful vocabulary
  (annual_report / semi_annual_report / quarterly_report / prospectus /
  equity_offering_prospectus / convertible_bond_prospectus / investor_relations /
  investor_call_transcript), but its `prospectus`/`equity_offering_prospectus` split is
  metadata-driven and title-regex driven, which is exactly what the design says is not
  enough.

## Real evidence from the plan's own observations (bounded excerpts only)

Read from `docs/plans/.../sample_observations.json.gz` + `sample_manifest.json`
(20 originals: 15 PDF, 4 HTML, 1 TXT). No PDF bodies were copied into this worktree.

- `cn-ipo-confirmation`: title_only_kind = **prospectus** (title contains 招股说明书) but the
  body is a single page whose only excerpt is whitespace -> `native_text_empty_pages: 1`.
  This is the headline misrouting: a confirmation letter must not become a full IPO prospectus.
- `cn-equity`: 恒锋 `2020年向特定对象发行A股股票募集说明书（注册稿）`, title_only_kind = **unknown**.
  The body TOC/heading evidence uses `第三节 董事会关于本次募集资金使用的可行性分析`,
  `募集资金使用金额`, `项目投资计划`, `项目建设周期`, `项目建设用地`, `项目备案、土地及环评情况`,
  `（七）项目投资回报情况`. So A-share "发行A股股票" wording must be recognized, and the
  offering keys on 募集资金/募投项目/建设期.
- `cn-annual` / `cn-h1`: A-share periodic reports signal `第一节 释义`,
  `第二节 公司简介和主要财务指标`, `第三节 管理层讨论与分析`, `第四节 公司治理、环境和社会`,
  `第五节 重要事项`, plus cover `公司代码/公司简称` and `x / 210` page footers.
  Quarterlies (`cn-q-business`, `cn-q-sparse`) use `第一季度报告` cover + `重要内容提示` +
  `一、主要财务数据` + `三、其他提醒事项` + `四、季度财务报表`.
- `cn-q-sparse` is the low-value case: its body is mostly the three financial statements and
  every other item is `不适用`. The other quarterly (`cn-q-business`) carries real product
  narrative ("第二代ICP刻蚀设备…付运到国内领先存储客户端认证"). Same family, different density.
- `cn-convertible`: 金禾 `公开发行可转换公司债券募集说明书`, TOC `第八章 本次募集资金运用`,
  `本次募集资金投资项目的可行性与必要性`, and a 项目总投资/拟投入募集资金 table with
  `单位：万元`. Money in these documents is an investment amount, not revenue.
- `cn-ir`: 万润 `投资者关系活动记录表`, structure `问：` / `答：` pairs, and a real negation:
  `公司现无生产VC（碳酸亚乙烯酯）的情况` answering a question that presupposed cooperation.
  `cn-ir-policy` is misnamed in the manifest: its body is actually another
  `投资者关系活动记录表` (业绩说明会), i.e. metadata/body conflict is real, not hypothetical.
- `hk-annual` / `hk-interim`: bilingual TOC (`Contents / 目錄`, `Business Review and Outlook /
  業務回顧及展望`, `Management Discussion and Analysis / 管理層討論與分析`), a cover that is
  mostly the word MINISO, and a genuine after-reporting-period section
  `RECENT DEVELOPMENTS AFTER THE REPORTING PERIOD` (TOP TOY / Temasek).
- `hk-ipo`: `全球發售` cover, Traditional Chinese TOC (`行業概覽`, `法規`, `歷史及公司架構`,
  `業務`, `未來計劃及所得款項用途`). Note this cover has no `招股` string at all.
- `hk-release` / `hk-deck`: `For Immediate Release` + `TENCENT ANNOUNCES … RESULTS` and a
  slide deck cover `2026 Second Quarter / Results Presentation`. These are not periodic
  filings even though they carry quarterly numbers.
- `us-10k`: index page `FORM 10-K ... PART I Item 1. Business ... Item 1A. Risk Factors ...
  Item 7. Management's Discussion and Analysis ... Item 7A ... Item 8`. Section body uses
  `Our segments`, `Azure revenue`, `remaining performance obligations`.
- `us-10q`: `Item 2. Management's Discussion and Analysis`, `one operating segment and one
  reportable segment, Insurance`, `hosted subscriptions`, `deferred revenues`.
- `us-20f`: `ITEM 4. INFORMATION`, `ITEM 5. OPERATING`, `Business Overview`, `VIE Subsidiaries`,
  `Item 3. Key Information—D. Risk Factors`. So 20-F numbering must never be applied to 10-K/10-Q.
- `us-txt`: `CALL PARTICIPANTS`, `Operator:`, `Jonathan Neilson:`, `Satya Nadella`,
  `Questions and Answers`, and per-speaker turns -> speaker/turn hints matter for transcripts.
- `us-release` (HTML) is a marketing/investor page wrapper: it contains `Business Highlights`
  and `Azure` in the body **and** `Azure`/`Microsoft 365` in navigation/footer boilerplate at
  character offsets 222 and 32469. Nav/footer boilerplate is a real negative hint.

## Implications for the profile design

- Metadata alone is insufficient and actively wrong in two of the twenty real samples
  (confirmation letter, offering prospectus with unknown title). Body/TOC signals must be
  able to override a metadata claim, and disagreement must be reported as a diagnostic.
- SEC item numbering, A-share `第N节` numbering and HK bilingual headings are three
  mutually incompatible section vocabularies. Applying one to another must be impossible
  by construction, so each profile carries its own aliases.
- The confirmation letter and the IR policy are administrative; their detection must fire
  before family assignment, and the output is `administrative_candidate`, never a skip.
- Page footers (`x / 210`, `Page 1 of 9`, `– 185 –`), nav footers and TOC pages are
  cross-type negative hints, not hard delete rules.
