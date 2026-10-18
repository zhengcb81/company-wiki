# P4-CONSUMER-CONTRACT — 发现

## CWP 运行时事实（探针实证，read/export 两条路都真跑过）
- `company-wiki-source-read`：raw 字节走 stdout、一行 JSON 收据走 stderr、exit 0；
  `--include-availability-evidence` 产出 schema `2.2` 的 `availability_evidence`，
  合成 sidecar 下为 `null`；错误走 `{"status","reason"}` + exit 2。
- **read 收据的 5 个 roundtrip 字段不在顶层**：顶层是
  `availability_evidence, byte_size, content_sha256, document_id, manifest,
  policy_sha256, read_at, review, schema_version, source_id,
  source_read_policy_sha256, status`，`mime_type` 只在嵌套的 `manifest` 里
  （`manifest` 23 键齐全）。因此 §5.5.1 的 `check_ref_roundtrip` 必须拿
  `read.receipt["manifest"]` 当 receipt 侧，顶层收据只校验 4 个字段。
- `company-wiki-source-export-v2`：stdin 恰为 `{schema_version:"2.0",source_refs,evidence_spans}`；
  stdout 一行 bundle JSON；bundle 键 =
  `bundle_sha256,counts,evidence_span_schema_version,evidence_spans,export_id,manifests,schema_version,source_manifest_schema_version`。
- **EvidenceSpan 是 12 字段严格对象，导出 CLI 拒绝手搓 dict**：`EvidenceSpan.from_dict`
  要求字段**不多不少**（unknown/missing 都抛），且 `span_id`/`output_sha256` 是派生量，
  `locator` 必须等于 `coordinates.locator()` 即 **`loc:v1/chars:37-49`**（不是 `chars:37-49`）。
  手拼 span 会得到 `{"status":"blocked","reason":"invalid_request"}`。
  → lane 侧统一走 `cwp.build_wire_span()` / `cwp.wire_spans()`，用 CWP 自己的
  `EvidenceSpan.create(...).to_dict()` 生成；lane 自己的 span 视图（含 `unit_tokens`）
  另存，不进 wire。
- **`bundle_sha256` 用 `ensure_ascii=False` 哈希**（`source_export_v2._canonical_json`），
  与 INTERFACES §1 规定的 lane 规范形式 `ensure_ascii=True` **不一致**。探针实证：
  同一 bundle `ensure_ascii=True → ce2c6ca7… MISMATCH`、`False → c7f56b68… MATCH`。
  → `cwp.recompute_bundle_sha256()` 必须复刻**生产者**的 `ensure_ascii=False` 才能对上；
  lane 自己写的收据/handoff 仍用 §1 的 `ensure_ascii=True`。已在函数 docstring 注明。
  `export_id == "urn:company-wiki:source-export:sha256:" + bundle_sha256`（已加 `export_id_for`）。
- reader 会**自建** `catalog_dir` 的说法要更正：`ReadOnlyCatalogReader` 对**不存在**的
  数据库路径**拒绝创建**（`"catalog does not exist (not created, not touched)"`）。
  read/export 两个 CLI 都不扫描；`SourceCatalog.__init__` 也不扫描。
  → 必须先跑 **`python -m company_wiki.source_catalog.cli --config <cfg> scan`**
  （`--config` 是全局参数，必须在 `scan` 子命令**之前**：放后面报 `unrecognized arguments`）。
  实证：同一 tmp 副本 export 扫描前 `rc 2 catalog_unavailable`，扫描后 `rc 0`，
  state 目录出现 `catalog.sqlite3` + `operation.lock.acquire`。
  → `cwp.ensure_catalog_state()` 在 session fixture 里对**缺 state 的 catalog** 扫描一次；
  只有我们自己复制出来的 fixture 副本必然缺 state；扫描只写 `config.catalog_dir`（allowed root 内）。
- reader 会**自建** `catalog_dir`（`catalog/state/catalog.sqlite3` + wal + `operation.lock.acquire`）。
  → `p4_catalog_config` 发现 env 指向本卡 `fixtures/` 时，把整个 `catalog/` 目录
  复制到 `tmp_path_factory` 再用（`shutil.copytree(resolved.parent, working)`），
  否则就地读会把 `catalog/state` 写进提交树，违反 card §7 完成定义 4。
  env 已指向 tmp 下的 catalog 则原样使用（ROOT 只读 catalog 场景）。
- `.gitignore` 不忽略 `receipt.json`，也不忽略 `*.sqlite3`；但 `*.pdf`（line 5）忽略
  `fixtures/catalog/sources/disclosure.pdf` → 提交时 `git add -f`（不改 `.gitignore`，写集外）。
