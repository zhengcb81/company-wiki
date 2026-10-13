# DU-BENCH — 文档理解真实质量基准

状态：READY，可独立开工；不依赖新profiles/structure模块。

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/benchmark`
分支：`codex/du-benchmark-20261013`
仓库：company-wiki。

## 任务和边界

读AGENTS及本计划README/design/INTERFACES/implementation。维护`.planning/du-bench/`三PWF文件，PLAN_ID=du-bench，PWF_PLAN_ROOT=<本worktree>/.planning。构建独立金标/oracle、离线反例套件和原生只读回放。你的任务是测出真正遗漏和幻觉，不能以当前selector结果生成期待值。不要修改生产算法来使基准通过。

独占：`tools/document_understanding_benchmark/**`（包含自己的tests/fixtures）、`.planning/du-bench/**`。不写src、其他tests、config、CI、另外两包、母计划、RF/FF/Audit/Dayu/IQS。只读使用原CWP与配置外部根原件，外部根不写；无下载/LLM付款。

## 实施步骤

1. 定义du-gold/1、du-observed/1和evaluate公开接口；用合成正确/错误observed先RED。真实gold先看原文/图片，逐事实记来源/定位/主体/时间/语态/数字口径，不看新实现来挑容易通过的事实。
2. 将20调查样本作为development种子；前期已经参与调规则的中微等不能称holdout。最低关键集：名创门店总量/经营模式/年份/TOP TOY海外、恒锋两期建设/投资与未来产出、中微产品验证阶段、万润“不生产VC”与提问前提、扫描确认函、财务季报负例、微软消费制Azure/电话会角色、TAL监管业务约束。
3. 原件通过SHA及本地bindings定位；ROOT调查manifest只是定位线索，临时路径可失效。优先补A/H/US各两家新公司作为holdout，行业横跨制造/零售/软件；真实US S-1/F-1/8-K/6-K容器缺样时写UNAVAILABLE和需ROOT FF补采清单，不用合成样本顶替真实覆盖。
4. 实现offline CLI（合成、不联网）和native CLI（只读原件调用现有公共parser/selector）。ROOT以后注入新adapter，当前缺新结构/模型摘要就是NOT_EVALUATED。输出实际入口/版本/counters；不要伪造POST数、truth标签或利用gold补观测。
5. 检查器分开报类型正确率、关键事实召回、上下文完整、引用回放、角色/语态/数字口径、双语冗余、派生空间、时间/资源、未测语义。regex/数值一致不能自动证明摘要蕴含，提供人工/独立agent大节点抽读列表给ROOT使用。
6. 写负例mutation：省主语、删否定、万元→亿元、总数→新增、GMV→收入、未来→实际、问题→公司陈述、丢表头、缺页却complete、只有目录、同source新版本错复用、测试输出自证。错误必须可被测出；如果oracle无能力检出，诚实NOT_EVALUATED。
7. 恢复测试：自有TemporaryDirectory里放预存哨兵，运行工具和失败案例，核对原件/配置SHAmtime不变与哨兵复原；删除新增测试下载/截图/DB，只有小汇总保留。

## A/B/C节点

- A：金标与反例冻结，记录当前baseline的真实FAIL/PARTIAL；不要求先把它改绿。
- B：oracle自身unit/离线CLI绿，故意坏观测必须失败，独立性与字段缺失状态通过。
- C：原生代表样本回放、恢复/资源报告、holdout清单；真实质量FAIL是可交付发现，不将它伪装测试工程失败或偷偷改阈值。

测试命令：`python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q`。工具公开命令按INTERFACES第5节。纯离线工具测试与native质量报告分开；不把全公司真实回放塞进pre-commit、pre-push或日常CI。

## 空间与交接

原件0复制；gold每文档摘录≤8KiB、合成fixtures合计≤200KiB；报告保存必要摘要/引用，禁止整篇MD、全量raw文本、全屏截图堆积。自有大失败证据可压缩单份，引用必须存在。目标是可复核，不是文件越多越好。

`.planning/du-bench/handoff.{md,json}`按共享接口，额外列开发/holdout样本数、缺失类型、每维度分母、baseline问题、尚不能自动检验的语义项、资料补采请求、0付费/原件写入、恢复和体积。commit本分支停止，ROOT负责三包集成/主线发布/真实摘要大节点。
