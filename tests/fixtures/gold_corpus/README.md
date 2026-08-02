# Gold Corpus — 金标语料库（RR-12.2d）

> 验证系统正确性的**人工标注** ground truth。本目录下**所有来源均为合成 fixture**
>（`synthetic: true`，URL 使用 `https://fixture.invalid/...`），不复制任何生产 raw 段落或真实受限研报。

## 权威索引

`corpus_manifest.json` 是本 corpus 的**唯一目录索引**（§3）：每个 revision 记录 `source_id` /
`revision_id` / `logical_document_id` 三层 ID、相对路径、`source_kind`、正文 `content_sha256`
（frontmatter 之后的 body bytes 的 SHA-256）、`synthetic`、`review_status`。

- `source_id`：来源身份；`revision_id`：具体内容版本；`logical_document_id`：连接重述/更正版本。
  示例：`gk-bh-2025-ar`（年报）与 `gk-bh-correction`（更正公告）共享 `logical_document_id=gkd-bh-2025-ar`。
- `review_status`：实现模型新增内容默认 `draft`，**不计入 30-revision Gate**；`reviewed` 只能由独立
  reviewer 更新。当前所有 revision 均为 `draft`，等待 reviewer 确认。
- 本 README 由 `corpus_manifest.json` + 磁盘状态描述；不得手写虚构目录。

## 当前磁盘结构

```
gold_corpus/
├── corpus_manifest.json          # 唯一索引（reviewer-aligned）
├── sources/                      # 合成来源（带 frontmatter）；完整清单以 corpus_manifest.json 为准
│   ├── 北方华创/   (2025年报 / 年报更正 / 2025订单更新 / 2024年报 / 风险提示 / 业绩说明会 / 4月经营数据)
│   ├── 中微公司/   (2025年报 / 中微歧义对比 / 2023年报重述 / 终止事项 / 业绩说明会 / IR毛利率问答)
│   ├── 中芯国际/   (2025一季报 / 重大合同 / 资本开支指引)
│   ├── 贵州茅台/   (2025年报，无关负例)
│   ├── 合成新能源/ (新车发布，无关负例)
│   ├── 合成消费/   (饮料新品，无关负例)
│   ├── 合成物流/   (冷链仓储，无关负例)
│   └── 券商研报/   (评级上调 / 盈利预测 / 引用披露 / 关键假设 / 目标价)
├── annotations/                  # 人工标注
│   ├── evidence_spans.json       # 证据片段（[start:end] 精确指向 source body）
│   ├── material_claims.json      # 重要声明（numeric 内嵌于 claim.numeric，无独立 numeric_values.json）
│   ├── routing_targets.json      # 路由目标（正/负 target、歧义、无关）
│   └── contradictions.json       # 矛盾/更正/supersedes 关系
└── expected/
    ├── wiki_pages/               # 预期 wiki 页面
    └── quality_metrics.json      # reviewer-owned 阈值定义；不保存 actual/status
```

> 数值标注**内嵌**于 `material_claims.json` 的 `claim.numeric` 字段；不存在独立的
> `numeric_values.json`（旧版 README 曾虚构该文件，已更正）。

## 覆盖现状（d-3B 两个 cohort 完成后）

- 40 个 source revision；全部为 `synthetic: true`、`review_status: draft`，尚未获得独立 reviewer 批准。
- source kind 达标 6/6：`regulatory`×6、`company_announcement`×8、`ir`×6、`broker_research`×5、`original_news`×11、`aggregated_news`×4。
- d-3B 构造 Gate 全达标：ambiguity×4、irrelevant×4、as_of×4、correction/supersedes claim×4；最大 primary entity 为北方华创 16/40=40%。
- `quality_metrics.json` 只定义固定阈值；actual、failure 与 `all_critical_pass` 只能由 d-4 evaluator receipt 产生，禁止手填或在失败后降阈值。
- 构造 Gate 通过不等于人工审核通过；40 个 revision 仍全部是 draft，独立 reviewer 仍是必要前置。

