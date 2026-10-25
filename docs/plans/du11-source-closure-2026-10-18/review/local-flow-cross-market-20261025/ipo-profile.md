# 中微 IPO：一次有界工作量热点诊断

## 结果与真实性

这是 ROOT 在三例报告冻结后要求的新增诊断，不改写原始三例结果。仍以同一份 SHA 绑定原件、同一个配置 16M 共享账户运行 parse＋select，最多 112 span；未提高预算，未编译模型，未保存新投影或原件副本。

**与未插桩实验的 9 个结果字段全部相同：** 429 页、14,025 单元、parse 420,052、最终 15,999,740／16M、exhausted=true、8,361 候选、0 span、needs_review。因此本轮计数可用来解释前一实验，不以插桩耗时作为性能基准。

只在诊断层继承 WorkBudget，实际 root ledger 负责计数；scoped 子账户仍使用原基类并转发到 root。只取一个固定起始 frame，最多跳过四个基类 charge 转发 frame，不遍历全栈。实际跳过 168,136 个转发 frame，未遇无法定位的转发。

accepted_delta 合计 **15,999,740，严格等于 root.used**；rejected_requested 另记 **276**，没有算入已接受工作量。所有 in-process hook 均已恢复；源码、配置、DB 前后 SHA 相同，未构造写 Store，也无模型／API／下载／原件副本／临时目录。

## 实测阶段

| 边界 | 进入 budget.used | 退出 | 接受的增量 |
|---|---:|---:|---:|
| PDF parse | 0 | 420,052 | 420,052 |
| reading._understand | 420,053 | 11,907,878 | 11,487,825 |
| 其中 pipeline.understand_units | 434,078 | 11,907,878 | 11,473,800 |
| reading._candidates | 11,907,878 | 15,999,740 | 4,091,862，耗尽 |

`_understand` 包含 `understand_units`，两项不可相加。前者之外有一个进入选择时的单单位计费，表中解析＋外层 understand＋candidates＋该单位正好为总量。

因此，不能把问题笼统归因于 PDF 转文字：原生解析约占总账 2.6%，understand_units 约 71.7%，后续 candidates 约 25.6%。这是**逻辑工作量比例**，不是 CPU／耗时比例。

## 主要直接计费点

| 文件／函数／行 | accepted_delta | 接受调用数 |
|---|---:|---:|
| structure/_work.py reserve:17 | 5,429,520 | 56,707 |
| structure/_work.py WorkPlan.stage:33 | 3,208,304 | 9 |
| narrative_reading.py statement_members:445 | 1,088,288 | 2,330 |
| layout_hints/contract.py charge:185 | 590,246 | 42,933 |
| narrative_operating_relations.py fact:612 | 415,020 | 501 |
| narrative_operating_relations.py local_qualification_dependencies:375 | 413,816 | 2,769 |

精确拒绝点为 `narrative_operating_relations.py local_operating_context_dependencies:555`：请求 276，剩余额度 260，拒绝而未扣入 accepted。没有把拒绝尾部金额加到预算消耗中。

`structure/_work` 明确是逻辑阶段预留 owner：输入访问、文字块、线性 pass、排序与图遍历计费，不是 Python 指令计数。上述 reserve/stage 是**直接扣账位置**，并不证明它们调用的每个结构算法存在重复或浪费。下一步应结合其调用方／阶段计划判断能否复用结构结果、降低重复 pass、分段恢复候选；不能靠删合理收费来伪造效率提升，也不能仅据总数加额度。

完整热点、阶段边界、源／配置 SHA、与前一实验逐字段对照及 hook 恢复证明见 [ipo-profile.json](ipo-profile.json)。本 profile 不给 IPO 内容金标或召回评分，不批准正式摘要或 RF。
