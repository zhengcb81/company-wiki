# 官方 JSON → AUTO：MAIN 实施细则

## 1. 边界与写集

这不是新增 provider。复用已验收的 official JSON parser/projection。下载原件、source manifest、字节/公司/公开时间和投影有效性由 source 层负责；AUTO 负责有限任务、精选、摘要、预算、恢复与派生发布；RF 消费来源不属于本卡写集。

MAIN 独占：

- `automation/narrative_batch.py`、`narrative_contracts.py`、`execution_context.py`、registry 和 batch CLI。
- `narrative_formats.py`、`narrative_select.py`、`narrative_generation.py`、`narrative_replay.py`。
- model input/summary/verify、`narrative_projection.py`、`narrative_transport.py`、transport contracts/evidence view。
- `AutomationStore` terminal compaction/pin 及既有 run store 的必要共同身份访问；不新增第二库。
- `source_catalog/cli.py` 的薄 official 子命令。
- 上述责任测试与本目录证据。根 PWF、生产配置、真实模型预算和发布仍只归 MAIN。

源层 parser 已接受，除证明 source 缺陷外不重新改写；必要处理 descriptor 由 source 层公开 port 给出，handler 不自行读库或猜目录。新类型内部名称按当前代码冻结后在本卡记录，不以名字代替完整测试。

## 2. 单一内部 subject/view，而非多套流程

内部规范对象包含：kind、item_key、真实 parent refs、issuer/as-of、可选 projection ID/SHA、parser/layout identity、coverage、selected original-language fields。Raw 的 item_key 继续为 document_id；投影为 projection_id。旧 raw DTO 适配进此模型，新 projection DTO 同样适配；共同流程不复制成第二套 select/summary/recovery。

投影输入只给 compact projection ID/SHA，由 source port load/replay 得到不可变 verified view。单次操作复用此 view，避免各 handler 重复全量解析；独立公开读取仍在它自己的责任边界实读验证。多 parent 的每条 evidence 都绑定实际母页，不能全部强制等于第一页。

request、事件、generation、pin、恢复、最终结果和读取共用 item identity accessor。模型/摘要/renderer 不自行恢复目录，不自行重做来源审批。artifact 若需真实 parent 作为外键锚点，必须明确只用于关联：metadata 保存完整投影身份/parents，查询以 item_key + generation SHA 选择准确 artifact，不按母页 latest 猜公司。不创建虚构 source/document 行。

## 3. 公共合同最小升级

旧严格版本不偷加字段，旧恢复语义不变；内部 helper 不分别建协议。SourceRef/SourceExport 2.0 原义保留，原页始终原页；复用已有 source-projection-ref/1，但不把含 records 的完整对象塞进全部 DTO。

建议有限 batch `/2 items[]`（旧 `/1 sources[]` 保留）；投影 source event/select/summary/bundle 显式 `3.0`，旧 raw `2.0` 保留；投影 generation `/2` 和 run binding `/4` 仅在旧版本无法表达新 subject 时使用，旧 raw `/1` 和旧 binding `/1–3` 恢复不改变。投影 reference/read 显式表达 projection identity，不能按原件引用冒充投影。

实现前先从现存 DTO/store 验证这组最小集合；若现有同一 DTO 可合法表达，不新增版本。版本表达数据语义，不做逐材料许可或版本协商人签。

generation 绑定真实 parent refs、projection ID/SHA、issuer/as-of、实际 parser、layout ID/version/fingerprint、selector/profile，以及现有 model/endpoint/parameters/prompt/bundle producer。配置变化只影响相应 generation；不得跨公司/期间/布局/模型误复用。未知或失败 usage 沿原 ledger，不清零。

## 4. 路由、原语言与角色

- 已登记官方 provenance/layout 或显式有效 projection 才进入 official_json。FMP JSON/TXT 电话会仍按 transcript；未知官方布局保留 raw、typed unsupported/pending、0 模型调用，不能 fallback transcript。
- `SourceVersionReader.describe_version` 目前不导出 official_source_subject/layout，不能只改 MIME 分类假设这些字段存在。优先从显式投影 input 加载；自动分类所需有限 processing descriptor 放 source port。
- JSON→narrative 薄 adapter 保留 original role，同时显式 source_role。investor_question 保留问题；明确公司回答/致辞可为公司来源，speaker_unknown 不伪造已知管理层姓名。event/unclassified/translation 不提升为管理层断言；译文不是第二独立证据。
- Q&A 成员各自 role/locator，按 record 分组；不得用组第一段问题的角色覆盖整组，也不得按物理相邻拼接不连续 quote。
- 只用本公司选中的原语言字段检测语言。JSON key、其他公司文字和译文不参与判定。空/缺页不宣布“全文完整无业务”，保留真实 partial coverage。

## 5. 终态、发布和 public CLI

subject-aware 身份须贯通：execution context event.subject → generation lookup → effect target → artifact pin → terminal receipt → compaction → transport reference/read。保留 raw 旧 narrative-bundle target 解释；新 target 明确 projection identity。坏匹配 artifact 给具体损坏错误，不默默新收费。

沿已有 lease/generation/outbox 工作流。模型完成、ACK 前和 ACK 后激活前的中断分别恢复一次，证明一次结算/一次发布；不是新建许可链。reuse 只读取准确已发布 artifact。

