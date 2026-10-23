# W11-CWP-SOURCES 发现

## ROOT已冻结的起点（2026-10-23）

- 与ROOT的W08源码写集无重叠，工区已实际检出；不复用母仓未提交源码。
- 历史输入由母卡同目录INPUTS.json绑定真实路径/SHA。只读历史，不覆盖旧封存。
- 旧IR结果/hash不等于保存了486789B HTML；如找不到body，必须保持不可重放外限，不编造原网页。
- 0新联网/外部模型/下载；统一预算与unknown保留，生产原件不动、不翻译。

## 实施发现（A 阶段，2026-10-23 实测）

### 正文可得性（body_available=false，已查范围如实）

卡片指定的两条根（audit run 树 + CWP holdout `r1-holdout-20261021`）内：

- 精确 486789 B 文件扫描：0 命中（audit run 2052 文件 / 159MB；holdout 65 文件 / 16.6MB）。
- 400–600 KB 全量 SHA-256 比对（89 个文件）：0 命中 `f1e822a8067c0b8eb7fc6376d8e1491acfa1ae3b60ce605db90c06326603396e`。
- holdout `.source_catalog`：sqlite 90 条 sources 无该 hash；WAL 逐字节 needle 扫描无 body SHA、无 `6eed999bdccb40c595c01c5c4b76f16c` event id；objects/sha256 仅 3 个 JSON 投影。
- needle 引用仅存在于 3 个结果/回执文件（faa5bf…stdout.txt、roles/fetch/call_reconciliation.json、roles/process/phase-a-dependency-capture-verification.json），都是"结果引用"而非保存的正文。
- faa5bf… 命令走 CLI `urls` 分支（live GET），body 只存在于进程内存中消费，从未落盘；capture 目录只有 250B 输入×2 与 2839B stdout。
- 结论：486789B 响应正文在本线授权范围内不可得。这不是全盘不存在声明；恢复条件（真实新 attempt 重抓）归 ROOT。

### 真实 discover 结果语义（不可抹平）

- 输入：`as_of=2026-10-21、start=2026-01-01、30 items、1MB、20s、urls=[wuxiapptec ir-material]`。
- 结果：3 个候选全是隐私/条款 PDF 导航锚，`dynamic_content_unresolved` + `publication_date_unknown`，`coverage_status=partial`，`no_documents_claimed=false` —— 状态字段本身是诚实的。
- FETCH-002 的定性是"覆盖不完整"（最新 deck/JPM/IR 活动未取得），不是"已证明分类代码错"。

### 代码观察（调查起点，B 阶段逐项验证）

1. `classify_document_kind` 按 title 匹配；`official_discovery` 里 `"earnings" in folded or "transcript" in folded` 直接覆写 `kind="investor_call_transcript"` —— "Earnings release/presentation" 也会被标成 transcript，符合卡 §4-B 描述的确定性误分类方向。
2. 候选筛选：`.pdf/.txt/.json/.pptx` 后缀 OR 关键词 —— 后缀条件让 footer 的隐私/条款 PDF 全部进入候选（真实结果 3/3 均为此类），法律导航与业务材料未区分。
3. 日期：`data-date` 属性或父元素 `<time datetime>`；窗口判断 `start <= published <= as_of`；无日期 → `date_unknown`。边界语义待测。
4. 去重按最终 URL 字符串（urljoin 后）；锚文本大小写不参与；同 URL 不同锚文本只保留首个命中。
5. `soup.find("script", src=True)` 或正文含 "loading" → `dynamic_content_unresolved`。真实页面 486KB 含外部 script，该 limitation 是真实观察，不是 bug。
6. `max_items` break 只中断当前循环后续页面（外层 for page 未 break），`item_limit_reached` 标记保留 —— scope 语义待测。

### 基线回归（未改产品）

`pytest -k 'discovery or official_index_http or cn_fundraising'` → **7 passed**，RED_not_observed（现有套件内无失败）。潜在缺陷需要新中性反例触发，B 阶段构造。

### A5 期望表（可观察行为 → 期望 → 责任 → 状态）

