# 用途范围配置加载 — 2026-10-15

## 根因与目标

真实旧源码恢复演练中，narrative-only CLI 的 Config.load 强制要求未使用的 Tavily key 和 legacy wiki_root。pytest 环境默认宽松，旧测试为 fixture 补搜索 key/路径，因此没发现真实入口阻断。应由统一配置层按实际组件范围加载和验证；不能向夹具永久补无关凭证、设置 PYTEST_CURRENT_TEST 或绕过校验。

## 实施边界

ROOT 独占 scripts/config.py、scripts/narrative_batch_configured.py、新 tests/unit/test_narrative_config_scope.py。不修改 DU4 新组件/测试/PWF，不改变生产 config.yaml、模型名/endpoint/generation_policy/真实密钥，不改 AUTO/预算/来源校验或已有各版本模型协议。

统一 Config.load 增加明确 finite validation_scope=all|llm（默认 all 保持既有调用）。llm 范围使用同一 YAML/环境/项目dotenv/供应商配置选择；构建时不消费无关 search/schedule/paths/downloader 内容，验证只针对实际 LLM 必需配置，仍拒绝缺真实密钥和无效模型参数。LLM-only 验证始终严格，不依赖 pytest 环境变量。公共全配置入口保留原校验语义。已有 fallback 切换继续使用同一 loader 解析，不能建立第二套模型默认值/credentials 表。

## A：TDD

先写真实 subprocess 场景，在无 PYTEST_CURRENT_TEST、无 Tavily key、无 legacy wiki 目录的隔离配置下，真实 configured CLI 应进入 batch 的参数处理（测试用 --help 已有单独免配置路径，不能拿 help 假通过）。使用当前全流程原生 official-import/选择/loopback/model/公开回开 E2E另做一次大节点，确认真实子进程没有测试宽松环境或伪 search 配置。

纯边界覆盖：llm-only 无关缺配/坏section不阻断；所选供应商/env优先与配置generation policy保持；model/key/temperature/token真实错误拒绝；scope拼写错误拒绝；all仍需要 search/wiki并保持旧测试。测试自己拥有 tmp_path/配置/sentinel，禁止外网和读取真实key。

## B：实现与集中验证

共用 builder/validator 只留一份LLM参数来源。configured narrative CLI 显式声明 llm 范围。新反例+已有config/model/purpose测试集中一次；Ruff/mypy按现责任范围；不把一次单元绿当真实CLI完成。

## C：真实隔离E2E及发布

复用实际生产E2E，明确清理子进程PYTEST_CURRENT_TEST/TAVILY/WIKI_ROOT依赖，fake LLM key仅为本机server；完整摘要/公开来源重放、费用和same-run复用保持。输入原件/生产配置不变、临时目录恢复。正常commit/push并核精确CI，不增加每个小步骤审批。

当前状态：计划已写，尚未写测试/实现。上一引用归属发布大节点完成前不改生产源码，避免推送测试期间漂移。

## 2026-10-15 当前结果

实施完成：真实CLI RED1FAIL/1control PASS；初步19新例+旧例68PASS；独审发现未选fallback仍被消费/第三provider进入full builder，RED3FAIL/2PASS后在同一provider默认表先选profile再构建。最终25新例+49旧例74PASS，真实configured CLI无pytest/Tavily/旧路径摘要及恢复1PASS，官方QA另PASS。旧all行为保持，源码/配置/原件边界均保持。详见[不可变验收](../common-root-quality-evidence/scoped-config-recovery-acceptance.json)。正常提交/重推/精确CI仍待收尾，母目标未完成。
