# G-CWP-CANONICAL-01 交付 — 公共 canonical 发行人→精确资料桥

状态：**CODE_PROTOCOL_COMPLETE_WITH_NAMED_PREREQUISITE / PARTIAL（生产 PRODUCTION_NOT_AVAILABLE）**，2026-10-30。
独立 reviewer 未派（按卡"独立reviewer另派（未实现）"，由 D00/总控另行派出）。

## 1. 固定树与边界

| 项 | 值 |
|---|---|
| worktree（绝对路径） | `C:\Users\郑曾波\Projects\dashboard-owner-cwp-canonical` |
| base（绝对 SHA） | `b04e9a80d37aff0a121fac06fd2b443cf1519ae2`（已审 CWP readiness 修复头） |
| branch | `codex/dashboard-cwp-canonical` |
| head | `47bca250…`（`47bca250a` = 复审补漏提交；首提交 `a58cd3d8…`；此后若有 docs-only 追加以 `git log codex/dashboard-cwp-canonical` 实时为准）。main `7a110b59` 等外部推进未并入，无旧 loop/C3/生产配置/钩子 WIP |
| StockWiki 依赖（只读、未改动） | `C:\Users\郑曾波\Projects\StockWiki` @ `8a5ac1cad831a7f0ea1acae4dc2e107d8ff6b917`（owner master，工作区仅既有未跟踪 `runs/c16b`，实现文件未动） |
| 冻结合同 | `investment-dashboard/.planning/unified-dashboard-2026-10-26/owner_extension_requests/contracts/stockwiki.dashboard_issuer_proof-1.schema.json`（未修改） |

新增文件（独占范围，无其他改动）：

- `src/company_wiki/source_catalog/public_canonical_browser.py`
- `src/company_wiki/source_catalog/public_canonical_browser_cli.py`
- `tests/contract/test_public_canonical_browser.py`
- `docs/handoffs/dashboard-G-CWP-CANONICAL-01/**`（本目录）

未修改：StockWiki / Dashboard / 总 PWF / 既有 public_document_browser、reader、readiness、store、scanner、PDF、narrative、注册入口（全部只读复用）。
worktree 中 `.githooks/pre-push` 显示 mode-only 差异（100755→100644，Windows 文件系统 exec 位伪差，无内容变化，非本包造成，保持未staged）。
生产 `config/` 零改动（会话边界核过 `git status`，见 §6）。

## 2. 交付内容

固定 CLI（query 全程只读、pathless、零采集）：

```
python -B -m company_wiki.source_catalog.public_canonical_browser_cli \
  --config <trusted CWP source_catalog 配置> \
  [--sw-python <解释器> --sw-cli <dashboard_issuer_proof_cli.py 路径> --sw-root <可信 SW 工作根>]
```

- stdin：`company-wiki-canonical-document-browse-request/1`（exact 字段：canonical_entity_id=ENT、可选 listing_id、可选 analysis_subject_id、显式 as_of（必须 UTC）、document_kinds/fiscal_years/language/limit/cursor/proof_snapshot_id；≤64KiB、严格 UTF-8/去重键/禁 NaN/类型界限）。
- stdout：`company-wiki-canonical-document-browse/1`（字段与语义见 `protocol.md`）。
- SW 部署三参数只能来自固定 operator 参数（或后续部署配置接线，本包未改配置加载器），绝不进业务 JSON；不完整配置→请求 blocked（named），不可用配置→binding `unavailable: stockwiki_proof_not_configured`（in-band）。
- transport 失败→stderr 单行 JSON（unavailable）exit 2；in-band 状态（available/empty/partial/stale/unsupported）exit 0。

核心行为（详见 `protocol.md`）：

