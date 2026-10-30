> 2026-10-30 M6发布后当前指针：M1–M6本局部已验收发布；本文件是原实施细则，禁止作为新待办重开。 唯一当前状态在上级CURRENT_STATUS.md/json；下一操作见 [M7](M7_C3_SOURCE_HOLDOUT_NEXT.md)，最终证据见 [M6验收](m6-source-evidence-2/README.md)。

---

# 实施细则：摘要覆盖/保真与非期次复用

基线6894f5ee，选定PWF不变。独立设计审查在本机 `.planning/summary-quality-20261030/{summary-design.md,nonperiodic-design/review.md}`，发布工程节点时归档。只在大节点独审，不增加材料授权或小节点签收；原件、生产配置、原生收费账保持。

## M1 非期次文档复用（先闭合已存在接口）

调查已推翻“必须给FF再造模式才能读取IR”：RF已提供 `prepare_registered_source_result` 和 narrative reference/read；前者被adapter与forecast证据合同两处HTTP URL假设阻断。由RF新增一个纯source provenance owner统一校验：HTTP URL保持原规则；严格 `url=None` 接受完整CWP SourceRef/manifest/read receipt/capture绑定的已验证原件。空字符串、伪URI和物理路径不伪装成URL。SourceCapture必须真实，未知发布日期由现有2.2 availability证据负责，不伪造FY/发布日期；无论require_capture开关，null URL必须保留完整来源链。不要新造身份库/审批/强制provider查询，不放宽valid_source_url(None)。

先写已登记IR/IPO/可转债及跨市场中性夹具TDD；反例包含SHA/原件身份/期间错配、删capture/trace、未来发布日期或历史cutoff不足、空/伪URL。所属路径RF `scripts/contracts/source_provenance.py`、`contracts/document.py`、`company_wiki_source_v2.py` 及新tests。RF预存assurance/runs三个WIP只记录SHA不暂存/回退。FF新增SourceRef输入作为独立产品能力缺项，暂不让它阻塞已有RF读取路径，也不把RF只读准备等同实际预测采用。

## M2 共享引擎的源码业务事实/优先级

在source assertion owner修“已销售产品组合/已开发数量”等真实经营观察被判纯description的共因。中英文/繁体、不同未知产品名、静态客户链与已发生/计划/否定区别、模板/抽象愿景/财务结果负对照；读取分值和SourceCard只投影已有观察，不再读一次正文或调高额度。既有0.8回放范围保持；独立新阅读策略版本和决策依赖对应更新。

## M3 新明确摘要协议与机器可读评估

保留现有/4与/5协议和旧artifact字节，新增明确协议identity（不复用已占用的extractive/5）。提示明确选定可支持任务的覆盖、归属/程度/条件不丢失、单modality分句，不因description语法忽略有业务价值的内容。共用解析器参数化期望prompt，不复制两套完整decoder。

复用SummaryTaskPlan.coverage及source admission；分开source-admitted、实际requested、最终retained。unavailable/duplicate明示排除；因预算未发送仍为budget_deferred；task emitted只表示有输出，不能证明该task所有子事实已覆盖。新bundle/raw2.1、projected3.1（最终版本以共享resolver为准）包含program-owned summary_assessment；SummaryResult DTO无需多造partial分支。producer、generation_manifest和effect key共用同一协议→实际schema/producer解析函数，旧2.0/3.0回放/hash保持。

评估绑定冻结source plan/admission/validator identity。source replay与extraction quality、task emission、summary semantics分别展示；未审语义明确not_evaluated。guard仅对可定位且命题绑定的已知来源限定做有限诊断，不从别的句子借“据/将/未”；没有发现违规不能变成semantic pass。若改变needs_review，应在旧quality projection之后应用，不能被其覆盖。诊断不新增人工许可，不把全部未知都变成阻断。

先不恢复已退役的付费coverage repair，不自动额外POST。已有真实v3 input/response/bundle作为离线反例；遗漏与归属问题修复后，才以当前配置小样本真实验证。若确需explicit bounded continuation，后续单独在现有AUTO run/lease/outbox预算内设计，不复活旧partial DTO/immutable零slot或第二库。

## M4 验收与发布

每个工程大节点：TDD RED→限定域绿→独审稳定版本→正常commit/push→精确CI；不反复全仓超时检查。新协议与M1均闭合后，真实原语言摘要8个冻结检查点与独审、paid response持久化/activation/restart/crossrun零重复POST、RF existing narrative消费与实际parameter/formula依赖采用分别验收。需要恢复测试湖时只走owner合法接口，不手写accepted数据库或篡改已付费generation。测试资料在独立owned目录，结束恢复；不新下载已有原件、不开全PDF批次。US RPO/W21 canonical C2/长路径/holdout及完整公司循环不冒签完成。
