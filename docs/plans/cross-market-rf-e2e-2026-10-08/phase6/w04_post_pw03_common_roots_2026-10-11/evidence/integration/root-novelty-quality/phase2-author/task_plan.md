# Phase 2 — 质量排序先于同级软配额

ROOT 2026-10-11已确认共同设计。原六产品freeze、30FAIL/1PASS正式RED、365工程绿与真实native FAIL均保留；不改固定事实检查。

## A 只读事实（已完成）

年报526候选/96选、15类→share7；product已选2组9spans后其余12组39spans全部budget_full。LPCVD绑定组3spans/maxscore16；钨系列组5/max17；PRISMO PD5组3/max17均已完整生成。泛化event10、project8、risk9、industry9被选。所有181诊断/32选组已读；仅focus保存实际score/reasons，报告不含全候选offer轨迹，不能声称完整还原每次选择。

## B 通用实现细则（确认后实施）

仅semantic_coverage/1内部sortkey增加质量带，不新增DTO/配置/表/人工门禁。先质量带，再现有_over_share、category、真正软重复、同产品内quantified stage/score、bounded chars/page/order。

- 0：已有source-owner明确的具体约束、量化行业变化；商业milestone必须结合完整组已有stage_assertions中realized=true的证明，不能只凭PRODUCT reason标签；customer adoption/operating milestone等具体owner分类在无已实现proof时属带1；显式否定/计划proof不能冒充已实现。
- 1：已有具体日期/项目timeline/量化行业outlook/量化经营状态等计划和事实类别；商业标签但仅计划/条件proof只在有实际数字或具体timeline时进入此带，未知阶段不冒realized。
- 2：定性项目计划、机制与具体定位；只带商业标签但无实际proof为未知上下文，不高估。
- 3：泛化event/risk/industry/other叙述；只有name/context而无事实、机制或stage proof也属此带。

重要具体risk与量化行业变化和已实现商业进展同带0，保留同带soft公平，不能被无上限product垄断。配额仍使用真实span数，整组原子选择；不拆组、不抬96/160cap、不删除候选、signature未知/截断不软重复。legacy/default0.6/0.7不读取新sort字段。

## TDD 用例与大节点

- [x] 正式公共tokenizer→完整组finalizer RED：已实现产品在低质量ESG/泛化其它category尚未满share时进入；相同商业标签的计划/否定/缺证明不能靠高score冒充已实现。
- [x] 实际3/5/3成本组的quota反例、不同主体/数字完整组不当重复；真正相同排版重复仍软降级。
- [x] 同带0的具体risk/量化行业变化在大量产品竞争下各有代表；同带公平与完整组cost/diagnostic partition/determinism维持。
- [x] 一次原365+新增必要测试、ruff/mypy；短tmp恢复；冻结phase2新产品SHA，22非写集原WIP与HEAD保持；作者STOP。

## ROOT验收

ROOT另做新attempt真实六原件回放（需要时仅加全候选metadata观察，不改变冻结check脚本语义），同source同组native原文绑定检查必须绿；原0.7.1full package hash、raw、caps、完整组/partition保持。工程绿不能代替该验收。作者不跑六原件、网络、下载、OCR/LLM，不commit/install/Git修改。

## Next Step

作者工程完成并STOP。ROOT用新freeze实跑原六文档固定绑定召回与legacy full hash，随后独立验收/整合/并线。此施工没有证明真实召回或摘要质量。
