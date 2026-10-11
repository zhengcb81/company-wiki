# findings — W06-CWP-PORTABILITY

## F1 真实读接口（source_reader.py，SHA be753a61…）
- `SourceRef(document_id, source_id, content_sha256, byte_size, mime_type, schema_version="2.0")`：只有 identity/SHA/size/MIME/schema，无路径。
- `SourceVersionReader(catalog, runtime_policy=None)`：
  - `query_ref(document_id, source_id, expected_sha256) -> SourceRef`（纯 SELECT，不读字节）
  - `query_local(SourceRequest) -> SourceQueryResult`
  - `describe_version(ref) -> dict`（title/document_kind/published_date/fiscal_year/fiscal_period/period_end/form_type/…）
  - `open_version(ref, *, purpose="filing_reuse", expected_read_policy_sha256=None) -> VerifiedContent`（data=bytes）
  - `verify_version(ref, *, purpose="source_export", ...) -> VerifiedVersionReceipt`（无字节）
  - `open_described_version(ref, *, purpose="source_export") -> (VerifiedContent, manifest)`
  - `read_policy_sha256(ref=None)`
- `SourceReadError(status∈{not_found,not_indexed,unavailable,blocked,ambiguous}, reason, detail)`：拒发不含字节/物理路径。
- purpose 合法集 {preview, filing_reuse, source_export, narrative_derivation}；**没有 open_verified 方法**（与 ROOT 补充一致）。
- `_verified_version` 每次重新查 catalog/root policy/位置；"Stored absolute_path is never trusted"；同 SHA 位置 fallback（候选按 candidate_rank 排序逐一验证字节）。
- 字节校验 `_read_verified_bytes`：缺文件→read_failed(FileNotFoundError)；SHA 不符→content_sha256_mismatch；size 不符→byte_size_mismatch；读中变更→changed_during_read。先拒后给字节。

## F2 ID 派生（scanner.py / source_manifest.py）
- `source_id = SOURCE_ID_PREFIX + content_sha256`（source_id_for_sha256）→ 内容派生。
- `document_id = urn:company-wiki:document:sha256:<sha>`（有 primary source 时）；否则 `document-logical`（root_id+group_key）。
- 含义：same bytes → same source_id/document_id；root/relative_path 变化不改 ID；同 bytes 双根=同一逻辑来源多物理副本（duplicate_group exact_copy）。
- `location_id = sha256(root_id + \0 + relative_path)`。

## F3 配置（config.py）
- YAML schema_version 必须 "1.0"；字段 schema_version/catalog_dir/roots[/reusable_root_kinds]。
- root 字段：root_id/path/kind/priority/adapter_id/admission_profile_id/read_only/reusable_for_filing/routes/allowed_document_kinds/allowed_statuses/symlink_policy/max_file_size/…
- CFG-05：reusable_for_filing=True 要求 read_only=True；CFG-08 布尔字段不能是字符串。
- root_id 唯一；path 支持 ${PROJECT_ROOT}/${USER_PROFILE}。
- 校验是防错/数据完整性：不能为虚拟化放开生产任意 path。

## F4 register/scan（service.py + registration_scope.py + scanner.py）
- `SourceCatalog.register_sources(root_id, relative_paths)` → register_catalog_sources → scan_catalog(root_ids={root_id}, relative_paths=…)：精确登记，不全根发现。
- `SourceRegistrationScope`：relative_path 必须规范化（无 \、无 :、不以 / 开头、无 . ..）。
- kind="directory" + relative_paths：`directory_entries`→ primary+`.source.json` sidecar 成对。
- **非 focus 分支**（无 routes 且 root_id != dropbox_stock）：每个 supported 文件（含 .source.json 自身！）都成 standalone original_primary → sidecar 会变独立文档（quirk）。
- **routes 分支**（root 有 routes 且 route_matches(dir)）：sidecar 与 primary 配对，sidecar role="metadata"，不单独成文档 → fixture 用 routes include ["*"]。
- evaluate_admission 仅对 root_id=="dropbox_stock" 且 "重点关注" 子树生效；其它 root 恒 None。
- sidecar 显式 document_kind 经 SIDECAR_KIND_MAP 信任最高；published_date 取 filing_date/published_date 字段。
- PERIODIC_DOCUMENT_KINDS={annual_report,semi_annual_report,quarterly_report,regulatory_filing,investor_call_transcript}；investor_relations/prospectus 非周期 → 不获假 FY。
- 位置注解 `_annotate_locations`：candidate_rank（合格候选内按 (root_priority,root_id,relative_path,location_id) 1..N）、is_canonical、duplicate_relation=exact_copy、duplicate_group_id。
- 同内容多位置 → 同 source_id 一组；`exact_source_locations(document_id, source_id)` 给全部位置。

