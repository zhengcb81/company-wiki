# 推送范围集中独立验收

ROOT源已停写，排他新review输出只能 `ci-docx-investigation/evidence/push-scope-independent-review/`（报告JSON/MD、少量独立probe），不改ROOT源码、既有tests、PWF共享、配置、sealed公司执行包。

实际工程base d3d807691efa68a30ae50fffb9980db4942eccae，源码 `tools/changed_unit_tests.py` 与 `tests/unit/test_ci_push_selection.py`。调查计划 PUSH_SCOPE_CONTINUATION.md，真实原RED5FAIL/43PASS、集中GREEN48PASS/1.35s、Ruff0、actual-range-green.json 与 old-tests-preserved.json，全原20 test函数AST一致（baseline40 items）。产品src/config没有diff。d3精确CI38106925215success只是DOCX修复，不代签这个selector新改动。

短读源/现hooks接线，一次独立定点：①真实ee293769→d3d80769区间只选DOCX测试，不被归档probe/conftest诱全量；②unknown range、删unknownruntime/globalconfig/sharedfixture仍全Unit；③真实runtime变动仍保守computed/CLI消费者；④test-only已知helper传递要保留，而未变无关CLI不全seed。不要再跑48/39/3198及公共财报E2E，已充分的断言只检查保留；最多4-6微型selector probe，可亲用源码构造不同反例证明责任。报告真实命令/exit/sourceSHA、证据scope与material findings；不要把selector优化称fullCI保证、不要要求小节点额外许可。若有合理重大漏洞指出实际反例；无material后STOP，ROOT正常commit/ff/push（gate自身变动此次合法fullUnit一遍），精确新HEAD CI仍待。

0外部GET/provider/model/费用，原件/config/Dayu/他repoWIP零改。适用AGENTS范围：结构CodeGraph优先，索引已对这些tools陈旧缺失，可说明后读取已定位文件，勿重复init或grep reverify图。PWF根因和初审结果无需复制公司材料。
