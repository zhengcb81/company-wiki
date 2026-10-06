# N5-DOCSET：多文档类型真实质量基准

**complete（工具范围），不重派。** 交接2c3583e已集中接收，43不同case通过、当前主线9原件/86点/744定位全回放；required12/33的产品缺口由MAIN按[S7细则](../s7_document_quality_implementation_2026-10-06.md)推进。见[MAIN验收](n5_docset_main_acceptance_2026-10-06.md)。下方是原施工要求，不能恢复成新任务；零LLM/下载，旧golden/报告保留。

## 1. 独占目录与基线

- 源仓：`C:/Users/郑曾波/Projects/company-wiki`。
- 工作树：`C:/Users/郑曾波/Projects/cwp-lanes-20261006/document-quality`。
- 分支：`codex/n5-document-quality`，基线 `e46108b4f30d5b7e47bfc712e360f173c00b702c`。
- 允许写：新目录`benchmarks/narrative_document_types/`、独立`.planning/n5-document-quality/`、`docs/implementation/handoffs/N5-DOCSET/`。测试、CLI、manifest、golden、说明都放允许目录内；不改现有tests、src、scripts、CI、配置或总PWF。

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/n5-document-quality 'C:/Users/郑曾波/Projects/cwp-lanes-20261006/document-quality' e46108b4f30d5b7e47bfc712e360f173c00b702c
```

工作树不自带ignored原件；通过明确只读source根寻找样本，固定SHA/size。运行时代码从本树已提交基线导入，绝不依赖MAIN未提交改动。优先读现有`tests/integration/test_narrative_runtime_e2e.py`、`tests/unit/test_narrative_evidence.py`和本线N4实施细则，查实际文件后使用；复用现有parser/selector/locator replay，不抄一套实现。

## 2. 目标与交接数据接口

至少8份真实资料覆盖：年报、半年报、季报、招股书、增发/可转债募集说明书（两者有资料则各1）、有价值IR、套话/程序性IR、英文电话会。既有四样本可作对照，但至少补半年/季报与再融资。某类型无本地样本如实缺项，不拿公告标题或合成PDF冒充；不自动付费下载。

`samples.json`每项：sample_id、doc_type、language、原件SHA/byte_size、只读定位参数（本机路径放非Gitlocal.json）、来源元数据是否fixture、golden文件。Git不存整份原文/PDF或机器绝对目录。业务上层Golden用来源ID/locator；路径仅属于评估工具的本地存储配置。

`golden.json`每份至少6–15个实读标注点：golden_id、业务主题、正/负例、required/optional、公司陈述/提问角色、actual/planned/forecast/negation/question、页码或TXT段落/字节定位、短原文引文及其hash、选择理由。主题包含主营进展、行业动态、新业务/出海、募集资金用途/项目逻辑；负例含纯财务表、目录、法律套话、重复段落。无事实进展的程序性文档允许skip；缺信号的季报不得直接推定没价值。

标注先实读原文再写，不能把当前selector输出当标准答案。每份至少注明已读的相关页段、未覆盖范围及歧义；不声称穷尽全部全文。人工Gold不是人工门：由执行harness读资料作ground truth，无需逐条向用户申请签收。

`report.json` schema `narrative-document-quality/1`：基线、样本SHA、parser/selector版本、scope、golden匹配逐条结果、required覆盖率、selected噪声率、角色/情态混淆、duplicate ratio、选中UTF8 bytes/raw bytes、耗时和总临时峰值、真实/fixture说明。覆盖率只对明确标注scope，分母写清；引文未定位/元数据合成时不标verified。输出source-only，不生成投资评价。

## 3. 实施与一次节点验收

1. 读当前来源接口与文档类型路由；列8类实际样本/SHA，再读业务页、融资项目页、IR问答。样本库存与标注完成后再跑selector比较。
2. TDD写评估器反例：页码偏一、相似段落误命中、未知golden引用、错误SHA、无标注范围、角色错配；先证明错误报告会失败。标准不能随实际实现改成“全过”。
3. 用现有parser/selector产出，不用LLM；解析输出仅临时。实现小评估CLI与报告，一次汇总全部类型，输出不同错漏类别及可重放locator，不由外线调阈值掩盖错误。
4. 集中Unit验证评估器；Integration用实际现有parser/selector；E2E用独立catalog和至少半年报、季报、再融资三份原件走正式只读接口/现有处理入口，真实引用回放、SHA不变、临时根恢复。若公开入口不能直接给中间选择结果，复用现有公开应用函数并明确测试层级，不伪称CLI全链。
5. 提交代码/goldens/小报告，交`docs/implementation/handoffs/N5-DOCSET/HANDOFF.md`与统一handoff.json。不要为有噪声的基准“修到全绿”：工具正确且真实报告准确即可交付；产品缺陷形成MAIN open_items。

测试预算：0网络/LLM/下载；总提交数据≤2MiB，长原文不进Git。短test root在本worktree/tmp内，finally关闭SQLite和子进程并恢复原状。真实资料结束SHA/size/mtime保持；不写任何生产catalog或索引。只需一次集中节点、正常提交钩子和本包lint，主线CI策略不变。
