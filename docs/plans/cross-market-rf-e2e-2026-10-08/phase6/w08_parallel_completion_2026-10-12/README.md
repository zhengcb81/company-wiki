# W08 三个可以现在独立启动的施工包 — 2026-10-12

本批三张新卡均已由用户交付，目前DELIVERED_NOT_ROOT_ACCEPTED；不要重新开工或重复派卡。ROOT负责总接口/共享PWF/最终验收并线安装；workers不推main。

| 卡 | 做什么 | 工作目录 | 施工卡 |
|---|---|---|---|
| W08-RF-COMBOS | 补五组已确认遗漏的原生模型组合；保留原16/36 | C:/Users/郑曾波/Projects/_harness_worktrees/w08/rf-combinations | [卡](cards/W08-RF-COMBOS.md) |
| W08-AUDIT-EVIDENCE | 在已有四审覆盖工具上实读执行证据/locator与当前attempt，报告缺口 | C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence | [卡](cards/W08-AUDIT-EVIDENCE.md) |
| W08-CWP-G2-REPLAY | 做可复现的摘要→公开read→固定RF消费离线包，不修改W04 core | C:/Users/郑曾波/Projects/_harness_worktrees/w08/cwp-g2-replay | [卡](cards/W08-CWP-G2-REPLAY.md) |

## 为什么能同时跑

三工作目录不重叠、三项目不同，唯一写集见dispatch.json。CWP包新tools/narrative_g2_replay与新测试，ROOT改W04 src，源码写集不重叠；输入仍固定122bbe3b，不读ROOT新WIP。RF包只扩tool，不动scripts；Audit包只改review_protocol/新evidence helper，不动loop/四review主卡。CWP只消费固定RF8dc26710代码快照，不等待新RF组合工具，Audit也不读另外两包。

## ROOT接线顺序

1. ROOT W04已证实共因修复→集中测试→正常发布，母目标仍暂停时不因发卡自动启动。
2. 接收三个分支和handoff，独立大节点检查；RF闭五组覆盖，Audit由ROOT接入四审/安装，CWP使用已修当前核心重跑同CaseSpec。
3. ROOT真正配置的G2有限付费模型/公开read/RF消费；G4原三家公司/12独审；G5新A/H/US三家及后续循环。工具工程绿不等于研究完成。

workers只在A/B/C三大节点审查；测试与下载资料归独立测试根并恢复原样。缺hash不新增签收，未知不PASS。各包0外网provider/LLM调用，ROOT累计预算仍$20/200万tokens。

完成后给ROOT卡号、workdir/branch/HEAD和docs/handoffs/<plan_id>/handoff.json/md绝对路径；一包不需要等另一包。详各卡和[共用交接接口](HANDOFF_CONTRACT.md)。母当前状态见[ROOT入口](../w06_parallel_verification_2026-10-11/ROOT-reception-status.md)。

## 用户全部交付 — 2026-10-12

三真实HEAD和只读输入/writes见company-wiki/.planning/w08-root-reception/intake.json；ROOT将按实际覆盖与必要反例验收，元数据自引用空值不新增门禁。

## ROOT 当前验收位置

CWP已完成ROOT补验修复、35测试及50.3324秒真实联调，正常并入本地主线，发布/精确CI收尾中。实测8→0复用，新版本与生成spec各1次；原request/receipt/bundle/context已归档203690字节。详company-wiki/.planning/w08-root-reception/cwp/README.md及acceptance.json。RF/Audit仍待ROOT接收；不要重派三张卡。RF优先补dated贡献及独立actual原生回测两个明确缺口，不把工具自报五组CLOSED当签收。


## 当前发布结果

CWP已验收发布：代码主线/远端d75e9698a3401854dfd4368bbe9b7c40f73c3263，正常push3648PASS197.96秒，精确CI38304041971 success。35工具测试/50.3324秒真实九文档联调，复用0POST，版本/spec各1POST、70输入SHA/mtime不变，预存哨兵及独立测试目录恢复。证据203690字节ZIP，136自有重复文件187288字节已逐字节验证归档后移除。W04原件/legacy/四事实节点和CWP工具工程接收完成；真实供应商摘要、RF/Audit两包、G4/G5真实研究与循环仍待做，完整母目标未完成；本轮0付费。
