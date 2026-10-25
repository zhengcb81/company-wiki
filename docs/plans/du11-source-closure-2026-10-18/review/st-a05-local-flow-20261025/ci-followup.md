# 06c CI跟进（2026-10-25）

精确CI40190090649六项失败已在本地同四文件复现：6失败、122通过，13.44秒；测试临时目录恢复为空。原工程独审/17SHA/真实attempt05作为06c历史证据冻结，当前子节点重新OPEN，不改写为已全绿。

## 共因与施工边界

1. 预算先付修复将原生读取纳入同一document_work账户。旧3例仍要求零共享工作量读80页，违反新明确资源语义。必须保留零账户0原生读取/0tablefinder和立即停止，补公共API与生产错误分类断言，独审确认后更新旧语义；不恢复免费扫描、不新增第二预算。
2. context_policy直接加入生成资产而未纳入既有reading_defaults→compiler单源链是实现遗漏。将相同策略归现有defaults并显式编译输出，--check不得忽略字段；新增中性mutation测试验证维护/运行一致。
3. 旧layout engine stub遗漏既有groups契约。以独立审查判断补完整stub还是需要兼容边界，不增加新layout契约。
4. 旧固定3block断言包含generic导航。改为精确父业务/期间/目标正文与物理proof断言并验证导航和兄弟业务不进入模型，而非仅放松数值。

ROOT仅修改CWP原owner及测试，不写W16/W17/W18工区。最终集中检查后独立复核、正常提交推送及精确CI确认。0付费调用/下载/原件副本。

## 最终验收（发布前）

最终218项通过/16.45秒、compiler --check和Ruff通过，独立增量终审PASS（7个变更文件SHA；旧17文件/9证据不变）。前三项停止预算断言保持零原生读取；新handler真实SHA夹具已证明预算原因，不被普通完整性错误误代。两次初版217PASS1FAIL因测试原件hash错，另两项defaults/compiler真RED及纠正后handler真RED均保留。布局stub遵守真实契约，产品未增加宽容fallback。导航测试验精确parent/period/target及source proof，不只放松数字。0新付费/下载/原件副本。

## 为什么本地没有挡住

pre-commit运行lint/type/host guard；此前宽影响push按既定快速策略跑154项契约，不承诺全单测，CI才跑完整单测。本轮大节点集中339项漏了legacy production budget、旧layout stub、策略生成工具及旧dependency消费者几套测试，是ROOT验收覆盖遗漏。后续共享阅读大节点要把这四个既有责任层消费者与新增测试一起集中跑（本轮8文件218项），不把每次commit重新变成上万项全量，也不另加人工许可或永续增长的smoke清单。
