# G-CWP-CANONICAL-01 协议 — 请求/响应/binding/namespace 矩阵

版本：`company-wiki-canonical-document-browse/1`（本包冻结；变更需新版本号）。
上游 seam：`stockwiki.dashboard_issuer_proof/1`（冻结合同，未修改）。

> 当前 D00 E13 集成对原 owner handoff 的额外支持范围见[集成补记](d00-e13-integration.md)：仅扩展 CWP issuer namespace 的 CN `cn.uscc` exact-SourceRef verifier；不修改上游 SW envelope/schema。以下协议正文保留原始 frozen-contract 记录。

## 1. 请求（stdin，≤64KiB，严格解析）

`company-wiki-canonical-document-browse-request/1`，exact 11 字段：

| 字段 | 类型/约束 |
|---|---|
| `schema_version` | const 上表 |
| `canonical_entity_id` | `ENT_<uuid4>`（与 SW 合同同 pattern），必填 |
| `listing_id` | `LST_<uuid4>` 或 null |
| `analysis_subject_id` | token 或 null；**非 null → state=unsupported**，不查 SW |
| `as_of` | 显式 UTC（`Z`/`+00:00` 结尾），必填 |
| `document_kinds` | token 列表 ≤32 或 null/[] |
| `fiscal_years` | int 列表 1900–2200 ≤200 或 null/[] |
| `language` | token 列表 ≤32 或 null/[] |
| `limit` | int 1–500，缺省 50；bool 拒 |
| `cursor` | opaque token 或 null |
| `proof_snapshot_id` | opaque token 或 null |

拒绝（exit 2，stderr `blocked` + named reason）：未知/缺失/多余字段、错误版本、类型/界限、畸形 token、duplicate key、>64KiB、非法 UTF-8、非有限常量。不接受 proof body、name/ticker、物理 root/path/URL/SQL/command。

## 2. operator 参数（不进业务 JSON）

`--config`（可信 CWP source_catalog 配置，必填）；
`--sw-python` / `--sw-cli` / `--sw-root`（SW 解释器/proof CLI 代码路径/可信工作根，全给或全不给；不完整→blocked；不可用→binding unavailable）。
SW 调用固定为 `read --root <sw-root>`，stdin `{entity_id, listing_id, as_of}`；超时 60s；stdout ≤1MiB；负态信封可出现在 SW stderr（nonzero exit + JSON object）。

## 3. 响应（stdout 单行 JSON，exit 0）

```
schema_version: "company-wiki-canonical-document-browse/1"
state: available | empty | partial | stale | unsupported
reason_codes: [named…]
canonical_context.requested: {canonical_entity_id, listing_id, as_of}
binding: {
  status: verified | ambiguous | unknown | conflict | stale | unavailable | incompatible
  reason_codes: [named…]
  association_scope: "issuer_only"
  issuer: null | {namespace:"sec.cik", value:<CIK digits>, verifier:"sec-primary-dei/1",
                  assertion_id, source_id, content_sha256}
           | {namespace:"cn.uscc", value:<checksum-valid USCC>, verifier:"cn-primary-uscc/1",
                  assertion_id, source_id, content_sha256} (CN exact-source route; see D00 E13 addendum)
  stockwiki: null | {entity_id, selected_listing_id, identity_revision,
                     receipt_sha256, envelope_state, library_revision,
                     selected_security_id?, selected_market?}
  cwp_resolved_source: null | {source_id, content_sha256, assertion_id}
}
items: [] 或 [ { …同既有 browse item…, source_ref: {document_id, source_id,
        content_sha256, byte_size, mime_type, schema_version:"2.0"} } ]
unverified_candidates: [] 或 [ {document_version_id, document_id, title,
                       document_kind, reason_code} ]  （≤32，pathless，无 SourceRef）
page: {next_cursor, proof_snapshot_id, total, total_status: exact|unknown}
catalog_revision: <证明集内容寻址 hex> | null
```

规则：
- **只有 binding.status=verified 才有 items/candidates/exact total**；其余状态 items=[]、total=null + `unknown`（不伪 0）。
- items 逐条同 issuer 证明（§4 矩阵），带完整 6 字段 SourceRef 与既有 opaque `document_version_id`（`cwpdv1-`，与既有 browse/reader 同 token，reopen 走既有 `public_document_browser_cli`）。
- 零路径泄漏：任何响应/错误不含物理路径、root、catalog 布局。
- `partial`：页内含当前配置根下不可解析（`not_resolvable`）的版本，同既有 browse 语义；SourceRef 仍完整，迁移根后 owner reader 仍可按 hash 重开。

