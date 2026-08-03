# 上游来源系统运维命令

> 本文档记录 company-wiki 作为 StockWiki 上游来源系统可执行的运维命令。
> 2026-07-16 起只允许采集、immutable raw 校验、规范化/解析、EvidenceSpan、索引和只读 export；不得运行生成投资结论、估值、研究 Wiki 或正式报告的任务。

## 运行边界

- legacy writer freeze 保持启用；没有明确迁移 Work Unit 与审核回执时，禁止运行任何研究型 writer。
- company-wiki 不写 StockWiki 的目录或数据库；跨仓交付只能使用版本化只读 export。
- 生产调度目标顺序为 `collect → normalize → parse → index → export`。当前缺失的 canonical 命令须等待 CW-1/CW-2 实现，不得用 legacy `assess`、`consolidate`、`judgment` 步骤代替。
- 所有真实运行前先做只读参数/目标检查；命令提供 `--dry-run` 时必须先使用。create-once collector 通过官方域名、内容门禁、目标预检和幂等复跑验收，原始资料删除或改写必须 fail closed。

---

## 零、Announcement Collector v1（create-once）

```bash
python -m company_wiki.source_contract.announcement_cli \
  --root . \
  --company 中微公司 \
  --entity-id SSE:688012 \
  --url https://star.sse.com.cn/.../announcement.pdf \
  --title 关于召开2025年度业绩说明会的公告 \
  --published-date 2026-03-25
```

命令只接受显式 SSE/SZSE 官方 HTTPS URL，并在每次 redirect 前重新校验域名；响应必须通过 PDF MIME、magic、EOF 和最大字节门禁。成功后创建 content-addressed raw、`source_manifests` 与 `source_provenance`，stdout 输出一行 canonical receipt。既有文件只校验不改写，冲突返回 exit code 2。详见 [Announcement Collector v1](contracts/announcement-collector-v1.md)。

该 collector 是 canonical source 的首次创建入口，不调用 `scripts/source_policy.py` 所保护的 legacy/general writer，也不解冻 legacy Wiki writer。采集仍保持单线程，不允许 `--parallel`、daemon、LLM 或 StockWiki 写入。

---

## 零点二五、Canonical IngestService v1（只读）

collector 已创建 raw/manifest，且 parser 已产出结构化结果后，通过 Python API 接入：

```python
from pathlib import Path

from company_wiki.ingest import IngestService, ParserResult
from company_wiki.source_contract import EvidenceCoordinates, ParseStatus

parser_result = ParserResult(
    source_id=manifest.source_id,
    coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
    raw_text="原文……",
    structured_value=None,
    parser_name="pdf_parser",
    parser_version="1.0.0",
    parse_status=ParseStatus.PARSED,
    quality_flags=(),
)
bundle = IngestService(root=Path(".")).ingest(
    manifest=manifest,
    parser_results=(parser_result,),
)
```

服务会重新校验 raw 的 path/size/SHA-256，拒绝跨 source parser result 和同 locator 冲突，并返回确定性 export bundle。它没有写权限；不得把 `LegacyResearchIngestService`、`scripts/ingest_v2.py` 或 `stage5_ingest.py` 接到 canonical 调度。公告 receipt 使用 `ingest_announcement()`。详见 [Canonical IngestService v1](contracts/ingest-service-v1.md)。

---

## 零点五、Source Export v1（只读）

```bash
python -m company_wiki.source_contract.cli export \
  --root . \
  --manifests manifests.jsonl \
  --spans evidence-spans.jsonl
```

命令只读取 raw、JSONL 和可选 `--base`，成功时向 stdout 输出一行 canonical JSON，失败时 stdout 为空并返回 exit code 2。CLI 不提供 `--output`，若需持久化，外层 consumer 必须自行负责临时文件、fsync 和 atomic replace；不得把输出路径指向 StockWiki 的可变状态目录。

当前 CW-1 已提供 export 验证与合并层；manifest/span 从 legacy ingest 自动生成的生产接线仍等待 CW-2。

consumer 读取 export 前应先校验并固定 compatibility policy：

```python
from company_wiki.source_contract import (
    SOURCE_CONTRACT_NAMES,
    compatibility_policy_sha256,
    negotiate_contract_versions,
)

consumer_support = {name: ["1.0.0"] for name in SOURCE_CONTRACT_NAMES}
negotiated = negotiate_contract_versions(consumer_support)
policy_sha256 = compatibility_policy_sha256()
```

