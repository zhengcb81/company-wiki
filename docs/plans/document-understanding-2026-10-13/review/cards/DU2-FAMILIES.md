# DU2-FAMILIES：文档用途、生命周期与完整阅读策略

状态 READY；这是新包，不是已交付 DU-PROFILES。可与 FACETS、LAYOUT 及ROOT根因修复同时开工。

仓库：company-wiki。
工作目录：C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/families
分支：codex/du2-families-20261013
PLAN_ID=du2-families；PWF_PLAN_ROOT=<本worktree>/.planning。

## 任务与上下文

先读本checkout的AGENTS、上级[report](../report.md)、[strategy_matrix](../strategy_matrix.md)、[INTERFACES](../INTERFACES.md)，再读原DU设计和sample_manifest。目标是把各类文件“如何识别、先读什么、哪些限定不能丢”做成可导入唯一策略库的数据规格和证据，解决泛化覆盖。你不改router/selector，不接生产，不新建skill。

只写 docs/plans/document-understanding-2026-10-13/review/deliverables/families/** 与 .planning/du2-families/**。自有数据测试也放前者tests/。禁止写原profiles/structure/benchmark/ROOT模块、FACETS、LAYOUT、共享PWF/接口/config/CI/安装/其他仓。

## 实施步骤

1. 记录base/status，创建自身三PWF文件。把每个文档形态登记到index.coverage的独立spec_status/evidence_status/integration_status及gaps；不能只列15个profile名字就报覆盖完成。
2. 按INTERFACES第2/4节先写两个代表规格和正反例，写数据验证测试并记录RED。随后覆盖矩阵中的定期年/半/季、A/H/US招股、定增/可转债/可研/项目变更、IR/call、release/deck、容器/附件、摘要/更正/制度、问询和重大经营事件。优先P1；缺样部分保留提案，不编事实。
3. 为每个用途列章节位置/层级与简繁英别名、识别证据/反证、业务问题、必要上下文、降权例外、fallback。10-K/20-F及10-Q的Part不可混；S-1/F-1不只贴form标签；8-K/6-K明确主件/附件读取范围。修订/摘要是正交修饰，不额外复制全部策略。
4. 以本地原件优先，至少核对年/半/季、招股、募资、IR/call、经营表/图等不同形态的小节。原20份样本是开发资料；cn-ir-policy其实是有业务活动记录，不能当制度负例。缺US注册/附件/版本对时可只读官方完整页面研究结构，并在acquisition_requests.json交ROOT补采需求；不直接下载入生产，不用搜索摘要代替正文。
5. 写真实case短引文/原SHA/定位/关系、反例与证据状态。用两家不同公司验证可复用的规则，且不得把公司名/固定页码变成执行信号。研究型文字与公司披露分开。样本各处合计引文≤8KiB/source；网页引用另遵来源限制。
6. 数据测试检查唯一ID、引用存在、枚举、非空理由、scope与生命周期、重复role保留别名、配额及显式跨市场反例差异。自动RED限规格结构不变量，语义输入/期望交ROOT行为测试并记NOT_RUN_ROOT_INTEGRATION；应读/不读含义在C节点对照原文核对。不能比较自己的JSON副本冒充测试，不能虚报引擎召回。
7. 交付 README、index.json、records/、cases/、tests/、coverage_matrix.md、acquisition_requests.json（可空），以及自己的handoff。ROOT把规则导入唯一registry并做实际消费测试；数据包工程通过不代表生产已支持全部类型。

## 三个集中节点及命令

- A：两份代表规格、失败反例、覆盖清单；确定输入/输出和目标没有强制财务抽取。
- B：全数据一致性和反例测试；多市场/生命周期变体，去掉重复规则。
- C：原文对照核实及未覆盖清单、恢复/范围检查、一次交接。

命令：python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests -q

只测本包，不跑完整公司研究、全仓慢suite或网络CI。测试断言真实涵义和明确关系，不以凑例子数量过关。可保留少量本包数据校验helper；不能做第二router或oracle。

## 独立环境和交接

bindings.local.json不提交；原件只读SHA/mtime前后一致。scratch全部自有TemporaryDirectory，含预存哨兵，成功/失败finally恢复；不留整篇MD/PDF拷贝或截图集合。建议本包持久数据≤512KiB，超出解释真实必要性，不删重要证据凑体积。

0付费模型；不需等待其他卡的实现。正常提交本分支，handoff按公共第6节，列清真正实现SHA/试验/缺样/接口偏差。然后停止等ROOT接收，不合master，不覆盖已在制目录。
