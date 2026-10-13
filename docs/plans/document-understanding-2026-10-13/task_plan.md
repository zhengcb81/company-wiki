# 文档理解架构升级：调查与实施计划

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
状态：三包已合并到 ROOT 分支并通过全量跨层验收（331 tests）；ROOT 已完成观察适配、编排、
选择桥与端到端 pipeline（**未接入生产入口**）；生产解析链仍未切换。

## 目标与边界

根据真实 A/H/US 文档及现有代码，设计文档类型/章节驱动的精选证据与摘要架构。原件不改，不增加逐材料授权、不复制全量 PDF/MD，不新增研究结论 writer。复用 SourceRef/SourceExport、AUTO Store、现有资源预算与配置供应商。W08 RF/Audit 接收和母计划真实 G2/G4/G5 不被替代或标成完成。

## 阶段

1. [complete] 读当前路由/规范化/选择/摘要边界与历史设计；20份原件原生扫描/重点抽读、4页视觉核对、3份真实selector回放。
2. [complete] 已写design、INTERFACES、implementation，明确共用结构/策略/语义证据、资源与A/B/C测试。
3. [complete] 三卡、冻结接口/交接格式和独立worktree已准备；共同基线 7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8。
4. [complete] 三包实施：DU-PROFILES（文档路由）、DU-STRUCTURE（章节与语义单元）、DU-BENCH（真实质量基准）各自实现并交付 handoff。
5. [complete] ROOT 接线：du-input/1 观察适配、du-packages/1 依赖闭合编排、选择桥（只增不减，保住必需上下文与否定）；docs/ARCHITECTURE 更新。
6. [complete] 三包合并到 ROOT 分支 + 端到端 pipeline + 全量跨层验收（含真实原件，0 skip）。
7. [pending] 真实模型摘要大节点与跨公司 G4/G5 验收；本层**未接入生产入口**，切换属后续步骤。

## 当前实现状态

三包已 merge 到 `codex/du-root-integration-20261013`，四个套件在**同一次 pytest 调用**下通过。

| 组件 | 位置 | 测试 | 生产接线 |
|---|---|---:|---|
| profiles | `src/company_wiki/document_understanding/profiles/` | 150 | 否 |
| structure | `src/company_wiki/document_understanding/structure/` | 47 | 否 |
| ROOT 适配/编排/选择桥/pipeline/摘要请求 | `src/company_wiki/document_understanding/{observation_adapter,orchestration,selection_bridge,pipeline,summary_input}.py` | 109 | 否 |
| benchmark | `tools/document_understanding_benchmark/` | 65 | 工具，非生产路径 |

同一调用下合计 **371 passed / 5 skipped**；`ruff check src tests/unit tools` 全绿；
真实原件节点 11 项实际运行并通过（不再 skip）。

实测对照（与基线同一证据预算，未多选提分）：development 关键事实召回 0.220 → **0.384**，
holdout 0.000 → **0.350**；恒锋「建设期」0.000 → **0.857**，万润否定 0.143 → **1.000**。
三份文档回退，如实记录未针对金标调参。详见 `.planning/du-root/c-node-results.md`。

端到端入口（ROOT 独占）：
`company_wiki.document_understanding.understand_units(units, ...)` →
`build_observation` → `route_document` → `get_profile` → `build_structure` →
`build_dependency_packages`，输出 `du-pipeline/1`。

摘要请求入口：`build_summary_input(pipeline_result, ...)` → `du-summary-input/1`。
焦点取自 profile（此前 `summary_focus` 无任何消费者），证据包按编排顺序排列并保留
`locator`/`page` 回指，预算截断记 `deferred`、未读记 `unread`；**不调用模型**。

引用可回放：`locator` 取 parser 的 `source_locator`，否则取
`EvidenceCoordinates.locator()` 派生值（`loc:v1/page:62/paragraph:3`）。
早前版本用 unit_id（内容哈希）冒充 locator，读层无法由哈希还原页码段落，已修。

QA 双角色取决定案：`qa_text_shadow` 是文本层副本，**不新增、不发送、但报告**；
结构层仍保留两份以配对问答（`NOT_SELECTABLE_WITHHELD` / `excluded.not_selectable`）。

真实跨层验证（原件 SHA/mtime 未变）：恒锋两期建设期跨页保留、万润“不生产VC”否定保留、
名创双栏不混读、中微季报业务文本可组织；恒锋 `发行A股股票募集说明书` 由 legacy `unknown`
转为 `offering`，鼎龙确认函由 legacy `prospectus` 转为 `administrative_candidate`。

尚未解决：名创门店表（0.000）已定位为 parser 将双语表抽成退化单格行、无法构成
`operating_table` 包，需表格几何重建；无编号纸质标题仍需 parser 保留 span 字号。

