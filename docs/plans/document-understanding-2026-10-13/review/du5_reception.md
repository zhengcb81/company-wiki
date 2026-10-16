# DU5 ROOT 接收 — 2026-10-16

状态：ALL_THREE_ACCEPTED。当前发布状态见末节；以下保留接收时发现与测试。三作者树均干净并保持只读；分支已正常merge --no-commit到各仓主线，保留history。CWP master 6336c854、RF main090a6310、audit maine5189a06为接收前HEAD；RF原alert三文件WIP按SHA保留不暂存。CWP/RF fetch成功，audit无origin，不能声称已远端同步。

## 已实测

- CORPUS作者head3558fd50：236PASS/9SKIP（10.26s）；真实原件测试本次未跑。
- AUDIT作者head583a13d9：全仓456unittest通过（97.254s）。
- RF作者headec636065：六组152PASS/10SKIP/59subtests（12.67s）。
- ROOT统一隔离runner保护配置、两个默认registry路径、sentinel/Temp及作者status，0供应商。上述原测试绿不能代替独立边界验收。

## 集中根因修复

1. CORPUS：anchor校验需真正验证原件SHA及line/page，单fact不可读例外不得免掉整sample；新金标的合法四舍五入被must_not_assert错误拦截，需独立版本更正记录，保留旧值与原分母。ROOT负责。
2. RF：share family仍须核shock_type真正数值单位，不能以record自洽替代ratio/basis_point一致；count单位与真实参数尺度需有事实正负控。独审先实跑，再在唯一helper修，不复制新表。ROOT分工给RF审查agent修复，主审最后交叉核对。
3. AUDIT：审查对象/目标冻结谱系共同核对；冲突报告无损聚合、版本键不能覆分母、引用与语义差异分列；实读预算耗尽/未读不得covered；共享片段避免每claim复制全文。独审先实跑，ROOT分工给audit审查agent修复，主审最后交叉核对。

仅在本接收大节点集中回归、真实CLI、静态与独立审查，不增加许可链/人工签收。旧20条8PASS/6WARN/6FAIL和PD5/Matrix遗漏保留，新语料12/37等漏读是生产待修，不洗绿。三包不关闭默认0.8、三组件生产接线、v4/旧付费恢复/真实质量及母公司审计循环。

## 证据和下一步

ROOT工作记录 `.planning/shared-reading-production/du5-reception/` 含精确intake、原测试、独立probe及首个失败；本节点结束压缩为紧凑验收证据并链接。完成共同根因修复→一次合并后集中回归/E2E→正常提交/推送/精确CI→PWF收尾。audit远端与安装副本只按真实配置处理，不能假报同步。


## CORPUS ROOT验收通过，待发布

原236PASS/9SKIP；ROOT首轮新测试含2个参数顺序错误，修正后真正6RED/1PASS，随后共同修复。最终252PASS/0SKIP/56.54s含真实原件，六处新测试E702格式修正后定点7PASS/0.35s，Ruff全工具包PASS。行/范围不退全文、复用resolve_original核SHA、单fact例外不免其他fact；旧location更正只在临时视图应用，一次提取检查全部，不重复解析。舍入更正显式v3保留v2字节身份与旧值、原锚点/重要性/100事实/193锚点/37关键分母；旧native12/37不重测、不洗绿。原始收据三处尾空格通过统一receipts字节角色保留，不裁剪失败。详[验收](../common-root-quality-evidence/du5-corpus-acceptance.json)。


## 正式收尾 — 2026-10-16

DU5三包已验收并线。CWP merge b083a1b1及配置补丁5dae70a0正常推送，精确CI 38834945691 SUCCESS；最终5954PASS/24SKIP、真实benchmark252PASS、Git12种往返PASS。RF main794240df/收尾5122107b已推且CI38833831553/38834985290成功，210集中及23CLI通过，三路径/两物理副本定点同步。AUDIT main58b2797/收尾a3f36d1本地并线、48集中/静态与真实CLI通过，两份技能同步；无origin/对应远端not found，未远端发布。

CWP首次正常推送5947PASS/24SKIP/1FAIL，原因是.gitattributes自身CRLF未规范，在autocrlf=false下被判尾空白。新增LF/CRLF×三种autocrlf×保留/移除夹具规则，先1RED/11PASS，再明确配置自身LF后12PASS，不放宽夹具断言。后续5954/24通过，但ROOT在commit hooks未结束就启动push，收据捕获旧HEAD并显示旧merge，不能作为5dae发布证明；随后单独正常核对真实HEAD和远端尖端均为5dae，并为发布helper加工作区/暂存区干净、期间HEAD不变、远端尖端一致的自动检查。该操作排序错误与所有失败收据保留，不根据commit时间猜hook何时完成，不把工作区绿套到另一commit。

ROOT新测试的参数顺序与E702、提交准备的raw log尾空格/历史Markdown EOF、一次未执行的patch格式错误、gh缺失、audit无origin、只读进程范围诊断regex错误（无写入）均记录；分别修工具用法/测试格式/诊断材料字节角色，未裁剪原始失败或绕过检查。

工程效率债：独立benchmark目录仍触发工具目录整库单位fallback；最后一次Git输出Everything up-to-date，但empty push input被当unknown仍全跑5954项/395.80s。对相同b083→5dae范围只读计算则会选1个unit文件。因此应在现共享runner区分Git已确认无ref更新、真正未知范围、工具所属测试与生产依赖，不新建检查框架。本轮不再扩CI实现，此效率债纳入主线简化维护，不加人工门。

[发布收据](../common-root-quality-evidence/du5-reception-publication.json)。原件/配置/作者树保持、Temp恢复，0供应商；生产源作用域/正式摘要及真实召回仍继续主线施工。
