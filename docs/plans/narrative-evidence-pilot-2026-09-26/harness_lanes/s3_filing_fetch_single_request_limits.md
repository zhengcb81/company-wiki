# FF-S3 独立任务：一请求、实际限额与安装面简化

## 启动状态与唯一所有权

**现在可以启动**，仓内实现不等 N4。root 会补 CWP producer 三个限额参数并最终集成；本卡不准把 producer pending 写成端到端通过。

唯一写入工作目录：`C:\Users\郑曾波\Projects\filing-fetch-s3-limits`；只写该 FF worktree 的代码、测试和局部 PWF。company-wiki、ET、RF、StockWiki、IQS、全局 `.agents/.codex` 技能目录只读。root 负责全局安装和跨仓集成。

真实基线：FF `origin/main@c47c397c4d93979d8a7defbe026eff9e9edf0e6d`；干净交付 checkout 在 `C:\Users\郑曾波\AppData\Local\Temp\ff-source-reader-v2-20260927`。常用 `Projects\filing-fetch` 是旧 `fcap@d35b6f5`，存在未跟踪 `config/FMP_API_KEY.txt`，不从它的工作区复制/提交凭证。最新 refs 若变化，先核与本基线的 diff 与计划；不要 reset 工作树。

建议从已发布 commit 建分支 `codex/ff-s3-single-request-limits`、worktree 到唯一工作目录。旧 integration/companion 只读，不重复合并已经交付的工作。工作目录已存在时先检查用途和 dirty，再复用同线目录。Git common-dir 必要元数据修改属于本仓；不清理别线工作树。

在自己目录选定 `.planning/s3-ff-single-request-limits-20261003/` 为局部 PWF，含 task_plan/findings/progress。不要覆盖 inherited active plan 或 root CWP 的三入口。只读参考本卡和本仓当前 AGENTS/已交付计划；旧审批/签收要求不能恢复成新门。

## 目标与已核缺口

当前代码已实现 SourceRef v2、ET `/2` companion、CWP canonical import；已安装 fetch 脚本与 c47c397 同字节。本包改实际行为和过期说明，不重做这条链。

1. `scripts/filing_contracts.py` 的 v2 `acquisition_limits` 只校验；`scripts/fetch_filing.py:_command_arguments` 和 `_resolve_source_ref_v2` 没把限额传给执行层，CLI 使用全局900秒而忽略请求60秒。
2. CLI 推导一次 allow_download，库 `resolve_filing` 仍有第二个默认 False 布尔，导致同一请求在库/CLI分化。
3. repo/installed SKILL 仍写 v1.4.0/schema1.1 和旧双门；已交付代码支持 v2，用户例子应更新。
4. `sync_installs_b3.py` 自动同步/manifest 安装面过宽：递归 config 有机会纳入本地 key，tests 也会复制多份。安装必须是明确动作，不能 pre-push 顺手改全局技能。

成功结果：一个明确下载意图、同请求库/CLI一致、byte/time/cost真正传递并有界执行、v2路径清楚、v1仅现有调用薄兼容、安装只含所需文件。

## 冻结接口（不猜别仓实现）

### CWP 来源

- 现有 v2 来源/SourceRef `2.0`、响应字段与 hash/期间/as-of继续使用真实 serializer。业务输入不得包含 raw root/path。
- acquisition_limits EXACT：`max_bytes` 正整数/非bool，`timeout_seconds` 正有限 int/float/非bool，`max_cost_usd` 非负十进制字符串/当前最多两位小数。reuse_only无额度；本包不静默变金额格式/来源版本。
- **新 CWP CLI 参数，root负责实现**：`--max-download-bytes <max_bytes>`、`--max-download-seconds <timeout_seconds>`、`--max-download-cost-usd <max_cost_usd>`，用于 ensure/close-gap。身份 Request ID 不掺资源额度。
- FF 时间取剩余全局 deadline、请求期限、配置期限的最小值；实际子进程/pipe读取共用 deadline 和输出字节 cap，超时回收自己创建的进程/后代，不 kill 无关进程。
- producer 不认识三参数时具名不支持/失败，不能去掉参数再发、回退v1绕过额度或伪报采集完成。root实现前该正式接口测试可记录 pending；你的离线参数捕获/超时测试必须通过且不 skip。

