# W08 错误context责任层诊断

**结论：p160错误标题及实际parent链已证实；p16表格质量守卫旁路已证实。** 不在下游删除context来掩盖，不要求所有财务表进96。

## p160 → p183 → p184：已证实的实际链

实际公开parse/build观测（同7f1431d…原件）：

- p160/paragraph19是普通`pdf_text_block → paragraph`，heading hint为空、table_id为空；layout明确给`heading_level=None, confidence=low, basis=in_table_region`。
- structure仍把它开成heading节`s567`，basis=`reading_order;heading_numbering`，parent=`s1`。
- p183/paragraph7是真实heading level2，节`s649`的parent实际就是`s567`。
- p184/paragraph4为footnote，实际body属于`s649`，祖先为`s649 → s567 → s1`。封存fullselection的group`3669a74d…`最终把p160余额行列为该脚注context。

首个错误在[structure/layout.py:196](C:/Users/郑曾波/Projects/company-wiki-r1-local-observation/src/company_wiki/document_understanding/structure/layout.py)：`is_heading`的短编号fallback忽略多行数值尾部，也未尊重上游`in_table_region`否定，重新把“5.期末余额…”推成标题。`heading_depth`将此编号按level1处理；section栈随后允许更深标题成为其子节。wire本身不导出depth，报告中的null只表示字段不存在。

`narrative_reading._prose_reading_packages`(约173–222行)沿真实section parent求标题祖先闭包，`_context`(811行起)再投影support/context。这两层传递了错误结构，不能靠按距离裁剪或删除p160来修根因。观察适配器178行起对多行短编号已有拒绝；此次layout也拒绝了标题，**结构层的第二次推断推翻了它**。

## p16裸数行：已证实守卫旁路，首次typed缺失仍待定位

实际p16/paragraph2、3都是paragraph，table_id/table_index均空、heading为空；layout basis=`no_heading_evidence;no_lane_split`，只属于`s59 → s40 → s1`，自身标题是一般“分行业、分产品、分地区、分销售模式情况”。fullselection两行kind=background、quality_flags=[]，view没有列头、万元或年度。

责任链：

1. `structure/tables._scopes`(96行起)只收typed row/header/cell及caption/note。无table_id的loose scope逐页重置，不能自己证明p15到p16续表。
2. `narrative_reading._prose_reading_packages`约138行只将table_index非空的prose成员保作table owner；这两行不在该集合。
3. `_candidates`449–450行对非`operating_table`包直接旁路资格校验。
4. `select_reading_evidence`1024–1031行的`table_structure_ambiguous`集合仍只包括`operating_table`；`_context`880行又只在已有该flag时追加定向unknown约束。因此background裸数行漏掉了质量闭合。

已核原文p15有真实万元/人民币和列头。它们没进入当前view，不能由裸数位置反推。**首要修法是诚实逐行unknown/partial；只有真实continuation/表归属证据闭合才可带原表头。** 本轮没导出完整fine-table descriptor，不能断言首次typed丢失究竟由fine detection、fragmentation还是跨页策略造成。

## 中性RED与可信修法

- 共享标题形状RED：普通paragraph、无heading/table hints，用`7.Closing balance\n-\n-\n5,000.00\n-\n75,000.00\n80,000.00`；40<len≤80。应非inferred heading。换中文标签、数字、tab；保留`1.2 Operating progress`（编号后有空格）、中文真小节、source显式DOM/native标题正控。
- 真实链RED：中性合成PDF经真实parser和public build，包含数值尾部假标题、后续真小节及脚注；不手工注入section/parent。余额行不得进入heading/ancestor/citation context，真小节仍保留；覆盖相邻页和连续多页。
- 表旁路RED：不提供typed table坐标，原文paragraph为行标签+多行值，分别由background/native_continuity拥有。被选时须真实表头单位闭合，否则逐span质量unknown/partial或deferred；保留raw/ID/locator，不测固定96/score。
- 续表负控：真实前页头/本页行；变CNY元/万元、删头、插入另一业务/币种的相邻表。无可靠continuation证据必须unknown，不能借相邻表caption；已有typed/native完整表保留正控。

可信修法：共享source shape primitive识别“newline/tab行标签+至少两个完整数值cell”，约束adapter、layout heading和structure fallback各个**推断入口**；显式source标题保持其来源权威。表歧义由source/structure owner声明，再对全部carrier传播同一质量状态；不新建数字词表或平行打分器，不抬预算。

## 观测与版本边界

本次diagnosis三次原件实读共4,824,678B；本agent此前内容复审加本次合计8,041,130B，仍低于8MiB。第一次build后MappingProxy序列化失败；第二次报告908,431B被64KiB守卫拒绝。ROOT逐次授权后，第三次先通过含巨大metadata的合成白名单门，再真实观测；成功产物仅14,312B。未落raw或超额报告，未模型/下载，源码/config/catalog前后hash均同；预算3,699,183/16,000,000。

实际结构：[context-actual-target-structure.json](context-actual-target-structure.json)，SHA `5a0e4bd554b36d56818fd3585d24ef2d758e14e06ab09c22c7808b16c4e09798`。完整诊断与所有代码指纹见同名JSON。sections.py仅单行types注解与fullselection不同，已用内存反向exact SHA核对；ROOT获准改源码后这些指纹仅代表修复前。

JSON SHA-256：`21077359db99d3d5cd3a890ff4ad5e8ad6f031d9e9c2d4c505f2bbeb23964988`。