- scan/读/export 全程本地；`git status --porcelain` 仅显示非忽略项，`__pycache__/` 被 line 16
  忽略，因此 session 内 `readonly` 快照不会被字节码缓存污染。
- `load_catalog_config` 的 `project_root` = 配置路径 `.parents[1]`：`catalog.yaml` 必须恰在
  重定位根的下一级（`<root>/catalog/catalog.yaml`），扁平复制即 `catalog_unavailable`。
- `company_wiki.llm_client` 在 `src/` 不存在（仅 `scripts/llm_client.py`）；
  §5.5.5 的模型断言目标是 `company_wiki` 包命名空间下的 `llm_client` 模块。

## 测试道环境事实
- 已装 pytest 9.1.1、pytest-timeout；`pytest.ini`：`testpaths=tests`、
  `addopts=-v --tb=short --strict-markers`、marker `integration`、无 mypy 插件。
- `tests/conftest.py`（先于本卡存在，不可改）：autouse `hermetic_runtime` 按测试
  monkeypatch `socket.socket.connect`→`RuntimeError("HERMETIC NETWORK BLOCKED")`；
  session-autouse `production_config_integrity` 断言生产 catalog SHA 不变。
  与本道 netguard 的关系：netguard 在 sessionstart 装 `AssertionError` 守卫；
  hermetic 在每个测试内临时覆盖（teardown 还原 netguard 守卫）——道内触发 socket 时
  需在测试内用 `netguard.guard()` 经 monkeypatch 恢复道守卫再断言 `NetworkAttempted`。
- `tests/integration/__init__.py` 先于本卡存在（写集外）；pytest 包根为 `integration`。
- `.gitignore:5` 的 `*.pdf` 忽略 `fixtures/catalog/sources/disclosure.pdf`；
  ignore 规则在写集外 → 用 `git add -f` 提交（不改 `.gitignore`），已在决策表记录。

## 为什么必须把夹具 catalog 复制到 tmp
- 若 env 直指本卡 `fixtures/catalog/catalog.yaml` 就地读：reader 自建 state 会写
  `fixtures/catalog/state/**` → 未跟踪生成物出现在 `git status --porcelain`，
  违反 card §7 完成定义 4（本仓无新增改动）。
- 方案：`p4_catalog_config` 把整个 `catalog/` 目录复制到 `tmp_path_factory` 再返回副本路径；
  `${PROJECT_ROOT}` 相对布局随副本保留；`inputs.catalog_sha256` 记配置原件的 SHA（副本字节相同）。
- env 已指向 tmp 下的 catalog 时按原样使用（ROOT 只读 catalog 场景）。

## RED 态与诚实记录（重要）
- 上一上下文跨度先实现了 `support/` 五类判定器 + 收据写入器（card 阶段 B），
  测试模块尚未写（card 阶段 A 要求先 RED）。顺序偏离如实记录，不伪造。
- 因此 RED 运行的真实失败点是**仍缺失的实现**：
  1. 夹具隔离（就地读污染 fixtures 树 → readonly 断言失败；relocated 断言失败）；
  2. `unit_tokens` 接线（conftest `p4_manifest` spans 未带 `unit_tokens` →
     派生 observation 无记号 → 保真/丢单位用例失败）；
  3. `receipt.json` 不存在（会话首次运行）；
  4. counts 记录接线缺失（`record_outcome` 无人调用 → `pytest_summary()` 全 0）。
- 比较器类用例（byte_size 差 1、同长度篡改、security_id 宽度、published_date 填充、
  换算 quote、availability observed 伪造）在 RED 时即通过——它们锁定的是已实现的
  判定器行为；reviewer 与 ROOT 以提交 1 复现 + 提交 2 全绿核对。

## 其他设计事实
- 收据在 `pytest_sessionfinish` 写出 → 本轮测试只能验证**上一轮**的 `receipt.json`
  （存在性 + schema 字段集 + 16 MiB 上限）；`counts` 与真实运行的一致性由
  `pytest_runtest_logreport` 接线 + `merged_cases` 单测 + ROOT 验收复跑核对。
- `counts.not_evaluated` 计的是**契约用例**（非 pytest 测试数），收据 `limitations` 显式说明。
- 消费端命令清单缺失时：用例本身 pass（如实建立了 not_evaluated），ledger case 记
  `not_evaluated`，顶层 status 保持 `partial`，绝不写成 `pass`。
- 道内有一次**有意的、被记录的** socket 触发（network 测试），产出
  `p4_network_attempted` 失败结果以证明守卫有效；审查者手工开 socket 复核（card §10）。
- INTERFACES.md §6 无 observation schema 常量 → 以 card 的 `p4-consumer-observation/1` 为准，
  `interface_versions.observation` 如实登记。
