# 合法结果误拒专项：当前收口

**本节点工程完成、集中独审通过、四个有CI的仓库精确版本全绿；真实公司主线仍OPEN。** 本页只归总这一节点，完整项目状态以主CURRENT_STATUS为唯一入口。

过去确有正常生成结果被错误拒绝：真实H1来源处理后被mtime/新增合法字段/300KB观察器拦住；一次实际MiMo响应及485241B artifact已保存，观察器缺字段遮住成功，后续同artifact恢复0额外POST。它们与真实研究/错币种/缺业务问题分开，不能称全部语义正确。[历史十类逐项证据](tools-history-audit.md)保留真实、合成、真正资源停止与旧测试失败的区别。

|责任层|删除或降为观察的额外限制|修后责任|最终证据|
|---|---|---|---|
|CWP output|20/40条、每task2/6条、280字、语言观察取样长度等额外许可|完整合法内容保留；生成目标仅建议，真实token/HTTP/引用/主体/限定校验仍负责|[cwp-repair.json](cwp-repair.json)|
|CWP CLI/storage|本地输入128/256KiB、retirement64/location256、pin标签长度及content_bytes诊断标量帽|API/CLI同owner；历史查询按真实work账户分页，错误诊断不再遮住真实truncated/known usage|[cwp-independent.json](cwp-independent.json)|
|Tools|日志/事件累计大小与观察文件I/O、mtime-only比较、freeze/prior-use执行许可|native结果与可选观察分离；内容SHA+bytes；开发样本可跑但不能冒clean holdout|[tools-independent-r3.json](tools-independent-r3.json)|
|StockWiki|256KiB/16KiB/1.31MiB与groups512/views2等表示帽、可选review/trace许可和字节canonical性|实际预算可配置；完整来源/不确定性保留，不产生研究签收|[stockwiki-independent.json](stockwiki-independent.json)|
|RF/invest|公式500字符和指数10上限|迭代算术；可选累计工作账户；真实overflow/非数/未知变量仍拒|[math-independent-r2.json](math-independent-r2.json)|
|ET|16/10/2/24MiB和60s对显式预算的二次顶帽；坏非权威sidecar拦原文|同一真实预算贯穿API/CLI/worker；健康TXT legacy复用，真实SHA/身份/期次冲突仍拒|[et-independent.json](et-independent.json)|
|FF|ET body10MiB/time60和编码pipe32MiB、已知原文32MiB/receipt64KiB钳制|按请求实际quota/原件精确size分配，源SHA/实际超额/父deadline/回收不放宽|[ff-independent-r3.json](ff-independent-r3.json)|

真实预算/来源真实性与可选观察曾被混成一套拒绝条件。现在由实际数据/预算owner负责正确性；可选诊断故障不翻转native成功，也不会把缺观察冒充质量通过。没有增加新授权文件、签收或skip开关。

## 独立验收与发布

- CWP核心27文件由非作者核完整长限定、历史分页/同预算耗尽、CLI坏输入、language unknown与持久化恢复；工具11文件初审发现的观察I/O遗漏已R3增量7P闭。
- StockWiki13文件：初审2P2保留FAIL，ROOT修复后独立11P＋两条public CWP→Stock合成E2E及资源/路径反控5P。
- 两算术owner：初审指数10遗漏修复，独立R2长期DCF/复利及真正overflow/复杂数/零负幂/实际工作预算控制通过。
- ET13文件：作者93例是分阶段证据；ROOT非作者7P包含真实FF→ET公共CLI→真实supervisor/假HTTP worker，非真实下载。FF最终4文件非作者R3独立6P；另一次现有进程域53P1旧oracleF，失败单节点迁移后通过。
- 首轮CWP精确CI7F和FF首轮失败均保留。CWP追加仅修旧oracle/fixture、唯一helper及其必要调用方并独审；中途发现当前inputSHA仅比旧值不同的弱断言，也改为真实request owner重建核对，未复制hash算法。第二轮Unit已通过，但Focused又暴露漏扫contract目录的一条旧20/280断言，已补整个tests/CI focused矩阵并保原失败。FF修90秒应变60秒的退休期待，未放宽真实反控。新精确CI与所有commit在[publication](publication.json)。没有在本地反复全Unit。
- RF/invest与FF只用既有canonical定点安装器更新各自2运行文件：12逻辑目标、配置保留、两次重复零写、6独立新进程通过；ET配置直指canonical工具。StockWiki无remote，只签本地主线；ET无本commit的Actions workflow，不虚构CI。

## 保留的实际检查及理由

- **source-truth**：原文字节SHA、公司/期次/as-of和真实引用检查保护错源错期，不是人工许可。现有主体/限定反控保留；新发现SEM-QUAL-01条件覆盖缺口仍OPEN，不能说语义验证完备。公开接收端校验实收字节，不能信任进程外自报verified。
- **numeric-truth**：币种、单位、finite、公式/收入重算保留；合法长式和长期幂不再按长度或指数被拒。
- **real-resource**：用户配置/请求的累计费用token/实读字节/时间/空间及明确工作账户保留；不会再用任意序列化大小或不可提高的常量充当第二许可。
- **recovery**：lease/CAS/幂等/未知费用/单POST保护防止覆盖原文、降账和重复付费。
- **protocol**：确实冲突的协议记录、坏JSON/重复key/NaN不能被另一条好回执洗白；普通日志和可选旁注不据此被要求人审。
- **experiment-honesty**：未冻结/开发/未知prior-use可执行，但不能计为未见holdout/clean停止样本；显式要求某producer版本时仍须实测版本一致。
- **unsupported-or-unproven**：真实不支持的执行协议、真正语言/语义不确定保留unknown；原始units仍可用的几何视图内存fallback不再被当来源拒绝。

## 防止同类问题再长回来

响应schema/提示/decoder变化时，在同一大节点从生产契约owner找调用者，扫描完整tests树的unit/contract/integration/e2e旧quota断言，再与实际CI focused节点/文件对照；列出golden/byte-hash/性质测试矩阵后一次迁移退休规则，不只测直接模块或Unit。测试应证明“预算内的等价有效内容不因空白、长度、可选旁注、mtime被拒”，同时保真实错误反控。不得通过删坏引用/币种/主体/unknown-paid断言换绿，也不增加每commit全量或小节点人审。

本轮实际模型/下载/原件与生产配置写0；测试自有新增目录按各报告清理，既有历史产物和其他owner WIP不擅清。不能把技术合成验收当新版真实摘要/缓存恢复/RF实际采用。下一步回[T4](../T4-source-note-parent-plan.md)，R4六共因、固定八家/三家clean及新市场责任保持。

**新增真实语义缺口SEM-QUAL-01仍OPEN，真实摘要前必须修。** “公司计划在项目建成后…”＋“仍须客户完成验收后方可投产”被改写成“公司已…”时，legacy与当前v7仍可能draft/needs_review=false、诊断为空。它不是门禁，也不是因为测试新就可丢的夹具问题；完整span/locator和两协议实际输出保在cwp-contract-followup.json，实施细则加入原T4。保留已支持模式的反控不能代它通过。
