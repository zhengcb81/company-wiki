# C — H1 current-v2 单次真实回放：公开合同失败，未签内容验收

ROOT 冻结 A4 能力失败传播后，仅运行一次 H1 canonical source-select，原 90 秒／16M work／112 span 上限不变。**23.170454 秒在公开 reading_context 合同处失败；本轮不重跑。** 本报告不沿用 v1 的 12/12、111 成员作为新版本通过证据。真实摘要、付费恢复和 RF 均未启动。

## 首个可确认责任

实际错误为 `NarrativeContractError: reading_context unknown fields: ['source_processing_complete']`。

- 引擎 `src/company_wiki/source_catalog/narrative_reading.py:1269` 新增 top-level `context['source_processing_complete'] = processing_complete`。
- `src/company_wiki/automation/narrative_contracts.py:1120` 的 `_reading_context` 只接受既有固定字段及 trace/deferred 扩展，没有接受这一新字段。
- 原生公开 `NarrativeSelectHandler._select_source` 在 `NarrativeSelectResult.from_dict(raw)` 发生拒绝，尚未完成后面的 selected-material replay；runner 没有绕开合同、删字段或调用私有 selector 假装成功。

这是生产者与公开 wire 合同未联调的工程缺口，不是原件损坏、预算耗尽或测试 SHM mtime 误判。建议由负责 A4 的 owner 将“正常／能力失败 source-select → 公开结果合同 → 序列化回读”纳入同一快速集成用例，保留未知／partial 含义，而非在本 runner 屏蔽字段。本任务不修改产品。

## 本轮检查点边界

| 冻结检查点 | 本轮实际观察 |
|---|---|
| p12 三个具体业务原文 unit | NOT_OBSERVED：公开结果未返回，不能签恢复 |
| 既有 D&M 原文业务测量 | NOT_OBSERVED，同上 |
| p14 完整八个原生成员 | NOT_OBSERVED，同上 |
| 全部 native 成员 111 的坐标／SHA对齐 | 本轮计数未知；111 仅是 v1 观察，不计新版本通过 |
| R4-CONTEXT-PAIR-1 至 9 | 9/9 OPEN_PUBLIC_RESULT_NOT_RETURNED，不 wholequote 匹配、不签旧错未重现 |
| 当前 coverage／selection／partial／source-processing trace | 未经公开结果合同返回，未知；不能从失败推导全文已覆盖或 source-only skip |
| Handler 对所有选中材料真实 replay | 未到此步骤，不能通过 |

失败前确实读取了指定 H1 原件并进入真实 parser/引擎；本轮未持久化内部未完成结果，不从已退出进程补造 span/member/view 索引。schema2 runner 已准备好 current span 的原文、direct-original IDs、native member SHA、source package anchors 与 group/view support/context 索引，待产品修复和 ROOT 再次冻结后使用新的输出名，不覆盖失败证据。

## 版本与读取不变性

- 425 个源码及语法资源，运行前后聚合 SHA 均为 `fc52375d2fdb67a1f576bf95d798d59f32a84c8eabbdaf8ba2a53b9cd420376c`；`runtime_unchanged=true`。
- 此冻结包含 `source-passage/6`。实际工作树与 Git HEAD 区分；不以 HEAD 代替上述 runtime 身份。
- H1 原件大小 1,216,470 B，SHA `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`，mtime_ns `1792698031359958500`；前后完全相同。本轮 observer 只观察 storage owner 实际解析并读取的原路径，不自行重选根或复制 PDF。
- catalog.sqlite3 大小 3,309,568 B，SHA `13d5fec8d8b8ce6d130a5974e721a5eee8caa167f052bb7587bfc3b03ed5f840`，mtime_ns `1793511775387103200`，前后相同。
- WAL 大小 230,752 B，SHA `e77a4a9b10d0e31cf4e45a0ca752a78cf4bf2e014c50746f5d146768e279f2d1`，mtime_ns `1793514175909561600`，前后相同。
- SHM 大小 32,768 B，SHA `af58611c512504d4fc66fd3e6d377272659ea08e9114b47bddffcced1e6d3b21`，前后相同；仅 mtime_ns 从 `1793531197332927000` 变为 `1793532898009082900`。新比较器允许这项同步变化，未恢复时间戳。`database_unchanged=true` 与 `original_files_unchanged=true`。

10 个内存正反例通过（0.18s），Ruff 通过。它们只验证 observer 比较器，不作为真实原文召回或归属通过证据。未构造 writable CatalogStore，没有 AUTO、原件副本、下载或模型 POST，未读密钥；正常本地 POS 能力在引擎内执行。

## 证据、恢复与下一步

所有本轮输出位于 `.planning/architecture-quality-20261101/real-acceptance/`：

- `h1-current-v2.json`：保留真实 FAILED 和 DB/WAL/SHM／原件／runtime 前后观察；shell 非零退出。
- `h1-current-v2-summary.json`：原收据 SHA 和 v1 未改 SHA；不更改原 receipt。
- `h1-current-v2-inputs.json` 与三个小 `.gz`：**真实启动前** runner／cases／comparator SHA 和精确输入快照，不是事后冒称启动前冻结。

本轮只有自身新证据文件，无外部临时测试湖或应删除原件。v1 和其 addendum 原样保留，不恢复备份、不清理他人文件。下一步由 ROOT 修公开合同并快速回归；当前产品失败真实保留。新的真实摘要／恢复／RF 仍按 C-preparation 的独立新环境方案，须待 source 工程验收后调度，不能从本次失败跳到付费阶段。
