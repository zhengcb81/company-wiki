# R6当前交接 — 全面整改实施中

唯一状态[CURRENT_STATUS](CURRENT_STATUS.md)/json，选`PLAN_ID=du11-source-closure-2026-10-18`/`PWF_PLAN_ROOT=docs/plans`。用户已恢复，不再按上一轮暂停启动新工区或重新revert。

## 已有工区和文件所有权

- 稳定ROOT `C:/Users/郑曾波/Projects/company-wiki`：master bb645437，恢复dbfec3be精确CI41306232306 success；ROOT维护本PWF。
- 主线整改 `ROOT/tmp/architecture-r2`：branch codex/architecture-rectification-r2-20261101，f298a383已重施候选；源码/测试在途，不在main物理目录改src。语义作者仅grammar/source_passage/business_policy/source_context；旧消费者5测试已冻结；ROOT负责迁移3测试、offline、CI summary工具及同workflow候选分支匹配。外来hook mode不要暂存。
- W23根修 `ROOT/tmp/w23-r6`：branch codex/w23-root-repair-20261101 from作者d2f6e6f0；只改实验tools/专属tests/本卡交接，不改production OCR/src/依赖/config。作者旧工区保持只读。
- 所有新工区--no-checkout+sparse，必须read-tree -mu HEAD初始化索引；不要全checkout公司资料/模型/旧产物。源码树无CodeGraph新索引，主索引帮助base结构，新增明确文件直接读；不建第二大库。

## 下一个具体动作

完成R6来源语义最终冻结与独立审查；对codex/architecture-rectification-r2-20261101执行现有完整CI，修复所有真实回归后并回master。W23在tmp/w23-r6独占工区修真实ledger/cache并独审，不切生产OCR。

1. 读取R6-ROOT、R6-source-semantics（待冻）、R6-consumer-migration、R6-independent-consumers与ROOT-test-changes收据。旧41消费者失败仅迁移私有patch到真实owner、增强exact查询/真实cache失效，没加代理或删断言。迁移schema正确新增一个既有AUTO空间账，历史facts/nullable receipt不造数。
2. 来源语义最终source_context纯策略需与matrix/typed proof区分，已计入原WorkBudget，不能增加全局16M/112或给未知业务建公司/行业词表。ROOT提醒避免重复objective扫描，待实际末次报告。
3. 集中独审确认语义/合同/recipe/helper资源及root CI diagnostics；完整unit/contract只由本候选的大节点CI执行，不反复本地超时整仓。pytest原子文件测试必须normal host Python：sandbox下os.link WinError5会掩盖成付费响应不可用，已同72域normal72P确认，不为它改产品。
4. 现有CI push加入总控codex/architecture-*，使候选可用同一GitHub CI先验收再并主线，无需公开日志API取缓存凭证。CI摘要已由真实长组RED修成首10条内分块、每条UTF8有界，17P；原63FAIL不改写成通过。修新失败只复跑对应责任域，最终CI绿后正常并线/commit/push/PWF。
5. W23看独立R6-W23-intake。旧PARTIAL 8页R0/N0、X1两失败/历史漏计与peak限制保留；四真实pathRED必须用真实X1入口stub/独立进程验证cache、预算0、inflight、异常、finite数值，不仅fake backend。新版本要真正独审，不能补造作者缺失最后两轮历史READY；生成PNG/7与8页/QA/N0/formula口径文档纠正，作者缓存不盲删。不加载模型或补跑以填未知。

## 工程整合后的顺序

structure修带闭引号编号句与备注长/跨行/同actor不同承诺scope，见R4-context-investigation；保持原始字符串与locator，确保主体引介恢复而非只删负边。再按real-source-receipts及本地schema2 runner冻结final-source单次H1，90s/16M/112原界，核12unit/native全成员与9context真实view/member对。不用v1数量或v2失败替代final。

来源通过后新独立catalog/AUTO引用既有原件做正式摘要、prepared中断/same/cross恢复、RF参数/公式/报告/snapshot实际采用，不能复制PDF/旧DB或改R3/R4封存。两旧P1临时配置absent，按C-preparation重建测试配置，不当生产写。原件/DB/WAL bytes/mtime严格保留；SHM仅相同存在/size/SHA允许mtime同步。不可构造生产AutomationStore作只读观察。

AUDIT根C:/Users/郑曾波/Projects/revenue-forecast-audit，RUN runs/r1-20261021-cn-wuxi-apptec，attempt r1-remediation-04；四报告/六issue/实施映射保持同RUN路径，scope72真实argv为R4、旧R3只描述，不为此收费重跑。ghost-formula与signed期间补集、买方范围/持续性和检测演进仍OPEN，ET unsupported/Q&A时间未知不编数。

预算config10M/$20、公司150k/$1软目标；母账1965633/762082估计、unknown8+prior7保留，本轮无真实模型。宿主C:/Miniconda/python.exe -B -X utf8；normal Git/定点部署沿既有授权，不改ACL/不no-verify/reset/clean。RF957c6283已绿且部署不再改，StockWiki381811e5本地无remote；Dayu/IQS/Dashboard/RF四WIP/外来hook及历史产物不动。全目标固定八家/泛化/三家clean仍OPEN；原生goal工具暂无active状态接口，当前是用户明确授权的手动续接，不另建竞争目标。
