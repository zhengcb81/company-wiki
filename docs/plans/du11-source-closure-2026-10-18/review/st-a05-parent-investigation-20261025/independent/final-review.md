# ST-A01/A05 真实来源层级修复：独立终审

## 结论

**工程子节点：PASS（可按“有界工程改进”发布）。A05 真实业务父级目标：OPEN，不能标记完成。**

当前改动把原生多层列表的父级栈、页码页脚识别、局部来源证明缓存与预算计量补齐，并通过聚焦回归。它没有绕过来源完整度或列/版面校验。真实无锡药明康德年报中，Chemistry 父项在 p13、D&M/TIDES 子项在 p14；尽管 p13/p14 不在局部 deferred 页列表中，p14 实际任务仍没有收到 p13 Chemistry 父项。原因是现有物理证明把全文件 coverage partial 当作所有页边都不完整；另外这组版面的 column 仍是未知值，现有代码按预期 fail closed。故可发布本工程子节点，但不得宣称真实 A05 闭环。

## 范围和绑定

- 仓库 HEAD：`1171aa6f8aad59001554b026200cf0dc6f0a439d`
- 终审依据：`review-final/final-receipt.json`、`review-final/final.log`、真实 SourceRef 回放 `attempt02/`，以及本目录的 [probe-receipt.json](probe-receipt.json)。
- 本审查没有改产品代码、测试或原件；只新增本 `independent/` 审查材料。

| 文件 | SHA-256 |
|---|---|
| `src/company_wiki/document_understanding/structure/__init__.py` | `db3b2cc328a8253de22cea4902a97da1ba9352b1042e11be1fcfff2d080a29bc` |
| `src/company_wiki/document_understanding/structure/layout.py` | `b365e55b6f0ad4b2a84f3fa3f7195c628b4fe401633bb487208b3edd77fa9072` |
| `src/company_wiki/document_understanding/structure/sections.py` | `8ff70fc94b5af97d856a651235577d85087fbdd2c0b42863f6701b3517dc6b4d` |
| `tests/unit/document_understanding_structure/test_page_counter_furniture.py` | `5b7af5bd601b01c2ba014cf1f08fe8cdead5dc868deb6b6e2d4c07b590f0cdb6` |
| `tests/unit/document_understanding_selection/test_reading_multilevel_native_ancestry.py` | `ec54418ca75cef6016bf86cc92f00f38f57d357514e2754706ae4ed1714aa675` |
| `tests/unit/document_understanding_selection/test_reading_decision_inventory.py` | `ed3c44551a1bcf9ddc14b9de6453c05e0784f0c34deca77eead93f0ece6b5926` |

`decision_inventory.py` 的现有实现 SHA 为 `d60bcdfd715615eea967b79f80fbc592d047f1ab85e66dfa57b66dc1eb05d46e`。它已经对 `structure`、`structure.layout`、`structure.sections` 等模块的实际字节做 cache fingerprint；本次参数化回归也明确覆盖 `structure` 和 `structure.layout`。

## 质量检查

- 新增的多层中性用例验证编号父项→缩进 bullet→罗马数字事实的祖先链进入引用和编译任务；同级切换、页缺口、来源不同、column 未知、正文中断和不可信页码均不得继承父级。
- 页码识别要求来源 ID、物理页码对应、有效几何、页边位置、相邻页连续、同页候选唯一以及归一化位置稳定。测试覆盖中英/中文格式、上下页边、错误页码、总页数冲突、单页孤立数字、正文位置、表格、异来源、几何漂移、跨边/跨格式重复和非相邻页。`review03-red`、`review04-red` 均先真实失败，最终版本在聚焦回归中通过。
- `page_neighbour` 的正/负证明按一次 scope build 内的物理边缓存；每个 opener 和 continuation cursor 都收费，sections 无 native context 时也使用共享 WorkBudget。布局阶段从 6 调整到 12 个逻辑 pass 预留。当前逻辑工作仍受原 16M 上限约束，没有新增预算池。
- 最终聚焦测试：**206 passed，15.44 秒**；pytest 临时根恢复为不存在。ROOT另报告 Ruff 和 Conda `mypy3src` 通过；本报告未重跑这两项，也未运行全量 pytest。
- SourceRef 回放：原件 SHA 验证且 source inventory 稳定；生产选择仍是 **112 spans / 9,030 chars**，共用预算 **12,978,295 / 16M**，没有模型调用、下载或原件副本。内容质量没有重评，模型响应没有审查，不能以该回放替代摘要质量验收。

