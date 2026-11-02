# T3 NOTE/PHYS 实施记录

状态：**作者实现已冻结，STOP 待 ROOT 集中独审和合组验收**；ROOT 维护主 PWF。本作者只实现来源备注局部 frame、来源成员/物理邻接与 exact partial 传播，ROOT 独占 terminal primitive、adapter/layout 及第三 layout heading producer。

基线：`tmp/w23-r6`，`codex/architecture-t3-source-scope-20261102`，base `c6bb801b`。沿用冻结 tests-first，未重复 47 RED；未读原件、调用模型、改配置或 Git/index。

已核现有 `page_neighbour` 仅作物理观察，不依赖未终句；TERM 投影误把完整编号句当 heading 会使其源观察失败。现 `edge` 的 paragraph-membership/block-char proof 在几何前置之后，本次抽同 owner 窄 helper，让充分的成员证明不被缺 bbox 否决。same-page 几何仅后备，不猜未知 column。

实现路径：source_scopes 只输出原始 IDs 与有界范围；sections 唯一维护父树/新 note 关闭旧 frame；exact 缺证 target 经 semantic partial 与 materials context_blocked 传播。不得只删错祖先而丢新 intro，不添加公司/actor 词库。

## 实际实现与责任

- `narrative_continuity.source_member_neighbour` 复用原 paragraph-membership 与 native block character ranges 判定，供旧 continuity edge 与新的 source scope 共用。后者优先使用该来源成员证明，不先要求 bbox/font/column；同 source、原始顺序、role/turn、原始范围仍需真实一致。
- `NativeSourceContext.same_page_neighbour` 是该 owner 的窄物理后备：观察已知同列、同源原生段落/block/ordinal/frame/覆盖及框顺序，不要求未完成句、相同 actor 或字体完全相同。既有 `page_neighbour` 没有放宽。
- 新 `structure/source_scopes.py` 只认原文行首/块首 `备注|備註 + 编号 + 冒号`，返回有界原始 intro/member/proof IDs。支持中文/全角编号，编号和 actor 不作身份。原单元长文本/换行不截断，marker-only 和同 block 拆分引介保留各原始 ID；缺证先关闭旧范围，不借旧主体。
- `sections.py` 仍是唯一父树 owner。每个新原始 marker 恢复其 outer stack 后开新 note，甲乙甲、同 actor 新备注、重复/跳号均不复用旧局部 frame。table/furniture/footnote/真实 heading 仍有原 owner 边界。
- exact 未证 targets 经 `SectionBuild` 内部集合、semantic partial 与有限结构诊断传入 materials 的既有 `context_blocked`，continuity.complete 诚实为 false；独立健康范围仍能生成材料。没有新 wire/许可/任务库。
- continuity feature `/12`，pipeline `1.16.0`，内部 `source-note-scope/1`；新模块通过真实显式 imports 进入现 recipe 闭包。本作者未运行 cache mutation 实验，不以 import 存在冒称其验收通过。
- continuity、结构 page-chain、operating `closed_source_statement`、materials 硬终句均委托 ROOT 的纯底层原语。结构 page-chain 仍保留原有冒号停止，不改 QA soft 分隔或经营 grammar/actor/数字语义。

## RED/修复/定点 GREEN（不是同次全部绿）

原 tests-first 冻结的 47 首跑和 27 真实 RED 继续沿用，未重复整 47。

| 本作者实际运行 | 结果/耗时 | 解释 |
| --- | --- | --- |
| 原 NOTE/PHYS 两文件 15 项 | 12P/3F，1.90s | 三项发现 layout_hints 第三标题 producer 仍把闭引号尾句投成 heading；保留真实失败日志，由 ROOT 从该 owner 修复 |
| 新 proof 11 + 既有 physical observer 56 + shared-budget 19 | 84P/2F，10.81s | 两 F 是本作者新增同 block fixture 错误：默认框不同，与真实 fixture 合同冲突；没有改旧测试断言 |
| 仅修正 fixture 的两项 | 1P/1F，2.04s | overlap 反控通过；split intro/原始成员边已正确，但自增“全 pipeline complete”断言忽略已有无几何覆盖诊断 |
| ROOT 修第三 producer 后仅原三 F | 3P，1.50s | 甲乙甲/同 actor/重复备注号全部通过，不重跑已过 12 项 |
| 仅 split-intro 一项 | 1P，2.87s | 按 ROOT 确认改为检查本 source scope 无缺口、原始 context refs、semantic complete；保留真实 `LAYOUT_GEOMETRY_UNAVAILABLE`，不把它冒称成整个 pipeline 完整 |

新 11 项还覆盖 guide/无号/非行首 marker 反控、中文/全角编号、无 bbox 同 block 引介、重叠原始范围拒证、未知列不能猜物理邻接、scope 上限 partial，以及 exact materials 阻断与独立健康范围保留。原 6 份 delivery 测试/夹具未改，仅新增 `test_source_scope_proofs.py`。最终原 47、ROOT 新 terminal 项和本新增 11 项由 ROOT 冻结后一次合组，不把上述分段结果合称同次全绿。

最终 Ruff 九个 owned 文件通过；mypy 八个 owned source 通过。命令及原始 pytest 输出保存在同名 JSON 的 `test_runs/test_logs`，可逐次核对。

## 冻结文件

基线 HEAD 仍为 `c6bb801b4e87bbffbab0feefbdbe663b693ab12c`，本作者不 commit/merge/push/index。以下九文件实际 SHA256 见同名 JSON `owned_files_sha256`：

1. `document_understanding/narrative_continuity.py`
2. `document_understanding/structure/source_scopes.py`（新增）
3. `document_understanding/structure/sections.py`
4. `document_understanding/structure/__init__.py`
5. `document_understanding/structure/relations.py`
6. `document_understanding/operating_states/relations.py`（仅 terminal 委托）
7. `document_understanding/pipeline.py`（仅 feature 版本）
8. `source_catalog/narrative_native_materials.py`
9. `tests/unit/document_understanding_note_scope/test_source_scope_proofs.py`（新增）

源码根为共享候选 `tmp/w23-r6/src/company_wiki`；不包含 ROOT 自己的 terminal/adapter/layout/text_evidence 文件。不以 HEAD 代替这些尚未提交文件的实际 SHA。

## 隔离、清理和剩余

独占短目录 `C:/Users/郑曾波/Projects/company-wiki/tmp/t3np-f91a` 初始不存在；五个 pytest basetemp 请求均在该目录、长度 51，日志 `CW-BASETEMP-DECISION` 均未 relocation。结束核绝对 parent、所有后代非 reparse 后只移除该目录；6 文件共 15,547B，最终 `exists_after=false`，已恢复原不存在状态。原始五份日志先存入报告 JSON，既有历史失败记录未改。共享施工 worktree 保留给 ROOT，并非待删的测试产物。

没有原件/模型/API/配置/生产 DB 访问或写入，没有独立全量测试/CI/真实 H1/正式摘要/cache恢复/RF 采用验收。旧几何覆盖状态不在本轮改写；英文 Note 与更广财务附注的歧义识别仍 OPEN。下一步是 ROOT 一次合组与集中独审，必要真实 H1 按原计划执行；本作者 **STOP**。