| # | 可观察行为（中性 fixture 实测） | 期望 | 责任 | 状态 |
|---|---|---|---|---|
| 1 | "Q2 2026 Earnings Release/Presentation" 标为 `investor_call_transcript` | release/deck 不是 call transcript；transcript 身份只能由 call/transcript 线索承担 | official_discovery | **缺陷（确定性误分类，卡 §4-B 明确）** |
| 2 | "Privacy Statement"/"Terms of Use" PDF 进入候选（后缀过滤兜底） | 法律导航不充业务资料，不应作为候选输出 | official_discovery | **缺陷（真实结果 3/3 全为此类）** |
| 3 | "Business"/"Investor"/"Conference"/"Contact Information" 纯导航靠关键词进候选 | 导航文本不是材料线索；关键词命中不等于业务材料 | official_discovery | **缺陷（覆盖状态被噪声污染）** |
| 4 | 真实 transcript（"Earnings Call Transcript"）→ `investor_call_transcript` | 正确 | — | 通过 |
| 5 | "Notice of Upcoming Investor Conference" → `index_notice` | 通知不冒充材料，disposition 正确 | — | 通过 |
| 6 | CN：关于召开…会议通知→`meeting_notice`；活动记录→IR；半年报→`semi_annual_report` | 正确 | — | 通过 |
| 7 | 年报/中报/report 无专用 kind → `investor_relations` 兜底 | shared classifier 语义，本线不改共享分类器 | narrative_routing | 通过（接口建议给 ROOT） |
| 8 | 日期窗口：start 当天/as-of 当天=包含；之后→`after_as_of` 排除；之前→`before_window` 排除 | 正确 | — | 通过 |
| 9 | `data-date` 优先于父 `<time>`；datetime 带时间取前 10 位；非法日期→`date_unknown` | 正确 | — | 通过 |
| 10 | 相对 URL（含嵌套）、跨 host 绝对、协议相对解析正确 | 正确 | — | 通过 |
| 11 | 非法 scheme（javascript/mailto/ftp）与 user:pass URL 不进候选 | 正确 | — | 通过 |
| 12 | 去重按 urljoin 后完整 URL：同 URL 多锚留 1 个；不同 query/fragment 视为不同 URL 保留 | 正确（保守去重不抹合法不同材料） | — | 通过 |
| 13 | 同标题不同 URL 两个都保留 | 正确 | — | 通过 |
| 14 | 空壳+外链 script → 0 候选 + `dynamic_content_unresolved` + `partial` + `no_documents_claimed=false` | 正确（诚实 partial） | — | 通过 |
| 15 | 静态页面文本含 "loading" 一词误触 `dynamic_content_unresolved` | 启发式外限，无正文不可证伪；保留 limitation 不作为缺陷修复 | — | 外限如实记录 |
| 16 | `item_limit_reached`：当前页收满后 break，后续页不再收（receipt event_ids 仍记录已读页） | 语义：limitation 保留 + coverage=partial，诚实 | — | 通过 |
| 17 | `byte_limit_reached`：超限后停止；跨页时 event_ids 只记已消费页 | 同上，诚实 | — | 通过 |
| 18 | `max_items=0/31`、`start>asof`、`max_bytes` 越界 → ValueError | 正确 | — | 通过 |
| 19 | xhtml 解析、unsupported mime→`unsupported_index_format`、inline JSON-LD script 不触发 dynamic（无 src） | 正确（无 src 的声明性内嵌不等于动态未解析） | — | 通过 |
| 20 | candidates 均带 `metadata_only=true`、`is_business_original=false`、`capture_id`、`index_source_sha256` | 正确（metadata lead 不冒充原件） | — | 通过 |

**RED 判定**：缺陷 1/2/3 由中性 fixture 在未改产品上稳定复现（probe_defects.py / probe12.py 实测输出），构成确定性内部缺陷；真实 faa5bf… 结果（3/3 隐私/条款候选）与缺陷 2 的机制直接对应。其余行为按表如实记录通过，不预设全改。

## 独立审查 1（agent 638a667b，绑定 ecc7d622）与修复轮

审查结论 CHANGES_REQUIRED，发现 13 项。逐项处置：

