# R4 STORAGE-002：来源 context 跨备注边界调查

状态：**只读调查完成；产品尚未修复，不表示 C 验收通过**。本项属于既有主 PWF source T3，不另开外包卡。记录日期：2026-11-01。

## 结论与证据强度

已用冻结旧 context 的四个精确赔偿尾句和纯结构合成夹具复现一个共同的最早错误：**编号正文以句号加闭引号结尾时，被 `structure/layout.is_heading` 误认作章节标题；真正的 `备注N：主体及承诺` 未被识别为局部边界，后面的新备注正文因此归属上一备注赔偿尾句所建的 section。** `narrative_native_materials` 随后按既有 section 祖先和 package 依赖取 context，把错误归属放大为引用关系。来源字节、span SHA、locator 全部正确，仍不能证明这个关系正确。

这不是 RF 释义错误，也不是缺少人工许可。`source_role=company_filing` 只说明文件类别，不能推出文中“本人”“本企业”“本公司”都指上市公司。应由来源结构/context owner 修复，不能由 RF 改写主体或按真实公司名称过滤。

已确定当前代码仍能复现的首个坏分支和典型传播路径；**未声称复原了旧 attempt 的全部内部图**。旧 context 没有保留全部 structure、package 和 view 索引，因而 span102/103 同时得到 span97 和 span101 两个 context 的每条历史中间边，不能仅凭现有 JSON 唯一重建。新 source v2 的精确 view/member 索引应在 ROOT 的 C 复验中完成最后逐边确认，不能拿 wholequote 匹配代替。

## 读取范围和原始身份

调查只读：

- AUDIT `runs/r1-20261021-cn-wuxi-apptec/reports/r1-remediation-04/storage.json` 的 STORAGE-002。
- 同报告目录 `roles/storage/context-boundary-observations.json`。
- 冻结 `execution_replays/r1-remediation-04/narrative/h1-public-read/context.json` 的 source_ref、evidence_spans、reading_context.groups/citation_views。
- CWP `.planning/architecture-quality-20261101/real-acceptance/cases.json` 的 `r4-cn-h1-real` 九对原始 unit oracle。
- 当前结构、native dependency、native materials、native continuity 的所属代码。

SourceRef：`schema_version=2.0`，`mime_type=application/pdf`，`byte_size=1216470`，`content_sha256=d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`。source_id/document_id 分别为相同 SHA 的 `urn:company-wiki:source:sha256:` 和 `urn:company-wiki:document:sha256:`。未重新下载、复制或解析原 PDF；原页身份采用此前 storage 独审已回原件核对的 p34–36 收据。

原文备注顺序：备注7 实控人避免资金占用；备注8 实控人减少关联交易；备注9 Summer Bloom 减少关联交易；备注10 实控人避免同业竞争；备注11 原一致行动人股份处置，续次页。t58–t64 共七卡都未被该 attempt 的实际八张 RF 采用卡采用；已证实的是来源关系/主体范围风险，未证实本次收入 DAG 有金额错误。

## 精确原始成员与旧输出关系

下表 span 数字是冻结 `context.json` 的零基 `/evidence_spans/N`，pair 对应 cases 中 `R4-CONTEXT-PAIR-N`。unit 均为 `urn:company-wiki:narrative-unit:sha256:<表中SHA>`；完整列表已在 cases 中冻结，本报告不另造身份。

| Pair | Support 原始 locator / span | 被禁止的旧 context / span | 冻结旧 group 索引 |
|---|---|---|---|
| 1 | p34/paragraph20/chars912-1058 / 94 | p34/paragraph19 / 93 | 57 |
| 2 | p35/paragraph5/chars195-335 / 96 | p35/paragraph4 / 95 | 58 |
| 3 | p35/paragraph11/chars605-785 / 98 | p35/paragraph10 / 97 | 59 |
| 4 | p35/paragraph13/chars786-994 / 99 | p35/paragraph10 / 97 | 60 |
| 5 | p35/paragraph16/chars995-1112 / 100 | p35/paragraph10 / 97 | 61 |
| 6 | p35/paragraph21/chars1302-1563 / 102 | p35/paragraph10 / 97 | 62 |
| 7 | 同上 / 102 | p35/paragraph20 / 101 | 62 |
| 8 | p36/paragraph2/chars37-270 / 103 | p35/paragraph10 / 97 | 63 |
| 9 | 同上 / 103 | p35/paragraph20 / 101 | 63 |

四个 forbidden 原始 unit：

- span93：`6ffd18ae45975ed750ba9ab70a5856dbe673def787834ebf6792fba7cd8a6750`；text SHA `e3092b31c6b73aa2d4fa9bf97fc745f52961c22e88a36a22b31aa33b3f2ef26d`。
- span95：`e5f3c65f09a46521c2bf87d3f45f23b25c7a7b706809f9b0b31f669a5ec6377e`；text SHA `dd3c2b500fed53437704e37a8aec7e382eddeb366ffc0c6cef2def402bf22e10`。
- span97：`5b0131a1b4d3b0e43f26730b200a482f0e49fffb46712a9d68b0c36108b7f668`；text SHA `63be3368fae42ca37405ffcc9ffbce07f6388cb635dc7b38761864f93bf480a3`。
- span101：`63e1f4d398bbb2fd0f5ed13a6deb0856918d15cff91feb65d42db74a87f90266`；text SHA `dee22682b08ee1afb18ab21a8a41f95f3f16163660e6b009e7d3598107072d58`。

