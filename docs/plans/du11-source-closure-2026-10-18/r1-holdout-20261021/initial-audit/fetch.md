# 独立二号采集复用审查：药明康德 initial

结论：FAIL。执行包可复查但仍 partial；不是来源覆盖或预测质量通过。未读取其他 reviewer 初稿，未启动网络/provider，未改产品。
绑定 manifest SHA：`ee08753799d7d2a849dd3fd9c811e7c0e83d20d7538f978218245fdf98dca458`。CWP 初始 pin 646b6937、FF e8740748、RF 9669c4d7。本角色归档了 pinned 源码，当前相关代码与 pin 经 LF 归一一致。

年报 FY2025 与 Q1 FY2026 真正通过 FF/CWP 复用和 verified read。正式最终RF只消费 qualified annual（7f1431…）。四份原件均同 SHA，新增 raw=0。两次官方同字节核验 GET 实收 entity 正文 **1,905,400B**；wire 与 web bytes unknown，不能写零传输。

关键原因按真实时间分列：

- 早次 native ensure：blocked/local_metadata_gap/publication_date_unknown，provider_started=false。
- scope-facts 后，2025H1 对 2026H1 已是 not_relevant。最新 journal 21:20:22Z 是 **local_candidate_limit**。只读窄 probe 复现默认16候选，第17个未登记目标仍为2018–2022历史财报；注册0、provider0。
- FF operation1.0 closed contract 不接 local_preparation/blocked/unavailable，统一变 invalid_producer_schema；最终 matrix 沿用早次原因。
- FY2026Q2 companion 实际被请求但未调ET；不能宣称FMP entitlement失败。FF error serializer却写not_requested，RF没有完整独立companion结果。

