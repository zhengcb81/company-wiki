# H1 v4 真实来源独立审查

结论：**真实来源运行与收据有效，但 C-source 仍需根修（1 个 P2），不能签 9 组上下文全部通过。** 新版已明显恢复局部归属和业务原话；仍有旧子标题跨备注污染真实选中上下文。

本审查只读已保存收据和原 PDF 第34–36页，不重跑 source pipeline，不调用模型、下载或复制原件，不修改源码、Git 或主 PWF。

## 本次版本与已证事实

- source run：`fee04ba4d8b8c66b3e651eacbf6168c5811fc521`；runtime430文件/语言资源 aggregate `6d7357b00c0319b6bd9156a197d2aa0149ded1d5cffbd3eb53c508e2280338d7`，本审查独立按同一规则重算一致。
- 原收据 `h1-r7-v4.json`：388,583B，SHA `e0847972f0dca968a85772e7932daa62bd4085bbaa69edbff8b89d67eaaa5feb`。完整报告可超过旧300KB；它不再因日志体积阻断业务。
- 产品39.902s、总45.14s，仍用90s/16,000,000work/112spans。12个固定 required originals 均 represented 且 parsed_exact_original；这是来源召回，不是12份摘要/世界事实核实。
- 当前112spans、101个**唯一** native originals，101/101 valid_slice；37个原文摘录及112个span文字 SHA 全部独立核对。不能沿用旧111的计数。
- source run 原件和DB内容不变；SQLite SHM只有mtime变化，不能称全部元数据不变。observer3源码SHA前后相同，审查又逐文件确认；原PDF审查前后SHA/大小/mtime也相同。
- 实际是 **partial**：work.used15,989,716、exhausted=true、source_processing_complete=false、selection.coverage_complete=false、layout.complete=false；199页文本已读不等于131张表已分析（tables_scanned=0）。原收据诚实保留这些边界。

## 9组正向归属、旧坏关系与覆盖

下表中的主体由当前原话与排版独立判断，`expected_actor_and_scope` 仅是待验oracle，未作为证据。旧坏 context 在9组均未观察到，但有6组当前根本没有选中view，该false不能单独算修复通过。

| 组 | 原始位置/独立读取的正向证据 | 旧坏关系 | 当前选择与结论 |
|---|---|---|---|
|1|p34¶20–22：备注8明确实际控制人；本人及关联企业；保留不损害公司/其他股东利益的条件|不再借前备注7赔偿条款定主体|原始结构可见正确本intro；0/3选中，**OPEN**；父链仍有旧子标题|
|2|p35¶5–6：备注9明确Summer Bloom；“本企业”而非上市公司；首项保留不利影响前提|前备注8“本人”赔偿条款不在当前context|2/2选中、正确intro存在；但实际view25仍含旧（4），**P2待修**|
|3|p35¶11–12：备注10实际控制人；截至承诺出具日、近亲属/下属企业、境内外、否定限定保留|前备注9“本企业”赔偿条款未混入|2/2选中、正确intro存在；view28仍含旧（4），**P2待修**|
|4|p35¶13–15：承诺将不会竞争/控股竞争企业/提供业务财务帮助；“竞争企业”定义原话保留|前备注9赔偿条款未混入|0/3选中；raw仅能证明本intro是备注10。后两项有TABLE_BODY_NOT_READ诊断，**OPEN**|
|5|p35¶16–18：自出具日起有效，任一条件终止；三条件及“暂停买卖除外”完整|前备注9赔偿条款未混入|3/3实际在同一native carrier，view65完整选中；不能误读direct映射1为遗漏2。正确note10 intro存在，但旧（4）仍混入，**P2待修**|
|6|p35¶21–22：备注11明确Fertile Harvest/Eastern Star/L&C；本公司是承诺股东，公告起未来6个月锁定期不减持/处置/担保|不借前备注9“本企业”赔偿条款|0/2选中；raw本intro正确，**OPEN**|
|7|同6，独立排除前备注10实际控制人赔偿条款|旧“本人”赔偿不在当前context|与6同support、不同坏context oracle，不算第二独立正向样本；**OPEN**|
|8|p36¶2–3：解除协议生效起独立行权、锁定期届满后作为特定股东交易；semantic intro正确为备注11|不借前备注9赔偿|0/2选中。跨页source proof另列p35首项与页眉/页码，不把物理证明当主体/语义。六个月定义只在prior undertaking（当前physical proof）中，未证明下游完整时间口径采用；**OPEN**|
|9|同8，独立排除前备注10赔偿|旧“本人”赔偿不在当前context|与8同support、不同坏context oracle；**OPEN**|

9组对应7套不同support集合、17个唯一original目标，7个已由direct/native representation保留；当前3组（2/3/5）完整进入选择，其余6组没有选中。不按direct-only计数误杀native，也不把raw结构观察升级成摘要/RF采用。

## P2 C-SOURCE-V4-01：旧小项仍成为新承诺祖先

原PDF第34页，“（4）减持股份的信息披露”之后依次是同级粗体备注6、备注7、备注8；第35页同级备注9、备注10、备注11。旧（4）属于更早承诺的小项，不能作为后续新备注的父节。

实际选中 `group-25/view-0`、`group-28/view-0`、`group-65/view-0` 的 context_evidence_ids 全含旧标题 span：
`urn:company-wiki:evidence-span:sha256:5c9eca078287e9d60d43988fecc63f132e24c0b6f2b52363519485640bf035bf`。

其原话就是 `loc:v1/page:34/paragraph:3` 的旧（4），并非物理source proof误报。虽然正确备注标题同时存在，但这仍会把关联交易/避免同业竞争的独立承诺挂到股份减持小节。

共因定位：`structure/sections.py`467–485行，新note只恢复上一note保存的stack，再把剩余stack原样记作新note父树；进入note之前已残留的旧嵌套heading没有在真正新scope边界退出。应在同一section/scope owner修父级边界、保真正章级祖先，不在observer/model里过滤公司名、备注数字或该标题字符串。

复现只需读取本收据、按上述locator找span、检查三个view的context IDs，再查看原PDF34–35排版；无需再解析整份原文。详细9组原话/IDs、三种角色、实际view、原文/SHA及图像hash均在同名JSON。

## 收口范围

可以确认：真实运行完成，12个固定业务目标召回恢复，本note主体/否定/条件大部正向可追溯，物理proof与semantic分离有效，预算与partial状态诚实。

尚不能确认：9组全部引用正确、全文完成、未选范围进入正式摘要、真实摘要/缓存恢复/RF实际采用。本报告为 **NEEDS_ROOT_FIX_SOURCE_CONTEXT**，不否认已证恢复，也不以新许可阻断健康业务。ROOT已收到最小共因和证据，可直接修复。

审查专属 `tmp/h1v-83c60a` 初始absent；仅临时生成3页PNG和2个小记录，图像hash/观察结果先归档，随后精确清理恢复absent；原PDF保留不变。