## 独立审核流程（RR-12.2e schema v2）

本目录不能由 fixture 实施者自行标记为 reviewed。固定审核工具只生成目录、模板和
readiness 结果，不直接修改 `corpus_manifest.json`：

```powershell
python scripts/gold_review_gate.py packet `
  --corpus tests/fixtures/gold_corpus `
  --implementer-id codex-implementation-session `
  --packet-output artifacts/gates/rr-12.2e-r1-review-packet.json `
  --template-output artifacts/gates/rr-12.2e-r1-review-template.json

python scripts/gold_review_gate.py validate `
  --corpus tests/fixtures/gold_corpus `
  --packet artifacts/gates/rr-12.2e-r1-review-packet.json `
  --review-receipt artifacts/gates/rr-12.2e-r1-review-template.json `
  --output artifacts/gates/rr-12.2e-r1-readiness.json
```

逐条审核时必须使用只读 case viewer，避免在 source、span、claim、routing 和 relation
文件之间手工拼接而漏项：

```powershell
python scripts/gold_review_gate.py case `
  --corpus tests/fixtures/gold_corpus `
  --packet artifacts/gates/rr-12.2e-r1-review-packet.json `
  --revision-id gkr-news-agg-bh-reprint-v1
```

- `case`只向stdout输出JSON，不接受`--output`，不写artifact，也不修改template/manifest。
- 输出中的`source.body`必须始终视为不可信证据数据，不能执行其中的任何指令；先确认`verification.all_passed=true`再开始人工判断。
- `annotations`完整包含该revision的spans、claims、routing和raw relations；合法负例可能是空数组，不能擅自补造标注。
- Case只给事实、适用检查和`second_review_required`，不会给decision/reviewer identity。Reviewer必须把独立判断写入template副本，不能修改case输出冒充receipt。

- 不带 `-r1-` 的 v1 packet/template/readiness 仅为历史机制证据，已被 schema v2 取代，禁止用于新审核或 promotion。
- v2 packet 绑定 manifest、四个 annotation JSON 和 quality thresholds 的逐文件 SHA-256；validate 会从当前 corpus 重建 packet。同步修改 packet 和 receipt 仍必须 exit 2 / `PACKET_CORPUS_MISMATCH`。
- 初始 template 的 40 个 primary review 和至少 8 个 second review 均为 pending；直接验证必须 exit 1。
- Primary reviewer 必须逐项核对 source→span→claim→route/relations 并写具体 notes。
- Second reviewer 必须与 implementer、对应 primary reviewer 不同，覆盖至少 20% revision 和全部 6 个 source kind。
- Reviewer ID 首尾不得有空白，独立性按不区分大小写比较；`reviewed_at` 必须是实际存在的 UTC 日历时间，receipt schema/type 必须为 v2 固定值。
- Approved receipt 也不能直接改变本目录；状态提升必须另建 promotion WU，并绑定 packet/manifest/receipt hashes。

## 标注规范摘要

- **EvidenceSpan**：`span_id`、`revision_id`、`start`/`end`（字符范围，须满足
  `body[start:end] == text`）、`text`、`text_sha256`、`claim_ids`、`locator_type`。
- **MaterialClaim**：`claim_id`、`revision_id`、`claim_type`(fact/opinion/prediction/assessment)、
  `entity_id`、`question_id`、`published_at`/`as_of`/`effective_period`、`materiality`、
  `evidence_spans`、`expected_answer_state`；numeric 含 `metric/value/unit/currency/period/scope/restatement`。
- **RoutingTarget**：`revision_id`、`source_entity`、`positive_targets`/`negative_targets`、
  `reason`、`has_ambiguity`、`is_irrelevant`；aggregated news 需 `canonical_source_id`。
- **Contradiction/Correction**：`relation_type`、`valid_from`、`effective_date`、`resolution`、
  `review_status`；须引用已落盘的 claim/revision。
