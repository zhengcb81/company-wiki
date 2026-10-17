# DU11 live runner 源码交ROOT独审（尚不冒称独审完成）

状态：IMPLEMENTED_TESTED_AWAITING_ROOT_INDEPENDENT_REVIEW。未commit/push；ROOT继续单独审查源/测试，发现问题再修。三源文件冻结SHA在source-freeze.json，最终集中9PASS/0SKIP、60.51秒，前后SHA完全相同。最终Ruff三文件PASS。母账保持599590tokens/385113µUSD，历史unknown7保留；8个真实prepared原件/gold/config指纹逐字/size/mtime最终仍一致。本包0外部POST/0收费/0密钥读取。

新增--source-mode registered_readonly --source-catalog-config <当前真实配置>，复用加载出的所有actual roots/adapter/route，仅catalog_dir移owned Temp。源owner resolve_source_location定位显式original，再register_sources只登记单relative path，query_local/open_version返回真实SourceRef/manifest；不复制原件、不写生产DB、不回填metadata、不编URL/period/身份。公共元数据不足或不一致明确NOT_RUN0POST，交ROOT在原source责任层处理。

新增--selector-versions0.9.0；默认仍0.9→0.8。single输出comparison_scope明确single_selector_no_paired_improvement_claim；exactRef不谎称旧LATEST，same/cross0POST断言保持。付费仍原purpose=narrative配置、BudgetedNarrativeCaller、Store reservations与同一母账，没有新模型/费用客户端或许可链。

准确新主线命令在live_acceptance_plan既有参数后追加：

```text
--source-mode registered_readonly --source-catalog-config C:/Users/郑曾波/Projects/company-wiki/config/source_catalog.yaml --selector-versions 0.9.0
```

完整入口仍tools/document_understanding_benchmark/phase_c_runner.py；需显式--mode live --sample cn-h1|hk-annual|us-10k --metadata <既有narrative-direct revision> --usage-ledger <同一live/usage.jsonl> --output <全新owned收据路径> --consumer-projects C:/Users/郑曾波/Projects --reading-model-projection reading-model-input/4。源metadata缺口不能用旧copy-import的descriptor回填隐去；发生NOT_RUN时不付费，不能冒称三样本通过。

最终测试细节：实际source owner读取/登记/实读、仅单group无旁路scan，rawcopy函数被测试禁止，原资料树/config/源DB全文件清单及SHA/mtime不变；metadata gapNOT_RUN0POST；坏SHA/外根拒绝；默认pair/single参数；母账native settlement去重与unknown7；注册SourceRef进入真实BatchRequest且在模型CLI边界主动停住（故那个反控的内部outcome正确为FAIL，没有伪造完整摘要）；单0.9原configured loopback实际1个本机POST、same/cross0新增POST/publicexact/read/清理通过。不会把分层测试说成挂载真实供应商全链已通过。真实三供应商/深页质量留ROOTC。

历史RED/失败未删：red-receipt.json是首4个功能接口缺失RED；first-concentrated-junit.xml是7PASS/1纯fixture错误，测试给live-shaped请求传http127地址但未允许localHTTP，原HTTPS检查正确拦住。改测试为永不调用的https://model.fixture.invalid，不动正式检查，受影响8PASS23.35s，最终冻结9PASS60.51s。最终保存test exit0、XML/log后，外层可选stdout echo遇WindowsGBK编码错误（wrapper exit1）；不把它算测试失败、不重跑已绿节点，全部实际XML/原日志/源SHA已落盘。

真停止/outbox恢复、原件篡改拒绝沿既有独立integration案例（详live_acceptance_plan），本卡不重复恢复管理器。独立agent复审通过后由ROOT统一并线/推送/母PWF更新，作者STOP。
