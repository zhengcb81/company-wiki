# MB-CWP 独立审查

审查 agent：`agent_eeb4e482-3059-4c96-8796-2b3a7cde80ec`（general-purpose，只读判断 + 可跑测试，未改任何文件）。

## Round 1 — 范围 `09434acef`（基线 `08dfe8bf1`）

判定：**NOT-DELIVERABLE**（2 blocker + 10 in-scope + out-of-scope/nit）。审查自跑证据：卡证明库 138 passed、B33 四文件 118 passed、四缺口+version_reader 72 passed、canonical 51、stream+issuer+calendar 27、B34+config+cli_output 69、ruff/mypy/config_doctor 绿、全量 contract 61 failed/3074 passed（A/B 复跑基线同红）、全量 unit 3 failed/8168 passed + 6 收集错误、Dashboard 24 条 4 failed。

### BLOCKER（均已修复于 `be955446f`）

1. **CI 绿转红**：`public_legacy_source_recovery_cli.py:11` 私有兄弟导入（`_emit/_nonfinite/_pairs`），撞 CI 门内的 `test_source_catalog_module_contracts`（测试文件与基线逐字节相同、基线绿）。修复：输入改走公共 `wire_json.parse_json`，输出保留本地 `_emit`（与兄弟字节同构）；不改名不加 `__all__`。
2. **T-READ locked 语义变更未披露且破坏命名消费端**：初版在 `begin_candidate`（验真前）发 `locked`，`test_missing_file_refuses_before_lock` 失败；我方测试还钉住了相反序。修复：`locked` 惰性化（首字节前 / 空原件 commit 前），无字节拒绝无锁行，`ok` 定义为全量验真声明，2.2 schema 不变；两用例钉新序；升级 1 披露于 findings。

### IN-SCOPE（修复/处置于 `be955446f`）

3. **非 primary 扩宽与消费端契约相反**（`test_non_primary_history_version_refused_like_the_reader`）→ 按 interfaces.md 升级 ROOT（findings 升级 2：失败例 + 方案 A/B），本卡不单方关闭。
4. **13+1 个未注册 reason code**（基线 65 → tip 78）→ 全部注册进 `REASONS`+`STAGES_BY_REASON`（集合相等），现剩 64 全为基线 code，本卡 net 0。
5. **findings/progress 计数错误**（canonical 60→51、port 12→21、isolation 9→16、recovery ~15→8、diff 61→66 文件等）→ 全部改正。
6. **T-N4 证据不可复现**（"agent 实证"非命令）→ findings 写入两条可复现命令 + 主线反向断言（`test_titleless_signal_free_quarterly_remains_reviewable`）的替代依据。
7. **基线既有红未披露** → findings 基线红名单（unit 6+3、contract 61、fc1301 64、source_system_docs）。
8. **`scripts/config.py` 超写集合未披露/无 owner 行** → 披露（T-CONFIG 卡行点名授权）+ ownership 增行。
9. **batch 路径仍隐式读预算配置** → `work_budget_factory` 由 `_run_owned` 一次解析并贯通至 handler。
10. **新边界测试未接 CI/门** → fast gate +6 文件、ci.yml ruff +1 路径；慢套件在 handoff §4 披露。
11. **task_plan 状态过期** → 全部更新。
12. **ownership 计数自相矛盾（242 vs 251）+ `__init__.py` 未分类 + `narrative_transport_cli` 兼容例外未列** → 修正/补列。

### OUT-SCOPE（交 ROOT，已记录于 findings）

13. Dashboard 2 条测试导入历史私有名（`resolver._ReadBudget`、`reader._admitted_candidates`），基线主线即不存在——消费端分支耦合，需 Dashboard 改用现行公开端口；基线红修复（unit 6+3、contract 60、fc1301 64、source_system_docs）。

### NIT（已处理）

14. `--system-site-packages` venv 与 `declared ⊆ wheel` 断言的保真度限制（handoff 披露）；`build/`/`egg-info`/`.ingested`/`__pycache__` 清理（已删）；progress diff 计数（已改指向 handoff 终态）。

### PASS 注记（round 1 复核确认，摘录）

