# 文档理解架构升级：调查与实施计划

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
状态：三包已实现并交付；ROOT 已完成观察适配、编排与选择桥（**未接入生产入口**）；生产解析链仍未切换。

## 目标与边界

根据真实 A/H/US 文档及现有代码，设计文档类型/章节驱动的精选证据与摘要架构。原件不改，不增加逐材料授权、不复制全量 PDF/MD，不新增研究结论 writer。复用 SourceRef/SourceExport、AUTO Store、现有资源预算与配置供应商。W08 RF/Audit 接收和母计划真实 G2/G4/G5 不被替代或标成完成。

## 阶段

1. [complete] 读当前路由/规范化/选择/摘要边界与历史设计；20份原件原生扫描/重点抽读、4页视觉核对、3份真实selector回放。
2. [complete] 已写design、INTERFACES、implementation，明确共用结构/策略/语义证据、资源与A/B/C测试。
3. [complete] 三卡、冻结接口/交接格式和独立worktree已准备；共同基线 7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8。
4. [complete] 三包实施：DU-PROFILES（文档路由）、DU-STRUCTURE（章节与语义单元）、DU-BENCH（真实质量基准）各自实现并交付 handoff。
5. [complete] ROOT 接线：du-input/1 观察适配、du-packages/1 依赖闭合编排、选择桥（只增不减，保住必需上下文与否定）；docs/ARCHITECTURE 更新。
6. [pending] 真实模型摘要大节点与跨公司 G4/G5 验收；本层**未接入生产入口**，切换属后续步骤。

## 当前实现状态

| 组件 | 位置 | 测试 | 生产接线 |
|---|---|---:|---|
| profiles | `src/company_wiki/document_understanding/profiles/` | 138 | 否 |
| structure | `src/company_wiki/document_understanding/structure/` | 47 | 否 |
| ROOT 适配/编排/选择桥 | `src/company_wiki/document_understanding/{observation_adapter,orchestration,selection_bridge}.py` | 35 | 否 |
| benchmark | `tools/document_understanding_benchmark/` | 47 | 工具，非生产路径 |

真实跨层验证（4 份原件，SHA/mtime 未变）：恒锋两期建设期跨页保留、万润“不生产VC”否定保留、
名创双栏不混读、中微季报业务文本可组织。

## 需要后续处理的真实缺口

- **parser 需保留 span 字号**：否则无编号纸质标题（如 `Store Network`）无法可靠判定为章节；
  几何猜测会误伤同页等高的表格片段，故不做猜测。
- **QA 页双套角色单元**：parser 同时输出 `investor_question`/`management` 与 `qa_text_shadow`，
  需在 adapter/选择层决定保留哪套；结构层不得删除任一侧。
- **design.md 的名创双栏描述需更正**：实测为**左栏英文、右栏中文**（原文写“中英左右栏”），
  且两栏各自语言统一，跨栏不存在同位中英对；真实中英并排对在同一栏内相邻。

## Next Step

三包 handoff 收齐后合并到 ROOT 分支做最终全量验收。生产切换与真实模型大节点按母计划 G4/G5 另行执行。

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
