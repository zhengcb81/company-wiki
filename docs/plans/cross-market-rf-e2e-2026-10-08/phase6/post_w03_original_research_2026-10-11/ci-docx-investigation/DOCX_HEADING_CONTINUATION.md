# DOCX heading归属及旧解析 replay — 实施细则

## 实际根因与输入

独立review.json SHA db81219e561af005aea9c830b3d9a9a4d678b4510292b10ad991bbaa95adf711、review.md db11cffe947ebca61a226eb9c5ded2a5c55e887d939daf2d377019919cffa1a0，位于相邻 evidence/independent-review；结论changes_required。docx_parser.py把任何w:p作为docx_paragraph，未保留style/outline，严格native traversal仍跨真实Heading。三真实executor已seal；其旧运行1152/0f不改写。这里只修解析责任/版本接线，经济/公开摘要DTO等等待四审expert另处理。

## 写入边界 / 交接

实施agent独占：src/company_wiki/document_normalization/docx_parser.py、units.py、__init__.py；src/company_wiki/source_catalog/narrative_normalization.py的DOCX version接线；一个新tests/unit/test_docx_heading_normalization.py，以及本目录 evidence/docx-heading-implementation/ 自有证据/IMPLEMENTATION.md。必要同责任既有docx/normalization测试可修改，但先向ROOT列路径，不碰已有ROOT selector/public/native_pipeline等文件。不能commit、checkout/push、安装同步、生产config、三run execution、Dayu和邻仓写。ROOT独占narrative_business_groups.py、narrative_evidence.py及最终公共接线，避免重叠。

交付声明当前docx_heading unit kind、真实heading_level/style元数据、locator与version，report所有源/测试SHA和先RED后GREEN；停写后ROOT接线strict0.7.1 barrier。若跨文件其余literal版本validation仍拒合法新DOCX，列具体影响或与ROOT先协调唯一owner，不临时放开所有parser版本。

## 通用设计

1. 新DOCX parser_version=1.1.0，旧1.0.0保留原样normalize与replay（单位身份、kind、metadata、locator、text和角色完全旧行为）；默认/normalization_identity真正绑定新版本，saved旧pin/预算不重标不重算。HTML、PPTX/OCR各自版本能力不随DOCX放宽。
2. 标题识别由DOCX解析层基于OOXML真实w:pPr/w:outlineLvl、word/styles.xml paragraph style及basedOn继承处理。尊重显式body outline=9覆盖继承，保留有限原style信息；不用标题文案、字体大小或公司特判猜标题。缺样式/坏XML/继承环等按现有资源/解析diagnostic责任有界处理，不能引入network/审批。
3. DOCX heading输出结构单元docx_heading，保持真实段落p locator与物理body遍历；table cell仍table语义，原Q/A/source_role不变，原文不改。样式读取继续使用既有ZIP/XML limits/no external relations。继承遍历有界、cycle不死循环，真实deadline继续执行。
4. 公共normalize_document(parser_version)及units身份validator支持DOCX新/旧仅所属格式；NarrativeNormalization.identity/normalize/replay和batch generation identity正确收新版本，旧保存版本仍传旧。不能删除全部source byte校验/已保存的locator验证，不能以改测试pin遮盖默认接线错误。

## TDD / 集中测试（大节点，非每小改重复全包）

先写RED在当前两source selector修复快照上：actual DOCX builtin Heading1最小原件 normalize应为heading、不同group不跨标题；custom paragraph style inheritsHeading、direct outline与outline=9 body override；style cycle有界；相同原件explicit1.0.0 exactlegacy单位/metadata/fingerprint/replay，default1.1.0新身份与旧定位字节真实。保留最小输入/失败与源码before/after SHA，测试先失败不是先写实现。

实现后一次集中新DOCX/相关normalization identity/replay GREEN和Ruff/mypy责任检查；允许selector heading group负控待ROOTbarrier接线，明确该责任未验收而不瞎PASS。ROOT随后添加generic native heading barrier并做native pipeline + group版本cache/public重放集中节点，旧全TXT/财表/shape未变不重复收费摘要。发现旧测试硬编码current1.0.0时当前default应引用真实DOCX常量，另加明确old1.0.0冻结断言，不能仅删除旧历史覆盖。

## 完成标准

实际default新DOCX结构准确；旧1.0原字节历史仍可replay；new/old generation分开；标题/财表不跨generic context，业务cell保留、正控完整。独立补充复核最小heading原反例和一个新继承/override组合，通过后正常发布全source变更一次normalpush与精确新HEAD CI；不拿旧0f绿代签。0provider/model/新费，不改变当前累计预算或运行原件。
