# CF3 结构关系与缓存身份独立审查

日期：2026-10-25。审查者：独立 agent `cf3_root_quality_review`。

结论：**本节点 PASS，0 项 OPEN 问题**。仅指结构关系效率、覆盖诊断索引与算法缓存身份的代码节点；真实 IPO 是否能够在原有 16M 预算内形成完整候选，仍须 ROOT 新 attempt 证明。不得据此关闭整个 CF3 或把内容质量标为通过。

## 审查绑定

基线 HEAD：`c3ad2ece1827cc7558e3c86a9f5b327c644d9595`。产品代码 SHA-256：

- `structure/relations.py`：`df8334faeb9ae648f329db67ee06c53dcb2f779b01a9017a23a296f88ad7fcef`
- `decision_inventory.py`：`0064578ac7b2dce0df3f82996c0b619937ef8fd602e9a30f615bf185c30dfeb7`
- `structure/__init__.py`：`5b86913bf420c13af3e62fa4eceb310c51e24599c6cd58a810ce2fbeedc2c412`

完整测试绑定及机器结果见同名 JSON。审查未修改产品、测试、配置、数据库或原件，未提交。

## 独立验证

1. 对基线函数进行 750 个固定种子的中性随机差分，覆盖列、DOM、实际书写系统几何三条路径；最终包含 285 个有真实关系输出的正例。最终输出与基线一致，仅允许删除下面已证实的异 kind 几何误配；其中 127 例受该修复影响。配对方向、列表顺序、最近邻和距离 tie 未发生意外变化。
2. 250 个混合 original / 缺省 source 的随机输入：每条已输出关系的两端 source 相同；未把缺省 source 当作任意来源通配符。
3. 独立检查真实 script 信号与 declared language 的分工：几何仍按文本书写系统判断，未以 `zh` 标签一刀切拒绝真正并列的中英文。其他列/DOM 路径保持原有 language-family 语义，语言未知不冒充双语证据。
4. 两个不同宿主路径、LF/CRLF 相同源码及嵌套新增/删除模块的闭包探针通过；现有结构包下未来子算法自动进入原有 `business_algorithms`，没有第二缓存、registry 或公开 wire 字段。
5. 自行运行三组聚焦测试：**52 passed，9.07 秒 pytest / 12.517 秒命令总耗时**。命令、日志与清理收据：`cf3-reviewer-focused.log`、`cf3-reviewer-focused-receipt.json`。测试临时根已恢复不存在。

随机探针在 `.planning/cf-source-20261025/reviewer/probe.py`，结果 `probe-results.json`。未复制原文或整份产品源码；仅内存读取 Git 基线。

## 找到并已修复的问题

**R1 / P2：几何分支缺少 kind 边界。** 最小反例：同页同高的左右两框，一端英文 heading，另一端中文 paragraph；没有显式 column。基线及第一次被审代码均输出 `language_parallel`。这不是本次效率改造引入的问题，但与其他两条路径 `_aligned` 的结构类别约束矛盾。

已向 ROOT 提供可复现输入。ROOT 在共享几何 owner 加入 `left.kind != right.kind` 排除，并添加负例；独审重新跑差分、原正例与 52 项测试后确认修复。实际相同 kind、不同 script 的正例仍通过。状态：CLOSED。

## 预算与测试调整判断

- 页/列、DOM、几何的索引遍历、排序和 script 文本块工作在操作前向原 budget 付费；只跳过已经证明不可能产生关系的组合。真正可能的双语组合仍付原配对工作，未提高上限、伪造 absence 或增加备用账本。
- 共享 `WorkPlan.stage` 的既有保守预留尚存。它是否还能精简，需要真实新 profile 支持，不能把本节点改善当作已解释旧 IPO 的全部 5.43M reserve。
- 原 12 参数缓存测试从 mock `inventory.import_module().__file__` 改为仅拦截指定真实 owner 的 `Path.read_bytes`，保留真实 interim pipeline、freeze complete、未变 same、变后 changed 四项断言。认可该修改：新闭包不再通过原 import mock 发现子模块，旧注入点失效；断言没有放松，也没有写生产文件。新增闭包测试补上此前遗漏的 relations owner。