四缺口为真 RED→GREEN（基线 blob 对照：`from_reader` 存在→删、`work_budget_factory` 无→有、guard import 迁移、`lxml` 无→有）；探针用 `-I` + 仅拒本仓模块，环境失败不冒产品 RED；写集合 62 文件全在授权范围；`pyproject` 仅 +2 行、console 表未变；非 primary 改动的 `query_source_reference`/`annotate_locations`/`reusable_only`/primary 读不变量全部成立；历史移植测试与历史 ref 逐字节相同（canonical/readiness/recovery/exact_history），仅 link 有已文档化的 PYTHONPATH 适配；**无断言被删除或放宽**（3 个改动测试仅夹具适配/纯新增）；T-CANON 无第二事实库/下载预算；T-B33 recovery 走既有 `restore_document_facts`、默认 preview；T-B34 无 8 条帽（`max_pages=3` 为基线既有）；ownership §1 与 pyproject/实际 CLI 一致；根模块边规则由既有 AST 测试覆盖。

## Round 2 — 复核范围 `be955446f`

同一 agent 逐项复验（自跑证据）：

| 项 | 判定 | 关键证据 |
|---|---|---|
| BLOCKER-1 私有兄弟导入 | **FIXED** | 三文件 `09434acef..HEAD` 对照 + module_contracts/recovery/link **29 passed**；三测试文件与 `09434acef` 逐字节相同（无断言削弱）；61 个既有失败重跑 → 60 failed/1 passed（唯一 pass 即本修复） |
| BLOCKER-2 locked 语义 | **FIXED** | stream 7 passed（含无字节=单拒绝、同尺寸篡改=[locked,unavailable] 无 ok）；Dashboard 重跑 **21/24**，`test_missing_file_refuses_before_lock` 转绿；`len==2→1` 判定为本 finding 要求的契约再钉，非削弱 |
| 3 非 primary 升级 | **FIXED-as-escalated**，分类确认 | findings 升级 2 含失败例/断言原文/两方案/不依赖声明；判定满足 interfaces.md（附注：代码先于升级落地，属"后补协调"，因交付不依赖该决定而接受）；`_ReadBudget`×2 OUT-SCOPE 分类**维持** |
| 4 reason code | **FIXED** | `REASONS↔STAGES` 集合相等双向为空差；stage 20 passed；fc1301 残留 64 vs 基线 65，`HEAD-only=[]`、`BASE-only=['catalog_unavailable']`；措辞精度注记已采纳（"基线既有发射点"） |
| 5 计数 | **FIXED** | 86+15+8+9=118、51+9+20+21=101、33+39=72、16、18+15=33、7 全部核对；diff 66 文件 +10490/−49 与 `git diff --stat` 精确一致 |
| 6 T-N4 证据 | **FIXED** | 两条命令复跑 9 passed（56 deselected）+ 78 passed；主线反向钉与 `narrative_finalize.py:237-244` 引用在案 |
| 7 基线红披露 | **FIXED** | 与审查方独立基线 A/B 完全一致 |
| 8 scripts/config 披露 | **FIXED** | ownership §4 owner 行 + findings 引卡 A0 T-CONFIG 行 |
| 9 batch 预算 | **FIXED** | 一次解析贯通四层；`test_narrative_batch` **17 passed** |
| 10 CI 接线 | **FIXED** | gate +6、ruff +1；fast gate **325 passed / 109.5s / exit 0**；慢套件排除有据 |
| 11/12 文档 | **FIXED** | task_plan 全状态、ownership 251/算式 `14+7+29+6+81+251+66+35=489`、`__init__` 分类、compat 注记 |
| 14 产物 | **PARTIAL (NIT)** | `.ingested` 已删；`build/`+`egg-info` 被测试运行重建（gitignored），清理归属已在 handoff §6 声明——接受为非阻断 |
| 复跑 | mypy 489 绿；CI-scope ruff 绿 | |

**Round 2 判定：DELIVERABLE**（代码与合同范围 @ `be955446f`）。打包条件（均已在本次文档提交与推送中落地）：commit `handoff.md`+`review.md`+入口测试加强、补 `handoff.json`、推送 `codex/mb11-cwp`。剩余 Dashboard 3 失败维持分类：非 primary=已记录的 ROOT 升级；`_ReadBudget`×2=消费端耦合 OUT-SCOPE。
