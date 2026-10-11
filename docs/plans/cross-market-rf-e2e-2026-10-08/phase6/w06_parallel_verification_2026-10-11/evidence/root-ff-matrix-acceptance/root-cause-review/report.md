# W06-FF-MATRIX 跨期阻断：ROOT 独立只读根因审查

## 结论

**确认 CWP 共用候选相关性和事实资格通道脱节（P1）。** 不是 FF 没有传下载请求、离线 fixture 没有服务，也不是缺人工签收。正常 provider→writer 入库的 FY2024 资料能按现有 reader 正常登记/验字节，但本地修复把其缺少“另一条修复断言”误当成 FY2025/FY2026 本期资料缺口，从而阻止 adapter 启动。

本轮仅只读源码和既有真实 public-boundary synthetic 留证；新证据只写本 `root-cause-review`。不改产品/tool/fixture/PWF/配置/真实原件，不伪造断言，没有重跑已有 8 秒 repro 或 41 场景。

## 实际证据

核对 `fix/cross-period-repro.json` 的原始 request/response/actual-indexed-facts 文件，**8 项已存 JSON SHA 均匹配**（3 个 CWP ensure response、2 对 FF request/response、1 个 actual facts）。结果见 `evidence-observations.json`，保留实际 indexed acquisition.request/candidate/receipt 摘要与 NULL 断言。

| 请求 | 真正的当前结果 | 执行证据 |
|---|---|---|
| US AAPL、CN 宁德时代 annual FY2024 初次入库 | `completed/downloaded_new`，有完整 SourceRef | 每个 discover/fetch 各一次；原件 619/621 B；SHA 实际入库；request/candidate/receipt 均为 FY2024/FY |
| 已存上述资料后，US annual FY2025 ensure | `not_found/missing` | `download_events=0`、`provider_started=false` |
| 已存上述资料后，US/CN annual FY2026 FF | `not_found` | 每次 FF calls=2、downloads=0；无新 adapter fixture 调用 |

两个已存来源的 `actual_verified_assertion` 和实际 evidence payload 都是 **NULL**，正常 acquisition 元数据仍完整保存 FY2024、身份、SHA/size、provider/request/candidate/receipt。不存在给 fixture 手填 source_fact_patch 的前提。

读取时 canonical HEAD 已是 `057f2f8d274a14019f59302095df4148d9e28c7b`；从 repro 基准 `8862372` 到该 HEAD 的 `src/company_wiki/source_catalog` Git diff 为空。13 个所读生产模块前后物理 SHA 相同。CodeGraph 命中了 writer/coordinator/resolver；新 local_reconcile/qualification 未入索引，随后按已知 import 读取当前文件，行号以物理源码为准。

## 责任链和具体代码

1. **入库边界接受正常 scope 声明。** `canonical_writer.py:226/444` 调共享 `candidate_scope_problem` / `receipt_binding_problem`，校验 request↔candidate 身份/市场/文种/财年及 receipt↔candidate；再验 staged 路径、size、真实 SHA。`:564` 持久保存 acquisition provenance，`:329` 注册，`:423` 返回确切已存 ref。它没有要求生成“steady source-fact 修复断言”。scope 声明已被检查，但不等于 SEC 原文 DEI 的独立语义提取。
2. **正常 resolver 知道旧资料不匹配。** `resolver.py:1296/1382/1390` 读规范 metadata，FY2024≠FY2025/2026 直接排除，返回无本期匹配；这里没有把旧年报冒充新年报。
3. **local prepare 又扩大回旧候选全集。** `local_reconcile.py:468/476` 仅按 kind/status 和 entity 筛候选，没有使用和 resolver 一致的已验 scope 相关性。旧 FY2024 仍进入 `:531` 的事实修复/原件验证 transaction。
4. **资格通道只承认修复断言。** `_prior_source_facts`（`:192`）只读 `get_verified_assertion(...reader="steady")` 的 `source_fact_patch`；非 SEC 原件在 `:206/307` 要求完整 prior patch。实际 writer-native acquisition 元数据没有消费入口，NULL patch 就是 `local_metadata_incomplete`，而不是“没有后续修复”。
5. **不相关失败变当前资料阻断。** `:569` 捕获这项旧资料错误后无条件 `targeted=True`；`:612/616` 汇总 `local_metadata_gap` 和 `blocks_download=True`。`:538` 的 `not_relevant` 分支本来可以正确跳过，但只有能拿到 prior patch/SEC 原文 scope 后才可到达。当前正常 provider 入库 PDF 在前一步已被挡住。
6. **采集和公开 DTO 又隐藏原因。** `acquisition.py:412/421` 把 local blocked 映射为 `AcquisitionStatus.MISSING`，adapter 的 `:437` 根本不执行；`acquisition_service.py:232` 原样变 missing，`operation_projection.py:98/116` 公开 not_found，`:120` 的 DTO 不带 local 原因。FF 只看到通用 `source_not_found`，导致看似缺资料却没有下载。

`restore_document_facts`（`assertion_service.py:439`）负责实读原件、并发观察 pin、原子事实修复；这是数据一致性责任。问题不是要取消该事务或 SHA，而是无当前请求相关性的旧文档不应被送进这个事务当先决条件。

## 已验入库 scope 能否复用：必须区分权威等级

**可以复用当前入库边界已经承担的资格观察，不能把 JSON 形状当权威。**

