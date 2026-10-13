# DU-PROFILES — 文档识别与阅读策略

状态：READY，可独立开工；不依赖另外两包完成。

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/profiles`
分支：`codex/du-profiles-20261013`
仓库：company-wiki。只在此checkout写入，原始资料在原CWP/外部根只读。

## 给新harness的任务

先读本卡及同目录上级README、design、INTERFACES、implementation，再读工作目录AGENTS。在`.planning/du-profiles/`创建并维护task_plan/findings/progress；PLAN_ID=du-profiles，PWF_PLAN_ROOT=<本worktree>/.planning。你负责可组合的文档类型策略和纯函数路由，不负责生产接线。实现完成提交自己的分支，交付handoff后停止。

## 独占范围

- `src/company_wiki/document_understanding/profiles/**`
- `tests/unit/document_understanding_profiles/**`
- `tests/fixtures/document_understanding_profiles/**`
- `.planning/du-profiles/**`

不创建上层`document_understanding/__init__.py`（ROOT负责）；不写现有`source_catalog/narrative_routing.py`、parser/selector/summary、其他包、pyproject/requirements/CI、母计划。新包使用现有Python标准库，根已按src路径发现namespace。

## 实施步骤

1. 保存git HEAD/base/status。按INTERFACES du-input/1写合成input和预期route：实际年报、年报摘要、述职、IPO确认函、`发行A股股票募集说明书`、SEC10-K/10-Q/20-F、HK中英业绩、IR制度/问答、无标题TXT、unknown、metadata与正文冲突。先RED。
2. 类型识别按披露元数据＋封面/目录/分层正文信号；行政误判优先处理。限制只看前N字会漏正文，probe按结构和文档跨度分层，记录已探测/未知。
3. 实现冻结三个公开函数，静态profile注册/组合；共同业务与风险关注点复用，类型差异只表述章节别名/优先级/语义包/摘要焦点。不要一类一套全文解析或一类一套skill。
4. 支持已输入容器中可识别子文档区间，外部链接标未读，不下载、不虚构来源；改稿/摘要/确认函用subtype区别，不靠路径猜国家或证券身份。
5. 负例覆盖同名章节、只在交叉引用里提到10-K/招股书、缺页/扫描正文、低置信generic_read。对低价值只返回administrative_candidate，最终skip留ROOT。
6. 使用本计划manifest/observations里的标题和有界原文片段作额外真实适配观察，不能复制PDF或以公司名/固定页码加入规则。英文/繁中/title缺失都测。

## A/B/C三节点

- A：接口/反例RED及profile矩阵；测试不得要求人工许可。
- B：全部本包unit和边界通过；immutable input、确定性、抽样预算限制、相反metadata内容有诊断。
- C：用不同公司/标题变体复核，记录真实支持/缺样；路径范围检查和交接。无需每helper单独审查。

集中命令：`python -X utf8 -m pytest tests/unit/document_understanding_profiles -q`；按仓内配置运行本包ruff。无网络、无付费、无全量suite/CI新增。

验收：所有冻结wire可直接由ROOT调用；确认函不会当IPO全文；A股股票措辞能识别；SEC与HK不互套；unknown仍可阅读；所有声明有输入依据。不能通过调高max_probe、改样本oracle或强制unknown都判annual过关。

## 交接

按INTERFACES第7节写 `.planning/du-profiles/handoff.{md,json}`，给base和实现SHA、公有函数、profile清单、测试命令/结果、资源上限、未支持格式、需ROOT适配字段、0原件写入和scratch恢复。commit只含独占路径，不并主线、不安装、不运行生产。
