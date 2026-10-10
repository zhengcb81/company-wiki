# P7 独立施工包准备

## 集成进度（2026-10-10T22:53:13.182893+00:00）

P7-CWP source已接收并正常合隔离MAIN，公开canonical CLI/AUTO/read/reuse全部通过；仅新增3shape负控已通过，最终mixed/empty/history9场景PASS。P7-RF/AUDIT继续外部施工，不互等、不碰各自源码。当前下一步正常发布CWP主线及精确CI；实际source/hash/旧字节证据见[MAIN验收](../main_auto_official_json/ACCEPTANCE.md)。本轮0外部供应商/费用、原件和配置不变。

## 当前交付状态（2026-10-10T22:49:12.575090+00:00）

- P7-CWP-PROJECTION：独立接收 **PASS / NO_BLOCKER**。source commit `1c11ef0b5a838655559e91fab9a7bf38f1533d89`，交付 HEAD `4f2c05c92f3aed9cdf91808a60e1c5d38adce6ee`；166 责任测试、两布局真实离线导入/存储/回放，以及旧 Git blob 字节比对均通过。已正常合入 MAIN 隔离集成树 `3f2ed5cb1b95492717652cba64eae35c9686a1a0`，尚未发布远端主线。
- MAIN public `official project` 透传显式 `projection_version=1.0.2`；缺省及显式1.0.1保留旧语义。新公开 canonical CLI→AUTO→read/reopen/reuse 3 场景已通过；不存在的新版本拒绝。非字符串参数裸 TypeError 已真实 RED，正在归档类型拒绝修复。
- P7-RF / P7-AUDIT：用户已发给外部 harness，MAIN未接到本轮完成通知，不写其专属源码、不代签完成。
- MAIN混合官方JSON/TXT AUTO全链5场景及完整空记录零调用1场景已通过；最终兼容恢复责任组及正常提交/推送/精确CI仍进行。工程结论不代替原三家研究、四路审查及新三家泛化。

验收：[P7-CWP只读接收](../main_auto_official_json/evidence/p7-cwp-reception/readonly-reception.md)。本轮零外部供应商调用/费用，原件/配置/Dayu与邻仓owner WIP保留。仅大节点审查，无新增人工签收。

## Goal

划出真实待修共因的三个独立较大责任包，配齐工作树/独立PWF/排他源码写集/测试和交接。MAIN保留AUTO共同接线、并线与定点安装。

## 大节点

1. 最新PWF/源码/真实待修根因调查：complete，三独立只读调查，旧已完成M3不重派。
2. 精确接口/写集和三个独立目录/本卡PWF：complete，仅启动文档正常commit，source实现未开始。
3. 集中包审查与交付完备性：complete，独立跨卡复核及54项启动/格式/隔离校验PASS。中央文档正常发布的实际回执另见publication.json/exact-ci.json，不用计划代替真实结果。

## 可启动卡（只有这三个）

见README.md：P7-CWP-PROJECTION / P7-RF / P7-AUDIT。三个实际目录、branch/sourcebase/最新bootstrap HEAD见lanes.json。用户可现在并行交给harness；本卡文档已备齐，不等MAIN或另一卡的新接口。

## Errors

- 新RF checkout体积预检发现跟踪870,118,781bytes；改复用已有本任务干净树，避免额外复制，旧分支保留。
- 实际PWF解析在Windows PowerShell5.1因缺IsPathFullyQualified返回空（exit0并非成功）；改用本机已有PowerShell7，三卡均实解析到各自PWF。未修改安装技能。

## Next Step

将三张唯一施工卡/工作目录交用户，由MAIN继续自己的AUTO责任TDD。中央文档发布以publication.json/exact-ci.json实际观察为准。默认0外部provider/model/新增费用。工程未实施，不核销真实研究。
