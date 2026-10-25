# W18 ROOT 接收（2026-10-25）

状态：IN_PROGRESS，作者 COMPLETE 不等于 ROOT 已验收。作者工区保持只读。

## 冻结与范围

- 作者交付 HEAD `b697bcf9b84de52b9d47c811554043e10ef2b551`，最终工具源码 `faa488a7cdbfe0f0aec953bb6cdfcf52baf7813e`；45个新增允许路径，工区干净。ROOT已无冲突合并到索引，尚未生成 merge commit。
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
