# DU5-CORPUS：真实新文档、独立金标和类型覆盖扩充

状态：READY。工作目录 `C:/Users/郑曾波/Projects/company-wiki-du5-corpus`；分支 `codex/du5-corpus-20261015`；源码固定基线 `8c027011037dc8c8659235fb65f529028dcd15ca`。自己的 PWF：`docs/plans/du5-corpus-2026-10-15/`。先读 task_plan、本卡和 INTERFACES。

## 为什么值得独立做

现有 DU-BENCH 已有完整 loader、observer、gold/observed/evaluation、污染记录、回放与 mutation 控制，不需要第二套 benchmark。但 `coverage_matrix.py` 仍列港股季报、美国中期6-K、S-1/F-1、8-K/6-K exhibit 等真实缺口；部分 `sample_ids` 对应命名样本并不等于存在可加载金标，须逐项实查。原 Microsoft/中微/万润/名创优品及旧 holdout 已用于诊断，不能继续称为全新泛化集。DU4 真实表格保留包又是截断观察，不能代替另一公司的完整原文验证。

本包扩充现有验收材料，让 ROOT 后续生产候选接受新原件的检查；不承担生产算法修复，不因 baseline FAIL 拖住交付。

## 独占可写范围

- `tools/document_understanding_benchmark/**`：优先新增 `gold/du5-*.json`、`tests/test_du5_*.py`、manifest/fixtures，以及对既有 `coverage_matrix.py`、`contamination.py`、holdout/README 的必要扩充。复用现 CLI/observer/oracle，不重写 matcher 或造第二 schema。
- `docs/plans/du5-corpus-2026-10-15/**`。
- 其他所有路径只读，尤其 `src/**`、parser、router、selector、v4、原件、总 PWF、已有真实质量收据。ROOT 接收前不修改本工具包；三外包也不写它。

## 工作内容

### A：真实盘点、冻结来源目标、工具反例

1. 阅读现 README/EVIDENCE_CONTRACT、schema/records/gold、coverage_matrix/contamination、真实 native observer 和现测试。先输出实查矩阵：shape、已有金标、可绑定真实原件、实际可读入口、已测/未测阶段；把“有名字/有 schema/有 synthetic”与真实 gold 分开。
2. 优先从本机现有原件中选 **6–10 份、至少4家公司、覆盖A/H/US**，力求至少6种形态：A股半年/经营季报/稀疏纯财务季报、IPO或增发可转债、港股中期或双语报告、US 10-Q/20-F/6-K/exhibit、IR/原语言电话会。特别安排另一公司的期间/单位表格，以及另一公司的否定/计划/问答；不是同公司换个文件名。
3. 先核已有污染名单/计划记录，再确认真实 SHA 与来源身份。缺类型在现本地找不到，记录具体缺口与后续采集条件，**本包不下载、不调模型**。不为覆盖率造假、不将8-K主表当完整exhibit、不把中文年报当美国中期。若连最小真实集都不足，交付工具与已核部分并明确 PARTIAL，不自称全部完成。
4. 读原件，独立写来源侧业务目标与逐项原文定位：主体/对象、经营阶段、计划/否定/条件、出海/新业务、投资或产能/收入区分、金额/数量/币种/单位/期间。纯数字财务季报可没有 required_business；若输出数字仍核正确性。重要性由原文阅读判断，不能照 selector 结果倒推。
5. 在读取本样本候选输出前冻结 gold 与范围（必要的 page/line/正文限定、已读/未读区域），记录摘要/金标 SHA、冻结时间和已知 prior use。保留原 gold、原 critical 分母和旧 FAIL；新集单列。
6. 先测试真实不一致：coverage 名称存在但 gold 不在、重复/错SHA/错页行、部分不透明、一个替代 support 不可用但另一个完整、声明 complete 却缺关键上下文。若现实现已正确，保留正控；不要为了 RED 伪造缺陷。新机制的首个真实 RED 是必需留证。

### B：沿现 benchmark 扩充并集中验证

- 新 gold 使用现 `du-gold/1`，新 sample 前缀 du5；新增冻结/范围信息放现可选 metadata 或本包 manifest。不要添加要求全库重签名的门。
- 现有 evaluate 继续负责确定性检查；自由文本蕴含用实际独立审查，未审给 NOT_EVALUATED。不得从生成摘要或 flattened selected text 充当来源证据。
- 修 coverage inventory 的共同责任：真实原件、gold存在、可读、已选择、正式摘要已审是不同轴；不要仅改文案声称全覆盖。新工具若需代码，优先沿现 coverage 模块扩展，不另建 corpus registry。
- 一次集中运行现 benchmark 测试（实际 `pytest -q tools/document_understanding_benchmark/tests`）、Ruff 本包。旧样本断言维持；固定总数断言应改为明确旧集合保持+新集合校验，不删旧个案。
- 金标字节/压缩夹具必须通过实际 Git add→blob→fresh checkout 验证；复用仓内已有属性与 retained fixture 测试，不改原件或gold来适应换行。

### C：原件回放与交付

- 使用当前真实 CLI `python -B -X utf8 -m tools.document_understanding_benchmark --mode native --bindings <owned local mapping> --output <owned temp>`；参数以实际 --help 为准。local bindings 不提交，不复制原件。
- 串行、一次只开一个原生解析子进程，沿现有有界子进程 owner 设置明确超时并保留失败；不要同时跑多份大PDF占满CPU/内存。每个 source 只解析一次，复用它的实际观察做统计。原件前后 SHA、生产配置/sentinel、临时目录恢复留证。
- native baseline 可能 FAIL/PARTIAL/UNAVAILABLE，这是待修生产质量而非本包自动不合格；报告正确分母、各阶段漏失和未读范围，不修生产源码使之绿。
- 至少一组新来源目标由另一独立 reviewer 看实际原文定位复核；只在C大节点做，不加每fact审批。盲审能力不足就明确未独立审，不把自己二次阅读写成独审。
- 交付 manifest、冻结 gold、类型矩阵、最小真实摘录与观察收据、旧/新分开报告、全部测试命令/结果和 `handoff.md/json`。STOP 等 ROOT；后续新候选质量由 ROOT 使用同一组冻结目标比较，不能换金标洗绿。

## ROOT 后续接入

将作者工具包合回 CWP，再对正式接线候选走同 CLI/du-observed。旧来源集作为 regression，新集首次候选结果作为冻结泛化测量；该样本一旦用于修规则，随即标 regression，后续不再称 blind holdout。本包不依赖另外两张 DU5 卡，也不等待 v4 实现才开工。
