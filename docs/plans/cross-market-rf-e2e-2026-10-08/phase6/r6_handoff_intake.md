# R6三包主线查收

状态：分包责任验收通过，进入主线并线与接线。不是产品全流程验收。

|包|真实交付HEAD|本轮集中复验|遗留主线事项|
|---|---|---|---|
|R6-FORMAT|d48ca1be9d377e14e3926b2c0ec1872ff08e0667|64PASS/12.45秒|Worker路由、表格选择、原语言、版本及一次批量locator回放；真实22页全图PPTX无文本，仍partial|
|R6-RF-INPUT|b1763fc034558674b56c941e0b13620df9c11a12|204PASS+8subtests/12.60秒|真实NarrativeRef消费、新研究、安装闭包；handoff宽集99FAIL/4ERROR不可记成绿|
|R6-FF-CAUSE|8bb7b85f57ca7effed2a42afe8fbcdbba72c15ff|36PASS/4.29秒|CWP机器原因/实际provider_started与usage证明；RF消费诊断；当前unknown不猜|

## 交接核对与并线方法

三包功能文件清单SHA全部匹配，写范围无交叉；FORMAT与RF的handoff.head指功能提交，后续HEAD仅提交交接清单，差异已解释。FF未提交仅HANDOFF.md和handoff.json，先定点提交这两项，再并入main。RF既有assurance/runs和output、FF密钥配置属于主目录原有文件，保留，不加入本次提交。Dayu零写。

由MAIN合并各自已交付分支，保留原始功能提交；不重复签身份合同。主线只在集中接线节点跑相关集成及真实原件验收；最终两组新研究再做用户要求的独立质量审查。不得用合成E2E冒充真实网络、收费模型或图片识读。

## 简化约束

来源层负责公司/期间筛选；入库层负责字节和原子保存；读取层负责当前SourceRef原件；解析层负责定位可重放；RF负责数量/目标/证据语义。不让title、URL、语言声明、旧policy观察或人工receipt重复决定访问。新的解析批量回放必须一次解析并匹配全部选中locator，不允许每个span重新解析全文。


## MAIN接线节点完成

- 三包已并各自主线；FF main a1f3e4f18bf644c6af668fddc009cacdf1aace20已推送且CI37847921596成功；RF main17fce29cbed65e839484b1df4c0c9ecf58aa51e7已推送且CI37848277872成功。CWP格式接线dbffc282已提交/推送，CI37849838844成功。
- 新格式路由、原语言、财务cell筛选、parser版本与batch生成identity、select/verify/公共transport共享回放均完成。一次解析回放所有选中locator，无全文MD/图片持久化。PDF/TXT普通batch的生成hash不因新解析器版本漂移；格式batch显式冻结document_normalization版本。
- 258项集中责任测试PASS/34.48秒；37项实际catalog→AUTO→3任务→projector→public read集成PASS/47.16秒，包含真实微软8,158,067B SEC HTML（SHA99d693f6...0bbe）；只有模型是本地ReplayNarrativeModel，无外部付费调用，不能据此签模型摘要经济语义正确。
- FF→CWP离线诊断25/25PASS，报告r6_ff_main_cause_e2e.json；脚本覆盖的一份工程报告已恢复原提交字节，其临时根确认不存在。FF→ET→CWP旧冻结契约仍PASS，新真实电话会账户entitlement限制保留。
- 实际补充发现capture争议未清空对应document列，已用共用字段alias投影修复，unknown种类按unknown处理；Worker不再比较当前kind与历史生成kind作为准入。原version/hash/byte-size/MIME绑定和locator仍保留。
- 全量CI unit现有范围2120PASS/4旧争议门FAIL，唯一4项已在上述258集中中全部通过；当前不逐修改重跑全部unit，发布后监控同一CI。4unit旧许可合同21RED→99PASS已在前提交关闭。
- 本轮清理6个owned根，释放141,697,363B，全部恢复不存在，原件/生产配置/外包工作树删除0。ruff现有CIscope和新格式测试绿，mypy五接线模块绿。

