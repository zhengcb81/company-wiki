# 研究发现（catalog 空间治理）

> 持续追加；每条记录日期、内容与影响。相关任务计划见 task_plan.md。

## 发现 1：G: 盘"满了"是 C: 盘的镜像，不是云配额问题
- 日期：2026-08-06
- 内容：G:（Google Drive for Desktop 虚拟盘，DriveType=3/FAT32）报告的 Size（510,913,744,896 字节）与 Free 与 C: **逐字节一致**；云端配额缓存（driveway_account protobuf，当日 16:31 更新）显示配额 2 TiB、已用 ~87.8 GB（含 Gmail/Photos 等全部服务）、剩余 ~1.92 TiB。
- 影响：释放 C: 即自动恢复 G: 剩余空间；Gmail/相册不是问题。

## 发现 2：C: 盘 475.7 GB 占用构成（治理前）
- 日期：2026-08-06
- 内容：Users 356.7 GB（.local 130.1 → opencode 快照 127.5；Projects 117.6 → company-wiki 82.8 + company-wiki-backups 24.3；AppData 54.2；OneDrive 26.0；Dropbox 18.3）；Windows 69.7；Program Files+ProgramData 31.8；pagefile+hiberfil 14.3；其余 ~5。
- 影响：定位清理对象；已完成清理见 progress.md。

## 发现 3：opencode 快照 = 内部 git 仓库，默认开启，按步骤快照整个工作区
- 日期：2026-08-06
- 内容：`~/.local/share/opencode/snapshot/{session}` 是 git 对象库；`config` 的 worktree 指向 company-wiki；单会话 d9d2f124（7/28–8/3）产生 73 个 pack（90.3 GB）+ 50 个中断残留 tmp_pack（36.8 GB，git count-objects 判定为 garbage）= 127.5 GB。官方文档：snapshot 默认开启、用于 /undo、大型仓库会显著占用磁盘。
- 影响：已删除该会话快照（释放 127.5 GB）；防复发：opencode.json 设 `"snapshots": false` 或把大目录加入 .gitignore。

## 发现 4：catalog.sqlite3 43.9 GB 构成（实测估算）
- 日期：2026-08-06
- 内容：page_count=11,530,002 × 4KB = 43.98 GB；freelist=0（无空洞，VACUUM 无效）。sources 表无 blob（只存 sha256/byte_size/mime/first_seen），**PDF 从不入库**。证据行内容 ~30.4 GB：span_json 平均 799 B × 25,985,291 ≈ 20.8 GB；URN+locator+parser 字段平均 364 B ≈ 9.5 GB；raw_text 平均 ~8 B ≈ 0.2 GB；其余 ~13.5 GB 为索引/页结构（span_id 主键 + UNIQUE(source_id,locator) + B-tree 页头）。
- 影响：空间大头是"单元格级拆解 + JSON 冗余 + 双重索引"，非二进制 blob。

## 发现 5：evidence_spans 只覆盖 3,272 份文档，平均 ~8,000 span/文档
- 日期：2026-08-06
- 内容：25,985,291 行 span 的 DISTINCT document_id = 3,272（documents 共 23,564）；completed 文档（2,704）对应 ~22.25M span → 平均 ~8,230 span/文档（财报逐页逐段落逐表格单元格拆解）。locator 样例：`loc:v1/page:1/table:0/row:6/column:1`。
- 影响：单份大财报可产生数千条 span；这是体积倍数（原文 23.4 GB → 证据库 43.9 GB）的直接原因。

## 发现 6：phase-15.6 治理遗留——9,578 份审计文档挂着 95% 的 span
- 日期：2026-08-06
- 内容：document_retire_audit 9,578 行（全部 2026-08-01，created_by=phase-15.6 / phase-15.6-governance，原因："59-byte placeholder stub (never downloaded); superseded by real cninfo download" 与 "legacy sidecar lacks source_url"）。但 documents.source_status 中仅 2 份 retired，**9,576 份仍 active**；document_restore_audit = 0 行。24,689,660 条 span（95%）属于审计文档。审计文档的源几乎都是真实 PDF（100KB–5MB 8,118 份、>5MB 920 份、≤200B stub 79 份）。
- 影响：状态不一致 + 软删除永不物理回收 → 证据只增不减的核心证据；需对账治理（Phase 1）。

## 发现 7：retire_document 是软删除，永不物理删除
- 日期：2026-08-06
- 内容：store.py `retire_document`（Phase 15.5）只 UPDATE documents.source_status='retired' + locations.location_status='retired' + 写 audit；"Nothing is physically deleted"。evidence_spans 不在 retire 范围内；normalizer 只在重解析该文档时 DELETE 其 span；focus_cleanup 只清理孤儿（无任何引用且 source_status 为 quarantined/incomplete 的文档）。
- 影响：退役数据无归档、无回收机制 → 需要 Phase 2 生命周期设计。

## 发现 8：归一化进度 2,702/23,564 → 数据库还会继续膨胀
- 日期：2026-08-06
- 内容：document_fingerprint_state：completed 2,702 / pending 20,728 / unsupported_terminal 127 / failed_terminal 5 / retryable_failed 1；normalizer_version 全部 1.0.0（无版本叠加）。normalize worker 当日 13:19 起运行（PID 19760，operation.lock 持有）。
- 影响：若全部按现状粒度归一化，DB 将远超 44 GB（粗估 100 GB+）→ 容量治理是刚需。

## 发现 9：pending 语料构成（实测）
- 日期：2026-08-06
- 内容：pending 20,728 = regulatory_filing 8,324 / broker_research 5,864 / investor_relations 3,312 / other 2,323 / original_news 903。completed 2,702 中 prospectus 204 已完成、original_news 仅 104。
- 影响：新闻类（original_news 903 pending）不适合单元格级证据 → Phase 4 分级策略。

## 发现 10：没有传统意义的"垃圾叠加"
- 日期：2026-08-06
- 内容：UNIQUE(source_id, locator) 防重复；normalizer 重解析前 DELETE 该文档旧 span（替换语义）；无孤儿 span（LEFT JOIN documents = 0）；无旧 normalizer 版本残留；sources 无 blob。
- 影响：结论修正——空间问题来自"粒度 + 冗余 + 软删除不回收 + 归一化未完成"，而非重复文件堆积。

## 发现 11：可配置性与部署约束
- 日期：2026-08-06
- 内容：`config/source_catalog.yaml` 中 `catalog_dir: "${PROJECT_ROOT}/.source_catalog"`（可配置，支持 ${PROJECT_ROOT}/${USER_PROFILE} 变量）；D: 现余 71.8 GB，仅够现状 DB 一次搬迁，容不下现状粒度全量增长。
- 影响：迁移可行但必须治理先行（Phase 5 前置 Phase 1–4）。

## 发现 12：杂项
- 日期：2026-08-06
- 内容：company-wiki 根目录存在 Windows 保留名文件 `nul`（可用 \\?\ 前缀删除）；.source_catalog 根有 100+ 个 worker_stdout/stderr 小日志（0 GB，量多）；artifacts 表 959 行 status 为空字符串（疑似中断残留）；`document_fingerprint_state` 中 3,735,837 条 span 属于非 completed 文档（pending 文档有早期解析残留，需在 Phase 1 对账中核查）。
- 影响：次要清理项，纳入 Phase 1/6 处理。
