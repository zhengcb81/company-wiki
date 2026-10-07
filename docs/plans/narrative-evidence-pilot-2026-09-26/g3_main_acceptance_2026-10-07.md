# G3 MAIN验收、接线与并线（2026-10-07）

## 本次授权与范围

用户通知三个G3包完成并要求查收。本次完成交接/写集核对、集中责任验收、必要MAIN接线、正常主线并入/提交推送及PWF同步；原全目标服务paused继续保持，不自动启动R2生产迁移、摘要/付费或G4工作。当前MAIN未提交G2-12与owner source_acquisition配置、RF三日志及其他仓/线程不被清理或混入提交。

## 已收到的交付

| 包 | 实际分支tip（可含后续交接commit） | 实现 | 主要证据/剩余 |
|---|---|---|---|
| RF-ASSURANCE | 4a936395，需按完整SHA记录 | e9f94059 | 74责任绿；默认SHA+size、工程阈值诊断、runtime定点包装；MAIN W1版本文件集/W2安装测试隔离/W3说明/W4贡献者指引/混合conftest问题。prepush两项缺邻仓在base同样失败，不能当新业务失败或跳hook |
| CWP-MAINT | 34d020f，需按完整SHA记录 | 245a7f77 | 35核心责任绿、旧写链薄stub、只读清单；MAIN公共CLI具名退休/help/源码指纹/工程清单。旧store字符串计数测试在base也红，不增加虚假store调用迎合测试 |
| SOURCE-FACTS | 3292eb5，需按完整SHA记录 | tools/报告多提交，核完整diff | 55责任绿，生产0写；S05/S06融资与S07身份提案，公开日缺口/retired原因如实保留；内部注册重复上界98845393B、实读36191979B、allocation/可释放unknown，不迁移决策需MAIN接受而非照搬新固定收益阈值 |

## 步骤

1. 读取正式交接/机器结果/实际Git diff；核各自写集、无生产/owner混入、真实待接线。SOURCE-FACTS测试字段exit/counts与总卡exit_code/count不完全一致，按事实规范化到MAIN小收据，不添加许可门或要求重签整个报告。
2. 在短独占MAIN接收工作树集成CWP两分支和RF分支，先复用外线集中责任，不重跑其已绿全仓/238秒历史UC。保留所有用户工作树。
3. RF先TDD版本集合与隔离安装，修W1/W2及相应说明；真正技能runtime能独立运行，测试不写用户技能目录。修prepush的邻仓发现/测试输入部署责任，保留真实三仓调用，不降低失败退出码。
4. CWP库层验收与SOURCE-FACTS提案/上界校验。若本次可在不发布半成品G2-12的前提下接公共CLI，则在隔离树TDD并集成；否则明确库层已接收、公共接线仍待MAIN，不宣称完整G2-04。
5. 真实失败只复测责任；源码/身份/预算与locator责任不删。历史数量/AST/coverage数值门按当前G2原则退休，不重新测数字凑资格。
6. 测试全在同OS账号的明确短owned根，先记absent/原清单、finally关闭进程/DB/transport后恢复。小收据存仓内，跨tool持久记录不放sandbox TEMP。生产原件/目录/库0写，模型/翻译/付费0。
7. 正常提交/并线/推送，外仓owner前后核。来源调查报告可并入CWP，但R2应用仍pending；不直接UPDATE或因为file存在复活retired。精确代码CI按实际HEAD核，纯文档不重复长测。

## 完成与剩余口径

交付收据区分accepted library / integrated CLI / published exact CI与read-only investigation；不把调查完成称生产metadata已修。S08冲突、S07公开日、S09 legacy TXT无历史回执是事实，不自动制造重新授权/下载要求；恢复/登记应使用当前正式来源入口和真实provenance，不能补假receipt。内部重复不实施对象化的理由是收益上界小且真实allocation未知、引用迁移成本，无新增256MiB资格门。

