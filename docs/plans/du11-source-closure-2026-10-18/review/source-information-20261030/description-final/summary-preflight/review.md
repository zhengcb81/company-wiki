# 真实摘要收费前独立预审

结论：**PASS，当前预审工程范围内 OPEN=0**。最终4文件（observer、records、unit、extractive）实际 raw/LF SHA-256 列于 `review.json`、`final-hashes.json`，测试前冻结并在签署时复核。

独立 **8 passed / 0 failed / 0 skipped，pytest 1.55秒**，见 `final.log/xml`。同时重放保存真实 selection 的正式 scoped compiler material；测试与该重放合计命令5.36秒。ROOT 宿主90P/71.78秒、ruff4文件为单独报告，不计独立数量。

发现并关闭一项P2：有一条有效 required fact 时，另一条 typo/None target_kind 被静默剔除，作者2项检查能以1/1获准。当前共用 canonical `records.gold_fact_target_kind`，所有显式 kind 先验枚举，缺省仅 narrative→required_business、document_meta→context；空 required 不再0/0通过。extractive旧空 gold 夹具换为真实来源锚点并断言1/1，原 material 篡改检查保留。

只签 active gold-v3／prepared-v4；旧草稿未作为当前执行依据。canonical validate_gold 通过，source SHA 与保存selection／准备指纹一致，gold自身SHA与prepared protected fingerprint一致。实际 compiler 产生 t1–t8 共8项，均有非空事实支持，成员等于 support/context并集。8个完整 exact_quote 的 page／locator 不只在context中出现，而确实属于各对应任务的 factual support；当前 full_request 的 required=supported=8、无 missing／not_sent。见 `actual-preflight.json` 和 `actual-material.json`。

这里的 full_request 仅指该选择结果的8张卡，**不等于全文完整或已实际发送**。输入仍partial、coverage_complete=False；没有执行HTTP、worker/Catalog或模型。已核原文保留影响“重大”程度及报道／家电前提、客户链与制造名词区别、收到问询／申请中止／条件未来恢复、已售清单与超过300研发数量、VC否认与股东联系／愿望、751吨/年项目建成后产能。summary_claim_coverage仍not_evaluated，后续实际摘要不能因此预签。

metadata记录native runtime、未设置可选SDK；未独立加载凭证或复查当前母账。当前canonical ledger、unknown保留、实际request收费前校验仍由真实运行路径执行；50k/$0.05是现有单次上限，不是新增许可或账单结论。实际请求、付费输出持久化、声明语义与引用、激活／重启／跨run零重复POST、FF/RF及完整召回／holdout仍需真实收据。

清理：只写此summary-preflight子目录，保留探针／测试／material／JSON／XML／日志。Python `-B`、pytest `no:cacheprovider`，无缓存子目录。未改产品、作者测试、PWF、配置或hook；config diff为空，原hook保持0/0内容变化的mode WIP。未读原件／密钥，未运行SDK或碰W21，0 provider／network POST，0下载。
