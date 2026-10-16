## ROOT接收更新 — 2026-10-16

ROOT接收组件验收通过，待正常提交/并线/远端；不是生产摘要接线完成。独审6类RED：partial碎片假整体数值、无观察的首格标签导致丢值、耗尽后O(rows*cells)扫描、坏格丢弃仍complete、fine页矛盾、header跨scope。隔离修复后43短测通过；逐row索引一次、排序/复制预付，耗尽尾部扫描由12万/49万/194万line变72/72/72。真实名创年报p12单parse、2表28格16值（12bound/4ambiguous），所有引用核对；2M预算用1,162,753、原件/配置SHAmtime不变，0供应商。集中557PASS/24SKIP/2FAIL均为ROOT稀疏树漏检出旧DU2资产，补既有夹具后原两项2PASS/4.03s，原失败保留，不改旧断言。六个本次作者新测试的错误首格/耗尽假设已保存原zip并纠正，旧binder/layout金标没改。全局e2e runner移入本PWF/e2e避免未来外包冲突。深页223/224因上游64页capture未覆盖，未知merged/空格/行标签及正式selection/summary/RF仍OPEN，由ROOT来源层后续解决。

**Next Step：** 正常提交并主线、可用远端发布和相关技能文件定点同步，由ROOT归总母PWF。

---

# DU7-PDF-TABLE

状态：READY；工区 `C:/Users/郑曾波/Projects/company-wiki-du7-pdf-tables`。源码基线 `04c7f1bc93386a5703693f9303c3a59bb7546025`，分支 `codex/du7-pdf-tables-20261016`。
PLAN_ID：`du7-pdf-tables-2026-10-16`；PWF_PLAN_ROOT：`docs/plans`。

先读本目录 [施工卡](construction_card.md)、[接口](INTERFACES.md)、findings/progress，再开始A。
本卡现在即可独立启动，不等DU6或ROOT下一轮源码。只改施工卡白名单，ROOT负责合流。

## A：调查、冻结接口、行为RED

Status: done

按卡真实代码与期望，保留旧正确行为，区分合成/真实/未运行。见 findings.md A-1..A-5 与 receipts/red-1、red-2。

## B：所属层共因实现和集中测试

Status: done

先测试后实现，不增加预算/权限/身份库；不改旧断言、跨仓或兄弟范围。见 findings.md B-1 与 receipts/。

## C：实际入口E2E、清理和交接

Status: done

只读原件，独立Temp/sentinel，成功/失败均恢复；正常commit后提交handoff.md/json和收据，冻结源码并STOP。见 findings.md C-1/C-2 与 receipts/e2e-*、cleanup-c.json。

## Next Step

已交付 handoff（handoff.md / handoff.json），owned 源码冻结，STOP 等 ROOT 接收；不执行 ROOT 接线与跨白名单扩张。
