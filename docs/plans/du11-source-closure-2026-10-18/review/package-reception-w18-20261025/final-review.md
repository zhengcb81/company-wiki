# W18 ROOT 独立终审

结论：**PASS_ENGINEERING_AND_ORACLE_SCOPE；本范围未解决问题 0 项**。

独立审查者未参与实现；审查作者最终交付以及 ROOT 尚待合并提交的完整工具、测试和 gold v4 增量。准确审查对象由同名 JSON 的 19 份源码/测试/金标文件 LF SHA-256 绑定，后续 merge commit 应保留这些字节。不会预先签收尚未发生的源码变化。

## 修复复查

- R1：bootstrap 在任何写入前验证绑定大小/SHA和 source-root 包含关系；独占创建新湖，旧配置与旧收据不会覆盖。
- R2：attempt 独占原子创建，碰撞拒绝；job/result/最终收据使用独占写入。现有目录拒绝链校验整个目录的字节和 mtime，包含旧 attempt.json。
- R3：结果必须为对象，绑定 schema、样本、候选提交、原件前后 SHA 以及严格布尔 unchanged；错误/非对象结果保留，单样本 invalid，不再冒充成功观察。
- R4：七个纯财务表目标改为 correctness_if_emitted，全部数值事实保留；业务增长归因、产品、临床、产能和条件性指引仍保留经营义务。不把金标范围修正计作代码改善。
- R5：PDF 真实加入中性 manifest 和 bindings，三种载体都进入实际子进程链；PDF MIME/自身引句均正确。
- R6：已读原件物理第9/25/26页与最终补充引句一致；研发比例覆盖两期与百分点，Sonrotoclax 与 BGB-16673 各用自身 FDA/临床段落。不同药物日期不再互证。

## 独立执行

在 ROOT 自有临时环境独立运行 W18 全部短包：**28 passed，pytest 49.53 秒，总计 70.77 秒**；临时根最终恢复 absent。包含真实中性 PDF/TXT/HTML 子进程、来源路径证明、第二绝对根、污染 PYTHONPATH、超时、失败、不覆盖与清理链。日志和收据为 `independent-green.log` / `independent-green-receipt.json`。

另加三项独立突变：`original_unchanged=1`、错误 before-SHA、`request_sent=true` 全部被拒，正常对照被接受；证据为 `independent-counterexamples.json`。没有运行全仓全量检查、真实模型或下载，没有写作者工区。

## 签收范围

此结论签收 W18 的工具与源侧 oracle 修正。旧 baseline、作者失败记录和版本化 oracle 保留；v4 已暴露给开发，应称回归集，不称新盲测。observe 默认 selector 与 compile 0.9 路径仍分别记录，不能把它们当同代生产质量比较。

ROOT 接下来提交冻结 v4 和候选，再做真实代表来源回放。正式摘要、缓存恢复、RF 四审及原有产品发现仍按主 PWF 执行；本次工具通过不代签这些内容质量。
