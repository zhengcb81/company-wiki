# DU11 10月18日交付快照（已由当前状态页取代）

本快照在2026-10-21按已提交证据纠正过期交付字段。**当前入口：[CURRENT_STATUS.md](../CURRENT_STATUS.md)。** 本文保留10月18日节点的最终结果，不声明当前HEAD仍是当时版本；原始运行/审查收据不改写。

## 当日最终交付

- B2来源闭合终审PASS，代码链`d55d3369`→`6a2ee853`→`2a80acf6`；终审当次109项，补充工程回归后110项。真实CN/HK/US选择10/10、7/7、8/8，原件/gold不变、0API。
- RF/FF DU11和P1–P4已由ROOT接收、合入master并发布。此前“领先7提交/四包待接收/默认关闭仅本地”的中途状态已被后续提交取代。
- 当日收尾发布`ef3f3d1c`，CI [39164683463](https://github.com/zhengcb81/company-wiki/actions/runs/39164683463)记录success。最新代码与CI见当前状态页，不以本快照代签新代码。
- 普通C链路三家已有真实请求、激活恢复、同/跨run缓存和FF复用/RF读取通过记录。核心摘要[MD](../receipts/c-live-receipts-20261018.md)/[JSON](../receipts/c-live-receipts-20261018.json)已提交；完整运行树仍是本机材料，fresh clone无法仅凭摘要重放全过程。

## 内容及实验边界

- CN：8/10、critical5/7，用户接受受限收尾，不继续为最后两条事实重复付费试验。
- HK：允许正确约数的口径下7/7、critical6/6 PASS；[逐gold独立审查](c-content-review-hk-20261018.md)已提交。401是更早一次失败，不代表最终HK未运行。
- US：所绑定原审查2/8、另1条partial；后续2–4/8属于不同实验，事实遗漏仍保留，不称完整内容通过。
- 实验性两次attempt补写默认关闭的改动已发布；`activation-resume`仍有`ReservationConflictError`。普通单次恢复PASS不代签这条实验分支。

## 预算与证据

10月18日按database+attempt_id去重快照为56attempt、1,091,219tokens / $0.278311估算，包含69,046tokens / $0.031208 unknown hold；上限累计2M/$20。本轮没有重计账或收费调用。

当日B2、C审查及收据摘要已提交；完整live树未提交，清理后本机保留5个live目录（CN三轮、HK、US）。历史RF assurance/output保留；旧RF临时目录的拒删记录不等于已清理。

## 尚未完成

新公司holdout/RF审查循环未启动；实验补写恢复、完整证据可移植性及工程债仍列在CURRENT_STATUS。当前代码实施暂停；不按旧快照重新派工、重复修B2或重复推送已发布提交。