| 检查 | 状态 | 观察 |
|---|---|---|
| F01 | PASS | 实际 source_preparation.py → 指定 FF 仓入口已启动；CN 药明康德/603259 由 CWP identify 返回 verified/active，annual FY2025、Q1 FY2026、H1 FY2026 与 2026-10-21 均在冻结确切输入。15 个相关 CLI capture 的输入未被输出覆盖，stdout/stderr/exit 实读。成功不由外层 exit=0 推定。 |
| F02 | FAIL | 请求与 SourceRef 为 v2，reuse_only/fetch_if_missing 明确；没有旧双授权/receipt/canary 阻断。但本次 current CWP ensure 返回 local_preparation + blocked/unavailable，FF 同为 operation 1.0 的 closed contract 不接受，实报 invalid_producer_schema。 |
| F03 | PASS | 年报与 Q1 最终真实 reuse→CWP verified_read，source SHA/size 与原引用相同，download_events=0。旧 H1/IPO 公开 preview/source_export 可开但 published_date/source_url 未证，不被冒称 capture-ready。另有官方同字节核验 GET，单列传输不计新增 raw，也不宣称从未联网。 |
| F04 | BLOCKED | H1 请求具备 50 MiB、180 秒、$0.00 且精确 2026/H1；两次 FF 尝试和一次 native ensure 均未启动 provider。早次 publication gap；最新旧期排除后在本地 discovery 的第17个未注册历史目标触及16候选限额。没有证据验证真正 provider 读取时的下载公司/版本/bytes/time/fee enforcement；不得把配置存在视为 runtime PASS。 |
| F05 | PASS | 本 CN 任务配置适配器 stockinfo-cninfo 1.3.0 → StockInfoDLSimple/v2-clean-rewrite json_command_v1，未使用旧 StockInfoDownloader。HK/US 配为 CWP-owned dayu_sdk_bridge bounded 路由且未执行；此 PASS 只覆盖本次选择/配置边界，不证明未跑市场的网络下载。封存配置指纹未变，未见本执行编辑 Dayu 证据。 |
| F06 | BLOCKED | 精确 FY2026 Q2 companion 请求存在，既未把 FY 年报推断成 Q4，也未转换 PDF 或翻译；但 filing 在 companion dispatch 前失败，没有 ET HTTP/provider 真实结果。ET 工具位置已配置；FMP 凭证、capability、entitlement、费用本次均未验证，不能归因为供应商不支持或订阅拒绝。 |
| F07 | FAIL | 成功年报/Q1 envelopes 保留各自 filing 与 transcript.not_requested；请求 companion 的 H1 错误却在 RF stderr 仅保留 filing failure，缺独立 companion outcome。FF error_envelope 无条件写 transcript.not_requested，即便请求确有 companion；离线纯函数 probe 证实该语义，不冒充一次 ET 运行。 |
| F08 | FAIL | 12 类矩阵全部有价值判断，没有因本地缺文件自动 N/A。可用 annual/Q1、历史 IPO preview 的 kind 没有互冒；但实际最新 IR/演示/战略材料、融资原件、最新交易与独立运营基准仍只 discovery/部分读取，不能据配置的财报 provider 宣称已采齐这些类型。最新材料会影响收入模型。 |
| F09 | BLOCKED | 两个官方 HTTPS 核验 GET 观测 status200、entity正文SHA/size 与现存 PDF 精确相同；CWP 原件 verified read 和 PDF页提取排除了空体/HTML当财报的本次结果。GET 无 outer capture，receipt 未留 Content-Type、Content-Length/encoding/wire 字节；无法核完整 HTTP一致性，也未证明 helper 的 response读取受 max_bytes 限制。 |
| F10 | PASS | CWP source-facts/verified reader 完成校验；RF 消费 pathless SourceRef，不自行搬入 provider 输出目录。正式原件只读根，隔离 catalog/下载根与派生目录受 scope 限定。acquisition observation cost=null/未知未猜零；无无界重试和新供应商订阅证据。 |
| F11 | FAIL | 文件存在/metadata unknown/provider未开始本可区分，但 FF 将 CWP JSON catalog_unavailable（CLI exit2）标作 producer_transport_failure，并将 named local preparation 状态标成 invalid_producer_schema。最新 matrix 又沿用早次 publication gap，实际21:20 journal 已变 local_candidate_limit；RF收到的原因不足以定位最新阻塞。 |
| F12 | PASS | 审查阶段按范围保留隔离 catalog/summary 供四路复查；封存 final verification 4份原件同SHA且新增raw=0，production config unchanged。现阶段无新增raw需清理；派生物清理须待复审/重放结束按 owned scope，不能提前删除现存原件。 |
| F13 | PASS | 本次无 JSON 默认当 transcript 的登记/消费；注册对象4份PDF归并为4 source ids，源事实kind为annual/semiannual/quarterly/prospectus。scanner 的 transcript classification 取显式 sidecar/标题语义，未按.json后缀默认判电话会。ET原JSON路径未执行，不能推广成ET内容质量已通过。 |
| F14 | PASS | SourceRef用raw content SHA/byte_size与document/source ID；PDF页提取和 narrative 作为派生内容另有引用。HTTP receipt bytes 是response entity长度，不冒称wire字节或新raw；pointer不是原件。最终RF sources仅qualified annual，IPO preview没有伪装成可用current参数。 |
| F15 | FAIL | 本次不能把未执行的ET写成missing config/unsupported/entitlement/HTTP失败；实际fetch错误是本地catalog/metadata/candidate limit与FF合同不兼容。named CWP unavailable/blocked未正确传给RF，影响四类差异化恢复。模型MiMo401是narrative另一路，非本次filing/ET HTTP失败。 |
| F16 | PASS | 按实际范围计量：archived ensure 明确 provider_started=false、usage_complete/wire_usage_complete/http_exchanges_complete=true，0 wire/entity/exchanges仅是该操作；cost=null。两次verification GET另有1,905,400 entity字节、wire=null，web传输unknown，未猜总量零。native模型预算39,026 charged tokens/9,720 microUSD proxy或hold、actual cash null，与filing provider量分开；没有费用每result重复。 |
| F17 | PASS | 相关15次CLI各有独立capture、真实stdout/stderr/exit及确切输入。相同annual请求重复尝试是独立call，不复制一次capture当多个result；annual/Q1 source id/period正确各属其请求。未运行multi-document filing batch，故不把未覆盖batch分派路径称已验证。 |