协商必须同时覆盖 manifest/span/export，并且只能选择 policy 的 `compatible_version_sets` 已发布组合；不存在完整精确共同版本即整体失败。兼容窗口、180 天通知期、后续两个 minor 的保留承诺及 `deprecation_notices` 字段见 [Source Contract Compatibility Policy v1](contracts/source-contract-compatibility-v1.md)。

---

## 一、上市公司文档下载（财报/公告/投资者关系）

> 本节是 StockInfoDLSimple 的 legacy 兼容说明，不是 canonical announcement 入口；公告必须使用上方 create-once collector。legacy writer freeze 未解除时不得以本节命令绕过边界，其中并行参数也不适用于 canonical 单线程采集链。

**工具**: StockInfoDLSimple v2-clean-rewrite
**频率**: 每周一次（或每季度财报季加密）
**前置条件**: Windows 环境 + Playwright 已安装

### 命令

```bash
# 下载全部 205 家 A 股公司（约 2-4 小时）
python scripts/run_downloader.py --tier all --parallel --workers 3

# 只下载 Tier 1 核心公司（35家，约 30-60 分钟）
python scripts/run_downloader.py --tier tier1 --parallel --workers 3

# 强制重新下载（清除进度）
python scripts/run_downloader.py --tier tier1 --clean --parallel --workers 3

# 只下载特定公司
python scripts/run_downloader.py --company 东方电缆
```

### 配置
- 公司列表: `a_share_companies.txt`（205 家 A 股）
- 下载配置: `config_template.json`（原始版本，未修改）
- 下载路径: `companies/{公司名}/raw/{类型}/`

### 下载内容
| 类型 | 后缀 | 保存路径 |
|------|------|----------|
| 招股说明书 | `latestAnnouncement` | `raw/prospectus/` |
| 定期报告 | `periodicReports` | `raw/financial_reports/` |
| 投资者关系 | `research` | `raw/research/` |

---

## 一点五、portfolio 提升为可复用来源（import-portfolio）

> dayu-agent `workspace/portfolio` 下的财报已被 source_catalog 扫描索引（`dayu_portfolio` root，
> 只读检索用），但 filing-fetch 的复用管线只认 `companies/` 子树（`company_raw`）。为避免重复下载，
> 先用本命令把已索引的 portfolio 文档**提升**为规范来源（拷贝进 `companies/{entity}/raw/` + 不可变
> `.source.json`）。设计见 `docs/adr/ADR-007-portfolio-promotion.md`。

```bash
# 单条提升（按 portfolio 文档 id）
python -m company_wiki.source_catalog.cli import-portfolio \
  --company-query "金山云" --market HK --document-id fil_cn_48ec0d41eb244001f0f3795438c351495c196ada

# 批量提升某公司全部 portfolio 财报（幂等：已提升的返回 deduplicated）
python -m company_wiki.source_catalog.cli import-portfolio \
  --company-query "金山云" --market HK --all

# 按年度/类型筛选；--dry-run 只预览不写盘
python -m company_wiki.source_catalog.cli import-portfolio \
  --company-query "金山云" --market HK --fiscal-year 2025 --document-kind annual_report --dry-run
```

- 身份（market/security_id）由 SecurityIdentityResolver 归一化（如 HK 3896 → 03896），
  与 filing-fetch 同源，保证复用精确匹配。
- 提升后 `filing-fetch`（revenue-forecast / invest-* / industry-research）只读请求即返回
  `capture_ready`，不再下载。
- 回滚：删除 `companies/{entity}/raw/` 下对应文件 + `.source.json` 并重扫即可，不影响 portfolio 原件。

---

## 二、新闻采集

**工具**: `scripts/collect_news.py`（Tavily API）
**频率**: 待改进（当前 daily，建议改为按 Tier 分级）
**API Key**: `TAVILY_API_KEY` 环境变量

### 当前命令

```bash
# 采集所有公司（当前每天运行，产生大量重复/垃圾）
python scripts/collect_news.py

# 只采集指定公司
python scripts/collect_news.py --company 中微公司

# 限制每轮最多 N 家公司（均衡覆盖）
python scripts/collect_news.py --max-companies 30

# 只打印不保存（测试用）
python scripts/collect_news.py --dry-run
```

