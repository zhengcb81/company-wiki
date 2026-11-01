# A 节点独立复审 r2 — 原例修复，仍有同根 P2

审查者 `/root/rectification_review_a`；日期2026-11-01。复审只针对 Q01/Q02 返修、资源/成本及其直接变形，不重新运行旧52/118整组或任何公司/模型/生产数据库。当前源码与资源 manifest 绑定在 [evidence](independent-A-r2-evidence.json)。

**本轮结果：原首轮 A-01/A-02 的明确实例已修复，但 A 节点仍不签完成，保留一个同根 P2。** ROOT 已认可并将继续统一语法通道；本审查到此 STOP，不增审查队列或人工许可。

## 已通过的返修

- 原第一人称词数/中文长度/aspect兜底已撤。独立语法 owner 使用离线 POS/词典资源，未见公司名/ticker/页码执行特例。原 `Our advanced vessels and trains.` 等名词片段不再支持，The company/Northvale/北岭公司的同义完整句可读。
- 三个 R4 p12 原文和其他行业同构例通过 prepared owner；Fact 对照为原 `project_reading_business_fact`，语法可读不改变事实 proof。只证明该责任层，不冒真实112入选/实际摘要/RF采用已完成。
- 原 PDF 表格观测分支已进入 PDF recipe。真实 `current_reading_decision_matches` 在 adapter 字节变化后失效；text carrier 保持不变。语法资源 bytes、实际推理包版本改变同样使实际缓存比较失效。
- 四资源实际字节与包内 manifest 全部 SHA 相符，10,775,669 B，每安装一份。模型不按公司/run复制，不运行下载。wheel/移位验收沿用作者收据，本复审未重复构建整个wheel。
- 资源不可用返回 `unknown/source_grammar_unavailable`；scope超过4096字符返回明确 unknown、不截原文。实际fallback在同一 WorkBudget 预扣 `32*len+1`，预算耗尽先于模型，原session转partial且重复访问零重复工作；typed proof不需要POS。该系数是逻辑计量，不宣称CPU指令精确等价。
- 冷装7.13s/RSS delta272.9MB是作者明示诊断；本复审未把tracemalloc 37s当正常时延。真实worker规模/并发内存和16M/112内容召回仍由后续C节点验证，不在此虚签。
- Q10/Q12先前未发现具体问题，本次未变更其结论，也没重复旧大域。

## 仍未解决：A-r2-01 / P2，通用 lexical witness 绕过唯一语法 owner

位置 `source_catalog/narrative_source_passage.py::_declarative`：`_EN_DECLARATION/_CN_DECLARATION`命中后仍直接返回True，不调用新的matrix predicate观察。它们是宽泛的语法字面线索，不属于typed event/measurement proof。

以下真实 `prepare_reading_business_assessment(text, {'relations': []})` 全部给出 `support / relevant=True`，但同一新 `observe_statement(text)` 全部给出 `fragment / no_matrix_predicate`：

| 原文 | 缺少的语法 |
|---|---|
| `Our vessels that are transporting gas.` | 只有relative谓词，无matrix谓词 |
| `Our vessels which were built at coastal yards.` | relative/participle名词片段 |
| `The company whose vessels are transporting gas.` | whose嵌套名词片段 |
| `The clinicians who have treated rare diseases.` | who从句无matrix谓词 |
| `正在运输液化天然气的船舶。` | 的名词化/定语片段 |
| `公司拥有的沿海码头。` | 拥有的名词化/定语片段 |

影响仍是同一A-01根因：存在两套互相不一致的通用准入语法，第二套直接放行而非复用唯一观察。没有新增公司数值错误或P0/P1实证，也不把这六句都推成已证明本公司事件。ROOT应保持真正typed proof快通道，但让通用语法witness在relative/nominal包络下受matrix owner判定，或统一该通用入口；加入有matrix谓词的完整句正例，勿只黑名单这六句话。

## 执行和恢复

实际执行55个新readability/runtime项＋3个真实cache项，**58P / 22.80s**；两条jieba/pkg_resources弃用警告诚实保留。测试包含前述原NP/第三人称、p12真实unit、资源缺失/预算/超界/不重复、PDF和资源/runtime identity。

另跑6个直接owner/observer对照确认剩余P2，未改源或资源。没有源原件复制/生产库/收费/全量回归。

测试原指定初始absent的workspace目录长度62；现有pytest设施将其重定位至sandbox TEMP长度134，较原请求更长。这是既有测试路径设施的独立问题，已告ROOT，未作为A产品缺陷或重复尝试借口。测试最终自动清理重定位根，指定根亦保持absent；证据JSON记录二者。

下一步仅修剩余lexical bypass并定点复查；原首轮修复和58绿不因这一条被抹掉，也不能用58绿冒签唯一语法责任已经完成。