`source-catalog official ...` 薄调用现有 official_source_cli.main，不重新实现 importer。dispatch 要在外层 stdout reconfigure/JSON print/catalog 生命周期处理之前；official read 保持原始 stdout bytes，不 print/重编码。使用 owned 临时 catalog，避免写生产 source_catalog.yaml。

## 6. TDD 责任测试包

先保留真实 RED 输出，再实现，共同责任通过后只做一次集中独立审查。没有每步人工审批。

| 测试组 | 正控 | 负控/期望 |
|---|---|---|
| 路由/语言 | multi-issuer 官方 JSON 与既有 FMP transcript 各正确路由 | 未知布局 typed unsupported，模型 0 调用；共享其他公司/译文不能改变语言 |
| 角色/定位 | 冻结 record36395 非空回答、answer-before-question、questionType3 致辞、speaker unknown | 问题不能支撑公司断言；translation 不是独立来源；组成员角色不丢 |
| identity | 同母页 A/B 公司各独立 item/event/result | wrong issuer 拒绝消费；不会 document_id 去重成一项 |
| 多 parent | 两页投影，各 span 引用正确母页 | 第二页改字节或字段绑定，第一页锚点不变也拒绝 publish/read |
| coverage/as-of | 完整与 partial 均如实传递 | 缺页/重复冲突不伪造完整；answer update 晚于 cutoff 不采用，未知日期不猜 |
| generation/reuse | 同投影同配置第二 run 0 模型调用、准确同 artifact | issuer/as-of/layout/parser/model 任一变化不能错误复用；匹配坏 artifact typed error |
| terminal/recovery | event→effect→pin→receipt/compaction 全部同 item | ACK 前/激活前中断只结算/发布一次；unknown ledger 不清零 |
| 公共 CLI | import→project→AUTO→local stub summary→verify→publish→read→reuse | 真实 stdout raw bytes不重编码；读取错 projection/company 明确拒绝 |
| 历史兼容 | 旧 PDF、TXT/FMP JSON、2.0 bundle/read、/1 batch | 新 projection 字段塞旧严格版本仍拒绝，旧原义不悄悄变更 |

集中包使用实际 parser/source port/store/Worker/CLI，仅供应商摘要为本地 HTTP stub；不用假的完整 JSON parser，也不用跳过 verify 的 hand-built bundle。stub 不能证明真实模型或投资结论。全链记录 module/version、exit、fixture/raw SHA、selected evidence、artifact/generation、provider/model calls、ledger、TEMP 初始/恢复；仅保留小必要证据，不复制真实全库。

## 7. 完成与交接

完成条件：责任测试由 RED→GREEN；上述公共链和恢复/兼容集中通过；独立关键不变量审查无未解决主要问题；原件/config SHA 与测试目录恢复；normal commit/push、精确 HEAD CI 通过。留 receipts、测试命令/真实结果、具体限制和 next step；不因 stub 全绿签真实研究。

之后继续根计划 W04 失败 final body 有界诊断、W03 精选业务内容、W05 profile/caps、W08/W09 校准/时序/stress；再原三家四独立审查、新 A/H/US 三家、冻结 NVDA/池循环。条件八家公司目标在原目标真正完成后才启用。

## 最终独立只读审查：补充存储与构造不变量

Catalog narrative_artifact_versions 的 document_id/source_id 为真实 documents/sources FK，现有 prepare/activate/read_current 只验单 active primary。投影 ID/SHA 不填原件列；同一 artifact index 增显式 subject binding 或同 store 的多 parent 表示，真实 anchor 仅关联。投影读取必须以 subject ID + projection SHA + generation 精确查找，旧 latest_visible_version(document,source,sha) 不用于投影发现，所有 parents 由 source port 校验。终态压缩、effect target、pin、generation 和 public read 共用身份解释。

独立纯内存实证：同一合法两页集合倒序输入，complete 都 true，但 projection_id 不同。新建投影时对可证的声明页顺序规范化，不能重签已封存 ID；保持真实记录内顺序/定位，不把不明分页猜成完整。相同合法页集合不同枚举顺序必须生成相同新投影/generation，防止重复付费。SourceProjection 只有浅 frozen，issuer dict 可变而旧 SHA 不变；新的 verified view 必须深冻结或隔离复制，调用方后续变动不能污染 view 或缓存。

三项集中必测：①同页 A/B 独立 subject/DAG/artifact，原件一份，交叉读取拒绝；②两页同 pointer 仍各自母 SHA，第二页字节/状态/绑定变化、问题冒充答案均拒绝，partial/cutoff保持真实；③相同语义精确零调用复用，变任何绑定不能错复用，ACK前/激活前恢复一次结算/发布且旧lease不能完成新generation。首次验证不是永久许可证：publish/后来 public read 在所属 source 边界核当前父页集合，handler 不各自重复解析。仍用现有 AUTO DB，不新增任务账本。

只读审查：/root/m3_usage_acceptance 与 /root/m3_joint_acceptance_review；均未写源码/配置/原件/数据库/安装，provider/model/费用0。这是下一节点接口风险与TDD要求，不是本节点实现完成。
