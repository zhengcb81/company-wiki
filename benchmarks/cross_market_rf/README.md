# 三家公司固定端到端回归套件

固定公司：中微 688012、腾讯 00700、微软 MSFT；信息日 2026-10-08。入口为 `tools/cross_market_suite/runner.py`。样本、单位、期间、目标和同行风险的 expected 来自这轮独立审查，不是从新运行结果生成。完整检查点在 [checkpoints.json](checkpoints.json)，固定 SHA 与事实在 [cases.json](cases.json)。

复现环境：Python 3.11+、Git，以及各项目现有运行/测试依赖；核心需 pytest、PyMuPDF、PyYAML、requests。可以使用已配置的项目环境；不要为了测试擅自更换生产模型或升级依赖。报告记录实际Python/commit，跨机器解析差异要如实对照，不重写固定原件或expected。

## 一次运行

从 company-wiki 根目录执行，PowerShell 示例（目录按实际机器改）：

```powershell
$projectsRoot = Split-Path (Get-Location).Path
python -B -m tools.cross_market_suite.runner run `
  --rf-root "$projectsRoot/revenue-forecast" `
  --ff-root "$projectsRoot/filing-fetch" `
  --et-root "$projectsRoot/earnings-transcripts/earnings-transcripts" `
  --delivery-root "$projectsRoot/revenue-forecast/output/cross-market-rf-e2e-2026-10-08" `
  --source-catalog-config "config/source_catalog.yaml" `
  --suite full --mode replay --output "tmp/rf-e2e-after-001.json"
```

输出 JSON + Markdown。退出码：0=检查全部通过或不适用，1=实际失败，2=PARTIAL（阻塞或没有运行的能力）。**不能把退出码 2 当完整产品全绿**。输出已存在会拒绝覆盖。普通 CI 只跑 runner 的小型单元测试，不跑真实样本，不下载，不调用外部模型。

### 实际跑哪些入口

- 每次导出指定仓库当前 HEAD 的 RF/FF/ET 代码到随机 TEMP；代码 WIP 不参与。CWP 运行代码也取本仓 HEAD。报告记准确 commit 和 Python 版本。
- 打开所有固定来源字节（含辅助公告/财报网页/PPT），检查 SHA；只按需复制测试使用的原件。原资料、旧 input/forecast/snapshot/独立审查不改。
- 真 CWP 注册/重复注册、原件字节读取、测试副本搬移后旧 SourceRef 读取、坏 hash 拒绝；真 RF `source_preparation.py`→FF→CWP v2 复用，记录嵌套子进程和零下载。
- 真正式 validator→engine→Markdown→新快照→registered-artifact 正向 registry audit，强检 input/result/snapshot；旧快照不可覆盖；独立复算桥接和 shock。固定经济情景路径不允许静默改变。
- 有限真 Worker 处理 CN/HK PDF 与 MSFT 原语言 TXT。模型 HTTP 回放明确标为 loopback；所有 span 的 hash/坐标合同与原文 replay 验证、CWP/RF NarrativeRef 内容相同、译文关闭、重复运行零新模型 POST。
- 实际探测 MSFT SEC HTML、22 页图片型 PPT canonical Worker 能力；人工 BS4/看图不算支持。没有支持为 BLOCKED，不删除此项。
- 真 FF companion→ET CLI/supervisor/worker/API→CWP importer/query/read 离线契约（供应商 HTTP 为明示 fixture）；复用零 provider_calls，超时清理。这个 Q3 合同 fixture 不冒充 MSFT Q4 的线上通话。
- 同一正式结果在 `PYTHONHASHSEED=0/1/2` 下强复核，避免进程内复算通过、换进程就失败。主重放固定 seed=0 只是复现设置，其他 seed 的失败照记。

### 仍须如实保留的项目级检查

replay 不重新启动三名研究 agent，不接触真实供应商，固定输入也不自动替换为新摘要。因此 `correct_provider_download`、`transcript_live`、`narrative_forecast_consumption`、新一轮 `skill_coverage` 不会被离线步骤冒充 PASS。旧技能 0–11 全量审查是历史参考；新一轮的事实正确性、预测情景合理性仍须在真实全流程大节点独立审查。未来实际没有发布时回测为 NOT_APPLICABLE。

## 改进前后比较

```powershell
python -B -m tools.cross_market_suite.runner compare `
  --before "benchmarks/cross_market_rf/baseline_replay.json" `
  --after "tmp/rf-e2e-after-001.json" --output "tmp/rf-e2e-diff-001.json"
```

