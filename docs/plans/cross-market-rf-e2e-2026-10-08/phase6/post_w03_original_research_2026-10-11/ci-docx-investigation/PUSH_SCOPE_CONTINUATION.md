# 推送测试范围的责任边界修复

## 已证根因

d3d80769普通push实际3198PASS/191.38s（whole198.676s），源产品7文件和生产2config保持、26原evidence checkout相等。只有一个live unit测试变动，但docs/plans下归档probe.py进入relevant，而graph仅扫描src/scripts/tools/tests，导致“deleted or unknown dependency”全量fallback。现CI已按docs/plans/**归档职责排除调度，本地selector应一致。

## 排他write set

ROOT只 tools/changed_unit_tests.py 与 tests/unit/test_ci_push_selection.py。本轮fixture-only39GREEN及4独立probe已接受；新source精确CI38106925215正在运行，不重跑产品public E2E。三公司审查source运行版本保持，不向其分享公司初稿。无原文/配置/Dayu写入，无provider/model费用。

## TDD与实现

1. 先写归档不同suffix和conftest、不存在archive probe、live test+archive混合、单位测试纯改与不相关computed consumer、已知test-helper传递消费者的反例；保存真实RED。
2. 以docs/plans/目录职责先排archive，再判断全局配置/未知代码；不按此probe文件名特判、不增临时whitelist。可信push range不变、None/删除/未知src/config/fixtures/dynamic runtime仍全量fallback。
3. 区分live test-only改动与runtime行为修改：live test文件本身和已知传递消费者照跑；未变的computed/CLI消费者只在runtime/support变化时保守纳入。不能让每次新增一个test都触发所有runtime CLI消费者。
4. 集中该selector全既有+新责任GREEN，实际d3 push-range只读诊断应选live DOCX测试，不因归档全量；真实source+archive对照仍保留computed消费者；静态Ruff。只一次独立定点，正常commit/master ff/push以及精确新HEAD CI（gate代码本身修改，这次既有规则正常全Unit跑一次，不bypass）。

## 验收

原source/global/unknown/dynamic fallback断言不减，runtime流程仍全CI。小节点不再新增审查链；此为根因测试范围边界的集中验证，未来docs evidence应只现有contract smoke，test-only变更按受影响Unit。原远端failure/历史normalpush日志保留；不得借快selector掩盖测试失败。
