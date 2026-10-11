# W06 三张施工卡独立试读

## 结论

**未发现设计层面的发布阻断，可以分派已准备的三张卡。** 这是计划可执行性试读，未运行未来产品测试，不能称三层实现、真实来源或预测研究已通过。上一轮 0.8 源码审查的 **FAIL 保留**。

三条线分别使用独立工作树，新增文件与 W05 OCR、RF 日期贡献、Audit pool_progress，以及 ROOT 的 selector/预算/LLM 配置/reader/跨仓适配没有写集重叠。input 目录仍只读；共同上级交接目录不扩大写权限。

## 已核对的真实接缝

- **FF：** 实际入口是 `scripts/fetch_filing.py`，类是 `EarningsTranscriptsTransport`。它调用配置的 ET 程序，再经真实 CWP transcript_import_cli 入库。卡明确禁止整层伪造 stdout、import response 或 SourceRef。
- **ET：** `transcript_tool.main` 确实有私有 retrieval launcher/spec/temp-root 参数；真实 supervisor/worker 仍会执行 transcript_api。只在 worker 内换 HTTP，能够实现零外网的三层联调，无需改生产 flag 或 producer。
- **CWP：** 有精确 `register_sources`、`query_ref`、`SourceVersionReader.open_version` 及 SourceExport v2 CLI。卡区分内容/引用稳定性与未承诺的 document_id 永久稳定；缺原文、损坏、重复副本、搬根、重新打开均有真实期望。
- **Audit：** numeric_audit 只复算显式 scale/FX，明确不证明出处或经济定义。新的 typed measure/关系诊断是实际能力扩展，与 W05 循环恢复独立；source_truth_verified=false 和 economic_reasonableness=not_evaluated 必须保留。

## 试读中修正的两点

ROOT 已把不准确的 transport/open API 名字换成真实接口。FF 卡还明确要求 supplied CWP src/PYTHONPATH、子进程模块 __file__/SHA、scratch cwd/config/company_wiki_root，避免照抄 existing IsolatedWiki 时误用 editable/生产 fallback。

最后读取的 workspace receipt 为 **READY**，三份 inputs.json 均存在，列明物理 SHA 与 Git blob SHA。CRLF/LF 差异单列；本次没有独立执行未来 runtime import 或代码快照恢复，不把准备收据冒充运行通过。

## ROOT 补充已解决实施歧义

已实读 ROOT_INTERFACE_AMENDMENT.md（SHA `b874c266a4cd37cb823fcbfda556606754fbcef9294ada5919a023a7844bb9bb`）。它明确 Audit overall 为 INVALID > FAIL > UNRESOLVED > PASS、退出码 2/1/3/0；必要关系 NOT_CHECKED 应为 UNRESOLVED。假设/压力测试可 source_ref=null，但必须带 rationale/依据和角色，不能伪造原件。未来预测期间与来源 available-by/as-of 分开。

补充还给出真实 FF scratch config 字段、精确 open_version 和有效简单 root_id，避免照抄说明中的斜杠标签。固定旧 card/input 保留。各线按既有 contract/测试节点实施这些规则，**无需新审查节点、许可或扩大测试包**。

## 隔离与 ROOT 接线

两套验证工具使用有效的小型 synthetic 原件，真实责任层读取/验字节，工程失败诚实报 PARTIAL。后续 ROOT 修共因，再重放原失败向量；不得更改 expected、skip 或冒称研究通过。根迁移必须新短生命周期进程 reopen，不用旧 buffer。

sentinel 清单、关闭 SQLite/子进程、finally 仅清 owned 生成路径、恢复 absent/sentinel baseline、持久 ≤8MiB 与 scratch ≤64MiB（必要代码快照另计）均写清。ROOT 负责共享接口修复、一次大节点接收、技能接线、快速 CI 选择、安装与并主线；没有新增每 commit 全链门。

机器报告列实际输入 SHA：[report.json](./report.json)。

**费用 $0；网络/LLM/provider/未来产品测试 0；产品、共享 PWF、旧证据无修改。STOP。**

