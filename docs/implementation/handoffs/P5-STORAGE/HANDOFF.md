# P5-STORAGE HANDOFF — 旧派生与数据库降容执行工具

lane_id: `P5-STORAGE` · branch: `codex/p5-storage-retirement`（基线 `a2563f9`，包含发布基线 `f775406`）· delivery_head: `7ac1e3d` · date: 2026-10-05

## 交付物

- `tools/legacy_storage_retirement.py` — 统一薄 CLI（argparse，SubParsers）
- `tools/legacy_storage/` — core / selection / inventory / retirement / spans / shrink / facts 模块
- `tests/unit/test_p5_storage_retirement{,_common,_spans,_vacuum}*.py`（26 项）
- `tests/integration/test_p5_storage_retirement_e2e.py`（真实原文链路，`-m slow` opt-in，不进日常 CI 强门）
- `.planning/p5-storage-retirement/{task_plan,progress}.md`
- `samples/`：小型示例 manifest + 三份 mutating 收据（全为隔离 fixture 实测值）

## 入口（精确命令）

```text
python tools/legacy_storage_retirement.py inventory --config <catalog cfg> --output <manifest>
python tools/legacy_storage_retirement.py retire-derived --config <catalog cfg> --manifest <manifest> --receipt <report> --apply
python tools/legacy_storage_retirement.py prune-spans --config <catalog cfg> --selection <sel.json> --keep-refs <refs.jsonl> --receipt <report> --apply
python tools/legacy_storage_retirement.py vacuum --config <catalog cfg> --receipt <report> --apply
```

不传 `--apply` 时 mutating 操作一律 dry-run（收据 `dry_run=true`）；inventory 恒为只读。报告 schema 固定 `cwp-storage-retirement/1`，全部字段见 `samples/sample_*_receipt.json`。

## 隔离 fixture 实测（build_catalog：真实 schema + 真实 normalizer/extractive summary/section extractor + 新 narrative final）

| operation | deleted | already_absent | files_before→after | db bytes | page/freelist |
|---|---|---|---|---|---|
| inventory | — | — | 8131 B（8 files） | 282624 B | 69 / 0 |
| retire-derived | 8 条（4 DB 行 + 3 section .md managed + sections/index.json） | 0 | 8131 → 0 B | 282624 B（不变） | 69 / 0 |
| prune-spans | 9 spans（keep-ref 1 条存活） | 1 | db file 不变 | 不变 | 69 → freelist 4 |
| vacuum | — | — | — | 282624 → 266240 B | 69→65 / freelist 4→0 |

全部 `integrity_check=ok`、`foreign_key_check=[]`、`source_facts_before == source_facts_after`（17 张事实/保护表 count+digest 全等，evidence_spans/artifacts 之外零变化）。

## 真实原文 E2E（tests/integration/...，0 网络调用）

- 拷贝中微公司2025年年度报告（SHA-256 `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`，只读复制）+ 本地 TXT 转写样本进独立短根；真实 scan / normalize（`pdf_page_aware_core` spans）/ summary / sections。
- 新 final 通过公开 `NarrativeArtifactStore.prepare + activate` graft 到 TXT 文档（真实 `narrative-bundle/2.0`、Replay 离线、本地模型 0 次 LLM API 调用）。
- 顺序执行四操作；`source_reader_cli --purpose source_export` 与 `narrative_transport_cli reference+read` 前后均 exit 0，narrative stdout SHA 前后一致（完整 locator replay 仍通过）。
- 收据要点：prune 删除全部 PDF span（泄漏 0），TXT spans 与 keep-ref 全部存活；vacuum 实测物理释放；artifacts 遗留 completed 旧角色句柄 = 0。

## 测试

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=src python -m pytest tests/unit/test_p5_storage_retirement_boundary.py tests/unit/test_p5_storage_retirement_spans.py tests/unit/test_p5_storage_retirement_vacuum.py` | 26 passed / 61.77s |
| `PYTHONPATH=src python -m pytest tests/contract/test_source_version_reader.py tests/unit/test_narrative_artifact_store.py tests/contract/test_narrative_transport_cli.py tests/integration/test_narrative_transport.py` | 79 passed / 1 failed（pre-existing，见下） |
| `PYTHONPATH=src python -m pytest tests/integration/test_p5_storage_retirement_e2e.py -m slow` | 1 passed / 173.93s |

pre-existing 失败：`test_current_public_producer_regenerates_normalized_txt_golden`（golden `bundle_producer "0.1.0"` vs 代码 `0.3.0`）。已在 MAIN checkout 复跑确认同样失败，与本线新增文件无关（本线零 src/ 改动）。

## 旧 generator/parser 分类（实测 inventory）

- 旧派生角色：`normalized` / `summary`(extractive+llm 同 role) / `sections`（DB 行指向 `sections/index.json`，其 managed_files= 各 `{role}.md`）；`markdown` 为历史兼容别名。
- 旧 generators：`source_catalog_normalizer`、`source_catalog_extractive_summary`、`source_catalog_llm_summary`、`source_catalog_section_extractor`。
- span parsers：markdown/txt=`plain_text`，PDF=`pdf_page_aware_core`(version=fitz.VersionBind)、历史 `dayu_docling`。prune-spans 需显式 selection；未知 parser 自动保留。

## 保守保留与保护

- 事实表逐表 count+digest：catalog_meta/roots/sources/documents/locations/entities/document_entities/source_metadata_assertions/document_fingerprint_state/retire+restore audit/activation_journal/llm_summary_failures/remediation_proposals/producer_events/producer_attempts/migration_*_journal/artifact_bindings/scan_runs；narrative_artifact_versions 当前操作完全不动（保护快照校验）。
- derived 下无 DB 记录的松散文件 → `unreferenced_derived` 报告并保留；`objects/sha256/**` 新 final 永不入候选；原件路径永不入候选。

## 假已执行边界

工具只交付能力；未执行任何生产清理，未删 implies-live 数据，未做全库备份。MAIN 接线项：旧 caller 退休（RF 默认 + CWP 核心正文消费者）、quality/metadata_only 语义、消费者清零后用本工具执行真实 S5/S6 并出总收据。

## 临时 root

pytest basetemp（`%TEMP%` 下短根）开始前不存在、结束后由 pytest 清理（absent→absent）；样本生成脚本亦同样清理。
