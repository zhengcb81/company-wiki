# W03 当前实施接口：来源时间证明 → 公共 narrative 读取

2026-10-22 ROOT 接口补正。用户已恢复实施。此文补足专家冻结 W03 卡未列出的两个实际断点，**不改冻结卡和其 SHA**。先完成本切面 W03-A，再继续0.9/v5真实选择/正式摘要/context消费的W03-B与W07。

## 目标与不变项

W01 已能在不补造发布日期的情况下，用同 SHA 原件的既有真实可用时间证明判断 source/raw/2.2。CWP narrative 与 RF narrative consumer 尚未接通，合法原件仍被 unknown publication 阻断。本切面只连通这项责任层合同；不改原件、生产默认、generation、frozen artifact、cache key、预算或来源身份。

- CWP母仓当前代码基线：`20a7fb0c`；RF母仓：`92b69682`。
- ROOT正在完成当前代码CI和PWF发布。两条W03线只在自有隔离工区施工，**不碰母仓和安装副本，不自行合并/推送main**。
- 总状态仍以 `../CURRENT_STATUS.md` 与 `implementation-progress.json` 为准。原 initial 四审FAIL不回写。

## 唯一公共 DTO 补充

仅 `narrative-read-receipt/1` 增加 optional 顶层键 `availability_evidence`。合法值完全复用既有 `source-availability-evidence/1`，没有新格式或第二种proof：

```json
{
  "schema_version": "source-availability-evidence/1",
  "source_sha256": "<原件真实SHA256>",
  "available_by": "YYYY-MM-DD",
  "basis": "prior_verified_capture | primary_archive | current_verified_open",
  "evidence_ref": "<现有owner证明引用>",
  "locator": "<现有owner定位>"
}
```

上述basis显示三个候选，不把带竖线的示例文字作为实际值。具体字段类型、日期、引用限制一律复用来源层/`contracts.source_clock`的已有validator。

1. CWP无proof时**省略该键**，保持旧known-pub golden字节不变。RF兼容省略或null，均不自动获得historical资格；不接受其它额外键。
2. CWP已有 `open_described_version` 实际验原件buffer后，只取一次 `source_availability.verified_availability_evidence(catalog, ref)`，复用同次已验ref与buffer，不再起raw子进程，不重读/重复hash原件，不创建新的observed proof。
3. manifest的`published_date`仍可为null，不修改`retrieved_at`。CWP用common `qualify_source`；RF用现有 `qualify_source_information`/`validate_availability_evidence`和已验证ref/manifest SHA。known未来或invalid publication保留拒绝优先；availability不能倒填旧as-of。
4. proof是读取时metadata，不进入immutable bundle、reading generation、模型输入或cache identity。receipt仍遵守原16KiB上限。
5. `narrative-read-receipt/3` projected分支**不接此顶层键**。多parent各自已验元信息仍由原来源owner负责；不能用A的proof放行B或整个projection。本切面不新增parent-proof数组、不借机放宽其它精确字段合同。
6. RF复用common `validate_source_events` 校验真实read_at/retrieved_at与所得eligibility，而不只校验日期格式。显式historical as-of仍由publication优先资格决定，known-past-pub不因晚capture退化。`as_of=None`是current读取，不能用read_at日期伪造historical cutoff；无proof/null保持旧语义，有proof只按同SHA合法proof的basis/available_by构造共用event资格（该资格published_date=None，manifest仍保留真实值）。proof不能晚于真实read_at、retrieved不能晚于read_at；已验证typed publication晚于read或retrieved早于publication的既有current元数据，不因新增proof被强行套入历史资格。current晚proof报真实`source_clock_conflict`，不报虚构as-of。

## 施工线与文件所有权

| 线 | 独占工作目录/分支 | 可改产品与测试 | 禁止 |
|---|---|---|---|
| CWP producer | `C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki`，`codex/r1-narrative-availability` | `src/company_wiki/automation/narrative_transport.py`；若确需常量才改`narrative_transport_contracts.py`；相关CWP transport单测/contract/integration；独立新计划`docs/plans/r1-w03-availability-20261022/` | 母仓PWF、W04runstore/summarize、W01writer、RF、模型配置、安装副本、下载/收费 |
| RF consumer | `C:/Users/郑曾波/Projects/revenue-forecast-r1-boundary`，`codex/r1-narrative-availability` | `scripts/company_wiki_narrative_contracts.py`；相关RF narrative_reader/source_clock/preparation测试；独立新计划同名目录 | CWP/FF/ET、母仓、CI/hook、模型和来源配置、安装、下载/收费 |
| ROOT | 母CWP与RF主线，公共PWF | 冻结接口、解决必要共享字段分歧、完整组合测试、集中独审、顺序并线/选择式安装/发布；之后W03-B/W07 | 不以初始四审或组件测试代签真实内容/研究 |

若发现需要增加可改文件，先给ROOT具体现有调用/失败证据，由ROOT统一接口范围；不是新增人工许可。

## 先 RED，再 GREEN

### CWP

- 真实 `published_fixture` PDF与native JSON，manifest pub置null，接合法prior capture或current verified open：当前真实CLI拒绝，修后可读同bundle，pub仍null，proof精确等于owner输出。
- known未来pub+更早proof仍拒；unknown+无proof、错SHA、晚于as-of、坏schema/type/额外path、裸mtime/first_seen均不自动合格。既有known-past-pub不因晚capture退化。as-of=None保持当前读取语义。
- 公开CLI/原件tamper/大小/manifest绑定等已有反控不删；单次操作原件只打开一次，lookup只读有界metadata，旧known-pub字节不变。
- projected双parent反例：A证明不能借B，root单proof或跨parent替换不获得许可；不扩大receipt/3。

### RF

- 真实validator对raw receipt/1 optional proof+null pub先RED；修后保留完整proof于`context.read_receipt`，不增context DTO。
- 复用既有source-clock拒绝控制，identity/期间/as-of/ref+manifest字节绑定不重复造一套。
- 旧omitted/null兼容；known-past-pub+更晚合法capture仍合格，unknown+无proof仍明确失败；future pub、wrong SHA、晚证明、proof被改/非法额外键拒绝。
- projected receipt/3仍拒single-proof扩展；现有0.9/v5/0.8消费合同和golden不重写。
- CWP producer未完成前可在隔离夹具验证公共wire；ROOT最终用真实producer→FF/RF公开读取联调，合成响应不能代签。

## 大节点验证与交接

每线集中跑相关测试、ruff与项目mypy，保留有效RED和最终GREEN、实际source SHA及temp恢复收据；正常commit。测试使用独占短TEMP/TMP，不污染production config，不运行外部/收费API。

完成时交`handoff.md/json`：产品commit/工作树HEAD、改动文件真实SHA与LF映射、公共字段shape、测试命令/数量/skip/RED原因、原件打开次数、费用0、临时根起止/清理、未实现范围。ROOT对两线做非作者独审、实际公开CLI联调、scope/golden和全src检查后，**先RF consumer兼容发布并安装，再CWP producer**。只一个大节点复核，不逐小步签收。

本切面通过后仍不能写“共享引擎生产完成”：W03-B实际0.9/v5语义与generation/0.8冻结、W07配置内正式摘要/普通paid恢复/cache/RFused参数公式、W06四审与新公司仍需实施。
