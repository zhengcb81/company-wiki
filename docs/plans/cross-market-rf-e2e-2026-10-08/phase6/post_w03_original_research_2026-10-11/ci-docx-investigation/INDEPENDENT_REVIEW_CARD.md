# native结构 / 0.7.1 / CI调度 — 集中独立审查卡

## 单一职责与独立边界

ROOT隔离代码目录 `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`；canonical真实executor仍冻结1152dad7/0f7540b5，审查不写canonical源码/config/生产原件/其它agent文件。不承担研究四审。只写本卡相邻的 `evidence/independent-review/review.md`、`review.json`、自有有限probe证据与日志。新fresh上下文，不读其它reviewer初稿，不替ROOT自签。已有用户明确授权代码修复/纯本地真实反例，无外部provider/model调用。

## 必读最小证据

- 此目录 task_plan.md、red.json/log、green-unit.json/log、green-public.json/log及green-public-txt.json/log、green-ci-scheduling.json/log（以实际文件名为准，不复制全文日志）。原精确CI38101290406/job114357569625真实1FAIL，原日志SHA301bcfd856beef2c1bf469e4f940d2a6d6dd3687835b9b8cc68fa7ea25cf1002。
- 两源码 `src/company_wiki/source_catalog/narrative_business_groups.py`、`narrative_evidence.py` 的实际git diff及所属调用边界；native normalized单位实际遍历/locator输出，可读源或已打开函数。结构查询先CodeGraph；隔离未建index只读源码，不为本review全量建index。
- 新 `tests/unit/test_narrative_native_business_boundaries.py` 与既有native pipeline/selector binding/public W03/CI selection的改动。原12345断言保留且整个财表加强，业务table正控要成立。
- .github/workflows/ci.yml仅新docs/plans/**忽略，生产src/tests有变化仍全unit；已有normal pre-push分类不变。

## 审查与最少新增反例

1. 确认物理遍历是native source层责任，不能以SHA、互不相同paragraph/table计数重建物理邻接；财表不能generic context被重新加回，业务table cell允许独立选中。
2. 查docx/html/pptx表格、PPTX shape边界、native heading/paragraph及重复业务段落的风险。自行选择最多2–4个不同于现有测试的有意义组合probe，真实normalize/selector，一次运行并记录正负控与实际输入SHA，勿重复112unit/4public大包；如果发现实质漏洞可补必要最小probe。
3. frozen0.6/0.7与保存history仍原行为/旧binding/generation；0.7.1语义新身份不偷用0.7 artifact、TXT指纹/原locator不改。检查已有集中green责任证据，不能把union 3PASS+1定点重验写成重跑4PASS。
4. docs/plans无runtime依赖，CI ignore计划正确且不扩大src/test/配置忽略。此调度变更不能遮盖真实sourcebug；本次source变化必须新HEAD远端CI。

## 交付

review.json含真实UTC、审查代码SHA、阅读材料/locator、逐check PASS/FAIL/BLOCKED、probes实际结果、material_findings及recommendation=accept|changes_required和限定范围；MD一致。不能把结构完整当经济研究绿，不能冒签尚未发布HEAD CI。将两报告SHA、所写路径、重要发现回ROOT，然后停写。TMP只删自己新建且已明确保留必要证据的probe目录，原件和三运行保持。

附：ROOT新增仅本phase JSON及CI调查证据的 -text Git属性，防Windows staging/checkout重编码破坏已声明SHA；正常发布节点核其blob原字节，不增加人工审批。
