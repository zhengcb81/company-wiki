# 当前项目状态 — 2026-11-01

**本轮P0–P2有界工程已收口：CI根修、新版真实源卡/排名、缓存恢复和RF实际采用均已独审、并主线推送，精确CI绿色。主线已进入P3药明康德W12新attempt；整个公司研究循环仍未完成。** 唯一入口为本页及[机器状态](CURRENT_STATUS.json)，接手看[HANDOFF](HANDOFF.md)，实施看[task_plan](task_plan.md)，最终完成条件看[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

| 节点 | 已完成 | 明确边界 |
|---|---|---|
| P0旧3例CI | 延期frontier/真实lookahead及消费者合同根修，精确CI绿 | 保留原失败，生产预算不变 |
| P1新版两来源 | 华利15完整卡/12业务原子，Berkshire73卡/10业务原子；各1真实配置模型POST，activation/同跨run0重复，独审PASS | /5是完整原文摘录＋advisory排名；Berkshire15条未处理、全文partial，曝光样本不是盲测 |
| P2新版华利v6 | 新a466 artifact完整t3/出处/理由进入实际参数、公式、报告、snapshot/registry，45独立检查PASS | 条件工程算例；2023IR不是2026新计划，不代签全公司买方研究 |
| P3原公司完整复验 | r1-remediation-03已冻结、CI依赖已清；真实401暴露共享配置/终态恢复问题，ROOT修复中 | 新正式summary/完整RF/四路复审及质量收尾尚未签收 |

## 此次修好的共因

- 旧CI3例的固定预算已在lookahead前耗尽，完整延期由frontier0表达；测试须验证真实语义和消费者，不能固定要求显式IDs。[P0](review/mainline-closeout-20261031/p0/README.md)。
- 原模型收到88任务、canonical只准72卡，晚附业务范围还被发现顺序挤掉。现在以来源优先级/支持坐标分配完整卡，原文与提示去重，仅发送正式准入卡；未发项仍unprocessed。实际Berkshire39520B/预留47840在原50000内。[P1真实运行、恢复](review/mainline-closeout-20261031/p1-current/README.md)。
- compiler/execution混淆物理可读与事实支持用途已统一source owner；context_only/unresolved正例及伪造事实负例验证，旧运行签名不改。后续类型/等价反射delta均独审并免费重放，两份实际HTTP/draft/execution相同。
- RF完整摘要原只留旁收据，现通过纯证据DTO持久完整支持/context和采用理由；修好非零单价显示、操作数锚与CI夹具归属。计算层不读物理目录。[P2根修](review/mainline-closeout-20261031/p2/README.md)，新版正式产物只在RF仓。
- 新CI3例是allocation旧版本pin与/5旧HTTP捕获未迁移：旧捕获不改、新wire单独精确冻结。选测原把不确定范围与已知消费者一并丢掉，现同一依赖图保留changed/最近静态consumer，最多32文件＋原smoke/180秒，其余明确交CI。快速部分覆盖不保证抓到全部远端错误。[CI与Windows夹具根修](review/mainline-closeout-20261031/p1-ci-repair/README.md)。

## 已发布与实际验收

CWP master/远端已[f98dd54b](https://github.com/zhengcb81/company-wiki/commit/f98dd54b78184ea6534941e1ae8bb40bbe6971da)，[精确CI41264855167](https://github.com/zhengcb81/company-wiki/actions/runs/41264855167)成功；正常pre-push **651P/133.64秒**。此前push实际挡住9个旧Windows嵌套TEMP夹具假设，现测量式共用夹具及extended自清理19P/13.28秒，生产60/180/32不改。原93f CI失败、642P/9F及中间结果均留证。

RF main/远端已[85054d7b](https://github.com/zhengcb81/revenue-forecast/commit/85054d7b260a3805b43ce6a4d49d44579745a015)，[精确CI41260918155](https://github.com/zhengcb81/revenue-forecast/actions/runs/41260918155)成功；v6仅更新验收材料，运行根修535604fa已定点同步三逻辑技能入口/2物理目标、重复零写、3新进程通过。后续PWF-only提交由workflow paths-ignore不另跑运行CI，不能伪造其CI。

## 当前W12与唯一下一步

继续 `revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution_replays/r1-remediation-03`。保留原2026-10-21截止日，checked/capture用真实当前日期；新summary→RF used参数/公式/报告/snapshot及完整16标签实际执行后封存，再四路独审、按共因修复/原公司复验、质量改善和检测演进。之后药明合联、Snowflake及固定八家/连续三家clean责任，不以工程通过跳过。

免费预检已通过实际RF→FF→CWP复用；11份canonical来源事实经既有CWP owner服务继承，隔离catalog元数据缺口已解决，原件/DB复制0。新浪三表已取得，今日snapshot/未知单位与PIT不冒历史asof证据；IR演示材料发现仍partial，电话会真实请求unsupported_exchange，保持具体gap，不能称无公开材料。预检及数据取得不代签正式forecast。

W21 canonicalC2真实增强/严格对齐、长文余项及新US监管/HK/US RPO按相关P3责任承接，nativefallback/股东信不代签。当前不扩施工包、不动Dayu/IQS/Dashboard、原件和生产配置。RF三份assurance WIP及CWP hook mode差异保留。外包只查[PACKAGE_STATUS](PACKAGE_STATUS.md)。

配置累计10M tokens/$20，最新已核母账1,935,796tokens/$0.756563（估计非账单），保留new_unknown8＋prior_unknown7。P3两次真实401新增保留85,927tokens/$0.017053；正确默认loader单H1新run被generation恢复指针拒绝，0新POST/预留，不退旧账。原生goal active。原件不丢；工程只留小型gzip收据/免费重放，不归档PDF或整库。本轮已清7个自有测试目录16,045,737逻辑字节及失败hook自有temp21,158,851字节；P3当前数据保留待独审，不能提前清理。此前新下载测试年报/全规范化清4,662,644B且62实际span保留。没有新增逐材料人工许可。

当前真实阻碍（非CI重新失败）：显式传同一canonical配置绕过受管.env，误用继承凭证而401；终态费用unknown又被当成执行未结束，阻止修正后新run。已假凭证TDD复现4F/7P，正在共因修复及原生恢复正反例，独审后继续W12，不重置账、不删pointer、不换DB绕行。

W12共享配置/恢复根修已集中独审PASS/0OPEN：96短unit/20.46s、4隔离integration/64.12s及8独立native状态探针；AUTO单snapshot拥有执行状态，batch薄适配，未知账不退，已有付费pin只走原恢复。已清本轮11自有测试目录18856387逻辑字节，真实P3/原件未动。现正常发布，后续精确CI与W12正式采用仍分别验收。详见review/mainline-closeout-20261031/p3-config-recovery。