| 文档类 | 实际覆盖 | 本审查说明 |
|---|---|---|
| annual_report | REUSED_VALIDATED | history/base/segments/policy/management targets |
| semi_annual_report | BLOCKED | 早次publication_date_unknown；latest21:20:22 local_candidate_limit。未把2025H1错当2026H1，也没有provider HTTP启动。 |
| quarterly_report | REUSED_VALIDATED_NOT_MODELED | Q1 exact source qualified; forecast authoring retained annual only. Issuer IR discovery listed Q1 and H1, no Q3 original qualified by cutoff; no inference from quarter end. |
| investor_relations | DISCOVERED_NOT_CWP_QUALIFIED | Official H1 press opened, including newer annual revenue guidance; not silently presented as native qualified evidence. |
| investor_presentation | DISCOVERED_NOT_READ | Issuer H1/Q1/JPM presentation listings found; actual PDF presentation was not CWP qualified/read. |
| strategy_communication | DISCOVERED_NOT_READ | JPM 2026 presentation found in official index, not marked checked. |
| investor_call_transcript | BLOCKED_NOT_EXECUTED | 请求不是discovery_only：frozen companion intent=fetch_if_missing，FY2026Q2，限额均已给；实际未dispatch。 |
| prospectus | PREVIEW_ONLY_PUBLICATION_UNKNOWN | 2018 issue context and substantive business chapter PDF248-263 read via preview; p248-251 inspected. Historical CRO/CMO/FTE/FFS definitions do not substitute for current 2025 recognition policies. No current revenue parameter sourced from this unqualified preview. |
| convertible_bond_prospectus | OFFICIAL_ANNOUNCEMENT_DISCOVERED_READ_NOT_QUALIFIED | 所读1225308070为融资公告，不是convertible prospectus；仅完成事件发现/部分条款用途读取。 |
| equity_offering_prospectus | DISCOVERED_NOT_COMPLETE | 2025 H-share placement and 2026 convertible-to-H-share event leads found; annual discusses historical perimeter. No automatic N/A by missing local file. |
| regulatory_filing_transaction | PARTIAL | Annual disposal/perimeter/policy pages read; latest H1/standalone transaction audit/pro-forma and post-filing regulatory originals remain unresolved. |
| independent_operating_reference | NOT_COMPLETED | Independent numerical operating ranges not verified. Conditional rates remain unverified with observed_range null; publisher-cited third party inside annual is not independent corroboration. |

## Findings

### FETCH-001 · P1 · code
CWP ensure 的 local_preparation/blocked/unavailable 未被当前 FF operation1.0契约接受，结构化原因降成 invalid_producer_schema。

预期：命名的来源资格/本地限额结果经FF→RF保持同义，provider是否启动和usage不丢。
实际：native capture返回blocked/publication_date_unknown；FF frozen H1调用两次都invalid_producer_schema。
责任与原因：FF跨技能合同；CWP公开operation契约。已定位：FF _SOURCE_OPERATION_FIELDS缺local_preparation，STATUSES缺blocked；当前CWP operation projection会生成该字段及状态；纯validator probe实际拒绝。
建议：由两端契约owner统一版本/字段与status映射，并保留safe local-preparation原因；不删字段伪造completed或放宽到任意JSON。
复测：用本次真实blocked与最新unavailable envelope经FF→RF重放，断言同义原因、provider_started=false、cost=null，无下载。
证据：[stdout.txt](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\commands\5173af840b924d96a40dbb93722660c4\stdout.txt) `/`; [fetch_filing.py](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\pinned-source\filing-fetch\scripts\fetch_filing.py) `L687-L747`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/ff_contract_probe`

### FETCH-002 · P1 · code
最新2026H1无法启动下载：identity-only discovery先枚举旧历史文档，第17个未登记目标触发local_candidate_limit。

预期：已证不同期间的2025H1不应成为2026H1 publication gate；在任务限额内能有界查明目标期是否缺失并进入正确provider。
实际：21:20:22 acquisition journal reason=local_candidate_limit；readonly probe 4groups/75entries、注册0、network0，17条目标均2018–2022历史财报；oldH1 scope relation=not_relevant。
责任与原因：CWP本地来源发现/采集编排。已定位机制：_discover_source_groups只接identity、不接request，计所有issuer未注册文件；默认max_candidates16，目标注册前整体失败。早次pub未知是真实前一状态，不能用于解释最新失败。
建议：保持有界策略，改为按来源层可验证的目标kind/period逐步发现/登记和可恢复cursor，避免无关历史候选耗尽本次请求；不得简单无限扩限或把未知身份当无原件。
复测：隔离真实同公司库：>16历史文件+缺2026H1；验证旧期排除、候选限额保持、目标期进入CN provider或准确报能力限制，真实下载限额在读取期间生效。
证据：[probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/acquisition_journal/lines/1`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/discovery_probe`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/old_h1_scope_probe`; [local_reconcile.py](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\pinned-source\company-wiki\src\company_wiki\source_catalog\local_reconcile.py) `L325-L365; L453-L471`; [local_inventory.py](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\pinned-source\company-wiki\src\company_wiki\source_catalog\local_inventory.py) `L16-L22`

