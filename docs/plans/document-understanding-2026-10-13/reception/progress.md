## 2026-10-13 发布完成

旧三 DU 包、ROOT 共同修复及共享 Windows 并发替换修复已正常并 master、推送 `9e9907cd7c013ecf0a6787dd0f591ba242eb223a`；[精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/38462668903) success。只读独审和集中工程/四原件回放通过。生产模型摘要与业务召回仍未完成，详 [接收汇总](acceptance.md)。新 DU2 三卡排他目录没有改动。
首次正常 push 捕获 1 共享 IO 失败（4053 PASS / 11 SKIP），不是 DU 失败。根因由独立真实 Windows 1000 轮复现：582 次同目标 rename 拒绝；共享原语先4RED→有界4次/35ms退避，仅已知Windows码，15相关PASS，实际500轮/1000writer零失败，原目标/外来stage/自有tmp语义保持。保留测试，未绕过hook、无新增锁/许可。
首份Linux CI38460502816的7个失败是旧测试禁单个 `/`、误报合法 `du-route/1`；本机模拟7RED后改成双风格完整路径/身份透传边界，整profile180PASS，独立14正例/35泄漏突变均符合要求。另修单一unit文件识别器只认顶层且误认test_*目录：先3RED→64全选择器PASS，嵌套消费/无关CLI/配置与未知回退保留。最终正常push 4064PASS/11SKIP，350.43s；CI失败记录保留，不以重跑碰运气。
仅回收3个干净且已合主线的ROOT自建fix/reception树，释放 `77111386` 字节；作者树与DU2树保留。新留证ZIP逐字节回读验证，没有另一份原件/全量MD。

# 接收进度

## 2026-10-13 A/B 完成、C 发布收尾

- 四作者树最新提交和范围核对；保留主线 review/三仓架构成果，ROOT 接收基线 f734ef926。
- 先8 RED，独审追加4 RED；共享绑定与最终闭包修复完成。独立7正反例、公开 normalize/replay 与 unknown 行为通过。
- 两排他内部修复叶合入：profile180 PASS；benchmark143 PASS/7 real skip，53/53新增adverse mutation检测，不靠baseline PARTIAL自证。
- 最终一次集中491 PASS/18 real deselected，13.76s；绑定4原件11 PASS/0FAIL，14.72s。4原件+6配置SHA/mtime不变，预存哨兵/自有tmp恢复。
- 最终 actual request→oracle mapper5 PASS；benchmark147 PASS/7 real deselected。代码审查指出三方source_ref对齐缺口已先补反例再修。
- 最终独立审查无新并线阻断。微软baseline业务4/8 FAIL、CID未测、生产与母计划未完成如实记录。
- 本轮0provider/0模型/0新费用，DU2独占目录和其他仓库零写。当前正常merge/push/精确CI待留证；不用另一套许可门。
