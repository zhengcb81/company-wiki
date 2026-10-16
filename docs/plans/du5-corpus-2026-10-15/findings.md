## ROOT接收收尾 — 2026-10-16

CWP已正常并线推送，252真实材料测试与12Git往返通过，精确CI 38834945691 SUCCESS。ROOT金标纠正显式v3，保留原旧值/锚点/重要性/分母；作者v2 handoff为历史。

**Next Step：** ROOT用同一金标验生产候选；原native12/37是待修质量，不自称生产完成。详[总接收](../document-understanding-2026-10-13/review/du5_reception.md)。

---

# 调查记录（findings）

2026-10-15。基线 `8c027011`，分支 `codex/du5-corpus-2026-10-15`。全部测量只读；
本卡生产写入 0、供应商调用 0、模型调用 0。已复现/实测与静态假说分开标注。

## 1. 实查矩阵（A.1）

“有名字”≠“有 schema”≠“有 synthetic”≠“真实 gold”≠“可读”≠“已选择”≠“正式摘要已审”。
机器可读形态：`coverage_matrix.SAMPLE_AXES`（每 sample 五轴 original/gold/readable/
selected/summary_reviewed，yes/no/unknown+测量出处）；新集冻结记录 `du5_manifest.json`。

| 形态 | 覆盖 | 已有金标 | 真实原件绑定 | 可读入口 | 已测阶段 |
|---|---|---|---|---|---|
| a_share_annual | real | smic（gold）；cn-annual 仅原件 | 2/2 | parse_pdf_bytes | cn-annual 未观测 |
| a_share_interim | real | cn-h1 + du5-iflytek | 2/2 | parse_pdf_bytes | cn-h1 历史回放；iflytek 本次实测 |
| a_share_quarterly | real | 4 旧 + du5-fangbang + du5-proya | 6/6 | parse_pdf_bytes | 旧 4 个有回放；du5 本次实测 |
| hk_annual | real | hk-annual/ali/biren/anta | 4/4 | parse_pdf_bytes | 3 个有回放；biren 仅探文字层 |
| hk_interim | real | du5-kingsoft-interim（gold）；hk-interim 仅原件 | 2/2 | parse_pdf_bytes | du5 本次实测 |
| hk_quarterly | real（du5 修正旧 MISSING） | du5-kingsoft-q1 | 1/1 | parse_pdf_bytes | du5 本次实测 |
| us_10k | real | us-10k/2×holdout/fresh-apple | 4/4 | normalize_document(HTML) | us-10k 实测 5,215 units；holdout 旧路由 units=0 未重测 |
| us_10q | real（仅原件） | 无 | 1/1（VRSK） | HTML 前端未验证 | 未观测（name-only） |
| us_20f | real | us-20f（15 facts） | 1/1（TAL） | HTML 前端未验证 | 未回放 |
| us_interim（6-K） | MISSING | — | — | — | 本地无 6-K；8-K 不顶替 |
| ipo_prospectus | real（仅原件） | 无 | 1/1（cn-ipo） | parse_pdf_bytes | 未观测（name-only） |
| us_s1_f1 | MISSING | — | — | — | REQ-2 开放 |
| equity_offering | real | cn-equity + du5-zhongmi | 2/2 | parse_pdf_bytes | du5 本次实测 |
| convertible_bond | real（仅原件） | 无 | 1/1 | parse_pdf_bytes | 未观测（name-only） |
| investor_relations | real | cn-ir | 1/1 | parse_pdf_bytes | 历史回放 11/11 |
| earnings_call | real | us-txt + du5-gbits-call | 2/2 | transcript / normalize(docx) | du5 本次实测 |
| results_release | real（仅原件） | 无 | 2/2 | pdf/html | 未观测（name-only） |
| presentation_deck | real（仅原件） | 无 | 1/1 | normalize(PPTX) | 未观测（name-only） |
| sec_8k_6k_exhibit | real（du5 填补） | du5-msft-8k + du5-msft-ex991 | 2/2 | normalize(HTML) | du5 本次实测；REQ-3 生产验收仍 open |
| amended_filing | MISSING | — | — | — | REQ-4 开放 |
| low_business_administrative | real | confirmation（gold）；ir-policy 仅原件 | 2/2 | parse_pdf_bytes | confirmation 实测扫描不透明 |

DU5 新集：9 份 / 7 公司 / CN5·HK2·US2 / 9 形态，目标≥6 形态达成
（A股半年、经营季报、稀疏纯财务季报、增发、港股中期、港股季报、8-K容器、
业务 exhibit、原语言电话会转写）。“另一公司的期间/单位表格”=珀莱雅
（本报告期 vs 本报告期末 vs 上年度末、元/元股/个百分点）；“另一公司的否定/计划/
问答”=吉比特电话会。全部 SHA 绑定、锚点冻结前逐条独立验证、
`du5_manifest.json` 记录冻结时间/读取范围/来源侧业务目标/prior use。