### 已知问题
1. **查询太泛**: `"{公司名} 最新消息"` + 问题驱动搜索 → 每家公司 6+ 个查询
2. **无内容过滤**: 股吧、Yahoo 导航页、空页面等垃圾内容入库
3. **频率过高**: daily × 241 家 = 海量新闻，交叉污染 3,886 条
4. **质量低**: 正文 < 100 字、标题 = 公司名（官网首页）等未过滤

### 改进方向（见下方"新闻采集改进方案"）
- 精简查询：每家公司 1 个精准查询
- 加强过滤：URL 黑名单、正文长度 ≥ 300 字、标题语义过滤
- 降低频率：Tier 1 每 3 天、Tier 2 每周、Tier 3 每月
- 按轮询采集：每轮只采最久未更新的 30 家

---

## 三、数据处理（Ingest）

**工具**: `scripts/ingest_v2.py`
**频率**: 每次下载/采集后手动触发，或 scheduler 自动运行
**前置条件**: 需修复 `pdf_extract_v2.py:248` 的 classify_pdf bug

> `ingest_v2.py` 是 legacy 兼容入口，受 writer freeze 保护，不是 CW-2 的 canonical IngestService。未建立隔离 Work Unit 时禁止运行其写入模式；以下命令仅保留作迁移参考。

```bash
# 处理所有公司的新文件
python scripts/ingest_v2.py

# 只处理指定公司
python scripts/ingest_v2.py --company 东方电缆

# 从 Layer 3 标签库取料（未来模式）
python scripts/ingest_v2.py --source segments
```

---

## 四、Legacy Wiki 质量维护（禁止写入）

**工具**: `scripts/maintenance.py`
**状态**: 冻结

禁止运行完整维护、清理或 LLM 富化模式；它们会操作 legacy Wiki/派生研究内容。只读报告模式也必须先证明零写入，并在隔离 Work Unit 内执行。新的质量门只评估 source identity、hash、locator、parser regression 和 extraction quality。

---

## 五、健康检查

**工具**: `scripts/lint.py`
**频率**: 每周一次

```bash
# 检查矛盾、孤儿页面、过时信息、断链
python scripts/lint.py

# legacy 自动修复会写 Wiki，当前禁止运行
```

---

## 六、Scheduler 自动调度（保持禁用）

旧 scheduler 含 `assess`、`consolidate`、`judgment` 等研究型步骤，禁止运行或配置为定时任务。CW-2 之后的 production scheduler 只能调度 `collect → normalize → parse → index → export`，并继续服从 writer freeze、预算和可恢复状态门禁。

---

## 七、建议的定时任务配置

### Windows 任务计划程序

**任务 1: 财报下载（每周六凌晨）**
- 程序: `python.exe`
- 参数: `scripts/run_downloader.py --tier tier1 --parallel --workers 3`
- 工作目录: `C:\Users\郑曾波\Projects\company-wiki`

**任务 2: 新闻采集（改进后，Tier 1 每 3 天）**
- 待改进后配置

**任务 3: 上游解析与 export**
- 状态: Source Export v1 CLI 已完成；等待 CW-2 canonical ingest/parse 接线后再配置自动任务
- 禁止: 用 legacy maintenance/scheduler 代替

---

## 八、手动检查清单（每周）

- [ ] 运行 `python scripts/run_downloader.py --tier tier1 --dry-run` 检查公司列表
- [ ] 查看 `log.md` 确认上周采集/ingest 无异常
- [ ] 核对新增 raw 的 SHA-256、source identity、MIME、size 与采集时间
- [ ] 检查 orphan span、locator drift、hash mismatch 与 parser regression
- [ ] 验证 export 只读、可重复，且不含评级、估值或 accepted investment conclusion
- [ ] 确认 Git index、StockWiki 路径和生产原始资料无意外写入
- [ ] 核对 `.source_catalog` 备份：按「九、备份与保留策略」执行一次 `VACUUM INTO` 备份并记录 sha256，检查备份保留份数 ≤ 3

---

## 九、.source_catalog 备份与保留策略（2026-07-31 新增，Phase 15.1）

### 备份方式

