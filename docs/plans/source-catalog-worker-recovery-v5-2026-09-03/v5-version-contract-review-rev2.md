# V5 版本合同 rev2：独立设计复审（2026-09-09）

审查者：independent design review agent（非作者，复审）
范围：`v5-version-contract.md`（rev2）＋更正后的 `README.md`／`findings.md`／`progress.md`／`task_plan.md`；复算对象含 `v5-version-reference-inventory.{json,md}`、`v5-baseline-equivalence.json`、`import_manifest.v5.json`、`baseline/history/**`、复活的旧目录与 Git 边界。

结论：**accepted_with_findings**。F1–F6（2×P0＋4×P1）经独立复算全部关闭：v5 manifest schema 已在 §5 显式定义（`plan_manifest.schema.v5.json`、`$id urn:…:plan-manifest:v5`、`schema_version const 3`、17 行必填字段、N7 澄清），该 `$id` 在 29 个既有 `$id` 中不存在；旧目录复活已被记录（38 文件／tracked／clean／与 v5 目录任一文件字节相同 0/38）并由 N9 约束；16/11→17/10 更正已入 progress.md，冻结 `progress.v4.md` 字节未动；`$id` 后缀 14/12/2/1 由枚举 JSON 与独立扫描双向复现；N1–N15 覆盖 F5 全部缺项并强制机器检查＋测试 ID；角色表覆盖全部 69 文件。F7 仅部分关闭（枚举 .md 范围措辞未改），F8–F10 关闭。**新发现 G1（P1）阻断 V5-2 冻结**：冻结集合定义自相矛盾（N14 要求 `.gitattributes` 入集 vs §5 的「48 份计划输入」「v5 自有文件入 excluded」、§6.2 角色、N13 的「多文件」拒绝），且 v5 manifest 的治理件（v5 schema／v5 checker）无任何哈希绑定。无 P0 残留，故接受 rev2 方向，但 G1 须在 rev3 关闭后才可进入 V5-2 冻结。

## 关闭判定（复算值，非作者声明）

