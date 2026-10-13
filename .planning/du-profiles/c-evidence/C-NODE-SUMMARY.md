# DU-PROFILES C 节点 — 真实原件复核摘要

对象：`codex/du-profiles-20261013` @ base `7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`
日期：2026-10-13
证据文件：`c-node-real-originals.json`（同目录）、`originals-{pre,post}-snapshot.json`

## 这一节点做了什么

用 `sample_manifest.json` 列出的**真实原件**（不是计划里记录的片段重建）各跑一次
`route_document`，并和现有生产路由 `classify_document_kind`（只按标题正则，即本 lane 要修的
旧缺陷）逐份对照。原件只读打开，不复制进 worktree；证据摘录按文档 ≤8 KiB 截断。

复现命令：

```
python -X utf8 .planning/du-profiles/_cnode_real_probe.py
```

## 结果总览

| 指标 | 值 |
|---|---|
| 探测文档 | 7 |
| 成功读取（OBSERVED） | 7 |
| UNAVAILABLE | 0 |
| family 与卡片预期一致 | 7 / 7 |
| 两个头部缺陷回归 | 0 |
| 解析出的真实 unit 总数 | 12 271 |
| 证据摘录字节 | 15 595（上限 57 344） |
| 复制进 worktree 的原件 | 0 |

## 两个头部缺陷：真实原件上的实测

### 缺陷 A — 鼎龙确认函被标题当成 prospectus

- 原件：`鼎龙股份…对《…首次公开发行股票并在创业板上市招股说明书》的确认意见.pdf`
- SHA-256 与 manifest 一致：`0829538f…0fa7`（解析前后均复核）
- **文件只有 1 页，PyMuPDF 原生文本为 0 字符**（`units_total = 0`，`native_text_empty = true`）。
  这一点很重要：确认函的空正文是**真实存在**的，不是造出来的。
- 旧生产路由 `classify_document_kind(title)` → **`prospectus`**（标题含"招股说明书"）。
- 本包 `route_document` → **`administrative` / subtype `administrative_confirmation` /
  disposition `administrative_candidate`，confidence `low`**。
- 诊断码：`ADMINISTRATIVE_PURPOSE`、`NATIVE_SCAN_UNAVAILABLE`、`OPAQUE_PAGES`、
  `NO_READABLE_BODY`、`DECLARED_KIND_CONFLICT`。
- 即：**没有**把确认函当 IPO 全文，**没有**因为读不到正文就丢掉它，且 confidence 诚实地是
  `low` 而不是伪高。`declared_kind=prospectus` 的冲突被显式报出。

### 缺陷 B — 恒锋"发行A股股票募集说明书"落到 unknown

- 原件：`恒锋工具：2020年向特定对象发行A股股票募集说明书（注册稿）.PDF`
- SHA-256：`37f7c62d…50d2e`；96 页，解析出 3 224 个 unit。
- 旧生产路由 `classify_document_kind(title)` → **`unknown`**（正则找"发行股票"，
  "发行A股股票"不匹配）。
- 本包 → **`offering` / regime `cn_exchange` / subtype `equity_offering` / `read`**，
  证据来自封面"向特定对象发行A股股票募集说明书"与正文"募投"章节词汇，
  而不是仅凭标题字面。
- 诊断码：`COVER_HEADING`、`SECTION_VOCABULARY`、`ROUTE_PROBE_LIMIT`。

## 其余 5 份真实原件

| 样本 | 旧标题路由 | 本包路由 | 结论 |
|---|---|---|---|
| 名创优品 2024 港股年报（246 页） | annual_report | `hk_periodic` / hkex / **annual** | 正确；未套用 SEC 编号 |
| 万润 投资者关系活动记录表（含真实否定） | investor_relations | `investor_qa` / cn_exchange | 正确；`QA_STRUCTURE` 命中 |
| 中微 2026 Q1 季报 | quarterly_report | `cn_quarterly` / cn_exchange / quarterly | 正确；未整类跳过 |
| 微软 10-K 2025（HTML，5 215 unit） | **unknown** | `sec_10k` / sec / annual / 10-k | 旧路由失败，本包正确 |
| 微软 Q4 FY26 电话会 TXT | investor_call_transcript | `earnings_call` / transcript | 正确；`SPEAKER_TURNS` 命中 |

## 真实数据暴露并已修掉的 4 个真缺陷

全部由真实原件触发，**不是**靠调整测试或样本 oracle 过关。每个都补了 C 节点回归锁。

1. **`SPEAKER_TURN` 把财务报表脚注标签 `Notes:`/`Note:` 当成发言轮次。**
   名创 246 页港股年报里出现 33 次 `Notes:`/`Note:`，叠加正文里的 "conference call"/
   "quarter" 词，触发了 `SPEAKER_TURNS`，把**真年报判成 `earnings_call`**。
   修复：新增 `is_speaker_turn()` 与闭合的 `NON_SPEAKER_LABELS` 负标签表。

2. **跨 regime 的 QA/transcript 候选可以压过 regime 专属的定期报告候选。**
   `decide()` 里 `_call_candidate`（score 76）无条件参与跨 regime 竞争，压过了
   `_hk_candidate`（score 70）。修复：仅当 regime 未被结构性证据确立时，形状类候选才可跨
   regime 竞争（`_regime_is_structural`）。

3. **SEC 表单标签从"正文里提到别家文件"被当成自己的封面标签。**
   微软电话会 TXT 的 u63 前瞻性陈述段落写了"…the risk factor section of our Form 10-K"，
   于是 `SEC 表单: 10-K` 触发，**电话会被判成年报**。修复：`labelled_units` 现在要求该 unit
   能作为本文档自己的封面行（`is_title_evidence`），或本身带真实 SEC 条目结构。
   同一条修复也顺带解决了原有负例 `test_sec_10k_mentioned_only_in_a_cross_reference…`。

4. **招股书正文里引用的《募集资金管理办法》被当成招股书自身的行政用途。**
   `_detect_administrative` 的标题通道把 `cover_text` 一起匹配，导致 429 页 IPO 招股书被判
   `administrative`。修复：标题通道（`observation.title`）与内文标题通道分开——内文里带书名号
   的标题是**引用**别家文件，不构成本文档自身用途；而真实鼎龙确认函的标题
   `关于《…招股说明书》的确认意见` 因为带自身用途词仍判为自发声明（`allow_self_purpose`）。

## 诚实性说明：本节点**没有**证明的

- 7 份原件全部 confidence = `low`，原因是 `ROUTE_PROBE_LIMIT`（探测预算 200 unit / 64 000 字符
  相对 3 000–4 000 unit 的真实文档必然到限）。这是预算到限的**诚实状态**，不是"路由正确但自信"。
  提高置信度需要 ROOT 用既有全局预算收敛，不属于本 lane。
- 名创年报有 1 个 opaque 页（p246），`native_scan = partial`。本节点**没有**跑 OCR，
  因此不能声称扫描页路由已好。
- 微软 10-K 喂给路由的是前 4 000 个 HTML unit（共 5 215），尾部未探测。
- 本节点只验证"路由到哪一类"，**不**验证章节/语义包/摘要召回质量（那是 DU-STRUCTURE 与
  ROOT 的范围），也**不**验证是否真能选出业务事实。

## 原件保全

解析前后对 7 份原件各复核 SHA-256、mtime、字节数：**全部未变**（详见
`originals-pre-snapshot.json` / `originals-post-snapshot.json`）。原件从未被复制进本 worktree。