1. SW 信封严格结构校验 + query 回显 + `receipt_sha256` 重算（canonical：ensure_ascii=False/sort_keys/compact/allow_nan=False UTF-8）；caller 提供的 hash 不是 authority。
2. state=available 时核 owner_package：entity/revision 一致、verified_issuer receipt active、selected listing 合法且 active、binding 与 listing/security/market 一致。
3. namespace 矩阵：SW `cwp_source_export_v2`（→ CWP 原生 source URN 解析）+ CWP `sec.cik`（verifier=既有 `sec-primary-dei/1` 原始 DEI 完整证据，hash 绑定、零原件读）。其他 namespace 一律 `unknown: unsupported_source_namespace`，不做未证转换。
4. items 只含逐条同 issuer 证明的文档版本（完整 6 字段 SourceRef v2 + 既有 opaque `document_version_id`，与既有 browse/reader 完全同一 token 语义）；证明不足→items 空、`total=null/unknown`，绝不伪 exact 0。pathless 未验证候选单列 `unverified_candidates`（封顶 32，reason_code：issuer_proof_missing / superseded_version / issuer_differs），不混入 items。
5. `proof_snapshot_id` 绑定 exact query + SW identity_revision + SW receipt + issuer pin（assertion/source/sha）+ 证明集内容寻址 revision；任一变化→stale，旧页不混。分页 cursor 内嵌 snapshot token，错配即拒。
6. `association_scope=issuer_only`；selected listing 仅核证券属同一发行人。analysis_subject 非 null→`state=unsupported`（reason `analysis_subject_unsupported`），不查 SW、不从 ENT/LST 造 ASJ。

## 3. 状态与前置（必须先读）

**生产 PRODUCTION_NOT_AVAILABLE。** 缺口前置只有一个：

- **G-SW-ISSUER-PROOF-READ-01 的真实 `dashboard_issuer_proof_cli.py` 未交付**（`C:\Users\郑曾波\Projects\dashboard-owner-stockwiki-proof-read` 不存在）。因此没有任何真实公共 SW proof CLI 可用于生产组合，也不存在真实 shared-key 生产 positive。

因此本包不声称真实 B/E04。已完成的范围：完整 CWP 侧实现 + 冻结 seam 消费/校验 + 真实双引擎受控组合验证（见 `verification.md`）：

- 受控正例与全部负例通过 **真实 StockWiki 引擎**（build_identity_request / IdentityReceiptStore / QuickScanStore / MarketRegistryStore @8a5ac1c）产出真实 G2b 2.2.0 owner_package，经冻结 seam 的 subprocess transport 消费；SW 侧 stand-in 只实现冻结信封装配/负态映射/选择规则，**不是 trust callback**，全部身份语义来自真实引擎。
- CWP 侧用真实引擎（scan + record_source_facts + 既有 source_scope_qualification/get_verified_assertion）在隔离根上生产 verified source-facts 与 sec-primary-dei 完整证据。
- 真实生产数据（Alphabet ENT `ENT_97bf6a65-…`、中微 83 active 版本）：**NOT_RUN**。等真实 SW proof CLI 交付后，由 operator 用其固定三参数对既有可信配置限量复跑（≤3 公司、page≤10）。

## 4. 组合与独审路径（给 reviewer/D00）

1. 取 G-SW-ISSUER-PROOF-READ-01 固定 candidate（其 handoff 给出 worktree/base/head 与 CLI）。
2. 用真实 CLI 替换本包测试中的 stand-in（tests/contract/test_public_canonical_browser.py 中 `DRIVER_SOURCE`/`_write_driver` 是唯一 SW 侧替身，生产代码零引用）。
3. 组合独审正反例：正例 same-issuer（真实 ENT+LST+隔离引擎 fixture），负例沿用本包矩阵（wrong issuer / wrong market / same bare ticker / foreign listing / subject / 缺证据 / 旧 revision / 撤销 / 多挂牌 / 旧 source 版本 / 伪 hash / 离线 / 非法 JSON / namespace 转换 / 回显错配）。
4. 独审通过后才可升 CODE_PROTOCOL_COMPLETE；生产 positive 需真实 shared-key 数据，否则保持 PRODUCTION_NOT_AVAILABLE。

## 5. 已知界限（诚实声明）

- CN/HK 文档（如中微 A股年报）：CWP 在此 base 上无原始发行人证据通道（sec-primary-dei 仅 US SEC 原件），这些版本只进 `unverified_candidates`（issuer_proof_missing），永不进 items；不猜测、不转换 namespace。
- SW binding URN 不在 CWP catalog / 无 verified facts / DEI 证据不完整（需读原件才能判定）→ binding `unknown`（named reason），不发起任何原件读/OCR/refresh。
- 认证扫描上限 20000 条 verified assertions，超限 named `issuer_scan_budget_exceeded`（unavailable），不静默截断。
- document 的多个 source 证明出冲突 issuer → 该文档整体排除出 items，binding reason 附 `document_issuer_conflict`。
- 零写语义：query 前后文件集合 SHA/size 全等（`*-shm` 为 SQLite 每次只读打开都变化的共享内存索引，无业务态，排除并已在测试注明）；DB 本体、WAL、源文件、SW 工作区全部字节级不变。

