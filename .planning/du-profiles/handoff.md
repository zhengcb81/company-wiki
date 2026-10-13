# DU-PROFILES 交接说明

- **lane**：`du-profiles`
- **分支**：`codex/du-profiles-20261013`
- **worktree**：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/profiles`
- **base SHA**：`7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`
- **实现 commit**：`PENDING_SET_BY_FOLLOWUP_COMMIT`
- **状态**：实现完成、测试与 C 节点真实复核通过，但**尚未接入生产**（生产接线属 ROOT）

---

## 一、改了什么

新增一个纯函数文档类型路由包，落在 `src/company_wiki/document_understanding/profiles/`：

| 文件 | 作用 |
|---|---|
| `__init__.py` | 冻结入口：`route_document` / `get_profile` / `list_profiles` |
| `vocabulary.py` | 冻结词表：regime、family、section role、semantic unit、reason code、默认预算 |
| `model.py` | 路由内部数据模型 |
| `registry.py` | 15 个静态 profile 的注册与组合（按继承去重，不做 15 套平行管线） |
| `observation.py` | `du-input/1` 校验；按**文档跨度分层抽样**，不是盲取前 N 个 unit |
| `signals.py` | 从封面 / 目录 / 分层正文抽取可引用信号 |
| `decision.py` | 唯一仲裁模块：行政用途 → regime → family → generic |

公开函数（可直接由 ROOT 调用）：

```python
route_document(observation: Mapping, *, limits: Mapping | None = None) -> dict  # du-route/1
get_profile(profile_id: str) -> dict
list_profiles() -> list[dict]
```

`route_document` 输出恒含 `schema_version / profile_id / profile_version / regime / family /
subtype / confidence / reasons / alternatives / child_routes / disposition_hint`。
15 个 profile 覆盖 `cn_annual / cn_interim / cn_quarterly / hk_periodic / sec_10k / sec_10q /
sec_20f / prospectus / offering / investor_qa / earnings_call / results_release / presentation /
administrative / generic`，共 11 个 family。

### 本轮新增的测试与工具

- `tests/unit/document_understanding_profiles/test_c_real_shape_regressions.py`：C 节点回归锁，
  每一条都对应一个**真实原件暴露出来的**缺陷。
- `.planning/du-profiles/_cnode_real_probe.py`：真实原件探测脚本（见下文如何复跑）。
- `.planning/du-profiles/c-evidence/`：C 节点证据（JSON + 摘要 + 原件前后快照）。

---

## 二、边界（本 lane 不做什么）

**允许写**（且实际只写了这些）：

- `src/company_wiki/document_understanding/profiles/**`
- `tests/unit/document_understanding_profiles/**`
- `tests/fixtures/document_understanding_profiles/**`
- `.planning/du-profiles/**`

**明确没做**：

- **没有**创建 `src/company_wiki/document_understanding/__init__.py`（父包 init 归 ROOT）。
- **没有**改 `source_catalog`、`document_normalization`、`narrative_routing.py`、其他 lane 的
  profiles、config、CI、依赖。**没有**新增任何依赖（只用标准库）。
- **没有**并 master、没有 push、没有安装技能、没有跑生产批次。
- 包本身**不联网、不读盘、不读配置、不读时钟、不调用模型**；相同输入必然相同输出，
  不修改传入的 observation，不读写公司名/证券代码/文件路径做特判
  （已用 AST 扫描可执行字符串常量复核：公司名与路径 token 命中数为 **0**，公司名只出现在
  记录真实样本来源的 docstring 里）。

---

## 三、如何复跑

在 worktree 根目录执行：

```bash
# 1) 本包单元测试（150 个）
python -X utf8 -m pytest tests/unit/document_understanding_profiles -q

# 2) 本包 ruff（与 CI 同规则，默认规则集）
python -X utf8 -m ruff check \
  src/company_wiki/document_understanding/profiles \
  tests/unit/document_understanding_profiles \
  tests/fixtures/document_understanding_profiles

# 3) 卡片验收条件自检
python -X utf8 .planning/du-profiles/_acceptance.py

# 4) C 节点：真实原件路由（只读原件，写下界证据）
python -X utf8 .planning/du-profiles/_cnode_real_probe.py

# 5) C 节点：计划内记录片段的回放（合成输入）
python -X utf8 .planning/du-profiles/_cnode_probe.py
```

实测：测试 **150 passed**（4.34 s 墙钟）；ruff **All checks passed**（0.15 s）；
验收脚本输出 **ALL ACCEPTANCE CRITERIA SATISFIED**（退出码 0）；
真实原件探测 **7/7 OBSERVED、7/7 family 一致、0 头部缺陷回归**（22.65 s）。

> 真实原件探测需要本机存在 5 份 PDF、1 份 HTML、1 份 TXT 原件，路径写在
> `_cnode_real_probe.py` 的 `REAL_ORIGINALS` 里。原件缺失时会如实报 `UNAVAILABLE`，
> **不会**伪造 PASS。

---

## 四、两个头部缺陷在真实原件上的实测

### 缺陷 A：鼎龙确认函被标题当成 prospectus

| 项 | 值 |
|---|---|
| 原件 | `companies\鼎龙股份\raw\prospectus\鼎龙股份：控股股东、实际控制人对《…首次公开发行股票并在创业板上市招股说明书》的确认意见.pdf` |
| SHA-256 | `0829538f…0fa7`（解析前后均复核，未变） |
| 旧生产路由（只按标题） | **`prospectus`** |
| 本包路由 | **`administrative`** / subtype `administrative_confirmation` / disposition `administrative_candidate` |
| 真实观测 | 原件只有 **1 页，原生文本 0 字符**（`units_total=0`）；诊断码 `ADMINISTRATIVE_PURPOSE`、`NATIVE_SCAN_UNAVAILABLE`、`OPAQUE_PAGES`、`NO_READABLE_BODY`、`DECLARED_KIND_CONFLICT`，confidence `low` |

结论：**没有**当 IPO 全文，**没有**因读不到正文就丢弃，且 `declared_kind=prospectus` 的
冲突被显式报出，confidence 诚实地是 `low`。

### 缺陷 B：恒锋"发行A股股票募集说明书"落到 unknown

| 项 | 值 |
|---|---|
| 原件 | `companies\恒锋工具\raw\research\恒锋工具：2020年向特定对象发行A股股票募集说明书（注册稿）.PDF` |
| SHA-256 | `37f7c62d…50d2e`（未变） |
| 旧生产路由（只按标题） | **`unknown`**（正则找"发行股票"，"发行A股股票"不匹配） |
| 本包路由 | **`offering`** / regime `cn_exchange` / subtype `equity_offering` / `read` |
| 真实观测 | 96 页、3 224 个 unit；证据来自封面"向特定对象发行A股股票募集说明书"与正文"募投"章节词汇 |

### 其余 5 份真实原件

| 样本 | 旧标题路由 | 本包路由 |
|---|---|---|
| 名创优品 2024 港股年报（246 页） | `annual_report` | `hk_periodic` / hkex / **annual** |
| 万润 投资者关系活动记录表 | `investor_relations` | `investor_qa` / cn_exchange |
| 中微 2026 Q1 季报 | `quarterly_report` | `cn_quarterly` / cn_exchange / quarterly |
| 微软 10-K 2025（HTML） | **`unknown`** | `sec_10k` / sec / annual / 10-k |
| 微软 Q4 FY26 电话会 TXT | `investor_call_transcript` | `earnings_call` / transcript |

---

## 五、真实数据暴露并已修掉的 4 个真缺陷

每个都由真实原件触发，**不是**靠调高 `max_probe`、改样本 oracle 或强制 unknown 过关；
每个都补了 C 节点回归锁。

1. **`SPEAKER_TURN` 把财务报表脚注标签 `Notes:` / `Note:` 当成发言轮次。**
   名创 246 页港股年报里 `Notes:`/`Note:` 出现 **33 次**，叠加正文里的 "conference call"/
   "quarter" 词触发 `SPEAKER_TURNS`，把**真年报判成 `earnings_call`**。
   修复：新增 `is_speaker_turn()` 与闭合的 `NON_SPEAKER_LABELS` 负标签表。

2. **跨 regime 的形状候选能压过 regime 专属的定期报告候选。**
   `decide()` 中 `_call_candidate`（76 分）无条件参与跨 regime 竞争，压过 `_hk_candidate`
   （70 分）。修复：只有 regime 未被**结构性证据**确立时，形状类候选才可跨 regime 竞争
   （新增 `_regime_is_structural`）。

3. **SEC 表单标签从"正文里提到别家文件"被当成自己的封面标签。**
   微软电话会 TXT 的一段前瞻性陈述写了"…the risk factor section of our Form 10-K"，
   于是 `SEC 表单: 10-K` 触发，**电话会被判成年报**。修复：带 `form <name>` 标签的 unit
   必须能作为本文档自己的封面行（`is_title_evidence`），或本身带真实 SEC 条目结构。
   该修复同时修好了原有合成负例 `test_sec_10k_mentioned_only_in_a_cross_reference_is_not_a_10k`。

4. **招股书正文里引用的《募集资金管理办法》被当成招股书自身的行政用途。**
   标题通道把 `cover_text` 一并匹配，导致 429 页 IPO 招股书被判 `administrative`。
   修复：把**调用方给的 `title`** 与**正文内标题**分成两个通道——正文里带书名号的标题是
   **引用**别家文件，不构成本文档用途；而真实鼎龙确认函的标题
   `关于《…招股说明书》的确认意见` 因为带自身用途词（`allow_self_purpose`）仍判为自发声明。

---

## 六、真实与合成覆盖各多少（不夸大）

**合成/重建输入（占绝大多数）**：单元测试 150 个中的 138 个（A/B 节点）。
`tests/fixtures/document_understanding_profiles/builders.py` 里的封面/TOC/正文常量，
是从计划 `sample_observations.json.gz` 记录的真实标题、目录行、标题行与**有界片段**重建的，
覆盖面 20 份计划样本的形态；但它们是重建片段，**不是**原件。

**真实原件**：C 节点 7 份，用现有生产解析器读原件后路由（另有 12 个回归锁直接由这 7 份
真实观测驱动，即 `test_c_real_shape_regressions.py`）。

| 指标 | 值 |
|---|---|
| 真实原件探测数 | 7（5 PDF + 1 HTML + 1 TXT） |
| 成功读取 | 7 |
| family 与卡片预期一致 | 7 / 7 |
| 解析出的真实 unit 总数 | 12 271 |
| 喂给路由器的 unit 上限 | 4 000／份 |
| 证据摘录字节 | 15 595（上限 57 344） |
| 复制进 worktree 的原件 | 0 |
| 模型调用 / 网络调用 / 付费 | 0 / 0 / $0 |

---

## 七、哪些仍没证明（诚实清单）

1. **真实文档全部 `confidence=low`**，原因是 `ROUTE_PROBE_LIMIT` 到限：真实文档 3 000–4 000
   个 unit，而冻结预算是 200 unit / 64 000 字符。这是**预算到限的诚实状态**，不等于
   "路由正确且自信"。提高预算属 ROOT 用既有全局限制收敛的范围，profile 不允许自行提高。
2. **扫描件没有跑 OCR。** 鼎龙确认函的原生文本真的是空的（1 页 0 字符），所以它是**仅凭
   调用方提供的标题**判为行政候选的。扫描件的 OCR 路由**未经验证**。
3. **名创年报有 1 个 opaque 页（p246）**，`native_scan=partial`；未覆盖页按未读处理，
   该页内容**未证明**可读。
4. **只验证了"路由到哪一类"。** 章节优先级、语义包、摘要焦点只用合成夹具验证，
   **没有**用真实原件验证召回质量；那属 DU-STRUCTURE 与 ROOT。
5. **微软 10-K 只喂了前 4 000 个 HTML unit**（共 5 215），尾部未探测。
6. **本包未接入生产**：目前没有任何生产调用方 import 它。ROOT 负责适配
   `NarrativeUnit`/`DocumentStructure` → `du-input/1` 并接线。
7. **US S-1/F-1、完整 8-K/6-K 附件容器仍无真实样本**（与 `design.md` 第 10 节一致）。
8. 计划本身的 20 份样本**不全是独立 holdout**，因此本 lane **不声称**盲测。

---

## 八、原件保全

解析前后对 7 份原件各复核 SHA-256、mtime、字节数：**全部未变**。

- 前快照：`.planning/du-profiles/c-evidence/originals-pre-snapshot.json`
- 后快照：`.planning/du-profiles/c-evidence/originals-post-snapshot.json`

原件从未被复制进本 worktree。摘录按文档 ≤8 KiB 截断，全文不落盘。

---

## 九、安装动作与下一步

- **install_actions：`none`**（未安装任何技能，未改配置，未加依赖）。
- **临时文件清理**：调试脚本 `_tmp_*.py`、`_inspect_two.py` 已删除；owned 路径下所有
  `__pycache__` 已在提交前移除（未被跟踪）。
- **给 ROOT 的下一步**：
  1. 从 `codex/du-profiles-20261013` 取真正实现 commit（见 `handoff.json` 的
     `implementation_commits`）；
  2. 由 ROOT 创建父包 `src/company_wiki/document_understanding/__init__.py`（本 lane 故意未建）；
  3. 适配现有 `NarrativeUnit`/`DocumentStructure` → `du-input/1` 并调用 `route_document`；
  4. 决定是否放宽 200 unit / 64 000 字符的探测预算（当前每份真实文档都会报
     `ROUTE_PROBE_LIMIT` 且 `confidence=low`）。
  在第 3 步落地前，**不要**把本 lane 当作已启用生产。

---

## 十、记录形状 C 节点复核（与上述真实原件复核互补）

除真实原件探测外，本 lane 还跑了第二个 C 节点：用计划 `sample_observations.json.gz` 里
**记录的全部 20 份样本形状**（标题、目录行、heading 行、≤8 KiB 摘录）重建 observation 后路由，
对照 manifest 的预期 family。该脚本补上了真实原件探测覆盖不到的样本：临时目录里的港股/US 原件、
以及本机不存在的原件。

```bash
python -X utf8 .planning/du-profiles/_cnode_probe.py
```

首次运行 **15/20**，又暴露出 5 个真实原件与合成夹具都触达不到的缺陷，全部在**路由器**里修掉，
没有一条是靠放松断言过关：

1. **裸 `声明` 章节被当成行政用途。** A股年报的董事会声明、以及发行文件的
   `发行人声明`/`特别提示`，都是披露必备前件而非文档用途；已从行政词表中移除。
2. **正文里引用的 `《募集资金管理办法》` 被当成招股书自身用途**（真实原件复核也命中同一根因，
   此处是记录形状侧的独立复现）。
3. **英文短语 `annual report` 在美股文件上触发港股年报信号。** 港股信号现在要求港股章节词汇
   或中英双语标题，纯英文短语不再算证据。
4. **繁中 `中期報告` 漏判。** NFKC 不会把繁体折成简体，导致真实港股中期报告被判成年报；
   现在繁简两种写法都显式列出，并在注释里记录为什么 NFKC 不够。
5. **散文里的裸表单名被当作封面标签。** 10-Q 自身会写 "our annual report on Form 10-K"，
   于是被改判成 10-K；现在表单名只在**印刷表单标签**或封面行上才算数，
   指向别家文件的引用一律不算。
6. **只探测到前件、募投证据在后面的发行文件掉进定期报告族。** 募投结构现在能识别发行文件，
   而自称为定期报告的文件仍保持原族。

最终记录形状一致性：**19/20**。剩下那一条不是失败而是诚实结果：
`cn-ipo-confirmation` 只有 1 个 opaque 页、可读字符为 0，确认措辞只存在于**文件名**里，
而路由器被禁止读路径。传入真实标题时同一文档判 `administrative` / `administrative_candidate`；
完全没有可读证据时判 `generic_read`。两种都不猜。

同时验证了不迁就样本：`cn-ir-policy` 在 manifest 里标为 `ir_policy`，但其记录正文是一份
`投资者关系活动记录表`，因此**正文胜出**，并把 `declared_kind` 的分歧显式报为
`DECLARED_KIND_CONFLICT`。

## 十一、验收清单脚本

```bash
python -X utf8 .planning/du-profiles/_acceptance.py
```

逐条断言卡片验收条件，当前输出 `ALL ACCEPTANCE CRITERIA SATISFIED`：

| 卡片验收条件 | 结果 |
|---|---|
| 三个冻结 wire 可由 ROOT 直接调用 | 通过（15 个 profile） |
| 确认函不会被当作 IPO 全文 | 通过（`administrative_candidate`，非 skip） |
| A股"发行A股股票"措辞能识别 | 通过（`offering` / `cn_exchange`） |
| SEC 与港股词汇不互套 | 通过（10-K 无 `Item 4`、20-F 无 `Item 7`、港股无 item 编号） |
| unknown 仍可阅读 | 通过（`generic_read`，永不 skip） |
| 所有声明有输入依据 | 通过（reason 带 code + unit_ids） |
| 未靠路径/公司名特判 | 通过（AST 扫描可执行字符串常量，命中 0；公司名仅出现在记录样本来源的 docstring） |

该脚本同时复核了"不能通过调高 max_probe、改样本 oracle 或强制 unknown 都判 annual 过关"
这三条禁止项：预算收紧只会降低置信度、未知形状一律不判 annual、oracle 未改。

## 十二、协作提示（本 worktree 有并发写入者）

本 worktree 在本次会话期间有**两个写入者**并行工作：真实原件 C 节点复核
（`_cnode_real_probe.py` + `c-evidence/`）与本节的记录形状 C 节点复核
（`_cnode_probe.py` + `test_c_real_shape_regressions.py`）系并行开发，
且 `signals.py` / `decision.py` 的部分内容被另一个写入者在本会话编辑期间重排过。

最后一次外部写入之后已端到端复验：**150 tests passed**、`ruff check src tests/unit` 全绿、
`compileall src` exit 0、验收脚本全过。交付状态自洽，但 ROOT 应知道该树存在并发写入者，
请以 `git diff --name-only <base>...HEAD` 作为出货范围的最终依据，
并预期本分支包含两个作者的提交。
