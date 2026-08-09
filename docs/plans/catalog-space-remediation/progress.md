# 进度日志（catalog 空间治理）

> **2026-08-09 状态：`completed_historical_scope_with_transferred_monitoring`。** Phase 1–4 与 ADR/工具收尾完成；Phase 5 因 D4 取消；长期健康/SLO/容量观察转 FCAP r2，不再从本日志维护旧 pending。

## 2026-08-06（规划日，未实施任何治理写操作）
- 完成：G:/C: 空间排查，确认 G: 为 C: 镜像、云配额正常（发现 1–2）
- 完成：opencode 快照成因调查（内部 git 仓库 + 中断残留，发现 3）
- 完成：用户确认后删除 opencode 会话快照 d9d2f124（127.5 GB）
- 完成：用户确认后清理 .source_catalog 旧备份 11.9 GB + company-wiki-backups 24.3 GB + 缓存 ~12.3 GB（uv/npm/pip/Temp）；C: 剩余 0.18 → 164.5 GB；G: 同步 156.2 GB
- 完成：catalog.sqlite3 深度分析（发现 4–10）：43.9 GB 构成、95% span 归属 phase-15.6 审计文档、软删除不回收、归一化仅 11%、pending 构成
- 完成：确认安全网（D: 7/31 catalog 备份 19.33 GB 有效）
- 完成：按 planning-with-files 技能创建 task_plan.md / findings.md / progress.md（docs/plans/catalog-space-remediation/，未覆盖根目录同名旧规划文件）
- 未做（等待用户决策）：任何 Phase 1–6 写操作；D1–D5 决策项
- 问题记录：PowerShell 内联引号导致多次转义失败（改脚本文件解决）；sqlite3 CLI 无 dbstat 虚拟表（改抽样估算）；25.8M 行 GROUP BY 查询耗时 >3 分钟（改轻量查询）
- 下一步：等待用户对 task_plan.md 的评审与 D1–D5 决策；Phase 1.1 只读对账可在确认后随时启动

## 2026-08-06 Phase 1.1 只读四路对账完成（9,578 份审计文档）

### 对账矩阵结果
| 分类 | 数量 | 证据占用 | 说明 |
|---|---|---|---|
| A 真正 retired | 2 | 少量 | 已退役（source_status=retired） |
| B 审计但 active | 9,576 | **25,425,840 span ≈ 29.5 GB** | 其中 1,686 有 span / 7,890 无 span |
| C stub（byte_size≤200） | 79 | ≈0 | 59-byte placeholder，从未下载，可物理删 |
| D 无 span | 7,892 | 0 | 仅需状态修正 |
| 磁盘 | active locations 21,614 / 缺失 6 | | 本地盘(C:/D:)抽样正常；G:/网络盘路径未逐个 stat（虚拟盘慢） |

### 关键结论
- 可回收 ≈ **29.5 GB**（B 类退役）——比 task_plan 预估 20-30 GB 偏高。空间大头 = 25.4M span 行（95% 挂 audit 文档）。
- 分类优先级：C 类（79 stub）物理删零成本；D 类（7,892）状态修正零成本；B 类（9,576）退役是主回收项（有 span 的 1,686 份退役前需 Phase 2 归档）。
- 对账脚本 `_reconcile_audit.py`（临时）已删；结果本段为 record。
- 待用户 D1–D5 决策后进 Phase 1.2（修复脚本 reconcile_retire_state.py）。

## 2026-08-07 Phase 1.2 实施完成（用户 D1–D5 已拍板）

- 决策：**D1=全部正式退役 / D3=新闻免 span / D4=不迁 D: / D5=归档保留 90 天**。
- 新脚本 `src/company_wiki/source_catalog/reconcile_retire_state.py`（dry-run 默认 + `--apply` 显式 + receipt `artifacts/gates/*.jsonl` + 验收对账归零）+ cli 子命令 `reconcile-retire` + 3 项测试（dry-run 分类 / apply 退役+stub 删 / 幂等）。
- **生产 apply（2026-08-07T08:08Z）**：退役 **9,499** + stub 物理删 **77**（79 中 2 个已 retired）+ **mismatch 归零**（验收 dry-run=0）。receipt：`.source_catalog/artifacts/gates/reconcile-retire-20260807T080844Z.jsonl`。
- 软删除不碰 span：**29.5GB 证据保留**（90 天窗口内完整可查）；Phase 2.1 归档随后（在 90 天回收前完成）。

## 2026-08-07 Phase 2.1 归档完成
- `archive_retired_evidence.py`（src/company_wiki/source_catalog/）：streaming 导出 retired 文档 evidence_spans → gzip JSONL（`source_manifests/archive/{date}/retired-evidence.jsonl.gz`），keyset pagination（span_id 分批 10 万行），只读连接不取锁（retired 文档不重 normalize，span 稳定）。
- cli 子命令 `archive-retired-evidence`；2 项测试（行数对账 / 空库）。
- **生产导出（2026-08-07T10:15Z）**：`rows_written=25,708,956 == rows_in_catalog=25,708,956`，**ok=true**（归档完整，零丢失）。产物 4.6GB gzip（≈30GB 原始压缩至 ~15%）。
- 剩余：Phase 2.2 生命周期（archived_at schema 提案）/ 2.3 定期回收（90 天）/ 3 粒度提案（D2 待拍板）/ 4 容量模型 / 6 验收 ADR。

## 2026-08-07 Phase 2.3 / 3 / 4 / 6 完成（catalog 治理收尾）
- **Phase 2.3** `prune_retired_evidence.py`（cli `prune-retired-evidence`，dry-run 默认 + `--apply` + 保留期判断 + 分批删 + receipt）。生产 dry-run：retired 9,501 / span 25.7M / oldest 2026-08-07 / **due=false**（90 天窗口未到期，正确拒绝回收）。3 测试。
- **Phase 3** `granularity-proposal.md`（表格级粒度 + 新闻免 span，D2/D3 决策，供上游评审）。
- **Phase 4** `catalog_size_report.py`（cli `size-report`，只读容量/健康报告 + 30GB 告警阈值）。生产：DB **49.27GB** / pages 12.03M / spans 27.0M / docs 23,488 / retired 9,501 / disk_free 173.1GB / 无告警。2 测试。
- **Phase 6** `ADR-009-catalog-space-governance.md`（D1–D5 决策留档 + Phase 1–2 实施记录 + 不变量）。
- 生产 DB 已从 43.9GB 涨至 49.27GB（worker 持续 normalize 新增 span，符合预期；治理后 90 天窗口到期可回收 retired 25.7M 行）。
