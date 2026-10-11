# 独立最终 DOCX 标题定点审查：accepted_for_reviewed_scope

审查时间：2026-10-11T02:28:06.328764+00:00。本次无 material 发现，关闭旧 NATIVE-DOCX-HEADING-01；接受所审解析、strict selector 和真实公共旧历史/新 generation 责任。新 HEAD 远端 CI 尚未执行，本报告不代签该发布门槛。

最小原件 SHA `c29c7c0d1a40da78cdf6215bb9675f27773b461af49d71f8e1877136d944702c` 原封读取。实际默认 DOCX `1.1.0` 将 Heading1 解析为 `docx_heading`，level1，原定位 `cwp-docx-body/1|p=1`；strict `0.7.1` 仅选择后续 qualifier，跨 heading context 未加入。旧1.0/新1.1 unit IDs 分离，原 locator 相同，全 units 和实际选中 spans 均 exact replay。

独立新 OOXML 原件 `own-inheritance-outline.docx` SHA `89ac8a4d3f7ff42f531f07ef9342af4697008cf31526724cd711f0fd1d78e87e` 覆盖三层 basedOn 继承、paragraph outline9 覆盖、style outline9 覆盖、direct outline2 覆盖 body style；继承 heading 和 direct heading 阻断上下文，outline9 正文 pair 成完整同组。真实业务 cell 保持 `docx_table_cell` 独立选中；同段正文正控保持原文整体选中。最终29个最小定点检查 PASS，全部源/生产配置审查前后 SHA 未变。

实施原 `legacy-original.docx` SHA `d428ad041147fb650671ee805c38a03539b4f28529a5516bce325cc3a8541761` 的完整单位字段、metadata、kind、角色、identity、coordinates/locator 与文档 metadata/errors，经我重新 normalize 后严格等于保存 before 和 after 记录，指纹仍为 `a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4`，6个旧units全 replay，saved old pin 仍1.0。旧unit增加伪造 heading metadata、新unit改变 heading_level、新EvidenceSpan经重新计算自洽hash后改变 outline_level，均由实际 replay 拒绝；未改任何 saved artifact。

ROOT首公共 attempt保留14 PASS/1 FAIL：旧producer的 manifest1.0与实际 worker/bundle1.1 不符。读取唯一精确 diff，`narrative_batch._normalization_parsers` 使用共享 `NORMALIZED_MIME_TYPES` 补上DOCX，原 manifest.version及旧fallback1.0保留，未放宽测试。最终 batch SHA `a483d786d99a7bef8f4420ada7770260b147c8048a9c1dceb4813d2f7d880df9`。

第二次只该公共责任实际1 PASS/21.68s，日志SHA `6288936168769b74376770e11ad348054e2822979a2a9f0135164bb830bc8045` 已独立核对。四次CLI均exit0；old producer1.0、current resume旧reference/binding/items/budget与AUTO/source只读SQL dump完全一致由真实已执行断言检查；new default1.1与旧source_ref一致但artifact version ID分离，标题spans保持独立，公共read原locator verified；同generation reuse与new reference相同且0新增tokens/费用。实际ThreadingHTTPServer的do_POST记录仅2次127.0.0.1请求，分别92 synthetic tokens/111 micro-USD测试计量，无外部供应商费用。原件/临时配置保护断言和真实temporary cleanup成功。

实施manifest全部源码/证据hash、两次ROOT receipt/log hash均与当前实际字节一致。7个最终源码与公共before/after SHA相同；原 replay.py 和生产 `config/source_catalog.yaml` 独立前后不变。CodeGraph先查canonical旧索引，缺当前native模块后阅读已定位源码，没有初始化索引。

自有harness早期构造伪造span未重算内部ID被构造器拒绝，随后修正为hash自洽后检查源replay；新fixture首长文件名触及Windows262字符限制，缩短自有文件名。首个完成probe的generic cell文案不满足既有eligible规则，旧0.7和新0.7.1均不选；原输入/脚本/28 PASS1 FAIL结果已留存，以明确eligible业务文案补正控后29 PASS。这些不形成源码问题，不放宽测试，不覆盖旧原件。

本审查0 provider、0外部model/新费、0源码/配置/saved artifact编辑，无commit/push，仅写自有final-heading-independent-review。没有重复104/112单元或既有4公共包。公共SQL/binding验收依据是保留日志与已执行的真实相等断言；测试已清理临时数据库。正常发布和精确新HEAD CI由ROOT完成。
