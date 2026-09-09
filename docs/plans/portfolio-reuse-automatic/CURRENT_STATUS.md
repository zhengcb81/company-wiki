# Portfolio 复用自动化 — 当前解释

> 2026-09-06状态补充：历史Strategy B局部成果保留，但新审计发现请求policy传递/eligible副本选择/全部root消费仍有反例；117 accepted不证明原完整目标解决。后续统一走[WP02/03/04/13](../painpoint-outcome-audit-2026-09-05/remediation-plan.md)。Strategy A仍取消，不通过复制/提升/默认下载修复复用。

核对日期：2026-09-04。覆盖本目录三件套；均已全文阅读，原始记录保留。

- Strategy B（配置驱动只读复用）窄范围历史完成；Strategy A自动提升已取消并回滚。findings中的推荐A、task_plan正文的默认auto_promote开关/失败转下载/Phase 0–6不是活动要求，禁止据其开工。
- 普通rescan的re-enrich和30秒读busy_timeout已在8/6日志收尾，旧候选“删location再扫”不再适用，不应删除生产行。
- 历史真实2020.HK验证、406/75测试和worker运行记录不是本次重新验收结果。任意future root/Dropbox等泛化后来由统一DAG接管，不仍停在旧FCAP r2 pending。
- 当前权威路由见 [PLANNING_STATUS](../../../PLANNING_STATUS.md)；后续GP生产验收余项与旧账本117 accepted分开。worker暂停边界不因本目录历史命令改变。
