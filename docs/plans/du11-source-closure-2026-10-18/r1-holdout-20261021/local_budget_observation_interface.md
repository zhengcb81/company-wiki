# R1 来源准备诊断共因修复（2026-10-22）

W06真实H1 reuse_only遇到`budget_exceeded`，已保留原请求/响应；后续合法fetch取得H1不覆盖旧失败。旧响应缺计量，不能追认究竟64候选、128MiB本地读或其它阶段耗尽。新问题作为原W01/W02的followup，不撤销其已测工程结果，不扩大配额、不重复扫真实湖来猜。

## 分工和接口

- ROOT：隔离`company-wiki-r1-local-observation`，`codex/r1-local-observation`；只改预算观察/本地prepare结果保留及其测试，不与主线W07工具或执行包重叠。
- FF：隔离`filing-fetch-r1-local-observation`，同名分支；仅自己的本地prepare错误传播、bounded观察和测试。
- RF：ROOT负责消费侧兼容，正式接线前按已发布FF契约写TDD；不跨仓import内部代码。
- W06 executor只写独立研究attempt。资料writer已于2026-10-22T19:47:10Z退出；已登记与实际下载分别计数，不以40新登记推断40下载。

CWP保持`local-source-prepare/1`原8个顶层字段。已有`operations/diagnostics`跨递归/失败保留；不把完成的操作在顶层except清空。预算owner产一条无物理路径的operation：`operation=local_read_budget`、`schema_version=local-read-budget/1`、本地读scope、phase、limits、consumed、triggered_bound和真实reason。计量区分成功计入的read bytes与实际charge入口观察的read bytes（可能包含被拒的尾块），不冒充网络字节或供应商费用。触发项在预算owner知晓时记录；共享底层只回通用reason而无法确定时保留null/unknown，不靠剩余额度反推。未知历史失败不补造计量。

FF保留可验证的原有operations/diagnostics，增加可选`local_preparation_observation`（`filing-local-preparation-observation/1`），包括实际local_read_limits/status/reason/blocks_download、pathless bounded机器数据与`local_io_usage:null`。不复制正文、任意stderr/路径；不把provider未启动的provider用量0当成本地I/O=0。CWP owner budget operation完整保留，不在FF重算或摘抄猜读量。原cause六字段、业务结果/transport区别、实际exit、retry_scope、来源/许可/限额不改。

RF只为留证透传optional observation，验证外层版本/type/大小/pathless、复制原值；不重新解释预算、身份、日期或引入下一层许可。坏观察不能将坏上游升级成完整合法结果；安全cause继续可用。三层在ROOT集成后做一次真实离线子进程链反控，再按正常hooks提交、consumer先安装发布。

## TDD与验收

1. 真实小型本地夹具/子进程先RED：候选、读取字节、metadata预拒、deadline/取消、group/entry限额具有实际计量；预算失败前已有操作/诊断不消失。
2. GREEN保持既有资格/注册和限额决策，未增加下载/重试/收费；同名错误原样传播，caps不提高，输出有界且无存储路径/正文。
3. FF非零producer、合法业务失败、畸形/超深/超大/物理路径的negative；RF安全cause与完整合法sibling各自保留，malformed不假通过。
4. 各线相关套件、正常类型/ruff与独占短TEMP恢复；大节点做非作者复核及CWP→FF→RF离线联调。不上升为逐材料或小步骤人工签收。

W07真实摘要无需为这份诊断修复重新下载资料；新问题不能用删掉旧失败或提高预算替代解决。

## W06原文口径补充

冻结专家W06卡的`11370/25095.8469百万`须按原文解释为TIDES与**non-TIDES余项**；2025Chemistry合计36,465.84688297 CNYmillion，不是25,095.8469。原冻结卡/SHA不改，research事实索引引用年报PDF13/183的实读记录；TIDES属于Chemistry，不能再加一次到公司收入。