关键 support 原始成员：

- span94：备注8标题 `919dc9d462d22a0d2d85052804aa328bbe61ffc491760ba5688caafa0a4f37b9`，引介 `4f6a20ab95ab0ee08e73137f40707d1afbbd67265aca926b2463696ee37dab33`，首条 `1c3a1095c7612c0acf02b586ecd85b3de68388dd470a41357aa50f2e42ee006f`。
- span96：备注9标题 `fc150a13e6786af4734cf7690aab6a47b959a2528df517c59e97e5929ea1d76e`，首条 `4fc4ce665976ad02b0c4ad268c32373e8d110da4e126e200120cae1fbc1ea531`。
- span98：备注10标题 `4a5a3f1d046fd9b898783713c9888aefffc5edf5ffdf270cc45062834403e013`，首条 `8f6835356515bf339d5596dac0630d26e518aab9f7804925463dacb85db0d75f`。
- span102：备注11标题 `8686dd8c32d8ce5377380aa47e4eb88e26044659b2912c7c8d4e8a4e0410f51b`，首条 `e27bfb6cb8205196ce15c27b94f657a99b96f308cd7263ccda76abbbe366eb25`。
- span103：次页继续条款 `999e2f10d1fc01aed6c7f63acd37995d70e0cafa288d0339beb814d6eac43a73`、`1769621d4476e8da84d9c798ca5321c03fa63e3758c5eb09ca7416acf68bc602`；其中“本公司”不能根据 document role 自行绑定上市公司。

旧 group57–63 的 kind 全为 `native_continuity`、section_role 全为 `unknown`。其 citation view 是明确的 support/context 两种边，不是仅仅一起出现在全文：94→93、96→95、98/99/100→97、102/103→97+101。

## 最早错误与责任边界

1. `document_understanding/structure/layout.py:is_heading`（当前约282行）：`_HEADING_NUMBER` 接受 `3、`、`5、`、`7、`；短于80字符时，仅以 `rstrip().endswith(("。", "；", ";", "."))` 排除句子。末尾是 `。”` 时排除失败；闭引号/括号改变了相同正文的结构类别。
2. `observation_adapter.py:_heading_level`（约184行）有另一套编号/终止规则。四个阿拉伯数字尾句在 adapter 为 None，但 layout fallback 为 True；中文编号加闭引号也能在 adapter 中误判。不能只改 adapter 而遗漏 layout，也不应在另一层新建第三套不一致的正文/标题规则。
3. 真正备注8/9/10/11标题在 adapter 和 layout 均未形成标题/边界。实测长度23、86、21、95，后两种长标题还跨行。因此把 `备注` 机械加进现有“短于80且无换行”的标题正则仍会漏长主体说明。需要来源局部 scope 边界和正文 actor 引介的明确模型，不能靠调大标题字数。
4. `structure/sections.py:build_sections`（约334行）：假尾句通过 `open_section` 建 section，后继新备注没有新边界就进入其 `body_ids`；同页/正常相邻页继续归属。这个可复现的错误先于摘要和 RF。
5. `source_catalog/narrative_native_materials.py:prepare_native_materials`（约109、175行）：`inherited` 求 section 全祖先标题并放到每个 body 的 headings；`context(member_ids)` 合并这些 headings、native dependencies、owner 的 external required_context。这是在既有图上做闭包，不能纠正前一层已经错的父子关系。应追踪每个 context 边的 owner/basis，不应在这里按赔偿关键词悄悄删边。
6. `narrative_native_dependencies` 只投影/校验 producer 已声明的边；`narrative_continuity` 使用 native section/scope 与实际物理邻接约束。它们不应承担按公司名单推测承诺主体的修补。结构层给错 scope 后，下游继承“同源且连续”并不能证明“同一承诺/主体”。

目前 `_native_list_scopes` 的 parent 语法是括号数字或 bullet 加空格，四个真实赔偿尾句是 `N、`，后继又是 `备注N`；小夹具的 `required_context_by_unit_id={}`。因此**没有证据把首错归给 native-list parent discovery**。首先修假 heading 与缺备注边界，再用 v2 trace核对旧双 context是否还另有 owner external closure。

## 已运行的最小纯函数试验

运行环境：宿主 `C:/Miniconda/python.exe -B -X utf8 -`，`PYTHONPATH=<CWP>/src`。仅调用 `ObservationUnit`、`is_heading`、`heading_depth`、`_heading_level`、`Ordering`、`build_sections(..., limits=DEFAULT_LIMITS)`；无 selector、模型、数据库、原件复制、索引和产品写入。

冻结真实尾句的分类结果：

| 冻结 span | 字符数 | adapter heading | layout heading / depth |
|---|---:|---|---|
| 93 | 49 | None | True / 1 |
| 95 | 42 | None | True / 1 |
| 97 | 44 | None | True / 1 |
| 101 | 40 | None | True / 1 |