## 6. 验证与提交记录

- 新契约测试：`tests/contract/test_public_canonical_browser.py` **38 passed**（正例 2 + reopen 互通 1 + 跨 owner 负例 11 + seam 完整性负例 4 + 旧版本/分页 2 + 请求校验 16 + 边界/缺证据 2）。
- 既有回归（受影响面，按实 collect）：`test_public_document_browser.py` **15 passed**；exact9 = `test_source_reader_exact_history.py` **9 passed**；相邻 `test_exact_source_read_policy.py` 13 passed 一并核过；`test_public_source_readiness.py` **86 passed**。受影响合计 123 passed。未跑全仓 CI（按卡以边界验证为准）。
- 静态：ruff（repo 配置）+ mypy（contract strict, follow_imports=skip）双清零。
- RED→根修→GREEN（本会话真实记录，输出在会话日志/verification.md）：
  1. fixture 证据缺 `document_kind` → 真实引擎 `_validate_source_facts` named 拒绝 → 补 DEI 证据项 → GREEN；
  2. **正例 RED**：`_issuer_for_source` 用 `isinstance(ResolvedIssuer)` 判 tuple 返回值，恒 None → items 空、state empty ≠ available → 根修为 `isinstance(resolution, tuple)` → GREEN；
  3. 畸形 cursor/proof_snapshot_id 在未验证绑定路径漏拦（in-band 空）→ 根修：`_optional_token` 提前做格式校验 → blocked/GREEN；
  4. 无 proof 配置 + 缺 catalog 时 exit 0 in-band（应为 transport unavailable）→ 根修：CLI 构造后一次只读 catalog 探测 → unavailable exit 2/GREEN；
  5. CLI 错误路径缺 `RESPONSE_SCHEMA` 导入 → NameError exit 1 → 补导入 → named blocked/GREEN。
  6. **sabotage RED**：把 `ISSUER_NAMESPACE_SEC_CIK` 改为 `"sec.cik-SABOTAGE"` → 正例立即失败（issuer 断言不匹配）→ 恢复后 GREEN，证明正例测试真实敏感。
- **复审补漏（2026-10-30 第二遍逐条对卡）**：
  a. exact9 此前漏跑 → 补跑 `test_source_reader_exact_history.py` 9/9 通过（见上计数修正）；
  b. CLI stdin 缺 nonfinite/depth 边界（违反卡"UTF8/duplicate/nonfinite/depth/64KiB等bounded"，深层嵌套会 exit 1 traceback）→ 根修：stdin 解析加 `parse_constant` 拒绝 + `RecursionError`→named blocked → 新测试 NaN/Infinity/20000 层嵌套 blocked → GREEN；
  c. 卡规则 5"旧 document_version reopen 走既有 reader"此前只有文档声明 → 补互通测试：canonical item 的 `cwpdv1-` token 经**既有** `public_document_browser_cli` reopen 精确还原同一 SourceRef（storage_state=resolvable）→ GREEN；
  d. "缺证据"负例缺 US 通道（证据不完整需读原件）分支 → 补测试：amended US 文档记 plain sidecar facts（无 DEI 观察证据）→ 既有 verifier 要求原件读（browse 不做）+ security master 缓存缺失 → named missing-evidence，binding 仍以完整 DEI 源为 pin，候选 issuer_proof_missing → GREEN。

## 7. 成本 / 清理 / NOT_RUN

- 成本：全部本地 fixture，零网络、零模型调用、零下载；两 worktree（本包 + bump 临时）均在 pytest tmp 内自动清理。
- 清理核验：仓库内只新增 §1 四路径；生产 config/、StockWiki、Dashboard、总 PWF 零写入；主仓与本 worktree 的未提交变更只有既有 `.githooks/pre-push` mode 伪差。
- NOT_RUN：真实生产 CWP 目录上的任何 query；真实 Alphabet ENT 的 SW proof read；真实中微样本（9MB 年报 / 0.43MB IR）组合读。前置与授权路径见 §3/§4。
- 本包不合 main、不 push、不动他包。
