# ET：显式预算和本地原文复用根修（冻结交 ROOT 独审）

状态：**IMPLEMENTATION_FROZEN_PENDING_ROOT_INDEPENDENT_REVIEW**。这不是已发布或真实供应商验收结论。代码位于 canonical `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts`；7 个源文件、6 个测试文件，精确 SHA 见同名 JSON。未 commit、push 或同步全局副本。

## 修复的共因

1. **预算传播断裂**：已分配的实际响应字节/时间预算，在 FMP、HTML、列表、原始 payload、worker JSON 表示和 CLI supervisor 被独立固定上限再次缩小。现在用原有 BatchBudget 剩余量和请求实际额度计算读上限；显式更高额度不再被 16/10/2/24 MiB 或 60 秒常量否决。无显式 raw 额度时仍沿用默认；正整数类型、实际流读取、原文 canonical-body 额度、截止时间、worker 终止/回收及费用限制继续执行。没有第二计数器或新许可。
2. **可选旁注错误变成原文许可**：先验证原 TXT、头部身份、期间及实际 SHA；坏 JSON、UTF-8、旧/未知 schema、旁注 I/O/内存失败只产生诊断，健康原文按 `legacy_unverified` 复用，不重抓、不翻译、不改原文或旁注。解析出来的显式 ticker/期间/SHA/size/URL 冲突仍拒绝；真实正文腐坏不能借坏旁注放行。严格收据 parser 保持严格，不伪造 verified 或采集 provenance。

scraper 清单和只读 audit 输出可选诊断；正常已有原文不会因这些诊断触发模型或网络。FF 的调用者两处 min 由 ROOT 在 FF 独占闭包修复，本报告不修改 FF。其配置直接指向 canonical ET 工具，无 ET 全局技能部署任务。

## 实际证据

- 原 20 个新增用例先 17F/3P，其中一条 CLI 是缺 synthetic base_dir 的测试夹具错误；更正后单独重现真实 CLI 1F，修复后 20P/10.45s。
- 60 个现有相关用例通过，6.93s：真实身份/期间/哈希、原文复用、strict parser、响应/正文预算、worker 信封、截止时间与回收等。
- 旁注容量新增 2 个控制：1F/1P（MemoryError 冒泡）→2P/0.71s。
- 显式时间预算新增 11 个控制：API/list/真实 CLI→worker 120 秒额度先 3F/8P；最终 11P/1.29s。都是立即 fake HTTP 返回，没有等待 120 秒。0、bool、Infinity、NaN 均在 HTTP 前拒绝。
- 20+60+2+11 为分阶段增量证据，**没有冒称最后重跑整个 93 条**。新 metadata 用例曾把成功状态错写成 available，实际是 discovered；中间 1F 收据保留，只更正新夹具。
- 初次 Ruff 12 文件、最后变动的 5 文件均绿。没有模型、下载、真实凭证、生产原件、完整 ET/跨仓 CI 或全局安装。

旧固定帽 oracle 迁移为“合法完整结果通过、真实错误仍拒”，不删除用例：bad-sidecar strict parser/真 pin 冲突保持，旧 2 个 fake-hash 夹具改成真实绑定后再单独变异元数据；旧 monkeypatch worker size/provider default 不再伪造业务许可。完整旧 RED、中间失误和最终日志/JUnit 均在 JSON。

## 交接和清理

ROOT 应按同名 JSON 的 13 文件 manifest 做一次独立节点审查，再处理发布；数学 owner 已获另一独审 PASS，本轮不再改。RF 四份已知 WIP 以及最终数学 4 文件 SHA 保持原样；ET 其余 runtime 不变。原有未跟踪 `.workbuddy-ai/`、`eval_results.json` 不属于本任务，未读取内容或删除。

本任务 `company-wiki/tmp/et-r7-b29f1c` 初始 ABSENT，日志/收据归档后已按绝对路径、无 reparse 检查清理 159 个合成文件（95,964 逻辑字节），最终 ABSENT。真实原文/模型缓存删除 0。JSON 包含实际清理、Git HEAD/status、各 case identity 及 source-before/after。
