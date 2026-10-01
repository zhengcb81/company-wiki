# 跨线收尾盘点（2026-10-01）

本页补充 Phase 33；事实取自当前 Git、各仓 PWF 和已交付测试收据。本次收尾计划与发布；仅修发布检查发现的两处复杂度超限与 source-workflow/legacy writer 误分类，不启动新功能。较早施工表为历史记录，不能据此重复派发。

## 当前进展

| 线 | 当前成果 | 尚未完成 / 恢复后的动作 |
|---|---|---|
| company-wiki | E-B 已并入 master；相关回归 349 passed/2 skipped，SourceExport CLI 6 passed，真实字节/transcript E2E 11 passed。叙述三阶段、独立 artifact store 和 Worker 恢复已实现。 | G-0 剩余真实读取/locator 证据，G-A FMP admission，独立 pathless NarrativeBundle export/read 与 G-C 跨仓消费，G-D 派生清理。生产 Worker paused/default-off。 |
| revenue-forecast | rf-impl main `3e03ce83` 已含 fcap 全部已提交历史；SourceRef reader、自动发布检查及缺 hash 诊断已提交。缺 hash 更新有 33 项定向测试，不声称整仓测试通过。 | dirty fcap 仍不可整树清理；旧 reader 原型只择要复用。FF envelope 和 selected narrative 消费等待正式生产者合同。 |
| StockWiki | master `b4f3846`；W01/W02/W03、SourceExport reader、工程门简化、W04/MIC 补强已本地合入。合并后整仓 686 passed；基本 G-B 已通过。 | 本仓卡验收与 IQS full G2b 分开：生产 preview/verified、多挂牌、AnalysisSubject、历史区间仍依 IQS owner 交付跟踪。无 Git remote，不擅自创建远端。 |
| earnings-transcripts | main `4924d57`；原语言 `/2`、精确 FY/Q、单请求下载意图、默认禁用 Motley、producer golden 已交付；离线 118 passed/2 deselected。 | FMP 真请求先前为 402；真实 200 权益未证实。FF→ET→CWP 仍未汇合。已有本地工具笔记和旧评测保留。 |
| filing-fetch | fcap `d35b6f5` 与已观测 origin/main 一致；SourceRef integration `5532ce0`、companion `29085f7` 两个干净 worktree 已有本仓成果。 | 同一 owner 合并四个重叠核心路径，更新到当前 CWP CLI；本地 main ref 落后 39。未验收汇合的支线不冒充主线发布。密钥不读取、不提交。 |
| invest-quick-scan | owner 已提交跨项目审计 `56ff421`；先前步骤 1–4 与 provisional G2b 切片完成，StockWiki→IQS 最新聚焦包 113 passed。 | owner 新增 V02/scoring 的四个未跟踪文件；保留不提交。full G2b 与 QA-04/SW-IDENT handoff 收尾仍 partial，DWA 跟进由现有 owner 管理。无 Git remote。 |

## 必须调整的计划内容

1. 撤销仍可派发 W04 或继续实施 E-B 的旧“当前”段落；这些实现已验收并线。既有收据保留，避免重复大测试。
2. FMP 接入仍是 CWP 的真实缺口：当前 importer exact-key 只收 24 字段，MIME 仅 HTML/TXT；ET FMP 有 26 字段、JSON 原件及带 symbol/year/quarter 的 URL。不能用 Motley fake fixture 的通过推断 FMP 可入库。
3. FMP 日期要分层：`call_date` 不等于 publication；golden 的 `publication_date=null`、`as_of_cutoff_verified=false` 必须保留。不制造公开日期；CWP 来源发现/存储与 RF 的历史 as-of 使用资格分别负责。恢复后先定义候选日期和 unknown publication 的正式语义，再用 producer golden 写 RED。
4. JSON 正文解析必须保留原始 JSON 字节，正确回放字符串转义、UTF-8 和 locator，确定抽取版本/旧 lineage 兼容；核验 ET canonical text hash 与本地 deterministic extraction。不把 JSON 当 HTML 或把重排后的 JSON 当原件。
5. IQS 身份边界按现有正式 DTO/golden 跟踪，不再写“DTO 不存在”；full G2b 不因 W04 单仓验收而自动完成。IQS 当前活动工作不交给第二个 writer。

FMP 大节点测试：真实 ET serializer golden→CWP import CLI→catalog→verified read→正文 locator 回放；重复导入零重复 raw；错误 SHA/公司/FYQ/危险 URL/JSON 截断与转义错误具名失败；publication 未知不能用于已验证历史 cutoff。隔离测试根前后恢复，原件 SHA 不变。只在接口变更后跑受影响合同和一次 G-A 汇合，不重复每个小节点整仓验收。

## 顺序和可改进处

保持原依赖顺序：G-0/G-A → CWP 独立 NarrativeBundle 传输 → RF/StockWiki 各自薄 adapter → G-C → G-D 精确派生清理。RF/StockWiki 可在接口冻结后各仓并行施工；FF 两支线须由单 owner 顺序整合。

已释放 37.630 GiB 是历史退役收据，不等于全部空间清理完成。真实 P2 replay 吞吐只改善约 6.3%、内存高约 23.5%，且锁等待未测；生产并发继续关闭，不为速度目标强开多进程。无新证据要求改变整体架构或增加 provider。

## 发布与暂停收据

- ET 已正常推送 `1aa9111..4924d57` 到 origin/main；未跟踪文件未纳入。
- RF 首次 push 被既有检查拒绝：稀疏检出遗漏已跟踪 `e2e/`，Ruff E902。仅补齐 e2e/.github，保留原字节；后续 Ruff/编译/host/mypy 通过，但 historical current_triplet ancestry 两项失败，RF 未推送。根因与恢复时的 TDD 修复范围见 progress.md，不 bypass。
- CWP 已正常推送 `f39bd5a..d6d33b8`，完整 pre-push 六门 GREEN、远端 SHA 一致。Actions run 36936780795 核对时仍 in_progress；本页发布收据作为后续 docs 提交正常推送，最终 ref 可由 origin/master 核对。StockWiki/IQS 无远端；FF 待汇合支线不在本次发布范围。
- 本次仅将 transcript importer 入口校验与工具合同的 byte cap 校验抽为 helper，保留错误顺序和原有行为；并修正六项来源工具的 legacy 分类（20 passed）；没有改生产配置或原始文档；不运行空间清理/生产 Worker。用户要求收尾后暂停，恢复后从上述剩余节点继续。

**远端 CI 后续覆盖：**CWP 已同步到 7c80031；d6d33b8 的 Actions 36936780795 已结束失败，Python 3.11/3.12/3.13 均 Unit tests exit 1，公开 annotations 未给具体用例。最新 docs run 当时 queued。本地发布门全绿不代表远端 full suite 已通过，恢复时先取日志定位，不把 runner/action 提示当根因。暂停状态不变。