- 用 SQLite `VACUUM INTO` 对 `catalog.sqlite3` 做一致性快照备份。**不要用 `cp` 直接拷贝活动库**——worker 写入期间 `cp` 会得到不一致副本（2026-07-31 曾因磁盘满留下 4.1GB 半成品）。
- 备份目标：`D:\company-wiki-backups\`（与主库不同盘；C: 余量不足以容纳 20G+ 的库）。
- 命令示例：

```powershell
python - <<'EOF'
import sqlite3, datetime, os
os.makedirs(r"D:\company-wiki-backups", exist_ok=True)
stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
src = r"C:\Users\郑曾波\Projects\company-wiki\.source_catalog\catalog.sqlite3"
dst = r"D:\company-wiki-backups\catalog.sqlite3.vacuum-" + stamp
sqlite3.connect(src).execute("VACUUM INTO '%s'" % dst.replace("\\", "/"))
print("dst:", dst, "size:", os.path.getsize(dst))
EOF
```

- 完成后记录产物大小与 sha256（`Get-FileHash` 或 python hashlib），作为可校验证据。
- 备份耗时参考：2026-07-31 实测 20.7GB 备份约 460 秒（D: 机械盘量级）。

### 保留策略

- 保留最近 **3** 份备份，超出部分删除（删除前确认不是恢复点）。
- 备份前置磁盘余量检查：
  - 源盘（C:）余量 < 15GB 时禁止备份（20G 库 + 缓冲）；
  - 目标盘（D:）余量 < 25GB 时禁止备份并告警。
- **磁盘余量 < 10% 时 worker 暂停写入**，恢复条件：余量回到 ≥ 15%。当前为人工执行（worker 自动化列入远期项）。

### 禁止事项

- 不允许把备份放在 `.source_catalog` 主库同目录（上次磁盘写满的根因之一）。
- 不允许删除最新恢复点之前的所有历史备份（保留 3 份内至少要留 1 份已验证可恢复的）。

---

## 十、文档治理：documents retire（2026-08-01 新增，Phase 15.5）

对 catalog 中的文档做**软删除**（转 `retired`），不物理删除任何行。用于清理占位文档、错误摄入等，同时保留审计。

```powershell
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml `
  documents retire --document-id urn:company-wiki:document:sha256:... --reason placeholder-cleanup
# 可选 --created-by <actor>（默认 "cli"）
```

行为：

- 文档与全部 location 转 `source_status`/`location_status = "retired"`；
- 写入审计表 `document_retire_audit`（audit_id / document_id / reason / created_by / created_at），可逆查询：

```sql
SELECT * FROM document_retire_audit WHERE document_id = '<document-id>';
```

- retired 文档对默认查询与 resolver 不可见（复用/下载不受其干扰）；显式 `query --source-status retired`（或 `query(source_status="retired")`）仍可查看；
- 未知 document-id 报错且零写入（无部分删除）。

历史遗留：2026-07-31 紫金会话前清理占位文档使用裸 SQL 删除；此后一律使用本命令。

---

## 十一、worker 版本管理与治理操作协议（2026-08-01 新增，Phase 16.3）

### worker 代码版本

- `worker_runtime.json` 的 `code_version` 字段 = worker 进程加载代码时的 git short commit（Phase 16.3 起）。
- **代码变更后必须重启 worker**：`worker-stop` →（确认 `runtime_state: stopped`）→ `worker-start` → 检查 `worker_runtime.json` 的 `code_version` 等于当前 `git rev-parse --short HEAD`。
- 长进程不热更新代码：旧进程会继续用启动时的代码（曾导致 F13 治理被旧 scanner 静默撤销）。

### 治理操作协议（防撤销）

任何批量数据治理（retire/restore/注入/删除）必须按序执行：

1. `worker-stop`（杀 worker 与 launcher）；
2. 确认无残留 launcher：`worker_launcher.lock` 不存在；如有残留 `taskkill /F /PID <pid>`；
3. 执行治理操作（写入审计，created_by/reason）；
4. `worker-start`（新代码）；
5. **立即重扫受影响 root 并验证**（治理目标计数门）。

禁止在 worker 运行中直接改 catalog 状态后不重扫验证——扫描会按摄入逻辑重写状态。

### 故障排查