MAIN最终更新三卡/并行总包/总PWF/README和此单，保存真实命令、exit、耗时、写集、保护与恢复、主线SHA/推送/CI。总目标与G2-12/R2–R5未完成，不标complete或resume。

## 实际完成记录

- 三包写集/真实分支交接核对完成。CWP在新短工作树mc用两个no-ff merge保留历史，接线commit `b2c9e66`；RF从真实G3 tip接线`ab7a7a44`。原仓分别已ff到本地主线，RF已正常推远端main。
- RF八责任包+新增版本回归+三tmp安装入口：78pass/26.27s。正常prepush Ruff、7公开合同mypy、107精选来源/预测用例14.80s全部绿，未绕hook；使用现有FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT，未改依赖发现/跳测试。
- CWP维护/reader/调查集中114用例：113pass，一项新增扫描夹具把文件放错layout；修成entity/raw后该项通过。另新增报告输出/输入碰撞保护，定点复测5pass/0.62s；最终责任用例并集115绿（不是单命令115）。CI同范围Unit一次1921pass/104.08s。相关Ruff正常，commit静态hook绿。
- 真实缺陷：RF版本文件集含tests、安装测试写用户根、CWP旧CLI许可以及工具import找生产库。TDD先RED后接线；Windows非法?夹具改成合法#并验证URI编码；实现阶段一次CLI删除块语法错误已在收集阶段发现并修复。
- 只有CLI未完成G2补丁需要单文件stash：旧、新增删内容各44行完全一致，已成功apply/drop原stash。其余10份CWP保护文件与RF三日志SHA全部不变；配置owner不stage。保护明细见before/after小JSON；临时快照经核后删除。
- SOURCE-FACTS建议修正：S08身份与公开日冲突可分开；缺source_url/旧receipt不产生新人工许可；S09先正式legacy登记，无假回执/强制重抓。原观察报告保持历史，MAIN修正见docs/implementation/g3-source-facts/MAIN_ACCEPTANCE.md。
- R4可选决策已按证据完成“不迁移”；注册上界94.3MiB、实读额外副本34.5MiB，allocated/releasable未知、删除0。不是大规模空间释放，也不添加256MiB门槛。
- CWP `4bde75a83e888071ab06a11676bc3d98a971d3a4`已正常推远端master；prepush既有短12项集合绿，未绕hook。精确[CI37665222739](https://github.com/zhengcb81/company-wiki/actions/runs/37665222739)执行Ruff/公开类型/compile/config/Unit/精选合同/CLI smoke均success，job84秒。
- RF `ab7a7a4434bbb4c52a5bd2a6cd6ed710d7151eee`精确[CI37664909065](https://github.com/zhengcb81/revenue-forecast/actions/runs/37664909065)共享local/CI实际检查success，job31秒。不是跳过状态，也没更改workflow放过失败。
- 所有本次MC/MR pytest根和root单文件暂存目录在子进程/reader关闭后已恢复absent，清理前校验精确绝对owned路径及无reparse；两个接收树Git clean，旧G2测试目录和三个外线工作树未清理。前后保护14文件中除合法G3升级CLI外13 SHA一致，CLI原未完成增删44行完整保留；正常doc hook后再次核绿，root CLI纯内存compile成功。
- 本次模型/付费/下载/生产源登记/生产raw删/Dayu/IQS写均0。生产状态仍未迁移；R2/R3不能称完成。之后只补纯MD收据，不重跑长测试或要求新代码CI。

## 后续唯一入口

本次G3接收结束后保持总目标paused；用户明确恢复后从未提交G2-12继续（CLI夹具两项和stage_selected期间gap_plan一项待修），接其他G2/G4及实际安装，再R2正式元数据/legacy TXT，R3有限原语言final和消费者，最后R5。不重派G3、不重复历史长测、不重新跑付费模型，不提前改生产原件。
