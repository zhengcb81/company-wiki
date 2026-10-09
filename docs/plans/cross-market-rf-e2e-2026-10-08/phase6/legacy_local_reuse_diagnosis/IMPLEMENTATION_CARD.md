# 拟施工卡：通用 legacy local reconciliation

状态：待MAIN授权；本卡不构成实现/生产恢复记录。诊断基础见DIAGNOSIS及两个receipt。

## 目标与单一责任

在现有CWP查询→ensure链中，真实raw尚存在且仅因历史metadata不足退休时，优先本地重新资格化，避免重复provider fetch。保留真正withdrawn、damaged、未知退休原因的事实。FF继续消费统一SourceRef v2，不增加投资state、权限DB、第二任务/费用账、人签或公司特判。

soft metadata retirement是“声明不足”，不能永远等价于“bytes缺失”。恢复的依据是原件和可信事实已足够，不是调用者声称某公司应被active。未知publication/URL保持null；publication未知不能获得历史as_of成功。

## 设计：观察→证明→单事务提交→原查询

1. **有界local inventory**：当前active候选miss后，在相同catalog/configured roots内观察exact source/document/locations与retire audit；先找已有local候选及等价hash，不全仓重扫。已退休也可成为待证明的inventory observation，不能直接成为消费候选。未索引本地组仅按有界、配置支持的source group discovery登记；原件不存在与原件metadata不足返回不同诊断。所有读沿现有root/path/symlink/size/hash guard，不复制存储责任。
2. **退休原因分类**：有结构化原因时用明确metadata-insufficient类；历史两次retire需回溯已知可信producer/batch及先前reason（Aug7 reconcile保留Aug1 F13因），而非只做contains('metadata')。分类以append-only observation保留原audit。任何withdrawn/upstream_rejected/quarantined/damaged证据、reason未知、互相冲突的历史都不自动activate；返回named local gap/ineligible诊断。不能按这四个SHA或公司名单开白名单。
3. **真实bytes/来源facts**：读取实际原件，验注册SHA/size以及当前root containment。通用SEC extractor从actual unambiguous DEI取得CIK/FY/Q/period，再与已verified active issuer/security映射比较；重用`verify_sec_primary`、date transform，不从请求推FY或从market猜issuer。CN由原件封面/公告声明提供issuer、kind、FY；日期证据独立取有定位的本地publisher/index/capture facts。缺/冲突/未知不能当成功。URL只能来自真实记录/可核验SECaccession+CIK+primary构造，允许未知null，不能补假URL。旧source sidecar/Dayu文件不改。
4. **原子document facts restore API**：拟内部`restore_document_facts(catalog, *, document_id, source_id, expected_sha256, facts, evidence, retirement_observation)`，名称/入口由责任owner落实，参数只是事实与乐观并发观察，不是权限token。成功返回现有SourceRef 2.0及统一source operation receipt；public DTO不另立一套。
5. **同一已有CatalogOperationLock与SQLite事务**：preflight在锁内有界读验bytes；事务内重验content-addressed identity、旧status/audit/facts观察未变，追加superseding source_metadata_assertion与事实projection，恢复document及仅已验证的可用locations，追加restore audit。一项失败则全部rollback。旧retire audit、sidecar/capture/source版本、未验证locations/坏副本保持。不得先restore_document提交active再record_source_facts；也不得用临时伪active绕过reader。需要从现有record_source_facts抽出共享prepare/write责任，保持同一原件校验，不复制事实或路径库。并发观察过期具名重读/重试，在相同有限deadline内。
6. **原public query与ensure接线**：default reuse读本身继续零写；需reconcile的有界来源intake/ensure composition负责事务，成功后重新走现有query_local/SourceResolver资格判断。考虑FF reuse_only仅query的真实入口，不能只在fetch_if_missing分支接线却声称两条都有效：MAIN明确公共local reconciliation入口由来源prep/FF composition调用后读；其读写行为如实记录，不能把查询暗改为全仓writer。命名missing/local_metadata_gap不能自动等价于允许新下载。明确fetch intent仍按既有时间/bytes/cost预算执行后续真正miss。
7. **历史日期与输出**：reconcile只改变来源可读事实，不把observed_at/captured_at/first_seen/filemtime变published_date。当前source/version登记与历史资格分开；outside-asof的原件可以登记但该as_of请求不得source_candidate成功，必须含正确排除诊断，不能借恢复动作重签成历史可用。返回SourceRef仍是原document/source/hash，public verifiedopen按当前manifest facts执行。
8. **重复/幂等性**：已有active+等价事实直接current read，不重复fact assertion/restore audit，不重复copy原件，不调用provider。不同bytes、真正新publication不是同一原件纠正。使用当前source-facts semantic idempotency（observed_at不制造新assertion）；没有第二账/权限表。

