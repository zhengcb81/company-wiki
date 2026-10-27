# G-CWP-01 独立审查报告（最终）

- 审查者：独立 general-purpose 审查 agent（非实现作者；独立构造 fixture、独立运行全部测试与 CLI 探针，不复述作者结论）。
- 审查对象：worktree `C:/Users/郑曾波/Projects/dashboard-owner-cwp`，分支 `codex/dashboard-cwp-public-browser`。
- **绑定最终候选 commit：`214c53796bd7f8e2c8fa0542f3ea713adebaf78d`**（= 候选实现 `7ef04c9c` + 返修 `214c5379`；基线 `0c988e8d` = owner master HEAD，已核实）。本报告与 `handoff.md` 为其后的无产品影响交接文件。

## 审查范围与方法

对照 `G-CWP-01.md` 全部要求 + `EXTERNAL-HARNESSES.md` 协议 + Dashboard `contracts/openapi.yaml`（0.1.1-b）+ owner `AGENTS.md`，逐项核对代码与行为；独立运行 focused 测试、相邻回归、自建 fixture 的 CLI 五链路与 16 项边界注入探针、路径泄漏扫描（含 cursor/snapshot token 解码内部）、commit 内容与行尾核查；在 owner 原仓同 HEAD 验证基线固有失败。

## 发现与闭环（ID / 严重度 / 根因 / 修复 commit / 独立复测）

| ID | 严重度 | 结论 | 根因 | 修复 | 独立复测 |
|---|---|---|---|---|---|
| F-01 | MAJOR | null `canonical_entity_id` 经 CLI 以 exit 1 + traceback 崩溃，违反自身 blocked 信封契约 | browse() 用可选校验 + 裸 `assert` 兜底；CLI 不捕获 AssertionError；`python -O` 下会静默以 NULL 查询 | `214c5379`：`_required_text` 必填校验 → `PublicBrowseError(invalid_canonical_entity_id)`；CLI 级 RED 复现入库 | **GREEN**：rc=2，stderr 精确 blocked 信封，无 traceback；`python -O` 同样拒绝 |
| F-02 | MINOR | 固定快照重放时同集合异序列表被误判 `snapshot_filter_conflict` | `_filters_conflict` 按请求序逐位比较 | `214c5379`：列表校验器内排序（seam 归一，建快照与重放一致） | **GREEN**：异序重放同页返回；真异值仍被拒（冲突检测未弱化） |
| F-03 | NIT | 伪造越界 offset cursor 返回 `available` + 0 项，语义失真 | `_serve` 未校验 offset 与 total 关系 | `214c5379`：offset≥total（total>0）→ `state=empty` + `page_offset_beyond_total` | **GREEN**：原反例复测 state=empty、reason 正确、next_cursor=null |
| F-04 | NIT | 空列表过滤器被拒，与 `_filters_conflict` 视 [] 为未发送的语义不一致 | 校验器与冲突判定对 [] 语义分裂 | `214c5379`：`[]` 归一为"不过滤"（str/int 两变体一致） | **GREEN**：`[]` 与无过滤 total 一致，token 内 filters=None |

无 BLOCKER；返修无新发现。

## 逐项要求结论（复审后）

| 要求 | 结论 |
|---|---|
| A1 browse 入参（canonical entity + 市场/文种/期间/语言/状态 + cursor/limit/固定查询） | PASS |
| A2 pathless 逻辑文档及历史版本（同 document_id 多 source 独立 item）+ 完整 SourceRef v2 六字段 | PASS |
| A3 facets 只统计过滤后快照、total 精确（total_status=exact） | PASS |
| A4 catalog revision + next cursor；empty/partial/unavailable/stale 四态区分 | PASS |
| A5 稳定 document_version_id（同 triple 恒等、异 source/hash 必异、is_current_version 提供最新件语义） | PASS |
| A6 仅凭 id 精确重开完整 SourceRef / not_found | PASS |
| A7 只读、无下载/OCR/摘要、零物理路径泄漏（含 token 内部） | PASS |
| A8 迁根后同一 SourceRef 仍可由 owner reader 解析（verify_version 直证；revision 不随迁根变化） | PASS |
| A9 不声称 Range/206 | PASS（两文件 grep 零命中） |
| B 合同兼容（DocumentVersionId 正则、非路径/URL；SourceRef 完整无截断） | PASS |
| C 正确性/边界/副作用（测试独立复跑、回归、注入、SQL 参数化、只读连接、commit/行尾） | PASS |
| D 可维护性（docstring 如实、角色白名单与 scanner/adapters 词表吻合、house 风格一致） | PASS |

## 独立运行的命令及结果

1. `pytest tests/contract/test_public_document_browser.py -q` → **15 passed**（含 F-01..F-04 的 RED→GREEN 断言）
2. `pytest tests/contract/test_source_version_reader.py tests/contract/test_source_export_v2_cli.py -q` → **40 passed**
3. `pytest tests/contract/test_cross_root_dedup_fc603.py::test_fc603_ex06_amended_original_stable_revision_rule`（owner 原仓 HEAD 0c988e8d）→ 1 failed（**基线固有**，先于本包存在）
4. 自建 fixture CLI 复测套件（五链路 + F-01..F-04 原反例 + 16 项边界探针：重复 JSON key、精确字段集、limit 0/500/501、非法 base64url、伪造 offset、snapshot-entity / cursor-snapshot 不匹配、过滤器冲突与顺序重放、stale、零路径泄漏、SourceRef 六字段、dvid 正则）→ **25/25 OK**
5. `git show --stat 214c5379` / `git diff 7ef04c9c..214c5379` → 仅声明文件；`git ls-files --eol` → LF；worktree 终态仅剩已知 `.githooks/pre-push` mode 环境变化（未入库）与 handoff 目录

## 仍存限制（如实声明，非缺陷）

- reopen 为有界无 spill 全表扫描（实测 ~2.7s @ 23k docs / ~10 万 locations），模块 docstring 已声明；无注册表、零写。
- 生产 catalog schema=1.2.0，代码 fail-closed 显式支持 1.4.0（owner 先在状态；与既有 v2 读路径行为一致，不在每次读时强校验）。
- `document_kinds` 等过滤值未按 13 值闭集强校验（按目录实际值匹配）——handoff 已如实声明。
- Windows %TEMP% 含非 ASCII 时 SQLite 落盘临时树查询失败为本机环境事实；本模块 SQL 已去 spill 化（owner 既有工具可能受影响，见 handoff §4.4）。

## 最终判定

**通过。** F-01（MAJOR）/F-02/F-03/F-04 全部根修并按原反例复测 GREEN；卡内 A1–A9、B、C、D 逐项达标；本包范围无未关闭缺陷。可交 D03 接入。