报告逐项给 improved / regressed / unchanged / missing。删除失败检查也是 missing，不是修好。模式、full/core、样本 SHA、检查定义变化时标不可直接比较。版本可改变；只比较相同固定样本/模式/定义。耗时只是观察，不自动当质量提高。失败日志包含 argv/cwd/exit code/输出 SHA/有限 stderr，不复制大段原文。

## 数据不在本机时：一次导出可搬移的数据包

```powershell
python -B -m tools.cross_market_suite.runner pack `
  --delivery-root "$projectsRoot/revenue-forecast/output/cross-market-rf-e2e-2026-10-08" `
  --source-catalog-config "config/source_catalog.yaml" --output-dir "tmp/rf-e2e-frozen-data"
```

该命令显式生成一份按 SHA 去重的数据包，含三公司固定 input/结果/旧快照、全部被引用原件和微软 TXT。不复制生产数据库、密钥、配置或研究目录。以后 `--delivery-root` 指向这个包，所有字节从包读取，原生产资料湖可完全不在新机器上。包中的 `bundle.json` 列字节/SHA；缺原件为 BLOCKED，SHA 不符为 FAIL。不要提交这个几十 MB 数据包到 Git，也不需要每次生成；复制到其他机器后可删除导出副本。Git 只保留小清单和报告。

## 真实供应商模式

同样 run 命令加：

```powershell
--mode live --acquisition-config "config/source_acquisition.yaml"
```

在线仍在隔离 CWP/registry/原件/AUTO/work 中执行，市场 adapter 的已提交代码导出到 TEMP；不改 Dayu 或邻仓。不临时换 provider 或伪造预算支持。配置 staging 必须使用 `${PROJECT_ROOT}/.source_catalog/staging`。固定缺文档请求：CN 2026H1、HK 2026H1、US FY2026；分别最多 40 MiB/180 秒/0 美元，电话会最多 5 MiB/60 秒/0 美元。真实 FF envelope、下载入库字节/身份/年份、第二次零下载单独校验。来源额度不够、Dayu 没 bounded 能力、ET 没套餐或 FF 根本没启动 ET 都留具体结果。

live 默认仍不调用收费 LLM；它不会重新消费财报生成完整新研究。真实模型摘要刷新必须按既有 MiMo/DeepSeek/MiniMax 配置和累积预算执行，不能在该测试里偷偷重置账。需要完整新研究时，按下面的施工卡运行，再用固定回归比对工程能力。

## 完整新研究大节点施工卡

1. 三执行 agent 分别只写独立的 CN/HK/US 测试工作目录，复用本清单固定公司和 as-of；记录实际 RF/FF/CWP/ET 命令、source ID、SHA、locator、期间、明确公开日和可用上界。
2. 先运行 live 下载/复用，再运行有限原语言摘要。记录 Worker run ID/NarrativeRef 和消费进入 RF input 的具体 source_id/claim_id/span_id；仅有摘要文件不能算消费完成。
3. 严格执行 RF 技能 0–11（含 1A 管理层沟通/目标、1B 独立基准、两期历史、全部情景、桥接、敏感性、置信度、正式产物、快照）。缺失数据列 gap，绝不补公开日/目标年份/未发生回测。所有目录位置经 CWP 接口访问。
4. 三名独立 reviewer 按 `docs/plans/cross-market-rf-e2e-2026-10-08/independent_review_contract.md` 复核完整过程；结果和未通过项单列，不靠机器回归宣称新研究正确。
5. 每次大改后跑本 full replay + live，给出相同清单的前后对比。reviewer 必查残差≠售后全额、CMP 全年目标≠部分并表、无年份达产目标、同行增长非本公司正向验证、季 CC 指引≠全年 reported、5pp=0.05。
6. 签收只在这个完整节点；期间不新增人工许可或逐小步骤签收。测试临时根必须恢复，原件保留。

## 隔离与异常恢复

所有注册/移动/下载/账/输出都在随机 owned TEMP 中；finally 关闭/清理，包括 Windows 只读的测试 registry；受保护外部输入 SHA/大小保持。保留的 JSON/MD 只有轻量工程报告。失败也退出并清理。强杀 Python 或断电无法执行 finally，残留根留 `.cross-market-suite-owned` 标记；仅经绝对路径/标记/reparse 检查才能清理该根，不允许删除任何原件根。标准 suite 不做完整备份恢复演练。

`test_tree_final_bytes_before_cleanup` 是清理前实测大小，**不是 OS 级瞬时峰值**；上限 256 MiB。默认离线外部模型请求/费用为零，跨仓离线回放和在线供应商结论分开。
