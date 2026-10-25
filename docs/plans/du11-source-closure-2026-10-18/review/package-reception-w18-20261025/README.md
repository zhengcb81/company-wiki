# W18 ROOT 接收（2026-10-25）

状态：ROOT_ACCEPTED_TOOL_AND_ORACLE；当前真实候选产品兼容不全绿，缺口保留。作者工区保持只读。

## 冻结与范围

- 作者交付 HEAD `b697bcf9b84de52b9d47c811554043e10ef2b551`，最终工具源码 `faa488a7cdbfe0f0aec953bb6cdfcf52baf7813e`；45个新增允许路径，工区干净。接收时ROOT无冲突合并到索引，现已正常merge/push f23ba2b7。
- 主线接收基线 `b57a716c18c209144744d86fafc35eae87e1546f`；保留既有 `.githooks/pre-push` 模式WIP与历史未跟踪产物。
- 三市场、8份原件、96个目标；旧基线及独审绑定作者版本。目标全部语义 not_reviewed；机械可见性不冒充摘要质量。

## 集中修复与验收步骤

1. 中性RED框住：bootstrap先完整校验，已存在的湖永不覆盖；attempt原子创建，旧目录任何文件不变；结果绑定样本/源码/前后SHA，损坏JSON只失败当前样本；PDF夹具实际进入解析链。
2. 在原有薄回放工具内修复，不另建任务库/权限签收。失败原始结果保留，工程失败不伪装内容成功。
3. 源侧gold v4：七个纯财务表目标改为“输出时检查正确性”，经营与业务目标仍必需；BGB-16673使用自身段落补全FDA及临床时间锚点，不借其他药物互证；研发比例不推断绝对金额。保留旧baseline，oracle修订不得计作代码提升。
4. 集中跑W18边界/真实中性链及必要DU-BENCH契约，独立复审范围内全部问题；正常merge commit、push。
5. v4已提交冻结后，在ROOT独占短路径、干净源码与新湖回放真实代表PDF/HTML/DOCX；不写作者湖、不复制原件、不调用收费API。清理只限本轮自有临时环境，保留紧凑收据。
6. 更新唯一状态、并行派发记录和下一步，正常提交推送。PDF-C2/C3及产品覆盖发现仍OPEN，不以工具通过代签。

## 初审实证

独立报告：`.planning/w18-root-acceptance-20261025/independent/intake-review.md`，中性复现 probe-results.json。确认配置覆盖、旧attempt收据覆盖、mutated-original仍ok、未进入链的PDF夹具及上述gold问题。ROOT集中修复后需终审。

作者基线产品问题保留：招股解析未完整、DOCX类型路由、业务覆盖不足、disposition观测缺口。observe旧默认selector与compile固定0.9.0需分开解读；不能把路线差异统称解析差异。样本已暴露给开发，后续是回归集，不宣称新的盲测。

## ROOT工程进展

新增9项RED全部复现；同实现完整W18 28P/63.80秒，修订后的gold v4另10P/0.73秒（计数重叠，不相加）。Ruff和diff-check通过，所有自有临时测试目录恢复不存在。新金标修订共10项，96个目标ID不变。待终审、正常merge/push及冻结版本真实回放。

独立终审PASS_ENGINEERING_AND_ORACLE_SCOPE，0 OPEN；独立28P/49.53秒＋额外3种结果绑定突变均拒、正例通过，19份最终LF文件SHA绑定，临时根恢复不存在。允许正常合并冻结v4，随后ROOT真实候选回放仍待执行。

ROOT真实回放资源说明：本次抽样上限每份120秒。启动后补读作者三次逐样本时间，H1为170.7/120.7/116.2秒，港股57.0/89.3/122.8秒；此上限可能截断既有慢路径，若超时不据此宣称代码退化，也不重复整批或盲目延长。ROOT先前资源预检只看了汇总而未读逐attempt耗时，记录为本次试验设计限制。原120秒失败保留，后续同owner分段剖析区分导入、原生观察与compile，不以提高cap掩盖效率问题。

## 真实候选结果与接收结论

W18工具/oracle组件已完成ROOT根修、独审、保留作者祖先的合并与推送：`f23ba2b7c9551bf6b6b83f9f9d9d25fa9a27489a`。19份最终review绑定文件逐一与Git提交吻合；正常pre-push154P/56.77秒。当前真实候选 **has_failures，不是产品全绿**。

| 既有源 | 当前候选实际结果 | 时间 |
|---|---|---|
| CN百济2024H1 PDF | 120秒上限timeout，未生成完成观测 | 120.1秒 |
| HK百济FY2022 PDF | observation ok，scoped v4 compile 76任务；direct native仍partial | 68.2秒 |
| US Alphabet FY2025 HTML | observation ok，scoped v4 compile 75任务 | 32.2秒 |
| CN海康2024H1电话会DOCX | observation ok，compile仍SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED | 4.2秒 |

以上是0.8直接观察与0.9/v4编译两条已明示路径，不把两者差异归因同一parser。compile只生成配置中的wire body，0POST/费用/下载；没有正式摘要响应，语义仍NOT_REVIEWED。H1旧作者用900秒上限，本次120秒不可直接作性能回归判定；不重复整批或提高cap强求绿色。

4原件与3配置前后SHA一致，原件0复制，冻结producer干净。临时工区峰值15,973,829B，worktree正常移除、自有临时根恢复不存在；完整attempt从424,247B无损压缩至94,749B，保留SHA及压缩回验。作者HEAD/工区仍干净，旧baseline与作者Git blob一致。

`product-findings.json` 将原产品四类发现保持OPEN，并与既有CF/PDF-C2/C3关联。H1另需同owner分段计时，DOCX先用中性种类/规范化路由反例查因；不得按公司名加补丁。**工具/oracle接收不阻止诚实暴露产品失败，也不代签正式摘要、cache恢复、RF采用或新盲测。**

下一步返回PDF-C2：按已有单层阅读owner细则先写通用段落缺口分诊/严格成员对齐RED，再做有界按需增强。正式C3前必须处理/解释本次源路由、耗时和coverage缺口。W18现在是已暴露的回归集，C3新公司/US PDF/扫描件仍需独立新样本。

真实候选收据独审PASS_RECEIPT_INTEGRITY_PRODUCT_COMPATIBILITY_NOT_ALL_GREEN：19 Git blob、gzip/展开SHA/长度、四样本汇总、import根及原件/配置前后证明一致；实际attempt/deploy根已不存在。未重跑批次或模型，内容缺口不改绿。见root-real-replay-review.md/json。

发布验收完成：精确[CI40232151718](https://github.com/zhengcb81/company-wiki/actions/runs/40232151718)绑定f23ba2b7，completed/success，2026-10-25T20:49:11Z结束。唯一状态与Next Step已回到PDF-C2，C1不重做；本节点剩余产品失败不被CI工程绿关闭。
