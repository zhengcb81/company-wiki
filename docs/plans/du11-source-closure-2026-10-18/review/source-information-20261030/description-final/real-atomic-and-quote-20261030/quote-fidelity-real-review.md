# 正式 /5 IR 引用卡独立审查

结论：**PASS，限定这一 development 来源的8张引用卡及留存的CWP恢复链；本范围0 P1/P2/P3。** 不签全文召回、多市场/长文本、生产默认迁移或RF采用。

原产物 `7a1cef66da05bb91b47f895c8a8eef452efff35d762a9b3c5711ac40d7166244` / 163606B，generation `ab6dd8151aa51ae6ef8fc1131ee9be52f1bc405ff5bb131ea4c419fcc438363f`。实际body、prepare checkpoint、public read保存bytes及当前既有owner从真实回复重建bytes四者一致。不是根据overall PASS自行推定。

## 内容逐卡核对

| 卡片 | 完整支持/归属判断 |
|---|---|
| t1-source | 当前市场行动与2025境内收入约8.19亿元/22%留在完整答复，未改成计划或添加业绩。 |
| t2-source | 新闻/家电事项/未构成重大影响完整同段；三星客户关系只在question context，未升级进答复quote。 |
| t3-source | 产品及三层下游链完整，主要限定未被删；不变成发行人生产事件。 |
| t4-source | 收二轮问询、申请中止及待更新后将申请恢复/回复同段，mixed诚实uncertain。 |
| t5-source | 2024需求减少原因、部分医药及2025沸石收入略低完整，年度/程度准确。 |
| t6-source | 无VC生产、根据控股股东信息、已联系及希望合作同段，非发行人签约/订单。 |
| t7-source | 已售名录、超300种已开发化合物及自述领先范围完整，未把开发集合当全部已售。 |
| t8-source | C05启动、约751吨/年及建成后保障完整；未新增设计口径或投产条件，mixed仍uncertain。 |

每张正文逐字等于其 support spans 的完整原文连接；support/context ID及role与实际计划一致、context分开引用，问句没有变成回答。8个既有gold的完整源quote全部出现，排名改变顺序但8 admitted全部保留。每卡modality=uncertain、needs_review=true，完整source selection仍partial/coverage=false；source_coverage_complete只表示这些已准入任务。

引用式结果中“该公司”等指代仍需单独展示相邻question/context；本bundle保留了闭包，不等于所有UI已正确展示。原文的公司自述和第三方报道不是外部真值。

## 真实调用与恢复证据

实际reply只有8个task/priority/disposition决策，没有模型生成正文/数字/引用；与native final SHA一致。原native1POST，6093 input＋179 output＝6272tokens，1076microUSD预算代理，非账单；审核新增0POST。

- 初次命令exit2对应明确test hold的activation_pending/partial，prepared checkpoint自称not_activation_proof，不能单凭prepare签激活。
- activation-resume命令exit0完成，正式ArtifactRef与body匹配；restart同run、同ArtifactRef、同累计费用/usage，未多算为0历史费用。
- cross-run命令exit0，generation_status=reused，同一ArtifactRef；新run charge0tokens/0microUSD，cache.native-usage=[]。
- 全events只有1个http_post_attempt、1个final_observed；read和exact-single receipt均ok/replay verified、15locator、同ref；latest reference和exact reference一致。
- prepare capsule/full final_generation与预留SHA一致；没有使用partial capsule伪造activation。
- exact SourceRef模式read as_of=null、expected_source字段null是未额外做issuer/期间/asof资格要求；manifest仍保留原security_id万润股份及未知published_date，不能据此声称特定历史时点公开可得。

原临时AUTO已清，独审交叉核对保留的实际命令/stdout、native usage、event、prepare/body/generation/read receipts；没有重新查询已删除数据库或重新解析PDF。复现脚本audit_real_quote.py只读这些材料并调用已有纯owner，输出real-review.json。

## 仍OPEN及下一节点

本run的overall.consumers明确NOT_RUN（未提供consumer checkout root），所以PASS只到CWP链，不能签RF read或预测采用。旧/7四P2没有被修改或“自动销号”；这里只证明新的/5源quote路径避开同类新增文字错误。

下一节点按PWF M5：新composition显式选择既有/5；旧schema请求省略仍/4及旧batch resume身份保持；先TDD和独审再改生产默认。无模型新DTO不作为当前完成门。另用已有中微同source正式/5做零付费RF采用准备，不编万润参数。
