# Progress — P7-CWP-PROJECTION

2026-10-10T21:08:43.915864+00:00 MAIN仅初始化独立工作目录、PWF和施工卡同SHA副本；未实施源码、未运行责任RED/GREEN/E2E，未调用项目外部provider/model，新增费用0。

启动pin见IMPLEMENTATION_CARD.md。下一步由独立harness执行M1；交接写本PWF内HANDOFF.md/handoff.json，绝对路径回报给用户和MAIN。不要改中央汇总。

启动准备实查：Windows PowerShell 5.1 的解析器因缺 System.IO.Path.IsPathFullyQualified 返回空；已有PowerShell 7实际解析到本卡PWF。施工卡启动命令已明确使用该7运行时，未修改安装技能或项目源码。

2026-10-10 施工完成（独立harness执行）：
- M1：基线4个M3测试文件139 passed（evidence/m1_baseline_20261010）；责任RED 24 failed/2 passed 真实保存（evidence/m1_red_20261010，红因为 projection_version 参数缺失等目标行为未实现）。
- M2：official_json_projection.py 实现 1.0.2 canonical 排序（可靠页号优先+SHA tie-break）、_FrozenDict/_FrozenList 深冻结所有权、persist payload/hash/ID 校验、producer 分派与 span producer 版本；1.0.1 默认逐字节不变（golden df3f65…）。集中 GREEN：新26（后27）+ 既有139 = 165/166 passed，ruff/mypy 干净（evidence/m2_green_20261010、m3_final_20261010）。
- M3：隔离 E2E（evidence/m3_e2e_20261010）import/2→builder→persist→close/reopen→load→replay→export，双布局、多issuer、两页全覆盖、三页全排列唯一身份；TEMP 初始0/最终0 已恢复，raw每页1份、派生3份（~447KB）。独立agent复核三不变量 NO_BLOCKER（m3_final_20261010/independent_review.md），两处 minor 修复一处、记录一处。0 external provider/model/费用。

写集严格限定：仅 official_json_projection.py、两新测试、.planning/p7-cwp-projection/**；git status 无其他 owner 改动。