| 审查项 | 级别 | 处置 |
|---|---|---|
| IR-01 标题白名单静默漏掉真实材料链接（表格 Download、aria-label、Annual Results、Corporate Deck、CN 电话会纪要） | High | **已修**：`_anchor_title` 支持 aria-label/img alt；表格/列表行由 item container 回补文档名；材料 token 扩到 results/announcement/press release/report/prospectus/circular/proxy/webcast/dividend/deck/公告/报告/电话会/纪要 等；`agm/egm/6-k/8-k/10-k/10-q/20-f` 用词边界；无标题文档后缀链接记 `unclassified_document_links` limitation，不再静默 checked_index_only |
| IR-02 briefing/upcoming 误作材料线索；notice 抢占 item 预算 | Medium | **已修**：删除 briefing/upcoming 材料 token；event notice 需 notice+event 双线索；候选按 materials 优先分配 max_items，notice 只占剩余名额 |
| IR-03 denylist 既漏（Legal/Accessibility）又误杀（Contact/Privacy 混排） | Low | **已修**：legal/accessibility/imprint 页级否决优先；material 线索优先于二级 legal-doc/nav 词；media/press briefing 显式排除；contact 仅在无材料线索时否决 |
| IR-04 共享容器/页面级 `<time>` 被当成每份材料日期；测试名与断言不符 | Medium | **已修**：日期只取 anchor `data-date` 或「仅含该一个链接」的 article/li/tr/div 内 `<time>`；页面级 time 不再排除材料；测试改为 page-level timestamp 语义 + item 级截断 + sibling 不借用 |
| IR-05 fragment 变体重复计数 | Low | **已修**：去重键去 fragment；query 仍区分 |
| IR-06 CLI 重复 byte_limit_reached；坏 page row KeyError | Low | **已修**：limitations 去重；page row/entity/date 校验，坏输入走结构化 exit 2 |
| IR-07 一个坏 href 中断全页 | Low | **已修**：per-anchor try/except，记 `invalid_anchor_url` 并保留其他候选 |
| IR-08 空/# href 自指候选 | Low | **已修**：空/hash 与指向索引自身的 URL 直接跳过 |
| IR-09 evidence_inventory.json 非法 JSON、字节总数不可复现 | Medium | **已修**：纯整数（audit 2052/166,731,220；holdout 65/17,360,200），全部 delivery JSON `json.load` 校验 |
| IR-10 无 RED 证据留存 | Low | **已修**：`delivery/w11/probes/red_probe.py` 从 git 0d7ada21 重建 base 模块（blob SHA 7d8fb129…），保留 D1/D2/D3 的 base/修复后对照输出 |
| IR-11 测试名/注释/未用常量 | Low | **已修**：删未用常量、修正 socket 注释、重命名日期测试 |
| IR-12 冗余 token、无 EOF 换行 | Low | **已修**：`_TRANSCRIPT_TITLE_TOKENS` 精简为 transcript/电话会/纪要；删 `" Cookie"`；测试文件带 EOF 换行 |
| IR-13 稀疏检出误删 delivery 文件 / 残留 0B 日志 | Info | **已修**：`sparse-checkout add delivery` + `checkout HEAD --` 恢复；删除 push-gate-rerun.log；cleanup.json 记录 |

修复后矩阵：新离线套件 40 例 + 既有 7 例 = **47 passed**（重跑 JUnit/日志已更新）。

## 独立审查 2（agent 68a33bb8，绑定 a6d12a53）与修复轮 2

审查确认 12/13 项已修，但指出 token 扩宽引入新 Medium：导航/section 标签（`公告`/`业绩`/`Annual Reports`/`Results`/`News Releases`）被当作候选并抢占 `max_items`。另 IR-12 残留（测试文件无 EOF 换行）。逐项处置：

| 审查项 | 级别 | 处置 |
|---|---|---|
| NR-01 导航/section 链接成为材料候选并挤占预算 | Medium | **已修**：`nav/header/footer` 结构否决（无文档后缀时）；精确 section 标签（reports/results/announcements/公告/业绩/报告…）否决；强/弱 token 分层（弱 token 需文档后缀或带日期 item）；候选排序改为「文档后缀优先 → 其他材料 → notice」 |
| NR-02 单链接页面级 `<time>` 仍被当作材料日期 | Low | **已修**：日期容器不再回退 div，只认 article/li/tr |
| NR-03 `unclassified_document_links` 对有意排除的法律链接误报 partial | Low | **已修**：删除该 limitation；法律/导航排除是意图，不是覆盖缺口 |
| NR-04 页级 legal 否决误杀 "Annual Report 2025 - Legal Entity Changes" | Low | **已修**：强线索 + 文档后缀可豁免页级 legal 否决 |
| NR-05 容器正文可变成 300 字标题 | Low | **已修**：标题截断到 120 字符并做词边界 |
| NR-06 多链接表格行（Download+View、无后缀）仍静默丢失 | Low | **未修，如实记为 bounded limit**（R1 不扩 scope） |
| NR-07 `?page=2` 自指链接成为候选 | Low | **已修**：同 path 且非文档后缀的 query 链接按自身/分页跳过 |
| NR-08 非法 page URL 返回干净空结果 | Low | **已修**：库层校验 page URL，非法则 ValueError（CLI exit 2） |
| NR-09 交付卫生（UTF-16 日志、band 计数、prepared_at、handoff 缺失） | Info | **已修**：日志改 UTF-8；band 拆为 84+5；时间戳更新；handoff 本轮补齐 |
| NR-10 `max_items` 不再约束工作量、每候选重算整页 SHA | Low | **已修**：每页只算一次 page SHA；pending 有界并在溢出时记 item_limit_reached |
| IR-12 残留：测试文件无 EOF 换行 | Low | **已修**：补 EOF 换行，删除冗余 `半年报` token |

修复后矩阵：新套件 48 例 + 既有 7 例 = **55 passed**；ruff 通过；审查 2 的 NR-01/02/03/04/05/07/08/10 场景均有回归用例。


