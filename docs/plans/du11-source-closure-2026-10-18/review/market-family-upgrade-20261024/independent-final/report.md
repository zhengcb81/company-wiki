# 五family最终组件独审

独审人：`/root/w08_reporting_rule_review`。最终结论为 **PASS（本轮离线组件范围）**。最终冻结16份源码/规格/测试/修订收据的字节绑定及实际执行见`report.json`和`final.xml`。这不代签22份材料、正式摘要、恢复及RF全面完成。

## 保留的中间执行记录

只在本目录增加独立测试/报告，未改产品、原有测试、母PWF或外包区。独立11例覆盖20-F编号/标题/父级反控、规格与runtime编译parity、case01原始SHA保留和case02原130/132锚点、active case引用、实际scoped请求保留源文及条件口径、内容变化对请求hash和相关/无关profile决策缓存的差异影响。

首次三个文件合跑在沙箱为47 passed / 1 fixture setup error（7.70秒），唯一错误是sandbox TEMP不能创建pytest编号目录；实质断言未失败。编译器独立`--check`通过24family/14facet。

随后非沙箱复跑，使用本目录`.tmp`作为唯一basetemp并通过已有`CW_SHORT_BASETEMP_DISABLE=1`阻止迁移到外部TEMP；没有跳过任何测试或断言。执行期间ROOT已加入四个IPO RED测试，结果为48 passed / 4 failed（4.85秒）：四项都因测试尚用不存在的`hk_prospectus`/`cn_prospectus` profile ID而失败。ROOT已主动说明正改为现有统一prospectus入口，且五family尚未冻结。不能把本次48P说成最终52例通过，也不能把这些夹具错误冒充新的生产缺陷。

该非沙箱测试退出后，本目录自有`.tmp`已核绝对路径并删除。当时尚待ROOT五family冻结，未签版；最终执行如下。

## 五family冻结后的检查

ROOT保留旧路径并新增显式限定规则：20-F的Item3 Key Information→D Risk Factors；HK中报实际中英期后标题及独立Business Review；A股招股业务技术根标题；港股招股/二次上市文件的我們的業務、我們的市場機會、募集資金用途。规则没有公司名、证券代码、特定文档SHA或单公司分支；router、matcher及引擎本体未因本轮而放宽。电话会策略把CC约定改为条件性解释。

独立扩充到20例：六个20-F标题/编号/错误父级反控、五个IPO标题/市场反控、两个原生单元经过实际`understand_units`的IPO主体规则绑定、编译parity、case历史与真实原文锚点、真实scoped请求内容与输入身份、四个相关/无关family缓存依赖反控。IPO pipeline夹具最初只给业务标题而无招股封面文种信号，诚实路由为unknown，产生59P/2F（5.23秒）；补入对应市场的真实文种封面后两个原断言通过（2P/2.18秒）。这是审查夹具完整度修正，未改产品或降低断言，不把局部片段的unknown声称为产品故障。

编译器`--check`验证24family/14facet；独立测试还将当前五份规格经原编译器生成的整个catalog与runtime做语义相等核对。所有family仍来自单index，未建立第二份策略注册表。

原case01的实际字节SHA同时匹配先前独立审查快照与case-revision记录，未被覆盖；新case02的130/132原文锚点直接对照原TXT，active family.case_ids、real_samples及index coverage都指向02。新的f2必须共同依赖两段，保留同比默认、CC when available与where same条件，不再要求全体数字重标CC。旧case为历史保留，不再作为该family的active引用。

实际`build_scoped_request`收到修正策略，输出reading_strategy包含条件解释，所有material正文仍来自原EvidenceSpan；调用不改变输入DTO。仅改同版本的已采用阅读问题也会改变profile_version与实际请求input_sha256，而material本身不变。真实完整HTML决策manifest对所采用HK中期policy内容变化为changed，对未采用的US/HK/CN IPO family变化仍same。这验证现有局部依赖，不引入人工许可或全catalog失效门。

最终同一冻结版本集中执行：**61 passed / 0 failed / 0 errors / 0 skipped，3.71秒，exit0**。构成为20个独立例＋17个作者永久例＋24个既有registry例；JUnit保留在`final.xml`。执行前后16份被审文件SHA全部相同。非沙箱仅为避开已实证的sandbox TEMP夹具故障，仍运行全部测试；使用本目录独占basetemp并只禁用其向外迁移。结束后`.tmp`和本目录`__pycache__`都精确清理，目录恢复无临时夹具状态。

## 结论边界

本轮三个原独审发现已在组件层关闭，新增IPO明确标题/原生绑定/市场边界也通过。本审查检查源规格、编译、匹配、实际pipeline、实际请求构造、缓存依赖与历史case完整性，没有外网/模型调用、下载或原文变更。请求测试使用合法选择DTO夹具与真实策略解析结果，证明模型边界接线及原文保留；不能据此声称完整真实电话会经selector到付费模型后的语义输出已通过。IPO原生单元测试也不代替PDF解析召回验收。ROOT仍须做已冻结真实业务目标、正式配置摘要/恢复、跨仓实际采用及RF四路循环；这份PASS不改变这些未完责任。