| 原ID | 原级别 | 状态 | 证据（file:line／本次复算） |
|---|---|---|---|
| F1 | P0 | closed | 合同 §5 `:50-79`：文件 `plan_manifest.schema.v5.json`、`$id …:plan-manifest:v5`（复算：不在 29 个既有 `$id` 中；`plan-manifest` 仅有 `:v4`）、`schema_version const 3`、`additionalProperties false`、17 行必填字段（含 `self_exclusion`／`supersedes`／`investigation_source`／`capture_manifest`）；`:80` 澄清 N7 只约束**导入的** artifact。除 G1 所指集合成员问题外，V5-2 无需再决策 manifest 的 schema 归属 |
| F2 | P0 | closed | `Test-Path`=True；`git ls-files`=38；`git status --porcelain` 空；mtime 2026-09-07 19:08:52+01:00；复算：38 文件与 v5 目录任一文件字节相同 **0/38**，与 `historical_v4_sha256` **0/38**；合同 `:90-92,105` 记录复活，`:126` N9，`:110` 取代链排除旧目录 |
| F3 | P1 | closed | `progress.md:8`、`findings.md:9`、`task_plan.md:44-45` 均改为 21/17/10（独立复算 48 份 plan 输入 = 21 exact／17 crlf_only／10 unproven，unproven 清单与合同 `:46` 逐项相同）；`baseline/history/progress.v4.md` sha256 `6c34d6da…`＝import manifest 记录值、`git diff HEAD` 为空、仍含「11 份」(`:28,:35`)，与「保留原字」披露一致 |
| F4 | P1 | closed | 枚举 JSON `totals.distinct_ids`(29) 与本次独立扫描（59 文件）同值：`:v4`=**14**、`:v1`=**12**、`:v5`=2、`:v2`=1；合同 `:13,36` 即此值 |
| F5 | P1 | closed | N1–N15 `:116-132`：自排除/覆盖写 N10、`supersedes` N11、`investigation_source` N12、normative 集合完备性 N13、`.gitattributes` N14、generation 映射 N15；`:114` 强制「机器检查＋测试 ID」，`:138` 要求 V5-2 checker 实现 N1–N15 |
| F6 | P1 | closed | 复算目录 = **69 文件**（12 根＋`baseline/` 54＋`reviews/` 3；`baseline/plan` 48 = 29 schema＋13 prose（含 findings/plan_review_findings）＋4 `.v4.json`＋1 py＋1 txt）；`:98-106` 角色表分组 9+3+3+48+5+1 = 69 |
| F7 | P2 | partially closed | 合同 `:33` 已改为「59 个文件 = baseline/** 54 份 + v5 根目录 5 份」（复算 54+5=59）；但 `v5-version-reference-inventory.md:3` 仍声明范围 `baseline/**`，其表 `:38-40` 已含根文件、JSON `scope` 亦未列根 5 份 |
| F8 | P2 | closed | `README.md:27-31`、`findings.md:41-44`、`progress.md:13-14` 均记录 tracked=64 与旧目录复活，并就地声明历史「tracked=0」失效 |
| F9 | P2 | closed | `git log --oneline -1` = `434a6c2`；`git ls-files`（v5 目录）= **69**；434a6c2 以 `A` 加入合同＋两份 JSON＋inventory.md＋rev1 审查；`git status --porcelain` 空 |
| F10 | P2 | closed | `:27` 定义 `freeze_generation`＝`capture_generation`(v5)、`protocol_revision`＝`source_protocol_revision`(v4)、`capture_manifest` 绑定 sha256（复算 `da7d116e…` 与 README:43 一致）、`plan_freeze_git_head`＝生成时 HEAD；N15 `:132` |

## 新发现（rev2 引入或残留）

| ID | 级别 | 证据 | 说明 |
|---|---|---|---|
| G1 | P1 | §5 `:72`（`normative_files`＝「48 份计划输入」）、§5 `:75`（excluded＝「同 v4 语义 + v5 自有文件」）、§6.2 `:100`（`.gitattributes` 归「导入元数据」）、N13 `:130`（「多文件」即拒绝）、N14 `:131`（`.gitattributes` 未入冻结集即拒绝） | 冻结集合自相矛盾：`.gitattributes` 属 v5 自有文件，按 `:75`/`:100` 应在 excluded，却被 N14 要求入集，而 N13 又拒绝多列（v4 的 excluded 清单见 `plan_manifest.v4.json`，其中无 v5 自有文件）。同时 v5 manifest 的治理件——`plan_manifest.schema.v5.json`（§5:54）与 V5-2 checker（§8:138）——不在任何哈希绑定集合内，而 v4 的 schema 与 checker 都在 48 份内；`:72` 的条目类型又要求每项带 `equivalence`，v5 自有文件无此类别。F5 的 `.gitattributes` 项形式上已覆盖但语义未自洽，V5-2 无法不复决策地实现 N5/N13/N14 → rev3 须显式给出冻结集合成员与 v5 自有条目的类型 |
| G2 | P3 | 合同 `:88-89`「64 tracked／5 未跟踪」、`progress.md:13`「git ls-files=64」 | HEAD 实测 **69 tracked／0 未跟踪**（434a6c2 已加入那 5 份）；另本复审文件在审查时仍未被跟踪，与 F9 同类但属本次审查自身产物 |
| G3 | P3 | 合同 `:90`、`README.md:30`、`findings.md:44`、`progress.md:14` 写 `2026-09-07T19:08:52Z` | 本机偏移 +01:00（GMT Standard Time），该时刻 UTC 为 `2026-09-07T18:08:52Z`（rev1 用的 18:08:52Z 才是 UTC）；四处同错 |
| G4 | P3 | `v5-baseline-equivalence.json` 的 `counts` 键为 `exact/crlf_only/unproven/unresolved`；合同 §5 `:73` 为 `v4_exact/crlf_only/unproven_new_baseline`，N6 `:123` | 等价类别命名不一致；N5/N6 机器比较前须先映射，按字面比较会误判 |

## 声明

本复审为只读、非作者；除本文件外未写入任何文件，未提交、未运行产品测试或旧 checker/worker、未联网。所有数字均来自本次机械复算（Python 3 只读脚本＋git 只读命令）。本审查**只绑定规划文档完整性**（版本合同、引用枚举、负例、Git 边界），**不授权实施**，也不构成对 worker 恢复、正式冻结或三路技术审查的通过。G1 未在 rev3 关闭前，不得生成 `plan_manifest.v5.json`，不得进入 V5-2 冻结。
