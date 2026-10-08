# G-D B3：两个旧派生归档精确退役

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> 2026-10-03 冻结实施卡。用户已授权保留原始下载文档、删除中间派生数据；本批没有新增人工批准。当前数据无反弹，只是上一批仍保留两个大归档。B3 可以独立先于 N4/B2 实施，不等无关全库迁移。

## 1. 原件与来源事实保留依据

`retire_source_catalog_db._make_shadow` 仅筛选 non-active evidence_spans，所有其他表原样复制并全行 digest 比对。2026-10-03 当前实读16/17张 metadata 表完全相同；scan_runs仅多一条 `files_seen=files_hashed=0` 的错误扫描，排除该新增行后原480行digest也相等。当前 sources/documents/locations/document_retire_audit/metadata assertions 保留来源和历史身份，不需要第二套逐span tombstone。

两目标：

| project-relative 精确位置 | 实际 B | 内容与处理 |
|---|---:|---|
| `.source_catalog/retirement/20260926T170825Z-4a9c67e1/catalog.full.sqlite3.zst` | 6,198,704,362 | 已退役旧 SQLite，hash 由 prepared/retired 记录；非下载原件 |
| `source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz` | 5,207,478,767 | 旧 non-active 派生 span JSONL；无现存 manifest，plan时stream hash绑定 |

合计 **11,406,183,129 B / 10.623 GiB**。gzip仅五条有界样本，不声称与zstd逐行全量等价；两者各自为已废弃派生，不要求彼此完全重叠。当前 EvidenceQuery 对非active来源已拒绝，运行时不读取任一归档，prune只发现manifest而这件gzip无manifest。测试前后原件保留，旧span不再保证恢复。

审计机器结果：[metadata audit](harness_lanes/results/gd_b3_metadata_audit_2026-10-03.json)。包括当前DB完整SHA/size/mtime、prepared/retired小文件SHA、逐表digest、额外scan行和两archive字节绑定。写入source_id/locator/历史事实的主DB不改。

## 2. 窄接口与文件所有权

本线只拥有：

- 新 `scripts/retire_derived_archives.py`：plan/apply/receipt CLI。
- `scripts/retire_catalog_snapshot.py`：仅完成B1重复查询不依赖已合法退役archive的窄分支。
- `scripts/writer_policy.py`：登记source lifecycle工具，保留legacy research writer冻结。
- `src/company_wiki/source_catalog/evidence_query.py`：只修非active旧span诊断正文，不改兼容error_type/nonretryable/as-of/原件验证。
- 对应新unit+一个integration E2E，补B1两项重复/新删除区别回归与旧query断言；本线交付结果文件。

三大PWF/ADR/合并/推送/生产apply归总指挥，其他仓目录及新N4代码不写。先RED，后实现；禁止完整恢复/全量gzip解压/复制数百万ID/新队列/原件删除。

CLI拟定：`python scripts/retire_derived_archives.py --project-root <root> --audit <json> [--apply]`，默认dry-run。audit内容/字段在源码和单测里固定version，不能把任意target列表变成通用删除器；只允许上表的两种退休archive布局和明确run/date，sqlite/raw/目录/越界/reparse拒绝。

## 3. plan 与 apply 规则

1. 当前 Worker控制保持paused，CatalogOperationLock只保护维护边界；当前DB无非空WAL（本机已停止），SHA/size/mtime绑定审计。audit与prepared/retired/run/metadata证明自洽；生成计划不修改任何文件。
2. 两目标hash/size逐字节流式验证，zstd同时核既有prepared/retired的backup身份，gzip核本轮捕获的字节身份。没有full restore调用。路径先绝对解析并检查祖先/目标不reparse、在本project限定派生子目录；不接受raw/主库，即使提供匹配hash也拒绝。
3. `apply` durable小intent先落盘/fsync，记录每目标计划，随后两件逐个精确unlink。每件hash/size当前复核；中断后只从该intent补已删记录/续第二件，不重复归因释放，不把无intent的缺文件称作成功。
4. 最后小receipt记录历史bytes、此调用新删bytes/恢复状态、每target状态与originalhash、当前DB前后SHA/size/mtime、同卷free前后。重复apply回显历史收据，不新增bytes；部分漂移只拒绝下一候选，不误报完成。
5. 当前原始文件不进入操作清单，主库字节不变。old prepared/retired、B1 intent/receipt、metadata audit全部保留；不改事实表/不VACUUM。
6. B1已有receipt且snapshot不存在时可以核小basis/intents/receipt并回显，不再强求archive文件存在；新的snapshot删除仍必须完整核保留archive。不允许缺archive的新删除路径借历史receipt绕过验证。

## 4. 旧证据返回语义

保留 `EvidenceQueryArchivedError` / `error_type=legacy_evidence_archived` / `retryable=false` 兼容行为，将“仍在 verified cold snapshot”改为中性明确说明：旧non-active evidence在当前catalog不可用，source identity仍保留。unknown仍NotFound，active正常；不隐式恢复、不回退下载、不伪造空success。

ADR-009的旧90天/恢复前置由本用户授权和实读事实取代，仅标superseded，不删历史。最终收据说明已放弃旧span正文的full restore；原件回源和来源版本保留。

## 5. 一个大节点测试包

先RED后GREEN，集中一次：

- 小型真实catalog、active/retired source+locator+原件，真实小gzip与合法小zstd；审计证明和plan从实际fixture生成。
- dry-run零写；apply两件；重复apply；第一件unlink后注入中断→恢复只删第二件/准确增量；无intent缺目标不误报成功。
- wrong SHA/size、metadata/basis漂移、当前DB/WAL漂移、原件/主DB/目录/越界/reparse拒绝；正文不参与metadata proof而来源事实不能被删。
- 删除前后source/version/location/retire事实全行、原件SHA/mtime、当前DB字节相同。active query和正式narrative-read CLI仍正常；旧span具名不可用，unknown为NotFound。
- B1已有完成收据在archive退役后重复查询成功；另一个新snapshot缺archive仍拒绝。
- Ruff/host guard/来源工具分类与受影响旧query/B1回归；不用全仓coverage、不复跑4份PDF节点。

独立短run root测试，finally检查绝对containment，只删除本次创建子树，原测试目录恢复。节点完成后交分支diff/测试/根清理收据，总指挥普通commit/push/精简CI，随后生产精确apply。理论三根 **39.760→29.138 GiB**，实际收据/盘点决定结论；原文目录不减。
