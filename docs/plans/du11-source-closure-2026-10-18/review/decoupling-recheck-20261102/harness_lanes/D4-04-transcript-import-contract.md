# D4-04 — 电话会导入 wire 与内部类型分离

状态：**已备妥，尚未派发。** 完成 D4-04（P2）。只写 company-wiki 的电话会 request decoder 与本仓契约测试。

## 唯一目标

保留现行 `company-wiki-transcript-import-request/2` 顶层合同和 FF 现有 payload；CWP 不再由 `dataclasses.fields(SourceRequest/DownloadCandidate)` 推导公开 JSON schema。内部加入带默认值的字段，不改变当前有效 FF 请求是否可读。

## 写域

只允许：`src/company_wiki/source_catalog/transcript_import_cli.py`、与本 decoder 直接相邻的纯 wire helper（若确实需要）、`tests/contract/test_transcript_import_cli_e2e.py` 中属于此合同的测试和静态便携 wire fixtures。禁止改 FF 生产 emitter/worker、source acquisition/write path、ET、其它 CWP 契约或 `integration/` runner。

## 先写行为测试

1. RED 先固定当前 FF 真实输出形状为独立 literal JSON fixture；不能用同一个 CWP dataclass `asdict`/`to_dict` 在运行时制造预期。
2. 该 wire 映射至当前 SourceRequest/DownloadCandidate，并通过真实 scratch catalog 进口路径直到 CWP writer/verified read；原 bytes/hash/身份/期次/as-of/预算均保持 owner 校验。
3. 给内部 model 派生测试子类增加私有/default field：相同公共 fixture 仍解码。改变公共 wire 核心 identity/source hash/period、错误类型和缺必需字段仍按清晰错误拒绝。
4. 重复键、NaN、非 UTF-8 和真的超 envelope/resource limit 保留当前有效处理；此包不移除这些实际合同检查。

## 通过标准

协议只由版本化 wire 字段与显式 project-to-owner mapping 控制；不能因内部 refactor 改变 wire，也不能放松真实身份/原文校验。独立审查 agent 必须检查 FF literal fixture 独立性、内部默认字段演进和写入后真实验证；缺陷全修后交 ROOT。

handoff.md 给出 `REQUEST_SCHEMA`、字面 fixture、确切测试命令、写入临时目录恢复、commit/独审及需 ROOT 做的 FF→ET→CWP 组合步骤。不得触碰生产公司目录/原件/配置。