## TDD责任节点（先RED，再generic修复）

| 类别 | RED与GREEN要求 |
| --- | --- |
| metadata-only retired bytes完整 | active-only query可观测miss，但在明确local reconcile→query/ensure composition后返回同SourceRef、actual bytes verified；provider discovery/fetch计数0；旧retire审计不变，新restore审计与fact supersession准确。 |
| URL未知 | 当前active/nullURL本已复用，锁住该责任；retiredmetadata恢复后仍null，不要求假URL，不把capture_ready诊断当新下载理由。 |
| 旧issuer/FY冲突 | actualSEC DEI+verifiedissuer纠正HK/FY25→US/FY26，旧声明可审计；caller request/文件名不能作为fact proof。company_raw同SHA dedup也走相同correction责任，不只imported_new。 |
| publication与as_of | 原primary/provider date独立于capture；未知publication与after_asof不能completed candidate。query、FF reuse_only/fetch_if_missing、ensure及下游manifest/publicread保持同一截点，不能恢复后变成功历史source。 |
| 真withdrawn/损坏/未知原因 | 不更新active、不写assertion/restore audit；坏SHA/坏路径/缺失bytes具名失败。另一个真实可用hash等价副本仅经现候选校验复用。不能把metadata-only规则应用到任意retired。 |
| 原子失败/并发 | 在fact insert、projection、locations、restore audit注入失败：原status/旧facts/审计完全不变；原件字节不变。两个并发同源只一次semantic restore；过期audit/source pin具名拒绝，不半reactive。 |
| 幂等与资源 | 连续两次localreconcile零fetch、同ref/facts，第二次无新assertion/audit；共有期限和byte cap不扩大；外部readonlyroot不改，正常owned TEMP finally删除。 |

## 实际现存原件验收（由MAIN授权后集中一次）

使用`actual_raw_readonly_observations.json`四个真实原件及fresh_sources_preparation的有定位来源facts，在**独立临时catalog**建历史metadata-only退休状态；所有输入readonly、先后SHA同。通用操作不按公司/SHA分支。

- MSFT三份：actual DEI证明US/CIK789019/FY2026 Q1/Q2/Q3和period；用独立publication事实，完整旧retire历史与错误HK/FY25声明。localreconcile→公共query/ensure→实际FF入口→SourceRef→verifiedopen；0 provider GET/POST、0 download、0模型。跨接口FY与as_of严格，重复第二run仍0fetch。
- 中微2024年报：原件封面/issuer/year和真实SHA，publication date必须有独立有效本地来源事实；现catalog的2025-04-17与文件名/retire审计不能独自当新primary publication proof。证据齐则同上0fetch复用；证据不足明确local_metadata_gap/asof_unresolved、仍0download，先补事实，不能为四源全绿编造日期/URL。
- 把as_of设在实际publication前一天，以及publication=null，锁住跨FF/CWP/consumer的不合格结果；不得悄悄重fetch同一未来原件或借current capture时间通过。
- 真withdrawn与tampered raw采用自有tiny fixtures；不改四份原件做破坏试验。
- 明示engineering与实际supplier：offline adapter只作zero-count/拒绝监听，不提供成功下载fixture。本节点无真实supplier或paid model。

## Ownership/交付

MAIN先读本卡并更新主PWF，再授权独立worktree实施。候选责任为source_catalog的local inventory/read guard、source-fact transaction与source acquisition composition；FF仅若真实入口需薄接线，由FF owner独占完成；不扩大到Dayu修writer。正常精准commit、责任RED/GREEN和actual original零download单据。当前只读诊断不改代码/生产state。