## F5 导出（source_export_v2_cli + source_contract/source_export_v2.py）
- CLI：`--config` + stdin JSON {schema_version:"2.0", source_refs:[…], evidence_spans:[…]} → stdout 一行 SourceExportBundleV2 JSON；SourceReadError→exit 2 + stderr JSON。
- `SourceExportBundleV2.build`：每个 ref 用 verify_version（无 span）或 open_version(purpose="source_export")（有 span），manifest 用 describe_version；bundle 字段（_MANIFEST_FIELDS）无任何路径。
- source_reader_cli：`--config --document-id --source-id --content-sha256 [--purpose] [--expected-read-policy-sha256]`，stdout 字节 + stderr JSON receipt（policy_sha256/source_read_policy_sha256/read_at/manifest）。

## F6 SourceRequest（resolver.py）
- 字段 entity/document_kind/as_of_date[/market/security_id/form_type/fiscal_year/fiscal_period/language/provider/provider_document_id/mode/allow_download]。
- query_local 走 query_ref→SourceRef；latest_as_of 按 (published, provider_document_id, source_id) 取 max；多命中→ambiguous。

## F7 目录分支扫描细节（scanner._scan_root_v1）
- company_raw 分支按 company 顶层目录分组；directory 分支按 os.walk/directory_entries；dayu_portfolio 其它。
- group_key：路径形如 X/filings/… → 前 3 段（.rejections 前 4 段），否则 group_key=relative_path。
- document_metadata 含 root_id/group_key/scanner_version/acquisition 等；`_merge_document_row` 合并旧记录。

## F8 接收/目录安全
- `_relative_segments`：拒绝绝对/盘符/../空段/控制字符。
- `_inside_configured_roots(os.path.realpath(candidate))`：symlink 逃逸防护；symlink_policy 默认 reject。
- `_needs_hydration`：云占位未水合 → placeholder_not_hydrated 拒绝（不下载）。

## F9 环境陷阱
- `import company_wiki` 解析到**主仓** src（editable fallback）→ 一切运行必须显式 PYTHONPATH=worktree/src 并记录 company_wiki.__file__ 与模块 SHA。
- conftest.py 有 Win32 路径长度改道（basetemp≤60 字符重定位）；owned-root/out-root 路径宜短（如 C:\tmp 或 worktree 外短路径）。
- worktree git HEAD=01ea86a3（基线一致）。

## F10 fixture 设计（≤6 synthetic 原件）
- 3 根（路径含空格/中文；root_id：local_company/external_dayu/external_dropbox，priority 10/20/30）：
  - local_company：`2025 年度报告/年报 文件.pdf`（最小合法 PDF-1.4）sidecar annual_report/FY2025/period_end 2025-12-31/filing_date 2026-03-01
  - external_dayu：`业绩说明会 纪要.txt`（中文原语言）sidecar investor_relations/无 FY/filing_date 2026-04-10
  - external_dropbox：`募集说明书 文件.html` sidecar prospectus/无 FY/filing_date 2026-05-06
- S4 重复副本：TXT+sidecar 复制到 external_dropbox（同 bytes 同 metadata，两根不同 priority）→ 4 物理原件 ≤6。
- sidecar 模板字段（对齐 test_default_steady_source_reader.py）：schema_version "1.0"、canonical_entity_id、display_name、market、security_id、document_kind、source_title、fiscal_year/period_end/filing_date（非周期省略 FY）、form_type、provider="example-filing"、provider_document_id（synthetic-…）、content_sha256、collector_name/version、retrieved_at。显式 synthetic 标记（source_title 前缀 [SYNTHETIC] 或 provider_document_id synthetic-）。
- 不用 SEC 标记（避免 filing_reuse 的 issuer CIK 鉴定）；open purpose 统一 source_export。

## F11 policy/receipt
- receipt.policy_sha256 = export_policy_2x(config)[0]（含 roots ${PROJECT_ROOT}-tokenized path_refs）→ 移根会变，可接受，非新授权门。
- receipt.source_read_policy_sha256 = exact_source_read_policy_sha256（含 source_ref/source_facts/registered_root_ids）。
- S2 必须实际记录 before/after policy SHA 并观察是否变化（oracle 反例"无实际policy变化观察"）。

## F12 交接契约（handoff_contract.md）
- handoff.json schema w06-lane-handoff/1 必含 lane/status/repository/workdir/branch/base_commit/head_commit/changed_files/input_evidence/interfaces/tests/findings/cleanup/cost/space/remaining/root_next_action。
- status ∈ COMPLETE|PARTIAL|BLOCKED；产品失败→PARTIAL+固定期望；NOT_RUN/null 如实。
- 另交 handoff.md、manifest.json（列交接文件相对路径/SHA/字节，自身不递归哈希）；RED/GREEN 日志分开保留；正常 commit 不 force/跳 hooks/不推主线。
- 测试红线：全新 owned root；sentinel 先记清单/原 SHA；只清本线生成路径；关 SQLite/子进程；交接 ≤8MiB、scratch 峰值 ≤64MiB；无收费/外部网络。