## 合并阶段发现并修掉的接线缺陷

这些缺陷在两包各自单测里都看不见，只有并到一条链上才暴露：

1. **路由对编排完全无效（no-op）**：`orchestration._role_priority` 从 `route["section_priorities"]`
   读优先级，但该键在 **profile** 上而不在 route 上（`route_document` 不返回它）。
   结果每份文档都拿到同一套通用优先序，路由等于没接。
   修复：`build_dependency_packages` 增加 `profile=`，优先级取 profile 优先、route 兜底；
   并补 `test_du_root_lane_seam.py` 锁死该契约。
2. **两 lane 的 fixtures 同名冲突，合并后 pytest 直接收集失败**：structure lane 把自身 fixture
   目录插入 `sys.path` 后 `from fixtures import ...`，而仓库另有 `tests/fixtures` 也在 `sys.path`。
   单跑 structure 能过，四套件同跑即 `ImportError: cannot import name 'available_inputs' from 'fixtures'`
   —— 正是 CI 的跑法。修复：fixture 模块改名为唯一的 `du_structure_fixtures.py` 并按该名导入。
3. **四个测试模块的仓库根路径算错**：`tests/unit/<lane>/test_*.py` 用 `parents[2]` 得到的是
   `root/tests` 而不是 `root`，于是 bindings 永远找不到、真实节点**静默 skip**。
   修复为 `parents[3]`；修复后真实节点由 10 skipped 变为 10 passed。
   （注意：structure lane 的 fixture 路径 `parents[2]/fixtures/...` 在同一深度下是**正确**的，
   不要一起改。）

## 需要后续处理的真实缺口

- **parser 需保留 span 字号**：否则无编号纸质标题（如 `Store Network`）无法可靠判定为章节；
  几何猜测会误伤同页等高的表格片段，故不做猜测。
- **QA 页双套角色单元**：parser 同时输出 `investor_question`/`management` 与 `qa_text_shadow`，
  需在 adapter/选择层决定保留哪套；结构层不得删除任一侧。
- **design.md 的名创双栏描述需更正**：实测为**左栏英文、右栏中文**（原文写“中英左右栏”），
  且两栏各自语言统一，跨栏不存在同位中英对；真实中英并排对在同一栏内相邻。
- **benchmark 的 holdout 仍不完整**：US holdout 为 UNAVAILABLE（本机没有非开发集美股原件），
  H 股 holdout 只有一家公司。`context_completeness`/`role_modality_quantity` 在原生基线上
  仍是 NOT_EVALUATED，需要 ROOT 注入真实 adapter 后才有分母。
- **探测预算**：真实文档 3000–4000 unit 对冻结的 200 unit / 64000 字符必然到限，
  因此真实文档 confidence 一律 `low` 并报 `ROUTE_PROBE_LIMIT`。是否放宽属 ROOT 用既有
  全局上限收敛的范围；profile 侧不允许自行提高。

## Next Step

生产切换与真实模型大节点按母计划 G4/G5 另行执行；接入方式见
`src/company_wiki/document_understanding/__init__.py` 的 `understand_units`。

## Errors Encountered

- 首次 CodeGraph 用宽泛自然语言命中旧 ClaimRouter，后续改用明确符号；未据此推断新解析链。
- 历史 W04 source_rows JSON 已归档不在原路径；改读已发布压缩回放定位六份原件，无重新生成历史证据。
- Python 首次输出中文编码失配；后续统一 `-X utf8` / PYTHONIOENCODING=utf-8，原文件不受影响。
- PyMuPDF原生save向沙箱Temp写PNG失败；改写工作区自有临时目录、tobytes写入后目视核查；四PNG已删除恢复。
- HKEX年报编制指南打开失败，正文未核验；设计引用本地真实港股年报和官网摘要，不将搜索摘要当全文已读。
- 母PWF首次prepend被Windows换行转换造成全文件diff；已按HEAD原字节保留正文、仅追加LF前缀恢复，diff仅14行新增。
- 新worktree --no-checkout后稀疏规则未填入空索引；在三个刚创建的指定分支执行read-tree -mu HEAD完成检出，三者status均0，无原件目录复制。
- ROOT 真实测试首次硬编码原件绝对路径，被仓库 host-assumption guard 拦下；改为本机未提交 bindings
  文件驱动，`src`/`tests` 内不再出现主机绝对路径，缺绑定则 skip 而非 PASS。
- 合并阶段：`compileall` 生成的陈旧 `__pycache__` 会让编辑后的模块仍按旧代码运行，
  出现"改了却仍失败"的假象；排查此类问题前先清理 `__pycache__`。

