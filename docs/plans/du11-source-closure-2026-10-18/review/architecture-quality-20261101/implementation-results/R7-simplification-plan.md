# R7 过度门禁系统精简（2026-11-02）

状态：工程已实现并独审通过、正常发布及真实C待收口。用户最新要求取消300KB等任意表示门槛并全面清理类似设计。延续当前主PWF，不设新目标/人工许可。R6/T3工程已独审及完整候选CI通过，fa8ef38e已正常推送master（167P，push78.141s）；真实H1 v3观察记录丢失，结果未知，真实摘要/缓存/RF采用仍OPEN。

## 统一规则

成功任务不能因日志、可选诊断、收据字数/字节数或无关未提交文件而失败。报告完整落盘，控制台可简明；可重建缓存坏了应跳过并诊断。显式pin、原件字节/身份期间/as-of、真实输出I/O、幂等恢复和配置的实际费用/token/时空预算仍由唯一责任层执行。不是删除事实正确性检查，也不引入caller skip_validation开关。不得静默裁掉必须证据换小收据。

## 工作归属与实施顺序

| 工作线 | 独占范围 | 根修与测试 |
|---|---|---|
| ROOT观察器 | tools/source_case_*、其两个unit tests、主PWF与发布 | 删除300KB/16KB/32祖先表示门；完整JSON，不因大记录变OBSERVATION_INCOMPLETE。分离语义context与物理proof，反控循环/缺失/外来文件覆盖。 |
| CWP核心 | src/company_wiki/{automation,source_catalog,document_understanding}及对应测试 | G1去多层结果/诊断固定尺寸许可；G2坏自动候选跳过，显式pin与未知费用仍严格；G4单次已验buffer不重复SHA/metadata；G5几何导航使用共享实际预算不静默64天花板；G3先用同unit正反例证实再修局部失效扩散。 |
| 工具 | tools/pre_push_gate、benchmark phase_c_observer、identity_audit、narrative_g2_replay、source_root_portability、storage_footprint、raw_duplicate_audit、cross_market_suite、holdout_replay及相应测试；必要bounded_process | T01日志/收据大小不能改真实退出结果，保留进程超时与实际payload资源限制；T02删除全树clean许可，用加载代码身份记录，冻结样本/期待不冻结旧引擎。 |
| RF | revenue-forecast scripts及对应测试，保留四份assurance WIP | RF01/02去重复wire/anchor大小门；RF03可选review/recipe诊断不阻断已验来源；RF04当前结果自含验证与版本写入，不依赖全局索引/历史链/反复chmod；RF05合并同事务重复验证。RF04消费者需协调验证，不单方面宣称全链完成。FF当前v2无人工许可，不为凑数改正常路径。 |

各线不得互改源码文件、主PWF、CI/hooks，ROOT负责集成，不碰Dayu/IQS/Dashboard、生产配置、原件和他人WIP。不加外包卡。详细静态证据见R7-core-gate-audit、R7-tooling-gate-audit、R7-crossrepo-gate-audit三份md/json。静态风险不冒称已运行复现。

## 验收与发布（只在大节点集中审查）

1. 定点TDD：超原阈值的合法结果/日志仍成功且证据完整；坏缓存→好候选/当前源；独立已证分句不被未知分句连坐；无关WIP不挡holdout。反控原件变化、引用错位、非finite核心数值、真正预算耗尽、输出写失败、显式pin损坏、未知付费恢复均不能被放行。
2. 各线一次受影响集成；ROOT对交接版本做独立大节点审查并直接修小问题。不重复全仓本地检查、不每个小点签收。
3. 正常commit/push，现有CI在重大版本运行；保留失败历史和实际耗时。RF registry的下游兼容未证就保留OPEN，不以局部绿代签。
4. 先单份真实H1只读复验（原90s/16M/112），12业务成员/9语义context及当前主体、原文/DB/runtime前后证据齐全；再真实配置摘要、缓存中断/同跨run零重复、同artifact实际RF参数/公式/报告/snapshot采用。不重跑超时整批，不用提高额度代替修复。

## 当前未完成

R7编码与验收正在实施；观察器R2独审发现物理proof与语义context混合，需ROOT同修。H1 v3未保存不推断PASS/FAIL；全公司循环和旧P3研究共因仍OPEN。本节点不新增收费调用或下载。

## 下游兼容根因补充（ROOT负责）

invest-skills canonical main 0ee1713初始干净。独占invest-core adapter及相关三测试/说明，取消global registry/host_signed默认许可，仍运行RF完整重算且不把未签结果伪造为signed。实际新4例3F1P/1.70s确认，实施后等待RF源冻结做联调。

另确认该仓pre-commit和pre-push重复全十组件测试+Biren E2E，push还自动整套同步三技能目录，属于用户要求精简的同根历史副本。ROOT将日常commit收敛为已staged Python静态检查，push固定小型adapter/跨仓篡改反控＋静态，完整测试/E2E留既有CI及显式大节点；全局部署独立定点执行，不再作为Git许可或隐式整套覆盖。原有skip flags不作为新授权，不以no-verify绕过旧链。适配器与下游三跳反控统一验收；不动IQS。

## 定点部署收尾（沿现有owner，不新建安装框架）

ROOT17源已最终独审通过，暂存字节/working-tree混淆P2、同owner重复bindingP3均闭合。实际invest快检2.716s，临时index/四WIP/80RF源完整保持。全局runtime更新必须显式定点，不再借Git整套同步：RF已有sync_installations --file；invest现有安装器缺该能力，工具作者仅在原tools/sync_installations.py及新test_targeted_install_sync.py补文件子集模式，合成temp验证仅写选中、未知config/output及junction保留、重复零写、部分失败如实。ROOT审核小实现后正常host定点部署，绝不执行旧整目录替换或改ACL。此为本次消费者修复必要发布细节，不扩外包或新产品。

## 发布暴露的同根跟进

RF正常prepush已累积41测试文件690例/84.924s，重复CI；需拆默认local固定少量反控和显式CI原完整集，避免每卡永续追加到日常阻断。原唯一失败v2独立索引仍期待v1链顺序，按真实新语义更新并增旧v1/行hash控制；不通过删CI或跳过hook放行。此补充由原RF作者实施、另一作者增量独审，仍同一发布大节点，无新施工包。