### FETCH-003 · P2 · observability
封存最终document_matrix沿用早次publication gap，未反映最新local_candidate_limit。

预期：每类doc最新状态绑定真实最后call/journal与attempt，早次失败保留历史。
实际：documents/1 request_id指latest d20c7，却reason写publication_date_unknown；最新journal不同。
责任与原因：执行记录/审计观测；FF原因透传为关联因素。executor矩阵authoring沿用旧diagnostic；FF错误遮蔽增加误诊风险。
建议：由实际latest call/result/status join生成并核对矩阵；分别保留early与latest，不回填封存历史。
复测：对initial与scope-facts后两个attempt关联request_id/capture/journal，latest reason应准确且旧reason仍可查。
证据：[document_matrix.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\document_matrix.json) `/documents/1`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/acquisition_journal/lines`

### FETCH-004 · P2 · config
隔离cold catalog未就绪触发catalog_unavailable，FF却报告泛化producer_transport_failure。

预期：有限bootstrap/注册在准备层完成，或把有效JSON unavailable及原因传给RF；不能把有效业务失败当transport或provider网络错。
实际：first-query stdout=JSON unavailable/catalog_unavailable、exit2；initial RF stderr为query producer_transport_failure；手动bounded register后才进入metadata资格路径。
责任与原因：隔离准备配置；FF transport错误分类。准备层初始catalog空/未就绪；FF对子进程nonzero只取退出分类而丢有效结构化业务body。未发现需要重新人工批准。
建议：准备层明确empty catalog生命周期，FF保留有限validated nonzero envelope；不启动全库scan，不复制raw到消费者。
复测：从同样空隔离catalog启动reuse_only：得到准备层具名初始化或准确catalog_unavailable，零provider/下载；再有界注册验证复用。
证据：[query.call.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\diagnostics\first-query\query.call.json) `/`; [query.stdout.txt](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\diagnostics\first-query\query.stdout.txt) `/`; [stderr.txt](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\commands\f209dd4887f948b5ae415642a9956d08\stderr.txt) `/`; [stdout.txt](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\commands\35e1764be41445a3a855fb47b1f2e59b\stdout.txt) `/`

### FETCH-005 · P1 · research
最新H1、IR/演示/战略、融资与外部运营基准未完成来源资格/消费，完整RF来源覆盖不足。

预期：所有有重大收入价值的文档类完成适当合法入口的发现/必要读取，能力缺口具体记录；正式final不能把partial矩阵作为全覆盖。
实际：12类都有评估，但最新H1 blocked、IR仅web、presentation/strategy没读、融资只公告部分、独立numerical reference未完成；Q1已qualified却未进入模型。
责任与原因：执行/研究完成度；产品依赖另见001/002。H1为CWP/FF产品阻塞；其余为本次执行/研究未完成或入口能力尚未实证，不能全部归成外部provider缺能力。
建议：专家分别排修产品依赖并完成已发现material文档的合法来源读取/资格；非财报不能冒用CN financial provider能力，未知供应能力如实交接。
复测：复跑12类矩阵，逐类保存需要/已有复用/真实缺失尝试/有依据无重大价值，并核正式RF最终source版本及使用关系。
证据：[document_matrix.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\document_matrix.json) `/documents`; [remaining_items.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\remaining_items.json) `/remaining`; [discovery.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\discovery.json) `/records/1; /records/3-4`; [timed-final-forecast.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-forecast.json) `/sources`

### FETCH-006 · P2 · observability
官方同字节核验GET未在调用前capture，HTTP观察与读取字节上限证据不完整。

预期：必要qualification verification也应按任务现有byte/time预算有界、留真实HTTP状态/type/length与entity/wire区分；原件不额外持久复制。
实际：2个requests.get timeout60各整读resp.content，存status/entity长度/SHA但未存headers/wire、无outer capture；正文合计1905400B，实际未超50MiB；webbytes unknown。
责任与原因：执行helper/HTTP观测；来源qualification接口。已读helper qualify-annual/q1分支采用未stream限制的requests.get；回填receipt并非原始HTTP header证据。核验本身对未知publication有价值，不判成无理由重复原件入库。
建议：将必要官方byte qualification纳入来源owner现有有界读取/观测接口；保留unknown wire，不把0newraw写成0network。
复测：限额内与超限/HTML/空体fixtures验证stream截断、status/type和wire/entity观察一致；真实复跑只做必要qualification，不为审计重复下载。
证据：[tool_call_index.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\tool_call_index.json) `/uncaptured_operations/2-3`; [annual-official-byte-comparison.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\qualification\annual-official-byte-comparison.json) `/`; [q1-official-byte-comparison.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\qualification\q1-official-byte-comparison.json) `/`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/http_totals`

