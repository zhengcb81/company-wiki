# W04 ROOT 技术接口 review

结论：计划技术方向可接受；ROOT 在 execution overlay 处理三项必要调整，并完成原计划要求的公共 v3 冻结后，可按既有大节点派工。不新增小节点 gate，不改 sealed 专家计划。

本轮只读文件、核实际 SHA、对照接口；0 GET、0 provider/model、0 测试/probe/fullsuite，0 产品/config/安装/旧 run/专家计划写入。只新增本目录两个报告，完成即 STOP。一次报告命令在 functions JS 解析阶段失败，无文件或命令执行副作用，随后修正写法。

handoff 实际 SHA 为 cdc7f015d2e162ad9478a2be6fc05f06f69d3c5f208b02f870040c12bea0fef6；seal 的 21 文件 SHA/size 全匹配，全部实际哈希在 review.json。主要文件：

| 文件 | 实际 SHA-256 |
|---|---|
| implementation_details.md | d196b886510f789dfb9282e067aa39b455a502a5ee2dddc55ea6fcd0d8c911ee |
| test_matrix.md | 894955db59dc14f9a29322d216b505fbb52dc86d18ff25c2fe7e997beb860e32 |
| OWNER_MATRIX.json | 307eb384d7313659d17dd78c3bd2cb2c826bef44c7d5c59407e8b101ba9dec56 |
| WP01.md | ca457ac34d5c8866ca8838612e0c58f88db2525a6b3e8233e4cf55a7660154f5 |
| WP03.md | 124077b2ecadddeef97ba1f28348a71a70703acdbf99659389772ed24d14f204 |
| WP05.md | e3c9e683672b3a425efc4b67532b86cba42bee99a27188e965ecb873837f27b6 |
| WP07.md | f988653a155b4c41b7fa0e684fd09116f53774dfa7442b9cfc7d446a63b083ea |

246 主 finding = 157 old + 89 new，实际 issue keys 唯一；3 TECH 与 1 NULL auxiliary 独立，未扩成 249/250。20 roots、7 WP，primary counts 为 10/22/15/10/12/87/90。归一化 44 条明确写路径无重叠；RF 共享 schema/type/install 具体路径仍由 ROOT 冻结。

## 必要 execution overlay 调整

1. **P2 / W04-ROOT-IFACE-001：CWP 新风险测试位置漏正常 gate。** WP01:19、WP02:17 拟写 tests/test_w04_*.py。pytest.ini:2 虽允许无限定收集 tests，CI:59 实际只跑 pytest tests/unit，CI:45 ruff 和 changed_unit_tests/pre_push_gate 的正常入口也聚焦 tests/unit。ROOT 只把两条路径改为 tests/unit/test_w04_source_transport.py 与 tests/unit/test_w04_narrative_semantics.py，owner 保持 WP01/WP02，沿 G1/G2 和正常 gate 验证。

2. **P2 / W04-ROOT-IFACE-002：ROOT 的 audit_run 范围标签过窄。** OWNER_MATRIX:178、WP07:19 限“expectedSHA hook”，而 WP07:192/:200 要求 retention_mode/blob_store/deadline、child 剩余时间、物理 reservation 与 cleanup 优先级。现 audit_run:597 freeze 调用、:625 child timeout 都属于 ROOT 文件。overlay 应明确同一 WP07 负责 opt-in freeze/capture/CAS/private-copy/deadline/cleanup 接线，legacy 默认行为保留。WP05 的 helper/composer/tests 写权不变，对 audit_run 继续只读。不新增 Windows immutable CLI lease 或第二 registry/任务库。

3. **P2 / W04-ROOT-IFACE-003：compact evidence 操作缺一条 WP01 写权。** narrative_evidence_view.py:108/:133 写死 projected view/receipt /2，:112/:140 从请求取 ref，:116 保留 body full binding/parents。transport 文件之外需要该 leaf 适配。ROOT 已读实际源码并确认：把 src/company_wiki/automation/narrative_evidence_view.py 加入 WP01 排他写集，只接 /3 compact DTO/receipt，保留 /1 raw 和 /2 projected，沿 T03/G1，不加 gate。此文件与现写集无重叠。

## 公共 v3 冻结细则

SourceRef 的 schema_version 精确是 2.0，六字段与 pathless 语义保持。CWP 现 raw NarrativeRef 为 narrative-ref/1，projected 为 narrative-ref/2，其 reference/read/receipt 也分别 /1、/2。现 raw bundle 是 narrative-bundle/2.0，projected bundle 是 narrative-bundle/3.0。这些独立 schema 不互换。