### ET companion

- `EARNINGS_TRANSCRIPTS_TOOL` 显式工具位置；`--request-stdin --include-source-payload`。
- `earnings-transcript-request/1` 输入、现行 `/2`输出；CWP import `/2`请求、`/3`响应。不改这些字段/版本。
- FY/Q唯一时才取电话会；全年不推Q4。原语言、不翻译；财报与电话会独立结果，缺配置/不可用provider具名降级。ET-S3是另一目录owner，你不写ET。

## 实施步骤（一个仓内大节点）

1. 核本仓基线、当前用户入口和安装调用者。保 v1真实golden/现行v2/ET `/2`；先写失败行为测试：同请求库/CLI单意图一致，三额度到argv，短deadline超时，未知caps不能绕过，安装manifest排除假凭证/tests。
2. 将一次意图和limits沿现有 request→resolve→command 路径贯通；共用实际执行器。v2作为推荐/正常来源入口；明确v1请求继续薄兼容，不并存两套root授权/资格检查。
3. 加有界子进程输出与剩余deadline；沿现有ET transport通用能力复用，避免再造第二后台pipe线程。静态错误不回显stderr正文、路径、key；不能吞所有失败为not_found。
4. 修改 installer：纯显式命令安装，pre-push不触发写全局；manifest只含运行必需 scripts/技能文档/明确公开config模板。exclude凭证/本地.env/测试/缓存/运行日志。用**假**FMP_API_KEY文件验证排除，不读取真实文件。global安装只交命令给root。
5. 更新本仓 SKILL/README：v2推荐例子、明确一次采集请求、限额、FY/Q、ET工具配置和失败分离。删失效的RequestPlan手工签收/二次下载许可说明；能力限制如实保留。
6. 一次相关测试包和独立CLI E2E通过后，提交/push自己的codex分支；输出下述交接，不自行合main/安装/启动无限worker。

不要新增签名、人工授权文件、逐候选review receipt、覆盖率或场景数门。真实 SHA/身份/期间、路径归属、实际限额和幂等仍分别由所属层负责。

## 独立测试包

- 复用现有 `test_ff_v2_contract`、`test_source_ref_v2*`、`test_transcript_companion*` 与旧v1回归。开工先 `rg --files tests` 查实际名，不复制旧卡猜测路径。
- 新测试：真 FF CLI→本地 fake child CLI，捕获实际argv/stdin；三参数/min deadline/输出cap/无隐式重试/超时有界回收；不 mock 掉 FF 整体 resolve 函数。
- 真 ET/CWP现行边界用隔离 fixture验证时期/语言/hash和已有复用；不把 fake CLI 声称是 CWP 限额已执行。新producer拒未知参数是显式事实，不强行让红测试变绿。
- installer 用本仓专属临时目标和假key，只比安装面/内容；不写用户 `.agents/.codex`。测试临时根由同OS账号创建/执行/finally清理；测试前不存在的原始副本必须退出删除，keep文件/目录基线原样。
- 全程无live FMP、无LLM、无真实key读取、无生产CWP配置/库写入。费用是0；成功mock只证明协议。

测试频率：RED先行，完成后一次责任包 GREEN；只对确切红灯重跑相关项。不要每个helper独立审查/全仓coverage/整套旧计划重验。

## 输出给 root（普通交接，不是授权合同）

本仓 `docs/implementation/s3-ff-limits-handoff.md` 与小型 `fixtures/goldens/s3_ff/`（若现有golden目录不同则复用）；PWF记录实际路径。报告含：base/branch/head、修改清单、v1/v2真实golden及版本、limits→argv表、ET/CWP实际调用0/1表、错误/退出码、测试命令/结果/临时根恢复、明确producer pending、显式安装命令/manifest。

不要提交密钥、下载原件、每次执行全文日志或备份。发回 branch/commit 和报告路径。root核diff和相关测试，补producer后做一次限额跨仓E2E、合main/统一安装；未合入保持分支交付状态。
