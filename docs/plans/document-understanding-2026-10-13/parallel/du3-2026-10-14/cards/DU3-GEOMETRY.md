# DU3-GEOMETRY：真实版面快照→既有原文单元元数据

## 直接启动

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/geometry`。
分支：`codex/du3-geometry-20261014`。读本卡、`../INTERFACES.md`和工作树`.planning/du3-geometry/task_plan.md`实际base。可现在独立开始。

背景：现PDF文字可读/可回原文，字体/页尺寸/粗bbox已透传；四代表样本实际细列/细cell仍0、layout partial。此次补的是**格式前端真实细元数据的绑定投影**，共享layout_hints仍是唯一布局关系引擎，不能再写一套章节/分栏/表头推断。

## 排他写范围

- `src/company_wiki/document_normalization/layout_snapshots/**`；
- `tests/unit/document_normalization_layout_snapshots/**`；
- `tests/fixtures/document_normalization_layout_snapshots/**`；
- `.planning/du3-geometry/**`。

不改现parser/normalization父__init__、PDF/HTML/OCR/PPTX入口、observation_adapter、layout_hints/bridge、registry/selector/summary、source_catalog、automation、ROOT PWF、依赖/CI/config或其他工作树。没有新增OCR后端、第二PDF parser或文件存储。

## 冻结接口与实际工作

公开`project_layout_snapshot(snapshot, units, *, limits=None)`，严格DU3/1。产品API只接受内存snapshot/已读原unit，输出unit_metadata patch、coverage/diagnostics/feature版本；不文件IO/网络/model。每binding提供已有unit_id及真实page/frame/bbox和可选字/字体/cell范围依据，不能解析opaque locator猜映射。

1. 支持实际PDFdict/span/words/table数据，按显式canonical unit绑定保留字符区间与原text/ID/locator/parser/role。模块无权增加新的可选择原unit或重造locator。
2. 源词/字体/格的位置必须来自实际提取；不能把整块/整行/整表框复制到每个cell。仅row_cells字符串不算细geometry。重复字串不同block不能靠全文文字相同合并。
3. 页dict未旋转尺寸与page.rect旋转尺寸要同frame；90/180/270deg、cropbox/非零原点/明确变换有反例。未知frame/错页/无合法bbox/歧义匹配标partial，不猜物理尺寸。
4. font runs混合字号/字体与原字符范围绑定；NFC/trim后的原unit如不能严格对齐，记录unknown而不篡改文字。真实cell可保留row/col/table ID；不自己生成column_lane或问答/续表/表头关系。
5. HTML/PPTX/OCR只支持已有前端**确实给出的**DOM/shape/box数据形态，缺字段保持unknown，不为了覆盖广度凭空给它们坐标。
6. 默认10000units/64pages/200000细元素/1000000work，caller可下调。预算覆盖索引、匹配、遍历与输出；中断不发布半完成binding，未读/deferred页不能complete。产物精简，不输出原文件路径/整页重复全文。

## A/B/C（只有三个大节点）

**A：TDD。** snapshot_contract/unit_binding先RED：旋转frame、混合fonts、跨行offset、NFC/trim、重复文字异block、缺/坏bbox、错页/缺unit、无细cells整行、zero/small work及输入不变。

**B：实现与工程。** metadata_projection/limits_identity一次集中，确认每patch可定位真实原unit、身份和原文未变、cell/row/table粒度准确、预算真的停止，旧layout_hints作为只读消费者回归；不复制其几何/语义算法。

**C：真实快照。** 自己测试/helper可对明确只读binding的原件用现有PyMuPDF/前端提取真实dict/words/cell snapshot，复用已存在native probe并限实际页数/字节/时间；该helper不进入产品模块。名创经营表、恒锋跨页项目表、金禾多列表、中微叙述页优先，再加一页未参与调试的新公司样本。目标页只作测量oracle，不写入产品code。缺binding=UNAVAILABLE；测量/绑定可靠不等于正式细分栏/细表召回已通过。

原件SHA/mtime/size、生产配置与预存sentinel保持，临时截图/table cache/native输出成功/失败都清理。无需原件备份/全文MD，不持久保存每页快照；小摘录和必要失败证据足够。

## 交付与ROOT责任

按DU3/1正常commit本branch、handoff列真实/synthetic、细cell/word来源与frame、未解歧义、caps/体积/时间、所有测试/临时恢复。STOP等ROOT接收，不并master或改默认。

ROOT将把原parser同一次snapshot/table读取显式传入，再接已有observation_adapter/layout_hints消费细metadata。本包能证明数据投影与真实绑定，不能仅凭metadata存在声称生产双栏顺序/细表头/关键业务召回已解决。若共享wire确有缺字段，给ROOT提出具体additive建议，不自己改其他包。