新增 compact narrative-ref/3、narrative-reference-request/3、narrative-read-request/3、narrative-read-receipt/3。ROOT 一次冻结 exact request/reference/read/evidence 的 success/refusal 字段；保留 CWP 老 /1 与 /2 原字段/字符串/旧 generation。RF 历史只支持 /1，本轮增加显式 /3 projected 路径，不虚称此前支持 /2。

所有请求、reference 输出及收据、read/evidence 收据仍 ≤16384B；read bundle ≤1310720B。ROOT 拟定 lineage_sha256 为 SHA256(canonical_json(full bundle.subject_binding))，parent_count 是全体真实 parent refs 的数量。receipt 与 body 对照 compact subject/generation、完整父 SHA、issuer/asof、每个原 pointer，不能剪父链、伪装单 raw SourceRef 或套 raw loc:v1。evidence /3 的 exact schema/字段也应同时冻结。

当前 projection_loader 接 NarrativeSubject 并返回 VerifiedProjectionView。compact resolver 可一次调用 CLI 已有 open_verified_projection(projection_id, expected_projection_sha256)，复用真实 VerifiedProjectionView 做 artifact/replay 检查，避免 load 后再次重开全部 65 parents。RF 对照 body 与 receipt，不承担第二套所有 source exact-open 验证。上述属于已指派 ROOT 的公共冻结及 T03/G1。

metadata 四键旧包加可选 declared_language 的扩展合理。新 projected 分支要接 CWP 合法 official_json 与 summary_not_needed 的 unknown language；raw filing/transcript、en/zh/mixed、nullable title、language-family 和未知 key 保持原版本严格规则。

## 已核对的边界

canonical narrative 已接线：native model_options_from_config 的 purpose 默认就是 narrative。main config 实际 SHA2f4df37c3d39ef380caf476b6b678949a1e4b7604bdb95b73b0033804209c589，generation_policy key 数为 0。policy absent 是配置事实。raw generation 对 null/omitted thinking、temperature、reasoning_split 的 SHA 不同，而 HTTP/projected 有效 wire 相同；这是已识别 NULL 效率风险。统一有效 wire、保留旧 generation 映射即可；explicit thinking/effort/maxoutput 已入 identity，label-only purpose 不重复收费。

RF 当前不会把 3.7/3.8 自动升级为 3.9。contracts/document:89 接三版本且不改 schema，旧版本拒新 period_flow；revenue_core:65 在验证后明确 result.schema_version=data.schema_version。schema_compatibility 允许现 engine4.2.1 处理三版本。因此新 snapshot header 取 actual schema 合理，观察双 schema 并沿 existing compatibility policy；历史 header/ID/hash 不改，不加旧 snapshot 内外版本相等门。本轮无需 snapshot probe。

未来 analyst_assumption 可非 null，没有 future actual 不判错；校准需解释经济量级、scope 和真实 DAG。CMP H1 calendar 与 May31–Jun30 contribution 窗口可不同，历史祖先日期不机械等于预测年。RF 做投资研究，CWP/audit 保持 source/诊断职责。

审计保持 59 legacy API 与 96 已接受；free0 是合法 finite nonnegative money，其他尺寸/time/token positive。builder exact request SHA/size 在 streamed freeze 同边界比较，失配 nochild；outer/requested/effective/observed/owner-enforced 分层，普通 RF 无 resource control 保持 unknown。transport0、business failure、invoice unknown 分别保存。

immutable no-replace CAS 加普通 private workcopy、物理 retained/peak reservation、同一 stage deadline、主错/secondary cleanup 优先级，以及旧 original_path/manifest/DB exact bytes 与必要 replay 状态留存已明确。第一版无需 Windows immutable CLI lease。唯一 raw、独有 AUTO/catalog replay 状态在未完成持久 public replay 前可保留并说明。

CWP source116 精确 CI38108528804、RF47f497ad P7RF38096229764、96 audit/59 legacy 均沿已接受收据引用，未重跑。未来 RED/GREEN、真实 G2、G4 研究和 G5 泛化仍 NOT_RUN，本 review 不签未执行项。历史完整 supplier response/helper 缺失保持 unknown。

CWP worktree CodeGraph 实际未初始化，本轮不建 index；RF index 行位置较旧，版本关键接口以已知当前文件读取裁决。报告写入后再核全部 seal。

STOP_REVIEW_COMPLETE。