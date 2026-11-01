# A 节点独立审查 — 首轮需修复

2026-11-01；审查者 `/root/rectification_review_a`。范围为 Q01/Q02/Q10/Q12 在 HEAD `1909286a` 之上的当前未提交改动。其他 agent 的 query/storage/legacy 工作不在本节点签收范围。没有修改产品、配置、原件、生产 DB、索引或 Git，没有收费/下载或整仓测试。

**本轮不签 A 完成：确认两个 P2，需 ROOT 修复并定点复验。** 没有依据新增公司数值错误或 P0/P1；这两项也不需要人工授权链。产品在审查期间仍可能变化，不能以此报告为后续版本倒签。

## A-01 / P2 — 泛化兜底仍按人称区分，且把名词片段当独立描述

位置：`source_catalog/narrative_source_passage.py::_subject_led_statement` 及 `_declarative`。新增判断本质是第一人称/公司前缀＋词/字数量，英文只检查固定位置不是部分 function words，中文只检查至少六字及末字。

真实 `prepare_reading_business_assessment(text, {'relations': []})` 纯 owner 复现：

| 原文 | 观察 |
|---|---|
| `Our advanced vessels and trains.` | support / relevant=True，名词短语无独立谓词 |
| `Our recently established coastal terminals.` | support / relevant=True，名词短语无独立谓词 |
| `本公司的主要产品及业务。` | support / relevant=True，标题式名词片段 |
| `我们在西部地区的子公司。` | support / relevant=True，介词/定语名词片段 |
| `Our vessels transport liquefied gas between coastal terminals.` | support / relevant=True，正确正例 |
| `The company transports liquefied gas between coastal terminals.` | unresolved / relevant=False，同义完整第三人称句仍漏 |
| `Northvale transports liquefied gas between coastal terminals.` | unresolved / relevant=False，未知名字的同义句仍漏 |
| `北岭公司经营铁路运输业务。` | unresolved / relevant=False，完整同义句仍漏 |

影响：资料准入仍由表面主语形式决定，新的 noun-fragment 可以抢占摘要材料，而同义第三人称业务被遗漏。没有把 source-readable 标记误报成已验证经营事实；`OperatingFact` 本身并未由这段代码升级。

根修建议：将已有原文章节/角色与独立陈述语法作为可读性输入，要求“独立陈述”而非词数/前缀；保持可读原话与 event/measurement/issuer proof 分开。用同义人称/姓名替换和上述无谓词片段作变形正反例，不能补某公司/某行业或另加并行谓词 owner。若现有 source capability 无法独立证明陈述，应保持有限且诚实的未知状态，不能直接将名词短语升级 support。

## A-02 / P2 — PDF 表格观测实际算法尚未进入 recipe

位置：`document_understanding/native_table_bridge.py:148` 实际 import/call `document_normalization.pdf_table_observations.build_pdf_table_observations`；新 `source_catalog/reading_recipe.py::business_algorithm_hashes.includes` 不包含该 package/adapter 子树。它被 `company_wiki.document_normalization.layout_snapshots` 的 PDF 区域之外漏掉。

独立探针：枚举实际 PDF recipe 得到 117 个模块，但 `native_table_bridge -> pdf_table_observations` 被排除。构造真实 interim pipeline，将 metadata 设为 `mime_type='application/pdf'` 和当前 `PDF_READING_LAYOUT_FEATURE_VERSION`；用真实 `build_decision_trace` / `freeze_decision_dependencies` / `current_reading_decision_matches`：

1. frozen.status=complete，baseline current match=True。
2. 进程内 patch `Path.read_bytes`，仅让 `pdf_table_observations/adapter.py` 的读取结果追加不同算法字节；没有写任何源文件。
3. current match **仍 True**；目标模块读取次数 **0**。

这证明 Q02 的源算法依赖身份仍有实际漏项，未声称生产已发生旧摘要复用。该 adapter 拥有 observed slots/headers/context 与 DU4 binder 的转换，变化能影响选择和完整性，不只是无关格式文字。

根修建议：由 PDF 前端组合 owner 声明实际表格观测算法区域并沿 import 追踪子模块；既包含 adapter 也自动包含未来 imported helpers。不能只补某个 adapter 文件名。添加上述真实 cache 比较反例，保留同一修改不影响 text carrier 的负例。

## 其余范围观察

- Q10：SourceRef/VerifiedContent/receipt/error 已进入纯 `source_contract/source_version.py`；SourceExport 使用 narrow Protocol，仍保留内容绑定和接收字节 hash。登记 writer 委派底层 identity projection，不再构造高层 SourceVersionReader；query_ref 的 lazy reader factory 保留缺 catalog 的命名错误。未发现本轮新跨层调用或功能缺陷。
- Q12：材料准备和准入已拆到明确模块；原 facade 注入 continuity backend，保留历史测试/导入点。复杂函数本身还较长，但没有仅凭行数另报 bug，也没有为了审查要求新增 registry/投票检查。
- recipe 本身按源码 bytes 缓存 AST、限制算法边界，不读取公司目录或整仓 hash，方向合理。A-02 是其当前声明范围的具体缺口。
- 没有在已审改动中发现真实公司/ticker/页码执行特判；真实文档摘录作为 regression fixture 不属于企业分支。

## 已执行的有界验证

命令环境 `PYTHONPATH=src;tests`、宿主 Python、禁自动插件并显式加载 `pytest_asyncio.plugin`。执行：

`tests/unit/test_source_contract_reader_port.py tests/unit/document_understanding_selection/test_reading_recipe_closure.py` — **10 passed / 7.28s**。它证明现有正反例通过，不覆盖上述新独立反例。

另执行纯 assessment 对照 11 条、recipe import 边界观察、真实 PDF cache 指纹模拟。未执行新的 Store 构造或模型。首轮读 `pdf_table_observations.py` 路径不存在，已根据实际 package `pdf_table_observations/__init__.py` / `adapter.py` 读取；未将索引缺边或缺文件当产品故障。

下一步只针对 A-01/A-02 修复和定点复验，再决定 A 是否通过；不用重复所有已过的公司/收费链，也不要求单 helper 人工签收。