去公司化反例：`3、甲方承担上述承诺损失。` 的 layout=False；只在末尾加 `”`、ASCII闭引号或 `）`，layout 均变 True。`3、经营进展` 保持 True，是必须保留的真实编号标题反控。`一、甲方承担上述承诺损失。”` 的 adapter=2/layout=True，说明风险不限于阿拉伯编号。

合成结构输入（ID u0–u8，仅测试局部身份）：

```text
u0 备注17：甲方关于减少关联交易的承诺
u1 1、甲方应减少关联交易。
u2 3、甲方同意承担上述承诺的一切损失、损害和开支。”
u3 备注18：乙方关于减少关联交易的承诺
u4 “1、乙方应减少关联交易。
u5 5、乙方同意承担上述承诺的一切损失。”
u6 备注19：丙方关于股份处置的承诺
u7 “1、丙方将按其承诺履行股份处置义务。
u8 [相邻次页] 2. 本公司承诺，股份处置前将事先通报。
```

同一 source、page1/2，均为 `pdf_text_block`；没有显式 heading hints。实际 baseline：u4 的继承 context 为 **u2**，u8 为 **u5**，正好复现旧备注尾句污染下一备注。`required_context_by_unit_id={}`，错误来自 section 归属，未经过 native dependency emitter。

两个诊断性反事实（仅内存输入，不是产品修复）：

| 输入变化 | u4 继承 context | u8 继承 context | 含义 |
|---|---|---|---|
| 无变化 | u2 | u5 | RED：前备注赔偿尾句成为父标题 |
| 仅让两尾句以句号收尾 | 空 | 空 | 仅修闭引号可移除污染，却仍丢新备注主体引介 |
| 为u0/u3/u6提供真实 native heading_level=1 | u3 | u6 | 新明确 scope 可隔断前备注，并跨页保持本地引介 |
| 两者都有 | u3 | u6 | 预期结构关系 |

最后两行是独立正控，**不是允许代码为任意备注伪造 native heading hint**。这里只证明结构层在收到明确边界后能闭合，并证明“删除错误context后变空”不等于主体完整恢复。相邻页 `build_sections` carry 的正确性也不等于 `narrative_continuity` 的真实物理邻接证据通过，后者仍需正式测试。

## 建议纳入 T3/C 的实施与验收

先用新通用夹具写 RED，再改 source owner；不要修改冻结 oracle 去适应结果。不增加逐小节点人工签收。

1. **统一正文/标题判断。** 在结构/observation责任层统一终结符与闭引号/括号处理，保留原始字符串及locator。正文编号、完整句的末尾包装符不能成为 heading 证据；真实短编号标题、显式 HTML/native heading 仍要保留。避免复制 A4 正在修改的 passage/grammar/reading 逻辑。
2. **建立 source-marked 局部备注 scope。** 识别编号备注的明确开头、同层新备注和长/换行引介；将标题作为当前 scope 的来源限定，不能继承前一备注同类赔偿尾句。相同 actor 的新承诺同样必须结束旧 scope；既有 raw 不变，边以原始 unit ID 指向引介。不要把 generic `company_filing` 当 actor，也不要将所有“本公司”绑定 issuer。
3. **原始依赖闭包审计。** context 边保留来源 owner/basis，局部新 scope 只继承有效祖先/本 scope 引介及真正依赖；跨 source/speaker/table/project 不得借邻近串接。native材料继续消费结构结果，不负责按真实公司或页码删除错误边。
4. **合成正反包。** 覆盖甲→乙→甲、同actor不同承诺、正文/赔偿尾句加不同闭引号、中文/阿拉伯数字、备注号变动、标题>80字符/跨行、正常编号业务标题、正文提到“见备注N”而非标题、table footnote/furniture、显式 HTML标题；跨页“本公司”须保留本备注引介，不能借前主体。加无原始scope或无物理邻接的 abstain/partial反控，防止误合并。
5. **ROOT 同批 source C 真实复验。** 使用现有 source-ref 和新 v2 view/member索引，对全部九对按原始unit关系判断：support原始成员必须完整；禁止context不得出现在该support view的context或跨组被错误提升为support；如果因行政低值根本没选该support，单独记“未选”，不可报“关系正确”。需要保留scope引介的正向断言；不能仅九个负边消失就验收。以 v2 trace补证 span102/103 双context历史路径是否仍存在。
6. **同一大节点独审与回归。** 限定结构/依赖纯函数、真实R4源选择回放及现有不同市场/文种反控；预算/完整性/原件不变。通过后再由 ROOT 解冻和并线，随后继续正式摘要/cache/RF采用验收。本调查未运行这些生产步骤。

## 本次清理与边界

无原件、临时原件、模型请求或生产数据库变更；无源码、测试、主 PWF、Git或作者工区修改。本次唯一持久文件是本调查报告。两次纯脚本的输入拼写/参数问题已在内存脚本纠正（一次缺`limits`、一次诊断输出表达式语法），与产品错误无关，不计入产品失败。
