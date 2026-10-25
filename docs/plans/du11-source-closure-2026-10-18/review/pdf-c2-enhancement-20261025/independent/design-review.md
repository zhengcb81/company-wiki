# PDF-C2 independent design review

基线8669e0cd；源码LF SHA及四gzip完整性见同名JSON。4/4压缩/解压SHA一致。仅只读源码/冻结证据，0模型、网络或收费调用，未改src/config/作者区。

## 需ROOT解决的三项问题

1. **P1 替代物理证明进不去。** `_Analysis.native`先经`observe_native_source_unit`，后者无精确native字体即返回None；hint只加在edge不能救此类分片。`edge`还先拒绝font/scope不同。严格成员证明可以是另一种物理正证，但不要伪造字体、不要绕过异源/页/原序/role/表格/标题/已知异栏/明确章节/项目反证。缺字体可在外部证明路径记诊断，native原有路径保持。必须用无字体、混合字体、错误scope反例验证。

2. **P1 历史8/8口径与事实边界冲突。** HK行业云4unit3块，符合上限；IPO技术8unit6块，整段超4block。其原文自然分成背景（paragraph10–12）、刻蚀应用（13–15）、MOCVD量产及地位（16–17），每个闭合事实不超3块。历史gold要同group兼含刻蚀和MOCVD，不能要求独立事实拆分同时又同原子。保持历史基线，新增版本化per-fact task/citation闭合指标；不得抬8unit/4block/2048或硬合业务凑绿。

3. **P2 必须审最终材料。** 普通结构容器会被`_prose_reading_packages`重新拆；只向metadata塞Docling结构不会生效。采用generic瞬态成员hint、现有continuity物理边owner和不折叠external-only native ID路径，须证明真实summary task含全部原成员、否定/条件/期间不丢，提示不进入持久EvidenceSpan。

## 最小反例组

- 同段中美元→单位/同比→原因闭包，旁边另一产品23%不串线。
- 同段中两个独立产品事实分开，不因external paragraph group成为同一经营状态。
- 跳过中间unit、逆序、重复文句、部分重叠、错frame/旋转/源SHA/页、表格混入、标题及不同项目均拒绝。
- 真实完全字符等价可允许明示NFKC/空白/bullet比较，但canonical文字/offset不变；私用字形、数字差异、引号替换不猜修。
- 超8成员/4块段落保留已闭合前缀，延期未闭尾；0页需求0模型；同页去重；共用账户/绝对deadline/子进程及临时清理。
- recipe事前冻结，actual记录实际启用，恢复仅验证canonical成员不重新跑布局。

这是设计初审，不是C2最终验收。最终源码/真实task召回/资源恢复证据到齐后复审。

## 真实native追查（独立补充）

两份原件经SourceVersionReader只读打开，Conda PyMuPDF1.26.7原生读取，分别只对目标页partial DU；0 Docling/LLM/下载/原件副本，config/catalog/budget SHA不变。详见native-diagnostic.json（紧凑12成员，不留全文）。

- HK四成员均9pt regular，scope=(s2,None,management_discussion)，company_filing，dict/observed_single_body_lane，全部paragraph，无heading/project，Native全部通过。首bullet成员paragraph9和paragraph10左缘差22.68pt，超过2.1×9pt，故仅10–12合组；这是确定物理证明缺口。
- IPO八成员均12pt regular，scope=(s4,None,business)，同role/frame/column，全部无heading/project。字体/scope并非本轮真实阻碍，**D1仅作泛化反例，不以此要求放宽生产规则**。
- IPO原生continuity已给10–12背景、13–17技术两窗口；冻结baseline最终按独立事实给三个完整native_range spans：paragraph10 char253–344背景；paragraph13 char344–408完整刻蚀65→5nm+具体应用；paragraph16 char408–474完整MOCVD量产+国内地位。**IPO旧gold缺组合组不等于内容丢失**。应修版本化验收口径，保持独立事实/最终task真实引用；不应为了旧8/8硬拼经营状态。