## F13 场景期望（7 场景，见卡）
S1 注册→query_ref→open_version→export 精确 SHA/期次/文档类保持；禁假 receipt 跳 reader。
S2 同 root_id/relative_path 整根 A→B+配置重映射：旧 SourceRef 读同 bytes；绝对旧路径不进消费者面；不支持→PARTIAL。
S3 改 relative_path/跨根=正常重新登记：记录旧/新 document_id、source_id、contentSHA、revision 关系；identity 稳定性只对承诺字段；需 ROOT 决定的标 UNKNOWN。
S4 两根同 bytes 同 metadata 不同 priority：候选按 root priority 非磁盘路径；逻辑来源 1/物理副本 2 分记；删一个 synthetic 副本后另一副本可读。
S5 raw 不可用→索引不伪称已验真（拒发）；恢复→正常读；改坏字节→真实 SHA 拒绝；新内容=新版本不覆写。
S6 as-of/period/document_kind 不因移根变未知/伪日期；IR/prospectus 无假 FY。
S7 export/pathless 消费者在新短生命周期进程复现（新 PID reopen，非旧 buffer）；PNG/PPTX OCR 不在本卡。

## F14 sidecar 完整性契约（WU-701 N-02）与非周期原件（实测）
- SidecarFilingAdapter 要求 fiscal_year/period_end 真值才算"完整"，缺→role=indexed_only、
  document incomplete（primary_source_id NULL、source_status=incomplete）→ query_ref 拒（source_not_active）。
- 合规解法：非周期原件 sidecar 写显式 `nonperiodic` 标记（fiscal_year/period_end）；describe_version
  的 fiscal_year 只接受 4 位数字 → 报 None（不获假 FY）；period_end 稳定为 "nonperiodic"。
- source-facts 不能救 incomplete（它先要 verify_version=active，鸡生蛋）。

## F15 身份派生实测（S2/S3/S4）
- source_id=urn:company-wiki:source:sha256:<contentSHA>；document_id=…document:sha256:<contentSHA>。
  同 bytes 多根/改 relative_path/移根 → same IDs（same_content_same_ids，观察非承诺）。
- locations 按 (root_id,relative_path) ON CONFLICT DO UPDATE：同路径改内容重登记=location 重绑到新
  document；旧 ref 之后拒发 no_indexed_location（非 SHA 类），旧字节恢复+重登记可复原。
- 同 bytes 双根=同一 source 的 2 个 active original_primary location（candidate_rank 按 root priority）；
  documents 表只有 1 行。全量 scan 才做 missing 清扫；register（bounded）不清扫。
- policy_sha256（export_policy_2x，含 ${PROJECT_ROOT} path_refs）随移根改变——实测可观察，非授权门；
  exact source_read_policy_sha256 另计。

## F16 篡改拒绝实测（S5）
- 同长度篡改（不改 size）→ 大小检查过、SHA 拒：failures 链含 content_sha256_mismatch，
  最终 SourceReadError("unavailable","no_verified_location","content_sha256_mismatch")。
- 增长/缩短内容 → byte_size_mismatch 先拒。raw 文件暂缺 → read_failed/FileNotFoundError 链，拒发无 receipt。

## F17 directory 根扫描 quirk
- 无 routes 且 root_id != dropbox_stock 时，`.source.json` 自身也注册成独立 standalone 文档（legacy）。
  配 routes include ["*"] 走配对分支（sidecar role=metadata）——本工具 fixture 采用后者。

## F18 E2E 实测（attempt-0003，elapsed 7.4s）
- 7 场景全 PASS，oracle overall PASS；source_read_calls 51（in-process 47+子进程 4），HTTP 0，报告 29KB。
- S2 policy 观察：before 385020d5… ≠ after e1108fd7…（change_observed=True，change_is_auth_gate=False）。
- S3：same_content_same_ids，旧 ref 经新位置可读（old_ref_reads_via_current_location）。
- S4：1 逻辑/2 物理；删 canonical 副本后 fallback 副本验真读出。
- S5：corruption=content_sha256_mismatch；旧 ref 在新版本注册后拒 no_indexed_location；新 ref 读新 bytes。
- S7：consumer pid ≠ runner pid，bytes_origin=fresh_read；consumer raw 直开 0。
- 过程教训：pytest/子进程审计钩子不能用 traceback.extract_stack（linecache 开文件→递归）；
  归属判定要"栈上任一 company_wiki 帧→reader"，否则钩子自身帧抢归属。