## 仍待MAIN完成

1. CWP失败边界发布有证明的provider原因、started/usage字段；FF/RF消费，unknown不可猜为0。
2. RF安装闭包定点同步、真实NarrativeRef→claim→参数消费；重做第一组三公司真实研究和独立审查。
3. 真实图片deck22页仍opaque，尚无配置可用OCR/vision正文识读；不要把named incomplete算成功skip。继续按已配置模型能力和预算调查，不硬编码供应商。
4. 现有AUTO/内容寻址对象实现跨run默认复用及显式refresh；保留原事件与费用账，不加第二数据库或人工许可。
5. 换A/H/US三家固定新样本真实执行、逐家独立审查与后续根因循环。


## R6查收、主线发布与合并后责任修复（2026-10-08）

三包已实际合并并推送：CWP master dbffc282d3247cc495790a93f745357c7eebb1d9（CI37849838844成功）；FF main a1f3e4f18bf644c6af668fddc009cacdf1aace20（CI37847921596成功）；RF main 424ba5b1596e7de0df4b3fc48cec5a0e447b0e64（合并后修复，CI37850906279成功）。分包责任验收通过，产品全流程仍未完成，外包工作树留存，不重复派发这三卡。

合并后的冻结full/replay 105.013秒，33PASS/1BLOCKED/4FAIL/26NOT_RUN/7NOT_APPLICABLE，71检查点无缺失；对前版1改善/15回退/1未解决状态变化/54不变。报告r6_merged_full_replay.json和r6_merged_replay_comparison.json永久保留，不能重写成绿。原因如下：

- CN及US：新validator要求重复unmodeled_reason，而旧输入已有rationale/measurement_rationale，违反新字段可选/旧输入兼容。真实两个subtest RED；共用层取消重复字段要求，不自动生成年度comparison或删业务解释。59项及2subtests集中PASS/4.84秒，现有125项prepush PASS/23.73秒；旧封存输入/快照不改，不加公司名单。
- HK：同一历史Social收入表格被同时用于机制支持和反证，新检查发现实质证据缺口。保留FAIL，归完整新研究重构，不抹平语义测试、不改原审查。
- PPTX：全图22页没有文本，准备阶段具名语言错误被CLI吞成NARRATIVE_BATCH_NarrativeLanguageError，旧probe靠英文substring分类失效。补闭集原因DTO（未知文本归SOURCE_LANGUAGE_FAILURE，不泄露正文/路径），测试3实际RED；具名能力缺口记BLOCKED并断言无artifact/无模型/费用0，坏字节和普通异常仍FAIL，不算成功skip。分类5RED，责任集中52PASS/4.27秒。新冻结整链回放待本次代码提交后执行。

RF九运行文件已定点同步两份既有技能（.agents/.codex，共18文件；.claude未安装），补同步targets后当前runtime整套读查零漂移。两安装实际导入3个builder，5pp→0.05均PASS。计划/应用/当前查验及入口报告r6_rf_install_*.json/r6_rf_installed_entrypoints.json。配置/output/未知文件保留。

当前CWP producer→RF公共CLI实链13PASS/2SKIP/32.02秒；两SKIP是未提供的owner原件sample，合成原件的真实producer已跑，不把它叫两份真实样本验收。测试根r6rfproducer/r6lang/r6diag已全部恢复不存在，冻结full根也恢复不存在；原件SHA/旧输入/生产配置保持。费用和外部模型本节点0。

工具操作记录：一次CLI测试夹具因猴补构造函数递归失败，修夹具后取得上述真实RED；多次猜路径失败，已统一改为rg --files先取实际文件，再读（语言模块在source_catalog，active PWF只在本根，phase6没有progress/findings）。不把工具猜错写成产品缺陷。

下一施工：先确认本次具名诊断和重复门修复在冻结整链中的效果；再做有证明的CWP provider cause/started/usage边界和RF真实叙述输入消费，跨run内容复用、图片识读及两组三市场新研究按总计划继续。身份/标题/URL/语言声明/旧许可观察不恢复为重复准入。仅大节点做集中验收。


