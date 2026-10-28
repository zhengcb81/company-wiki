# C3 下一次正式验证：恢复提示

**暂不执行。用户要求手头完成后暂停。** 恢复后，语义候选及observer独审绿，再用既有runner只做一次HK开发attempt，不重跑0.8/历史整批，也不先重复全源Docling。本次仅查代码、既有缓存/收据与只读母账，没有PDF/模型/下载/生产测试。

## 实际任务检查

精确旧v2缓存 `.planning/c3-20261026/hk-v2-source-check/diagnosis.json.gz` 的group[34]经真实compiler成为 **t35**：p13 paragraphs9–12四个support，p13 paragraph1标题为context；完整part/shared-ref可解码回同一原组。行业云来源及首发任务物理闭合成立，不等于完整gold oracle或模型摘要已过；研发/展望仍须新语义材料验证。

已实证旧observer的repair空洞：真实行业云第一条anchor仅作内存control，full view支持；只发不含该anchor的t1，旧oracle仍借全selected报支持。未改gold。现两文件窄修明确：`full_selection.scope=full_selected_source_availability`；`sent_tasks.scope=source_support_in_current_request_tasks`按实际task闭合、记录supported_task_keys/not_sent_ids，claim coverage始终not_evaluated。**首发实际sent任务缺gold先于reservation拒费；repair如实报告未发送项，不要求已完成全部gold重现，也不把其算本次覆盖。** 新6RED→新6+原4共10P；ROOT另做独审，见observer-task-gold/handoff.md/json。

冻结完整行业云quote另有数字|CJK行边界oracle误插空格问题，ROOT已委派另一owner修；不改gold或生产来源规则。不应拿旧缓存冒充新语义版本通过证据。

## 准确准备与命令

工作目录 `C:\Users\郑曾波\Projects\company-wiki`。恢复后由ROOT创建新准备revision `.planning/c3-20261026/prepared-hk-development-runtime-v2.json`：继承旧prepared-hk-development.json的protected fingerprints/gold/source/mother baseline/预算，仅更新revision和runtime来源说明，**不改旧文件**。

metadata的c3_reading_runtime与实际环境均指 `.planning/c3-20261026/pdf-env/runtime-4g-v2.json`，raw SHA `077654bd7eeb016d57667ec3560e602f4de480a74c2cbb236fc1100dda942fd6`。实际owner只读取 **COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG** 环境变量；metadata不会自动设它。旧v1/d843…不用于新attempt；核实际recipe/config SHA与v2一致（本地Docling2.96.0、120秒/3页/4GiB，无下载）。

在正常获批宿主shell中，设ROOT独有短TEMP/TMP/TMPDIR/SQLITE_TMPDIR并设上述v2环境，然后执行下面唯一入口；结束恢复环境和scratch。新metadata/output本次尚未创建，output必须不存在，不覆盖hk-formal-v1。

```powershell
& C:\Miniconda\python.exe -B -X utf8 tools/document_understanding_benchmark/phase_c_runner.py `
  --mode live `
  --sample c3-hk-kingsoft-h1-2025 `
  --metadata .planning/c3-20261026/prepared-hk-development-runtime-v2.json `
  --usage-ledger .planning/shared-reading-production/live/usage.jsonl `
  --output .planning/c3-20261026/hk-formal-v2 `
  --source-mode registered_readonly `
  --source-catalog-config config/source_catalog.yaml `
  --selector-versions 0.9.0 `
  --reading-model-projection reading-model-input/4 `
  --consumer-projects C:\Users\郑曾波\Projects `
  --activation-recovery
```

原件SHA `4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36`，3,396,644B；HK03896/2025H1/zh、开发样本。冻结gold为本节点hk-development-gold.json。Config.load的现有mimo narrative配置必须与metadata逐字段相同：mimo-v2.6-flash、token-plan-cn.xiaomimimo.com/v1/chat/completions、max_completion_tokens8192/temperature1/thinking disabled；只使用现有MIMO_API_KEY，勿输出密钥或造另一配置。

## 费用与恢复

只读现有mother_totals：**1,783,378 tokens/$0.724836**；新ledger unknown_count6，历史unknown7及FXhold仍保留。实际配置上限10M/$20；旧metadata里2M是历史字段，runner使用当前load_budget_policy。每次POST前重算，不重置账本、不退款unknown、不另加许可。

单paid request保留200k tokens/$1/300秒，transport120秒、请求/响应262144B，final2MiB/persistent64MiB/scratch32MiB；112span/16M work不增。300秒是request预算，后续激活/回读/consumer有原来的独立CLI时间界限，不能把整个harness误当300秒后强杀。

旧phaseC-090-777179bc3756有完整PRE_RESERVATION_BLOCKED/PHASE_C_GOLD_SUPPORT_MISSING证据：reserved=false、POST0、native_usage空、母账无增，temp已删除，不能恢复旧AUTO。新语义通过后可发新UUID；保留旧失败收据。新attempt若已POST/unknown则不换目录盲重发。

--activation-recovery在同一owned AUTO/run/request/workdir先制造activation_pending，先存native journal/母账，再凭known usage+paid-response/request身份解除hold并forbid_post恢复；attempt/response/final generation/收费须不变。之后同run重启与跨run缓存均0POST/无新增native charge。失败须保留named原因/hold；不要以新请求代替恢复。

finalization若需重对账，只用现有无模型入口：`C:/Miniconda/python.exe -B -X utf8 tools/document_understanding_benchmark/phase_c_runner.py --mode live --output .planning/c3-20261026/hk-formal-v2 --usage-ledger .planning/shared-reading-production/live/usage.jsonl --reconcile-run-id <实际收据run_id>`。它只将已有native journal重放入同母账，不重建已清理AUTO或重发模型。

## 一次attempt验收位置

1. preparation/harness/原件/gold/config/实际reader recipe与模型身份一致；pre_reservation_material的首发sent_tasks三required闭合，缺口先于费用命名拒绝。
2. 正式响应与真实support引用：行业云人民币1,340.4/1,245.4百万元、7.6%及IT需求/方案复制原因；研发420.5百万元属报告期、1,094人属2025-06-30时点；下半年AI是计划。不可借23.0%、620人或把计划写实际。合法协议/引用不代表语义真，交独立内容审查。
3. activation恢复、已完成run重启、跨run cache、完整exact Ref公开回读：零额外POST，native费用与final material/response身份稳定。
4. --consumer-projects对应现有filing-fetch和revenue-forecast sibling入口，FF reuse_only downloads0；RF source+narrative与RF narrative消费同exact Ref/full context/evidence/summary，offline禁止网络。省略参数只会NOT_RUN。**此runner证明公共准备/读取消费，不运行RF预测模型，不能冒称实际RF模型已引用。**
5. mother-after/unknown journal、protected/sentinel不变、temporary_lake_removed=true；只留小收据/压缩input及返回final，不留密钥、reasoning或重复原件。

ROOT统一更新PWF暂停交接；本agent完成observer交接与本提示即停止，不启动任何真实attempt。