## 4. namespace / verifier 矩阵（本包支持集）

| SW binding source_namespace | SW source_record_id | CWP 解析 | CWP issuer namespace | verifier | 结果 |
|---|---|---|---|---|---|
| `cwp_source_export_v2` | `urn:company-wiki:source:sha256:<64hex>` | 源存在 + `get_verified_assertion`（hash 绑定）+ 既有 `source_scope_qualification`（`_proved_sec_issuer`/`_reusable_sec_scope` 完整原始 DEI 证据，零原件读） | `sec.cik`（int 归一 CIK） | `sec-primary-dei/1` | verified（issuer 相等才成 items） |
| `cwp_source_export_v2` | 其他/非 URN | — | — | — | `unknown: unsupported_source_record_urn` |
| `cwp_source_export_v2` | `urn:company-wiki:source:sha256:<64hex>`（精确 CN PDF；CN 年/半年/季报） | active hash-bound facts + exact `SourceVersionReader` + bounded native PDF text + cache-only exact active CNINFO security record | `cn.uscc` | `cn-primary-uscc/1` | verified only after own legal name/security table/registration USCC checksum and exact security identity agree; otherwise named unknown/unavailable |
| 其他任何 namespace | * | 不解析、不转换 | — | — | `unknown: unsupported_source_namespace`（保留 SW 已验证半证据） |

仅表中 SEC CIK 与本 addendum 授权的精确 CN `cn.uscc` 路由可产出 verified issuer。其他 namespace/转换继续 named 拒绝；本扩展不改变 SW schema。

## 5. binding 状态映射

| 触发 | binding.status | 典型 reason_codes |
|---|---|---|
| SW CLI 未配置/配置不可用 | unavailable | stockwiki_proof_not_configured |
| SW transport 失败（crash/超时/非 JSON） | unavailable | stockwiki_proof_cli_failed / stockwiki_proof_deadline / … |
| receipt 重算不符 / 回显不符 / 未来 schema | unavailable | stockwiki_proof_receipt_mismatch / stockwiki_proof_query_echo_mismatch / stockwiki_proof_envelope_version_unsupported |
| SW state=ambiguous（多挂牌无选择） | ambiguous | SW reason + stockwiki_proof_not_available |
| SW state=not_found（实体/foreign listing） | unknown | listing_not_found_in_owner_package … |
| SW state=unverified（provisional owner） | unknown | owner_identity_not_verified |
| SW state=unavailable（如 receipt 撤销/缺失、market 未注册） | unavailable | receipt_not_active / market_not_registered … |
| SW state=incompatible / 信封内部不一致 | incompatible | envelope_entity_mismatch / receipt_not_active … |
| namespace 不支持 / URN 不支持 | unknown | unsupported_source_namespace / unsupported_source_record_urn |
| URN 源不在 catalog | unknown | resolved_source_not_indexed |
| 源无 verified facts | unknown | resolved_source_unverified_facts |
| issuer 证据需读原件（不完整 DEI） | unknown | issuer_proof_requires_original_read |
| 非 US 文档（CN 以外无本协议支持通道） | unknown | issuer_namespace_unsupported_for_document |
| CWP facts 与 SW 主张冲突（primary_issuer_conflict） | conflict | source_facts_blocked primary_issuer_conflict |
| 文档多 source 证明冲突 issuer | verified* | + document_issuer_conflict（该文档排除出 items） |
| snapshot 任一 pin 变化 | stale（response state） | proof_snapshot_stale |
| analysis_subject 非 null | unavailable + state=unsupported | analysis_subject_unsupported |

## 6. proof_snapshot / cursor

token（base64url JSON）：`{v:1, query:{entity,listing,as_of}, filters, stockwiki:{identity_revision, receipt_sha256}, issuer:<issuer pin>, revision:<证明集 revision>}`。
证明集 revision = sha256(issuer pin + 全部证明版本的 revision_member 列表)——任一 SourceRef 版本/事实/facet 可见变化都改 revision（与既有 browse 同成员语义）。cursor 内嵌 snapshot token；错配、跨 query、跨实体、filter 冲突一律 named 拒绝。不使用 git HEAD/mtime 作业务 revision。