### FETCH-007 · P2 · data
已有2025H1与2018IPO publication/URL未知，无法作为截止日内qualified来源使用。

预期：未知published_date如实保留，由所属来源层用可信原始发布记录/精确byte关联补齐；不能凭文件名/mtime猜日或要求无理由人签。
实际：两个原件可preview并保留SHA，source-facts正确记录null；IPO只能历史业务preview，旧H1不应阻新期（latest相关性已排除）。
责任与原因：CWP来源事实/历史元数据。来源历史元数据不足；并非文件缺失、provider账户拒绝或原件损坏。
建议：在有重大价值时从已有官方来源记录校验publication/URL并绑定同SHA；不为填日期发起无必要重复下载，也不将缺失自动N/A。
复测：原字节不变；补齐前仍preview-only，补齐后用途及as_of资格明确；不同期间查询不受未证publication历史文件阻塞。
证据：[source-final-verification.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\source-final-verification.json) `/verification/0/source_facts; /verification/3/source_facts`; [document_matrix.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\document_matrix.json) `/documents/7`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/old_h1_scope_probe`

### FETCH-008 · P2 · code
被请求的companion在filing异常时无完整独立结果；error_envelope将其标作not_requested。

预期：真实requested但未dispatch的companion应保留精确period/intent及not_run原因，与filing失败分开；ET外部能力与费用仅按真实工具结果。
实际：FY2026Q2/50MiB/180s/$0在两次frozen request中明确；RF错误无transcript；纯函数error_envelope携request仍not_requested。没有真实ET/FMP entitlement或HTTP失败结果。
责任与原因：FF companion orchestration/envelope；RF失败结果保存。FF只有resolve_filing返回handle后才调companion；exception envelope硬编码not_requested；RF source_preparation失败投影未保留完整child结果。
建议：对requested companion生成独立具名未执行结果并留envelope；需要时按任务既有授权走ET独立原工具，有界按精确FY/Q请求，不从FY臆造Q4。
复测：真实filing failure+requested companion时结果不能not_requested；独立ET查询若执行必须保留原语言TXT/JSON、精确季度、真实provider_requests/bytes/cost或null；不可用保持具名。
证据：[input-0001-f4199aabf7c6.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\commands\d20c7b3f9b36473ab51dc984e40d8bb8\input-0001-f4199aabf7c6.json) `/companion_transcript`; [stderr.txt](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\executor\commands\d20c7b3f9b36473ab51dc984e40d8bb8\stderr.txt) `/`; [probe.json](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\probe.json) `/ff_error_envelope_companion_probe`; [ff_v2_envelope.py](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\pinned-source\filing-fetch\scripts\ff_v2_envelope.py) `L146-L154`; [fetch_filing.py](C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\fetch\pinned-source\filing-fetch\scripts\fetch_filing.py) `L1496-L1522`

未完成能力与准备失误分开记录：StockInfo/ET真实provider读取没有验收，最新IR/演示/融资与独立参考是有意义的待完成工作；旧H1/IPO publication缺口为来源数据不足。无需新增逐文档人工签收。当前停止在独立审查，修复和真实复跑由协调员/专家统一安排。

细项 artifact+locator+SHA 以 [fetch.json](fetch.json) 为准；[probe.json](../roles/fetch/probe.json) 只证明所列本地读取与窄诊断，不证明原始GET/header或provider成功。
