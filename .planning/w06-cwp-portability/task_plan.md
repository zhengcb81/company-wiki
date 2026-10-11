# W06-CWP-PORTABILITY 虚拟存储根迁移回归工具

Goal: 独立、离线、多根迁移与引用回放套件（tools/source_root_portability/），检验"公司/Dayu/Dropbox路径属于存储细节、上层只用一个来源湖"的抽象。工具正确 + 报告准确即范围完成；发现缺陷只写最小重放证据，不改 src 存储层。

工作目录: C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-portability（分支 codex/w06-cwp-portability，基线 01ea86a37edb5506d6269b6e10d9cb56a1270efd）
排他写集: tools/source_root_portability/、tests/unit/test_w06_root_portability_oracle.py、tests/integration/test_w06_root_portability.py、.planning/w06-cwp-portability/、docs/handoffs/w06-cwp-portability/（input/ 只读）。src/scripts/config/现有tests/CI 全只读。

## Next Step
Phase 6：交接件（handoff.json/handoff.md/manifest.json）+ 两次普通 commit（代码、交接件）。

### Phase 1 — 实读真实公开 API/CLI（完成）
- Status: complete
- 结论见 findings.md F1-F12。真实方法：query_ref / query_local / describe_version / open_version(ref, purpose=...) / verify_version / open_described_version；source_id=urn前缀+contentSHA、document_id 由 source_id（内容SHA）派生；register_sources(root_id, relative_paths) 精确登记；导出 source_export_v2_cli（stdin JSON→SourceExportBundleV2，无路径）；source_reader_cli 是字节+receipt 通道。

### Phase 2 — PWF 计划文件（完成）
- Status: complete

### Phase 3 — 阶段A：oracle 反例 RED（完成）
- Status: complete
- oracle stub（全放行）+ 22 反例/契约测试 → RED：19 failed, 3 passed（logs/red-oracle.log）。
  反例类：漏 reopen（旧buffer/同进程）、SHA只核metadata/假receipt跳reader、消费者偷开rawPath、
  移根造假日期/非周期假FY、物理dup当逻辑来源、无policy观察、清理越界/丢sentinel、改写fixed expected、
  UNKNOWN混入same-ID通过、畸形记录→INVALID_RECORD（不算产品漏洞）、HTTP≠0。

### Phase 4 — 阶段B：工具/fixture 实现 + 单元与短集成 GREEN（完成）
- Status: complete
- 实现 oracle 真判定 + fixture_builder（4 synthetic 原件/≤6，3 根含空格/中文）+ scenarios + consumer_spy（审计钩子+栈归属）+ run.py + report.py。
- 33 passed（logs/green-unit-integration-final.log；含真 SourceVersionReader+临时catalog、跨进程 spy、sentinel 清理）。
- 过程修复：审计钩子递归（linecache）→ 纯帧遍历+重入保护；归属判定先查 company_wiki 帧；
  日志只记 raw/catalog 类；非周期 sidecar 用 nonperiodic 标记（findings F14）。

### Phase 5 — 阶段C：完整手动 runner E2E（完成）
- Status: complete
- attempt-0003：7 场景全 PASS、oracle overall PASS、exit 0、elapsed 7.4s ≤120s；
  source_read_calls 51（in-process 47 + 子进程 4）、HTTP 0；owned root 清理恢复 absent 基线；
  报告 29KB。历史 attempt-0001（oracle 抓到 S4 记录缺字段→FAIL）/0002 保留不覆写。
- 产物：logs/e2e-runner*.log + e2e/attempt-0003-report.json。

### Phase 6 — 交接与普通 commit
- Status: in_progress
- handoff.json（w06-lane-handoff/1）+ handoff.md + manifest.json + RED/GREEN/E2E 日志 + ROOT fix 建议；
  正常 commit（不 force/跳 hooks/不推主线）。

## Decisions Made
- root_id 用 local_company / external_dayu / external_dropbox（ROOT 接口补充：斜杠只属于目录路径，不把 local/company 抄成 ID）。
- 真实公开方法按补充锁定 open_version(ref, purpose=...)；verify_version 只给 receipt；没有 open_verified。
- 订阅 open 用 purpose="source_export"（避开 filing_reuse 的 SEC issuer scope 鉴定），fixture 不带 SEC 标记（provider=example-filing）。
- fixture 用 sidecar `.source.json` + adapter sidecar_filing_v1 显式 document_kind/固定日期；根配置加 routes include ["*"] 使 sidecar 走配对分支（role=metadata），不各自注册成独立文档。
- source_id/document_id 由内容 SHA 派生 → same-bytes 迁移天然 same-ID；S3 跨根/改 relative_path 记录实际 revision 关系，不预设 document_id 永不变。
- 场景失败报 PARTIAL+固定期望，不假改 expected；需要 ROOT 决定的 identity 稳定性标 UNKNOWN。
- 运行/测试时 PYTHONPATH 显式绑 worktree src，报告记录实际 company_wiki.__file__ 与模块 SHA（防 editable fallback 跑到主仓代码）。

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| （暂无） | | |