## 局限与执行卫生

本次没有运行全量 pytest、下载、API、LLM 或真实 IPO。没有读取密钥。真实内容 gold、摘要与缓存恢复仍是后续节点；不能从关系函数的合成正负例推导整份文档召回率。只保留命名脚本/证据，探针 `TemporaryDirectory` 与 pytest 临时树均恢复不存在。

探针首次 ROOT 路径算错一层，立即以明确 parent 修正；后续重跑恰遇 ROOT 修复 R1，旧基线等值断言因此失败，随后将已证实的异 kind 误配删除作为唯一允许差异。两次均未修改产品或产生虚假通过记录。

## 扩展审查：覆盖页诊断真实热点

ROOT 的实测新 IPO 仍为 0 span，但固定深度 profile 证明旧 `_build_structure` 按 gap 页数乘全源 unit 数预留 **5,154,576** 工作；对应 `_coverage_diagnostics` 每页重新扫描全源。这是新证据揭示的共享效率根因，不能以原关系负例测试绿推断整份 IPO 已修复。

已审查 ROOT 修复：一次 `page → original unit IDs` 索引代替逐页扫描；只有真实存在 opaque/deferred 页才遍历原 units，无 gap 页不建立空耗索引。原账本在索引前预付 N+P，每份实际输出的成员列表在 copy 前另付大小。保留 opaque 在前、deferred 在后、原 page 顺序、重复页、无 unit 页的空列表、原 unit 顺序、独立 list 与 native partial/unavailable 诊断。

独立追加验证：

- 500 个固定种子的 helper 输出与 Git 基线逐项完全相等。
- 24 个完整 structure 输入，含重复/空页、三种 native_scan 状态；最终 structure、coverage、diagnostics 与基线完全相等。
- budget=0 时不迭代 source；重复页结果列表无别名污染。
- 追加 **22 passed**（覆盖新 3 项诊断测试和已有共享预算 19 项），2.17 秒 pytest / 3.771 秒命令总耗时；临时树恢复不存在。见 `cf3-reviewer-coverage.log` 与收据。
- 两个 mypy 变量只改名 `page_lanes` / `dom_scope`，重新运行前述 750+250 探针结果不变，以上 SHA 已绑定最终改名版本。

此扩展无新 OPEN 问题。第一份新回放使用 venv/PyMuPDF 1.28.2，14,006 units，与旧 14,025 不同，已明确保留为非同 backend 诊断，不能据此比较减幅或耗时。

ROOT 随后使用 Conda/PyMuPDF 1.26.7 形成 `cf3-ipo-indexed-replay.json`：与旧基线的原件 SHA、429 页、14,025 units、parse 420,052 一致；理解工作为 6,334,220（旧 11,473,800），但候选阶段仍耗尽原 16M，所以是 **partial、112 selected**，没有变成整源 complete。112 亦受原 span cap 限制，不能视为内容召回充分。

独审只读检查该收据，所有 runtime 源文件 SHA 与被审源码一致；caller accepted work 相加为 15,998,158，与唯一账本 used 完全相等；嵌套 stage 的 inclusive 数值不能再叠加。source stable、hooks restored、protected unchanged 均为 true，无 write store、model/API/download/raw-copy 调用。报告 SHA：`21cfbb96fcf57745c0bae16e49254389fdff8403f69f9307d629d7c3daf1dda5`。未重新运行原文回放。

该收据明确 `NOT_GRADED_NO_FORMAL_IPO_GOLD`，认可此边界。剩余 fact/candidate 热点、正式内容 gold、摘要与恢复仍 OPEN；独审代码节点通过不关闭它们。