- worker 启动失败 `worker_exited_clean_before_writing_runtime`：查 `worker_process_events.jsonl` 的 `unhandled_exception` 与 `worker_launcher_events.jsonl` 的 exit_code；旧 launcher 持锁时先 `taskkill`。

---

## 十二、documents restore（2026-08-01 新增，Phase 16.6）

`retire` 的对称反向操作：把 retired 文档与 locations 转回 active，写 `document_restore_audit`（与 retire 审计对称），不物理删除。

```powershell
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml `
  documents restore --document-id urn:company-wiki:document:sha256:... --reason correction --created-by <actor>
```

- 仅 retired 文档可 restore（active 文档 restore 报错且零写入）。
- 治理工具化：批量恢复一律调用 `store.restore_document`（带 created_by/reason），禁止裸 SQL。

---

## 十二、测试 fixture 约定与契约变更影响面清单（2026-08-01 新增，Phase 16.10）

### fixture 工厂

- `tests/helpers/source_factory.py` 提供 `canonical_source()` 与 `company_raw_catalog()`：
  - **默认生成完整 capture-ready sidecar**（market/security_id/source_title/https source_url）——新测试一律使用，复用路径开箱可用；
  - 需要"缺 URL / 缺身份"场景时**显式**传 `drop_url=True` 或 `market=None`——缺失是显式异常，不是默认；
  - 需要 dayu portfolio 或复杂 multi-root 场景时仍可手写 fixture，但 company_raw 基础文档一律走工厂。
- 目的：契约变更（如 16.2 的 capture_ready 复用门）不再靠"测试逐个爆红再补"传播，而是让默认 fixture 始终代表最新契约。

### 契约变更影响面清单（变更 resolver/摄入语义前必做）

1. grep 所有 `.source.json` 写入点与 sidecar 内容假设：`grep -rn "source.json" tests/contract/`；
2. grep 复用断言：`grep -rn "REUSED\|capture_ready\|resolver" tests/contract/`；
3. 列出受影响测试文件，一次性迁移到工厂（或显式 `drop_url`/`market=None`），并在同一提交内完成；
4. 全量测试必须一次全绿，禁止"改一行跑一次等爆红"。

### worker 依赖注入

- `SourceCatalogWorker.__init__` 接收 `project_root`（CLI 传入）；worker 内部不得依赖 `catalog.config` 内部结构（调度门禁测试强制）。

## 十三、身份断言与发行人归一协议（2026-08-02 新增，Phase 18）

### 身份断言（identity-enrichment）何时使用

- 旧摄入文档缺 `market`/`security_id` 且无法从 sidecar 或 security_master 补全时，用 assertions 显式核对身份（`preview_assertion` → `verify_assertion`）。
- 断言只回答"该文档属于哪个发行人"；不构成任何投资结论（`verified` 仅表示来源身份/抽取质量通过）。

### 更正流程（supersedes 链，Phase 18.2）

- 对同一 (source, document, content) 已有 verified 时，verify 新候选会**自动 supersede**（链式），查询返回最新一条——纠正错误断言的正确方式 = 再 verify 一条新候选，**不是 reject**（reject 只接受 candidate）。
- 同一证据键（source/document/content）多条 active verified 解析到最新（含 Phase 18.2 前的历史损坏行，如 Alphabet GOOGL/GOOG 双 verified）；不同证据键仍视为冲突（fail-closed，返回 None）。

### 发行人归一（issuer anchoring，Phase 18.1）

- 请求 ticker 经 security_master `canonical_name` 锚定到发行人：双类股（GOOGL/GOOG/GOOGM/GOOGN → "Alphabet Inc."）任意 ticker 互查命中同一文档；别名（如 "Alphabet"）同样命中。
- 市场过滤仍严格（`_identity_matches`）：CN 请求只命中 CN 文档；跨市场同发行人不误共享（如 601899/02899、9988/BABA）。
- security_master 中跨 issuer 共享的 token 不锚定（fail-closed），防止泛化别名误匹配。

### 排查（resolve 诊断，Phase 19.6）

- resolve 响应的 `debug_trace`（非空时）列出逐候选排除原因（`entity_gate_rejected: N` 计数 + identity/year/form/capture 各步），filing-fetch `--debug` 透传；`not_found` 时一次给出原因链。
