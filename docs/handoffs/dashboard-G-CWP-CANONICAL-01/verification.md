# G-CWP-CANONICAL-01 验证记录

环境：Windows 10.0.26300 / Python 3.13.9（Miniconda, pytest 9.1.1）/ worktree
`C:\Users\郑曾波\Projects\dashboard-owner-cwp-canonical` @ `codex/dashboard-cwp-canonical`。
SW 依赖（只读）：`C:\Users\郑曾波\Projects\StockWiki` @ `8a5ac1cad831a7f0ea1acae4dc2e107d8ff6b917`。

## 1. 最终 GREEN（全部本会话实跑）

```
python -m pytest tests/contract/test_public_canonical_browser.py -q
  → 35 passed in 64–86s
python -m pytest tests/contract/test_public_document_browser.py \
                  tests/contract/test_public_source_readiness.py -q
  → 101 passed（browse 15：含 exact/reopen 语义 9 项；readiness 86）
python -m ruff check <3 新文件>            → All checks passed
python -m mypy src/.../public_canonical_browser{,_cli}.py
  → Success: no issues found in 2 source files
```

未跑全仓 CI（按卡：边界验证替代全仓 CI）。

## 2. 正例（真实双引擎组合）

`test_same_issuer_positive_through_real_engines`：
- CWP 侧：隔离根真实 scan + 真实 `record_source_facts`（US 10-K html，8 项 DEI 证据，`primary-dei:/…` locator、`sec-primary-dei/1` method、primary_cik/issuer_record_id 绑定当前 sha）；
- SW 侧：真实 QuickScanStore/IdentityReceiptStore/MarketRegistryStore + 真实 `build_identity_request` 产出 G2b 2.2.0 owner_package（verified 实体 + IVR receipt + cwp_source_export_v2 binding → CWP source URN）；stand-in 仅做冻结信封装配/`receipt_sha256` 重算；
- 断言：binding verified、issuer `{sec.cik, 87654321, sec-primary-dei/1}`、items 恰含 proven 版本（完整 SourceRef + cwpdv1 token）、total exact=1、3 个 pathless 未验证候选（amended/bare-ticker/CN）、零路径泄漏、**query 前后文件集合 SHA/size 全等**（`*-shm` 排除并注明理由）。

## 3. 负例矩阵（全部实跑 GREEN）

| # | 负例 | 结果断言 |
|---|---|---|
| 1 | wrong issuer（ENT_BETA→BETA 源） | items 仅 BETA，ACME 不出现 |
| 2 | same bare-ticker（同 entity key，无证明） | 永不进 items，仅 issuer_proof_missing 候选 |
| 3 | SW 绑定源无 CWP facts | unknown + resolved_source_unverified_facts，total unknown（非 0） |
| 4 | foreign listing | SW not_found→unknown，items 空 |
| 5 | 多挂牌无选择 | SW ambiguous→binding ambiguous |
| 6 | 多挂牌显式 listing（真实 receipt listing_ids） | verified + selected_listing 一致，association_scope=issuer_only |
| 7 | receipt 撤销（真实 revoke 事件） | unavailable + receipt_not_active |
| 8 | provisional owner | unknown + owner_identity_not_verified |
| 9 | 未注册市场（ZZ/ZZZZ） | unavailable + market_not_registered（owner 引擎拒绝） |
| 10 | 外来 namespace（sec.cik 冒充） | unknown + unsupported_source_namespace，不转换，保留 SW 半证据 |
| 11 | 伪 receipt hash | unavailable + stockwiki_proof_receipt_mismatch |
| 12 | query 回显错配 | unavailable + stockwiki_proof_query_echo_mismatch |
| 13 | 未来 schema | unavailable + stockwiki_proof_envelope_version_unsupported |
| 14 | 离线（crash / 解释器缺失 / 未配置） | unavailable 三态 named，total unknown，绝不伪 0 |
| 15 | 旧 source 版本（amended 无 facts） | 不进 items，仅候选 |
| 16 | SW identity_revision bump 后旧 snapshot | stale，total unknown，新 snapshot 返回 |
| 17 | 证明集增长（新 proven 版本）后旧 snapshot | stale，不混 revision；新页 total=2 |
| 18 | analysis_subject | state=unsupported，不查 SW |
| 19 | 畸形请求 13 参数化 + duplicate key + 超限 | blocked exit 2 named |
| 20 | 不完整 SW 配置 | blocked（invalid_request） |
| 21 | 缺 catalog | unavailable exit 2 |

## 4. RED → 根修 → GREEN（本会话真实序列）

1. RED：fixture DEI 证据缺 `document_kind` → 真实引擎 `ValueError: each changed fact needs matching field evidence` → 根修：证据集补齐（facts/evidence 同键集）→ GREEN。
2. RED（核心正例）：CLI 返回 `state=empty ≠ available`；进程内定位 `_issuer_for_source` 以 `isinstance(resolution, ResolvedIssuer)` 判断 tuple 返回 → 恒 None → 根修：`isinstance(resolution, tuple)` → GREEN。
3. RED：`../etc/passwd` 类 cursor/proof_snapshot_id 在绑定不可验证路径漏拦（in-band 空响应）→ 根修：`_optional_token` 提前 `_TOKEN_RE` 校验 → blocked/GREEN。
4. RED：无 SW 配置 + 缺 catalog → exit 0 in-band（应为 transport unavailable）→ 根修：CLI 构造后一次只读探测（`SELECT 1`）→ unavailable exit 2/GREEN。
5. RED：CLI stderr 错误路径 `NameError: RESPONSE_SCHEMA`（exit 1 traceback）→ 根修：补导入 → named blocked/GREEN。
6. sabotage RED（测试敏感性证明）：`ISSUER_NAMESPACE_SEC_CIK = "sec.cik-SABOTAGE"` → 正例立即失败（issuer 断言不匹配）→ 恢复 `sec.cik` → GREEN（恢复后复跑 1 passed）。

## 5. 边界与卫生核验

- `git status`（worktree）：仅 3 新代码/测试文件 + handoffs；`.githooks/pre-push` 为 base 既有 mode 伪差（100755→100644，无内容 diff，未 staged、未提交）。
- 生产 `config/` 零改动；未写穿任何生产配置；测试全用 tmp 夹具。
- StockWiki 仓：零修改（只 import 其真实引擎进隔离子进程；工作区仅既有未跟踪 `runs/c16b`，未读未动）。
- 零网络/零模型/零下载；全部 fixture 在 pytest tmp 内自动清理。

## 6. NOT_RUN（明确未做）

- 真实生产 CWP 目录上的任何 query（含中微 9MB 年报 / 0.43MB IR 真实原件组合）。
- 真实 Alphabet `ENT_97bf6a65-a9e6-43f0-8409-c5695e2f6e1e` + `LST_417535c6-7046-4acd-833d-de3f50116e76` 的 SW proof read。
- 独立 reviewer 独审（按卡另派）；SW 真实 proof CLI 组合（前置未交付）。

以上任一前置落地后，按 README §4 路径组合复跑即可升级状态。