- Canonical provider import 已验证 request/candidate/receipt 声明一致和实际 bytes SHA/size，它应产出/保存 owner-qualified、source SHA 绑定的 scope。它可以用于请求相关性和来源选择；它不能冒充“我从原文 DEI 提取了财年/CIK”。
- 仅 scan sidecar 是观察到的用户声明。`.source.json` 恰好有 year/market/类似 acquisition 结构、目录像 canonical、文件名像 2024，都不能证明走过 writer，也不能以此断言“不相关”后绕过真实可能当前资料。
- SEC 原文 extracted DEI 保留现有 parser/locator 的独立原文资格。`_sec_original` 对 US HTML/相关 filing 会进入原文路径；`_proven_facts` 先 `_scope_matches`，真实旧期可早返回 `(None,None)`。本次实际 US fixture 是 **PDF**，不能扩成所有 SEC HTML 跨期都失败。
- 已有 metadata conflict、explicit unknown、不匹配 SHA、坏字段始终保留为 conflict/unknown。没有 correction assertion 的含义应是“没有修复覆盖”，不能全局否定合法正常入库观察；反过来也不能自动把未验 scan 升级。

实现上让 CWP 写入者在现有 SourceRecord/metadata/projection 中记录资格来源与 scope，读者共用 typed `SourceScope`/relevance API。若历史条目只有 sidecar 声明没有 owner provenance，则走现有有界验证/reconciliation，或真实具名 unknown；不要另开许可表、人工 receipt、canary/private/public 或第二任务库。迁移回放只消费实际 provenance 和实际 byte binding，不能手造断言或签名。

## 建议的系统改造顺序

### A. 先用失败定义共用责任

把本 repro 固化为公共 ensure 正负测试，而非修改 FF matrix expected 或 provider 资料来避开旧期。共用 scope 数据明确：identity、kind、FY/period、publication、content SHA、authority/source-origin、conflict/unknown。

共用匹配返回 `MATCH / NOT_RELEVANT / UNKNOWN`：

- `NOT_RELEVANT`（真正已验的其他期/其他代码/其他文种）只作诊断并跳过，不设 `targeted`，不阻断本期资料发现。
- `MATCH` 保留完整 ref 和真实字节验真，源状态、as-of、现有并发及资源限额由所属层负责；已有原件零下载。
- `UNKNOWN` 仅对可能属于当前请求的资料做有界本地补证；不能假装无原件、不能清洗成成功、也不能让完全无关旧期资料拖住整个公司。

resolver、prepare、acquisition 读同一 scope/relevance 观察；避免 selection 一套声明权威、repair 一套断言权威。同一执行中已经确认的实体/期间不重复换库求证，不按每阶段加身份门。

### B. 改公共结果的失败含义

保留数据资格失败，清掉许可含义。沿现有 versioned pathless DTO 传当前 relevant local `metadata_unknown/conflict/unavailable` 的具名原因及 `provider_started=false`，和 provider 真正空结果区分。采用一个 DTO 责任，不拼第三套 hash/审批链。FF 不自行再校验公司的磁盘目录/身份库；它消费 CWP 的结论、负责触发正确 provider 和不重下，并如实传达失败阶段。

不因为缺许可/人工 review 保留这种阻断；真正缺当前资料资格时是具体数据原因，不应写“等待授权”。

### C. 一个大节点收敛验收

Unit scope RED→implementation→有界 public ensure integration→现有 41 场景离线矩阵一次→独立审查→正常 repo gate/发布。不要每个 helper 增一层签收，不重跑 real LLM/OCR，不把 fixture 联调算真实 provider 或经济质量认证。

## TDD 测试包

详细机器可读条目在 `report.json.TDD_test_package`（15 项）。推荐三层并成三个大节点：

| 层 | 必须约束的正反例 |
|---|---|
| Unit | writer-native scope 与 scan 声明区别；source SHA/size/origin；旧期正确不相关；缺 patch 不否定正常 import；冲突/unknown 不升级；Q2/Q3、H1/FY、非周期文种不冒 FY；import 声明不冒原文 DEI |
| Integration | public ensure warm2024→new2025 一次新采集/入库，旧原件及 manifest SHA 不变；同一期 zero provider reuse；未验 sidecar 不假绿；当前相关原件坏 SHA/MIME 拒绝；metadata-only retirement 限定相关范围；latest-as-of 真实 metadata discover；并发锁/统一预算/恢复不退化 |
| Offline E2E/contract | 正确传播 local gap vs 真 not_found、零 provider 时不伪造网络/费用；同现有 FF→ET→CWP 41 场景联调，保留旧 FAIL、新正确 refs/usage；测试 unique 目录前后完整恢复 |

原件错 SHA 仍必须被拒绝。省掉的是不相关旧资料的重复事实修复和许可误解，不能省掉本期实际复用/入库字节验证。scope 身份只在来源所属层校验一次，消费者不重复深入底层目录。

## 范围和 STOP

本共因证实的是 **CN/US synthetic PDF annual 跨期**；HK、半年/季报其他 matrix FAIL 还要绑定各自当前 metadata/period normalization 证据，不能宣称全被这一个修复覆盖。入库 scope 声明有效不等于其经济事实真实；未做真实网络/LLM/投资质量检查。

13 生产模块前后 SHA 不变，8 个原始 JSON SHA 匹配；没有生产/tool/fixture/PWF/raw 写入，没有新 provider/LLM/费用，没消耗预算。已完成独立只读诊断，**STOP，由 ROOT 施工。**
