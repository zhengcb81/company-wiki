# CN-IR 零选材／US 已存任务诊断

**FINAL：CN不是title/kind/context错载，而是当前native问答发现与角色物化缺口；另有oracle角色合同及US原句匹配假阴性。** 原CN219units/0spans/0÷6、US112spans/4÷8和两次harness序列化错误记录全部保留，未改写历史。

## CN：一次授权native诊断及生产合同

source SHA `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7`，153851bytes。原件6页均读；无parse错误或opaque。ROOT的实际文件名、`investor_relations`、zh、selector0.9及PdfReadingContext三参数与生产NativePdfBackend合同一致，未发现缺设置。生产会补layout_max_seconds15并由PdfReading.read做身份校验；本次通过这个无SDK公共native reader复现0spans，work537356比ROOT537137正好多219个unit校验charge，不是不同语义配置。0.9不会因零选材自动走旧full-table-scan重试；强制fullscan不能称为补一个原来遗漏的生产参数。

这一次读取立即归档 `parsed.json.gz`，随后同一份内存parsed捕获 `diagnostic.json.gz`；以后无需再parse来猜。准确源／运行代码／artifact SHA见JSON。

已锁定链路：

1. 外层route为investor_relations（96上限、不允许按kind空跳过），完整DU route为investor_qa／cn_exchange／ir_activity_record。不是行政制度误路由。ROUTE_PROBE_LIMIT200/219降低置信度，未直接删掉业务。
2. geometry profile正确，但没有outline：NAVIGATION_MISSING，6页全部not_requested_by_intent，requested/table-scan页数均0。不是16M work耗尽。
3. emitter发现页上问答标记后，把**全部219个pdf_text_block标为qa_text_shadow**；实际没有生成任何structured investor_question／management／pdf_table_qa_fragment替代物。
4. adapter正确拒绝shadow作为独立事实，non_selectable=219；73个包全部INCOMPLETE_OR_NONSELECTABLE_CONTEXT，eligible0、admission实际调用0。故不是SOURCE全scope用途策略把6facts逐项拒绝。NEEDS_UPSTREAM_GRANULARITY同时报告219聚合框／11整row缺单元格几何。
5. 最终needs_review、coveragefalse、candidate212／omitted212／0spans。生产require_usable_selection会PARSER_INCOMPLETE、模型前失败，未冒空跳过成功。

纯内存单宽cell问答结构反例已存 `synthetic-single-cell-qa.json`：同一既有Q/A cue，单列candidate=false，两列对齐counterpart=true，关闭qa时false。根在候选的>=2对齐cells先于QA cue；原始fine DICT已经回收，已存parsed只有coarse框／native文本，**不宣称重演了原页逐字节snapshot**。发现只是安排find_tables／QAowner资格核验，不应等同表结构或角色已证。shadow应只覆盖实际替代范围；不得把全部shadow直接洗成management/company_filing。

六个required原文字词均在指定p1/p2/p3的已读shadow中。`saved-analysis.json`逐gold记录实际unitID／paragraph／原文，诊断whitespace/NFKC拼接只证明“字词已读”，没有制造canonical证据或新角色。VC否定、控股股东已联系且希望合作、投资者问题前提、境内收入8.19亿约22%、沸石收入略低于2024、九目审核中止原文都在。九目是**审核中止**而非停产或被否决；问题不是公司既成事实。

## CN评分另一个独立合同缺口

当前oracle接受company_filing／management／unknown且严格role相等。gold前两项标management_answer，问题项标analyst_question，其他三个答复标company_filing；与真实问答管理层角色和问题context合同不一致。当前0选材足以解释0/6，但即使恢复真正Q/A，这套role匹配仍可能全false。问题前提应审核“context可读且不被采纳为issuer已成事实”，不能要求它进入factual claim支持。保留gold历史，之后由oracle责任层处理，不按gold改生产角色。

## US：不再parse，原4/8与语义可用至少6/8分开

已存t7含Commercial products/cloud+14%、Commercial cloud+15%和seats+6%；t8含Consumer products/cloud+11%、cloud+11%、subscribers+8%至89m。t10含Server products/cloud+23%、Azure and other cloud services+34%，层级明确。这两项false来自gold另一种exact原句句式，实际所选段以金额＋or百分比、再独句grew表达同一且更完整含义。因此不是这两业务意义漏选，**原exact4/8不改，人工语义下界至少6/8**。不应为了命中gold挑选另一原句。

RPO375/368b及未来12月约40%在50个可用saved card文本均没有。另两张card是source_table_unresolved，保存的supportID仍在但text/locator空，不能确定其内容。原result未保存parsed、selection gzip、deferred或budget诊断；15983870/16M与112span满上限提示压力，**不能证明RPO未读，也不能排除purpose拒绝、closure／排序、省略或表归属问题**。本次不为补证重parse。金标解释还存在7,265与另项67,265million的内部说明不一致，未改gold，也不是RPO两项当前false的原因。

US原HTML8158067bytes／SHA与gold一致，仅校验字节，未重新normalize。逐项exact支持IDs、locators、actual texts及未证范围见 `us-saved-analysis.json`。

没有SDK、收费模型／HTTP、下载、工程测试或holdout访问；仅授权1次CN native读，US0次parse。原件SHA/mtime不变，无临时TEMP；只写本目录，未改产品、PWF或gold。**FINAL，诊断交接后停止。**
