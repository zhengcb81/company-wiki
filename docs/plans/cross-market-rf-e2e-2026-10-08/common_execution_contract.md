# 独立执行接口（MAIN → 执行 agent → 独立审查）

## 固定信息与目录

- as_of_date：2026-10-08。真实未来预测，不使用虚构未来业绩做回测。
- 三公司：CN 中微公司 688012；HK 腾讯 00700；US Microsoft MSFT。CN 年报本地复用；HK 年报复用并真实获取缺失半年报；US 先复用 FY2025、再经 Dayu 获取缺失 FY2026/最近可用季报。若官方未发布必须记录，不把“截至日之后”文档混入。
- MAIN 唯一维护共享 PWF。执行只写 `executions/{CN-688012|HK-00700|US-MSFT}/`。审查只写 `reviews/{company}/`。任何共享代码问题先报告 MAIN，不自行修改代码/配置/安装副本或 Git 提交。
- 预测 input/forecast/md/snapshot、临时解析文本和捕获原文只放 `$env:TEMP/cwp-rf-e2e-20261008/{company}/`（实际绝对路径在 manifest 中记录）。CWP 计划目录只留工程过程、哈希、引用与审计记录，不留正式研究 writer。
- 正常使用：RF `C:/Users/郑曾波/.agents/skills/revenue-forecast`，FF 同级 filing-fetch；CWP catalog config 为本仓 config/source_catalog.yaml。核对实际 installed 与 repo 文件 SHA/版本，发现漂移报告，不绕过安装配置。
- Python stdout 明确 UTF-8。网络/邻仓读取用正常 require_escalated，不改权限。Dayu 是外部 provider，只调用不改代码。邻仓 owner WIP 一律保持。

## 必须执行与记录

1. 阅读 RF SKILL 与它要求的 data-governance/compliance/research/model/input/output 等引用；建 `skill_step_matrix.json` 覆盖步骤 0、1、1A、1B、2、3、4、5、6、6A、7、8、9、10、11。每步对应具体产物/命令/原文。
2. 首先调用实际 RF `scripts/source_preparation.py --company-wiki-catalog-config ...`，由它真实调用 FF 和 CWP；不能用单独下载绕过这条链，不能手拼 producer 结果。先 reuse_only/只读，缺失才显式 fetch_if_missing / allow-download。
3. 下载每请求最高 40MiB、180 秒、0 美元 provider 费用；不要循环全公司历史下载。全部原件最高 250MiB。至少保存一条真正 downloaded_new 的 receipt；失败也留原错误。成功后相同请求再跑验证零下载复用、SHA 不变。
4. CN 工具 StockInfoDLSimple/v2-clean-rewrite；HK/US 工具 Dayu；电话会 earnings-transcripts 原语言 TXT，配置/免费能力不足时明确记录，不强制 FMP 付费，不假装网页替代验证了 ET。FF companion 确切 FY/Q，独立结果，provider 不可用不能阻止财报结果。
5. CWP 通过 SourceRef v2 打开真实 raw bytes。记录 source/document ID、SHA、size、mime、company/period/pubdate、root provenance 与派生版本。检查 CWP 已有 narrative/parse 或确定性选段；没有实际处理应明确写“未跑”，不自称 Worker 摘要已完成。选段及解析只为本批，不重启全库常驻转换。
6. 每条财务/经营事实直接核对官方原文完整上下文；公开网页需 web 工具真实打开并保存引用/摘录，不能只用搜索摘要。事实和 analyst assumption 分开；日期未知不能冒填，不能手工改 manifest 凑通过。
7. 模型覆盖各经济业务，至少两历史年度对账，低/中/高三年（若选其他期限须说明）、九维覆盖、六类官方沟通及管理目标、收入确认、因果驱动树、反证、敏感性、置信度；所有事实/假设有来源或明确 gap。
8. 真实运行 template/lint/hash/validate-only/forecast 输出、强 input-required 验证、render 与 immutable snapshot；保持失败尝试记录。不修改 runtime 来迁就 input；字段未知先查 schema，不能盲猜十轮。
9. 未来实际业绩未知只冻结，backtest evaluate 不适用；不得用生成的情景当实际数据。强签名/注册未启用保持真实 unattested，不伪造签名。

## 全程日志

全部关键 shell 命令通过同目录 `run_logged.py --log-dir <company>/commands --label ... --cwd ... --timeout ... -- <program> <args>`，保存 start/finish、退出码、完整非秘密 stdout/stderr、SHA；失败同样留档。大输出写文件，工具响应只显示摘要。

非 shell 的 web/阅读/模型动作，及时追加公司 `events.jsonl`：`timestamp_utc, agent_id, step, action, tool, input_summary, source_url, artifacts, outcome, error`。不可写密钥/环境变量内容。使用现有配置，默认无需额外付费 LLM；如确需外部调用先向 MAIN 报告剩余累计预算，不改 model/profile/温度等。

## 交接 manifest.json

`schema_version=1.0, company, market, security_id, agent_id, as_of_date, started_at, ended_at, skill_root, runtime_version, runtime_file_sha256, output_root, status (complete|blocked|partial), step_matrix_path, command_index, sources [{IDs,SHA,bytes,published_date,request_path,response_path,resolution_outcome,downloads,provider}], artifacts [{absolute_path,SHA,bytes,role}], facts_index_path, communication_coverage_path, defects, gaps, calls_and_cost, owned_cleanup, unchanged_originals`。

额外必须：`execution_report.md`、`fact_checks.json`（每条事实/参数/原文 locator/摘录/单位/日期/核对结论）、`skill_step_matrix.json`、`events.jsonl`。没有正式 validated forecast 的公司不得 status=complete。

## 独立审查成功标准

逐公司复查所有 step，不抽样替代用户要求。重跑正式强验证和独立算术；每条事实从原文重新读；核对 request→实际命令→response→raw→claim→parameter→result；检查失效缓存、目录穿透、错期间/身份、免费限额/真实 provider、未来数据、归因/目标口径、偷跑/漏跑、日志一致性。每项有实际 evidence，不把执行者自述当证据。输出 `review.json`/`review.md` 含 PASS/FAIL/NOT_APPLICABLE/BLOCKED，问题优先级、确切路径与可复现命令。审查 agent 不得自己修复后给自己签收。