## 旧检查点和 A13 输入

独立核对旧报告中的 10 个 `PASS` 目标（ST-A03、A04、A06–A12、A14）：其当前实际编译 payload 保留原核验材料。A03 的旧 p16 paragraph 19 表格行没有继续传入；该行带 `table_structure_ambiguous` 标记。A03 的 p11 四地区收入事实及 p16“客户母公司所在地、可比期间已调整”说明则都在当前实际模型 payload 中，因而仍足以支持原来核验的输入事实。其他 9 个 PASS 目标的旧 span ID 全部仍在当前选择和实际 payload 中。

A13 的七个原输入 span ID 与 attempt01 完全相同，且七项都在当前模型任务的 support/context/member 中；p119 的两项政策证据也实际进入 payload（`page:119/paragraph:9`、`paragraph:11`）。这不是只在候选集合中找到它们。选择上限仍为112，A13 输入未被 A05 修复挤掉。

## A05 尚未闭环的根因与最小架构建议

真实回放中 Chemistry 父项仍是已选来源，但 p14 D&M/TIDES 实际任务没有该父项；只把候选或 section 结果标成已选不算闭环。读取当前物理 owner 可见两个不同约束：

1. `_understand` 把整个 `parsed.coverage_complete` 折成单一 `native_scan=complete/partial`；`NativeSourceContext.coverage_complete` 又要求全局 `native_scan == complete`，`native_page_neighbour` 因而拒绝所有跨页边。当前 140 个 deferred 页中不含 p13/p14，但其他页的缺口仍封锁这条局部边。
2. 物理证明还要求相同且已知的 column，并单独要求 bbox lane 稳定。真实目标 units 的 column 未知。不能把 `None == None` 当成同列，也不能只删掉 column 校验。

建议下一个 PWF 设计/实施节点保持这些责任分开：

1. `DocumentStructure` / native observation owner 输出可追溯的**按页 coverage**，区分全文件扫描是否完整与本次邻页边两端及其顺序片段是否完整。全局状态仍保留 `partial`；一处无关页的 deferred 不应自动否决其他本地完整边。若任一端页不完整、页间存在未解释正文/未知页、来源不同，边仍失败。
2. 布局 owner 为边输出明确的 lane 证据（如 `same_lane` / `different_lane` / `unknown`），并绑定页面 frame、页内候选以及几何来源。`unknown` 继续拒绝；只有具有正面观测的同列/单列关系才能通过。不要把几何位置本身当业务父级。
3. `NativeSourceContext` 只消费局部 page coverage 和显式 lane proof；`sections` 只在物理边通过后负责业务父项/context 继承。父项继续作为引用 context/source proof，不混入事实 support，也不增加span预算。
4. 用三组大节点集成测试闭环：真实 p13→p14 同页边在其他页 deferred 时可以证明；端点页 deferred/opaque 时拒绝；lane 已知同列可通过、异列与 unknown 均拒绝。再断言 D&M/TIDES 的**实际 model-view task**同时带 Chemistry 父项及本地父项，且页脚不在正文、同级 Testing 不泄漏。保持 16M 与112-span上限不变，无需引入新状态库或授权门。

这项建议只界定下一节点，不代表本次已实施或允许放宽安全条件。A05 的结束条件仍是 SourceRef 完整回放中物理 proof 真正产生、Chemistry 祖先进入正确子项的实际任务，并保持其余检查点和限制。

## 最终评语

**本工程子节点 PASS，可作为限界清楚的结构/页码/预算改进发布。A05 真实父子业务归属仍 OPEN；禁止把本次 206 例绿灯或 selection 候选存在描述成端到端解决。**