## 修复后的冻结整链复核

CWP cda5470c、RF424ba5b1、FFa1f3e4f、ET282e8908冻结回放185.323秒：43PASS/2FAIL/1BLOCKED/18NOT_RUN/7NOT_APPLICABLE；相对第一次合并回放10改善/61不变/0回退/0missing。CN、US全部正式预测/算术/新快照/跨seed/旧快照保护恢复通过，经济路径不变。CWP cda5470c CI37851842260也已成功。原件/配置保护与测试根恢复全部通过，外部模型/费用0。报告r6_corrected_full_replay.json，两个对比报告保留。

PPTX尚FAIL原因复核更正：本样本已有正文语言声明，实际Worker走到select，已在documents[].errors提供PARSER_INCOMPLETE/DEPENDENCY_TERMINAL；不是此次具名语言错误，探针只读顶层error失去诊断。现探针在原件SHA打开后再次规范化，必须证明0units、0parser errors、全部page_count/pages_read/opaque_pages一致且>0，才将这些闭集文档错误归BLOCKED；另有MODEL_BUDGET_DENIED、坏error结构或无全图证据仍FAIL。1RED→26PASS/1.59秒，ruff绿。没有能力成功、自动skip或放宽产品完成标准；下一新冻结整链验证真实22页proof。

默认沙箱TEMP曾使5夹具setup报权限错误，显式owned短根+正常OS重跑26项全绿，不改断言。工程JSON新增输出统一LF，staged diff-check曾发现CRLF，已仅规范换行并验证JSON逐值相同，不改原始数据。

下一MAIN采集失败接线细则已写[r6_provider_cause_integration.md](r6_provider_cause_integration.md)：责任缺口在CWP公共失败边界，无启动/用量证明保持null，不增加权限或签收。其余新研究、图片识读、跨run复用与第二组仍待。


## R6查收收尾

最终冻版：CWP d41edbbad629537b3d1a6c3d23ae7862d9c78ebb、RF424ba5b1596e7de0df4b3fc48cec5a0e447b0e64、FFa1f3e4f18bf644c6af668fddc009cacdf1aace20、ET282e8908。三卡分支均为各仓main/master的ancestor，精确并线证明r6_merge_proof.json；CWP最新代码CI37852832070成功，RF37850906279、FF37847921596成功。所有工程代码已提交/推送，RF原有三assurance文件/output及FF密钥未混入。外包目录仅保留追溯，无未交付R6功能分支。

最终full/replay214.595秒：43PASS/1FAIL/2BLOCKED/18NOT_RUN/7NOT_APPLICABLE，71检查点全部保留；相对第二次回放0回退/70不变/1未解决状态变更（PPTX FAIL→BLOCKED，不冒称能力改善）。相对并线前1改善（真实HTML）、5回退（HK新检查阻断旧语义问题及其后续4项未运行）、65不变。只有HK正式forecast因旧同摘录正反混用仍FAIL；HK官方出版证明、全图PPTX正文两项BLOCKED。数据/对比见r6_final_intake_replay*.json、r6_final_vs_*.json。

全图PPTX实读SHA后再解析，实际22页全部opaque、0units、0parser errors；Worker具名PARSER_INCOMPLETE，未发布artifact、未调用模型、收费0。新测试没有把它做成skipped_no_narrative或PASS。CN/US正式结果、独立算术、快照registry、跨seed及旧冻结保护通过；新的canonical摘要未悄悄替换旧研究输入，新研究与独立语义审查仍待。

全部owned环境恢复不存在，最终峰值67,192,413B（<256MiB上限）随临时根清理；本轮工程日志不保存原件/全文图片/完整研究副本。所有本节点外部模型与项目模型费用0。

判定：三张分包责任验收及主线接线节点完成，产品计划未完成。MAIN下一优先项为已实查的provider失败证明边界/真实RF叙述输入消费，然后跨run复用、图片正文能力和两组真实研究；不用重派R6、不恢复任何旧identity/policy/receipt许可。
