# 跨仓正常结果被拒 — 当前实链只读复核

**确认5个同根残留组；此前保留理由经反例重新验证后被推翻，不能按名称保留。** 本报告冻结修复前证据，不是修复验收。342个allowlisted runtime Python做SHA/AST清单，重点公有调用链详读；不是342文件逐行全功能保证。

|项|真实拒绝与caller|实际结果/责任|
|---|---|---|
|CR-01 RF/invest公式500|derived参数/period-flow/投资参数验证→各算术owner|x0+0=3.5；仅合法内部空白变505chars，AST同为6nodes，两公有入口却too long。字符数不是运算工作。|
|CR-02 Stock原文receipt256KiB|run_source_read_v2→VerifiedOpenTransport→真实bounded child|同配置stdout1024、原文2B；合法receipt1414B成功，271415B（合法大title）stderr_over_limit；两个bundle parser均接受，配置无receipt预算可调。|
|CR-03 Stock叙述表示/诊断|read_narrative→load_verified_view|gold4042B通过；只改optional review为unavailable→review_fields；合法schema4context通过，加当前optional source_processing_complete=False→reading_context_fields；显式2MiB stdout预算直接reader_config_invalid。|
|CR-04 ET并行固定provider/结果帽|fetch_transcript→_operation_session→_read_fmp_payload|显式20MiB response预算；同一JSON125B成功，合法空白扩17MiB wrapper在16MiB+64KiB读时失败，未用完真实预算。HTML/opt-in同owner另有静态固定帽。|
|CR-05 ET可选sidecar|verify_stored_original→scraper._finalize_existing|同TXT/SHA/公司期次：无sidecar可legacy_unverified复用；仅添坏JSON→receipt_invalid/output_conflict。真实bodySHA不符负控仍receipt_mismatch，必须区分。|

## 共用整改方向

1. 算术：去字符许可，支持真长式和等价空白；只在单一算术owner承担实际parse/AST/evaluation工作预算。保未知变量、finite、除零、幂范围、非法节点/经济重算，不strip空白掩500，也不新增批准flag或RF↔invest循环依赖。
2. Stock：实际stdout/timeout/进程树工作界保留，但receipt/combined预算应可由caller控制，不能另设不可提高常量顶帽；叙述wire正确保核心引用/partition/identity/partial，新诊断不作许可证。groups512/views2、config/request/receipt16KiB、body1.31MiB属于同owner静态邻域，需ROOT用定点控制统一处理，未冒每一条都已动态复现。
3. ET：显式response预算沿既有唯一meter，不再被FMP/HTML/opt-in常量min；省略才用合理默认。坏非权威sidecar只降级未知/legacy，不能比无sidecar更糟；真正source/body hash/pin矛盾仍拒，原TXT绝不覆盖、不重抓绕冲突。

## 当前未发现需恢复的人为许可

- RF/invest当前不要求全局registry/host_signed才可用。无可信签名诚实unattested，strong input/economic/hash仍验；不可伪称signed。
- FF当前无逐材料人工许可/旧双download门；root配置64KiB和localprep大小拒绝已修，optional附注不抹主状态。本次没有新证据证明FF32MiB实际读取预算拒绝预算内正常成功资料，故不凭常量凑问题。
- ET默认不翻译，只有显式--translate才创建Translator；原文API不启动LLM。不读真实key，也未调用外部供应商。download_authorized为请求网络意图，非人审文件。
- 原件SHA/公司/期次/as-of与输入输出重算各自保护实际信任边界；同事务VerifiedOriginalRead已复用。保留依据是错源/错期/改字节会错误，不是它名为contract。

## 范围和版本诚实

SourceExport16MiB、PaidResponse262144、run binding262144已闭，不重复算发现。StockWiki当前9e8e308本地主线，历史无remote。RF/FF/invest/ET HEAD与342源码SHA及RF4WIP前后SHA见JSON。StockWiki quick_scan_* IQS集成仅静态出现；没有执行/干预IQS或其他owner工区，不据此签全StockWiki不存在任何权限。

所有公有反例只用技术golden和合成资料；Stock原文probe真的运行了本地子进程，叙述probe只回放transport字节而没有mock validator。ET HTTP是fakeSession、假测试key，不是网络。原件/实际key/模型/下载/收费均0。raw结果和可复现源码/hash保在JSON；自有tmp只含合成TXT/receipt/config，清理收据随后写JSON。

ROOT已授权先冻结本报告，再由本作者窄修RF/invest算术及ET，分别另交crossrepo-repair和et-repair供最终集中独审；Stock由ROOT处理，本作者不写Stock。主PWF/Git/CI/hooks/config/全局技能不动。

清理完成：自有tmp/gcf-b2e61a共9文件548149逻辑B，逐文件SHA保JSON，核绝对路径与无reparse后原生删除，结束absent；RF4份WIP前后完全相同。