## 2. 真实不一致（A.6，全部实测，两个真实 RED 已留证）

1. **coverage 名称存在但 gold 不在（RED-coverage-axes，3 failed→绿）**：旧矩阵把
   五轴压成一个 REAL；`a_share_annual` 注释称“金标事实”却引用无 gold 的
   cn-annual；us_10q/ipo/convertible/results_release/deck 等 REAL 行名不副实。
   B 实现 `SAMPLE_AXES` 五轴后转绿。
2. **错页行（RED-gold-anchors，2 failed→绿）**：独立提取核对旧 317 锚点，309 命中，
   实测 3 个 wrong-page：cn-equity p62→实为 p61；cn-q-sparse 两锚点 p2→实为 p1。
   旧 gold 字节不动，`gold_corrections.json` 提案更正（ROOT 决定是否发布 applied
   版本），RED 留证后转绿。
3. **不可独立验证 4 项（显式记录非通过）**：扫描无文字层（cn-ipo-confirmation）、
   CID 乱码（hk-annual-mojibake×3 锚点）、复选框字形分歧（glodon）、引文跨
   inline-XBRL 边界（us-20f）——全部入 `unverifiable` 带类别与理由。
4. **部分不透明 / 一个替代 support 不可用但另一个完整 / 声明 complete 缺关键上下文**：
   机制现实已正确，旧正控（test_reception_contract）保持；另在真实 du5 gold 上
   增加正控：可读替代组不被不透明组拖累、错页引文永不召回、重复 sample_id 拒载。
5. **C 节点独审发现的金标内容缺陷（改错金标，版本2）**：珀莱雅 3 条
   must_not_assert 含真命题/半真析取（会惩罚正确摘要）、吉比特 1 条 modality
   误标 conditional（应为 plan）。按 INTERFACES“改错金标需单独更正记录和版本，
   旧值仍可回放”处理：`gold_corrections.json.content_corrections` 逐字段记录
   old/new，manifest 保留冻结版哈希（`*_at_freeze`），锚点/重要性/分母未动，
   且不影响本次实测分（基线无 claim 输出，负例与 modality 仅作用于 claim 级检查）。

## 3. 冻结纪律（A.4/A.5）

- 9 份 gold 在读取任何本样本候选输出前冻结（support_set_digest、gold SHA、
  冻结时间、已读/未读页域、prior use 全记录）。冻结后仅发生上条第 5 项的
  版本化独审更正，旧值可回放。
- 事实来源：9 个独立子代理逐字读原件回报（`reader_reports/*.facts.json` 留存），
  重要性由原文阅读判断；2 个子代理请求被平台内容过滤拒绝，重述为
  “事实核查用负例对照”后成功（如实记录，未改语义）。
- prior use 检索（.planning/docs/plans/docs/implementation）：金山雲（du-bench
  文字层探测）与 Microsoft（us-10k/us-txt 诊断史）标 contaminated；科大讯飞、
  方邦、珀莱雅、中密、吉比特 fresh 并附已知旁证（路演名单/重复审计路径/会议转写）。

## 4. 实测结果（C，native 真实 CLI，两次复跑一致）

`python -B -X utf8 -m tools.document_understanding_benchmark --mode native
--bindings <du5 本地映射> --output <owned>`，9/9 原件可读（pdf×6/htm×2/docx×1，
unavailable=0）；新集 holdout critical=12/37=0.324（8 FAIL、1 PARTIAL），narrative
15/55=0.273。按卡定性为待修生产质量，不修源码洗绿。分母全部真实：
critical_fact_unavailable=0、coverage=1.0（全部锚点在原件可解析层）。恢复证据：
raw_unchanged=True（9 原件前后 SHA 一致）、config_unchanged=True（真实生产
source_catalog.yaml + sentinel）、sentinel_restored=True、model/paid/network=0、
raw_copies=0。

## 5. 行换行与字节锁

宿主 core.autocrlf=true（旧 gold 工作副本 CRLF、blob LF）。字节锁按 git 归一化
内容（=blob 身份）计算；`.gitattributes` 沿 tests/golden 先例把 benchmark JSON
钉 `text eol=lf`（首个 `**.json` 写法只覆盖单层，实测发现后改为三条显式路径）。
实测 add→blob→fresh-checkout 全链字节一致，fresh-checkout SHA 与冻结
manifest 的 gold_sha256 完全一致（receipts/git-blob-roundtrip.txt）。未改原件
或 gold 适配换行。
