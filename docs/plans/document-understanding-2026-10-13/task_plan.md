# 文档理解架构升级：调查与实施计划

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
状态：调查/设计完成，分包准备中；生产解析链未切换。

## 目标与边界

根据真实 A/H/US 文档及现有代码，设计文档类型/章节驱动的精选证据与摘要架构。原件不改，不增加逐材料授权、不复制全量 PDF/MD，不新增研究结论 writer。复用 SourceRef/SourceExport、AUTO Store、现有资源预算与配置供应商。W08 RF/Audit 接收和母计划真实 G2/G4/G5 不被替代或标成完成。

## 阶段

1. [complete] 读当前路由/规范化/选择/摘要边界与历史设计；20份原件原生扫描/重点抽读、4页视觉核对、3份真实selector回放。
2. [complete] 已写design、INTERFACES、implementation，明确共用结构/策略/语义证据、资源与A/B/C测试。
3. [in_progress] 三卡已写；冻结互不重叠路径，准备独立worktree与发布计划。
4. [pending] 三包实施、ROOT接线、真实摘要/公司G2/G4/G5；本轮不执行生产重构。

## Next Step

发布计划并准备DU-PROFILES、DU-STRUCTURE、DU-BENCH三个工作目录；由用户分发，ROOT不代为启动。

## Errors Encountered

- 首次 CodeGraph 用宽泛自然语言命中旧 ClaimRouter，后续改用明确符号；未据此推断新解析链。
- 历史 W04 source_rows JSON 已归档不在原路径；改读已发布压缩回放定位六份原件，无重新生成历史证据。
- Python 首次输出中文编码失配；后续统一 `-X utf8` / PYTHONIOENCODING=utf-8，原文件不受影响。
- PyMuPDF原生save向沙箱Temp写PNG失败；改写工作区自有临时目录、tobytes写入后目视核查；四PNG已删除恢复。
- HKEX年报编制指南打开失败，正文未核验；设计引用本地真实港股年报和官网摘要，不将搜索摘要当全文已读。
- 母PWF首次prepend被Windows换行转换造成全文件diff；已按HEAD原字节保留正文、仅追加LF前缀恢复，diff仅14行新增。
