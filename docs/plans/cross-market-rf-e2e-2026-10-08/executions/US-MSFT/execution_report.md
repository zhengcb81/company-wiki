# US-MSFT 执行交接

## 状态：PARTIAL；正式模型技术校验通过，供应链端到端未闭环

唯一研究目录见 manifest.output_root。v1 input、正式forecast JSON、同源MD、immutable snapshot已冻结；不写 CWP canonical研究state，不改共享代码/配置/Git，不改Dayu。独立审查尚未开始。

## 实际完成

- 按安装RF技能调用source_preparation，经过FF/CWP复用FY2024和FY2025；SourceRef v2实读FY2025 SEC HTML的8158067字节并SHA匹配。原manifest未知值保留，read_at是真正读时。
- MAIN修复schema2包络、旧retrieved_at校验及mixed年收入合同后重跑成功。初始失败原日志留存。最终运行文件SHA见runtime_hashes_final.json。
- 真实打开官方完整电话会、最新release、metrics、22张FY27重分类presentation、战略和重大公告、AWS独立category benchmark。最新新口径和旧季度口径有逐项说明，不把旧三个segment与新两组混用。
- 八条官方重述收入流核对两年；公司总额三年。运行三年三情景、九维、四因果根及反证、八敏感性、低置信度；所有增长是明确analyst assumption。
- 真正运行template builder、lint、hash --check、validate-only、forecast、strong input-required、同JSON render、独立算术、snapshot及拒绝重复覆盖。无未来actuals可回测，无伪造实绩。

## 未完成且不能冒称成功

1. FY2026已发布原年报真实经FF→CWP ensure下载失败，尚无downloaded_new receipt。失败stderr见manifest.defects；不能以官网辅助capture代替这条链。重复新下载零下载测试因此未完成。
2. FF companion不能声称已调度成功。独立ET exact FMP discovery不支持、fetch返回套餐权限限制。电话会HTML是官方阅读来源，不是ET原语言TXT集成成功。
3. CWP生产叙述链未处理SEC HTML；临时BS4文件明确temporary_only，未称Worker摘要/切片已跑。
4. 数值target ledger结构green，但完整定性管理目标在旁表；季度/constant currency不能强行年化。最新年报not_available实际是acquisition_failed，不能解读成未发布。独立审查应单列这些语义差距。

## 复核入口

从manifest→skill_step_matrix→commands/index.jsonl/processes→facts/communication→TEMP frozen inputs/outputs依次复核。formal_validation只证明结构/哈希/重算，TRUST_BOUNDARY明确无host signer、经济假设和来源搜索仍需独立审核。不要因模型green把供应链或目标语义标PASS。

## 费用、配置、清理

无外部LLM调用、无翻译、无付费升级。FMP密钥仅从既有配置继承，不记录值。下载预算40MiB/180s/$0未放宽。REVENUE_PUBLICATION_REGISTRY仅本进程指向独立TEMP，ET工具同样仅请求进程绑定。未清理审查所需TEMP；待MAIN验收后再按精确owned清单清理，不触碰原件。
