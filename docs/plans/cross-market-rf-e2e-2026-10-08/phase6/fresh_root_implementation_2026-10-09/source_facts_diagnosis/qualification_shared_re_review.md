# W06 shared qualification：最终源码独立复审

## 决定

**FAIL，暂不验收/并线。** 确切源码 `4c92b72cbae8c3507588b4c4fbe99bba6e0ee676`，PWF-only tip `d6dd3c83a8d4d0d9f36f09bb62206a0805570689`。交付 manifest 的全部22项源码/测试 SHA 在首组验收前一致。旧 `independent_review.md`、原 FAIL/RED 和作者历史证据均保留。

本次共28项独立正常 API/故障/预算控制：**23 PASS /5 RED**，7.24s；没有复制作者260项全套。随后用标准18位 SEC accession URL 独立再跑五条错误公司入口，**5项全部 RED，脚本 exit 1**。此额外控验保留为独立 observation，不与首组28项合计成唯一测试数量。

## W06-R2 [P1] SourceRecord 自洽仍被当成 requested company 归属

责任：`assertion_service.source_scope_qualification` 的 registered CIK 分支。`_registered_sec_cik` 从官方 URL 取得 CIK 后，代码用该 CIK 以及已有标签的 canonical_name/market/security_id 拼 `SimpleNamespace identity`，却没有证据证明这个 CIK 对应这些标签的已登记公司。随后 `SourceScopeQualification.scope` 只比较 raw DEI 与 URL CIK。两者一致证明是 B 的材料，不能证明是请求 A 的材料。

此次正常 API 控验：既有 Acme/ACME 身份库的 CIK 为12345；传入原文实际 CIK99999，正文为 Other issuer B；完整原文 URL 为：

`https://www.sec.gov/Archives/edgar/data/99999/000009999926000007/original.htm`

来源登记和请求仍声明 Acme、US、ACME、FY2026、10-K/FY。`import_official_source` 真实正常 API 返回 `imported_new`；再用 `record_source_facts` 正常 API记录实际相符的 form/period 与 provider declaration。没有 SQL 篡改、伪造完整 DEI proof、mock query、改 SHA、篡改原件或调用外部 provider。原文448B，完整 SHA `c51b7559ff90c7b26d30cb44587a767818255b7f4446f2eabce91e87d331e605`。

| 真实入口 | 当前错误结果 |
| --- | --- |
| `SourceVersionReader.open_version(... filing_reuse)` | 返回448B B原文。 |
| `SourceVersionReader.verify_version(... filing_reuse)` | 返回成功的448B版本验真 receipt。 |
| `SourceResolver.resolve(A request)` | `reused_equivalent`，1 match。 |
| `SourceAcquisitionService.ensure(A request)` | `reused`。 |
| `AcquisitionCoordinator.stage_selected(A request, B candidate)` | `reused` / `existing_catalog_source_reused_after_discovery`。 |

所有 query 均 found，五条路径都没有 supplier调用，已有 assertions 和原件不变。它们不能以“正常 SHA/零下载”抵消错误公司归属。

### 可运行复现和接口

独立脚本 `qualification_shared_re_review_reproduce.py`，SHA `ca78ffd2ce3e0eb09efcad06b7ca32437f8ae4e2d07baac9a058b44f577746b0`。

```powershell
python -X utf8 -B C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/fresh_root_implementation_2026-10-09/source_facts_diagnosis/qualification_shared_re_review_reproduce.py --code-root C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki
```

审查实际运行使用最小 OS 环境（SystemRoot/Windows/PATH、Temp、用户路径等）加 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHON_DOTENV_DISABLED=1`；未输出真实环境、key或配置。脚本自建独占 TEMP，并拒绝 socket connect/DNS；仅输出合成 API 输入和观测 JSON。exit1表示原错误公司被某条入口接受。

receipt 的 `standard_url_five_entry_reproduction` 保存确切 argv、exit、时间、完整五输入/原文、结果和 TEMP absence。首组 `independent_control_harness` 与 `independent_controls.controls` 保留全部28项控制，不覆盖第一次失败。

### 应在真正责任层修复

在首次来源归属/登记或 CWP 共用资格责任中建立 **requested/registered company → actual CIK → SHA绑定原文 DEI** 的一次事实观察，并沿用既有 source_fact_evidence 保存结果。官方 URL CIK可做 provenance，用于与真实原文比对；它不能自己生成公司到 CIK 的关系。

修复之后完整实际 issuer-DEI proof命中仍只stream一次SHA、master0、parse0；缺少公司 binding 的首次资格可以在CWP共享层读取一次既有 registered issuer，再用同一个 verified buffer解析一次DEI。MAIN/作者已明确这项责任；因此旧部分proof控验观测到master0只是当前实现现象，**不是后续必须继续保持master0的门**。不让每个读者重复 identify，不新增消费者身份DTO、许可文件、额外 proof库或人工签收。

## 已独立通过的控制及具体范围

| 控制 | 结果 |
| --- | --- |
| 原文 CIK99999、URL仍CIK12345：open/verify/resolver/ensure/stage | 5 PASS；都 blocked/primary_issuer_conflict。 |
| 原文FY2022、URL/公司正确、缓存/请求FY2026：五入口 | 5 PASS；都 blocked/primary_scope_conflict。 |
| 正确目标、缺完整原文scope proof，reader/resolver | 两项：目标实读1次、同buffer parse1次、历史raw0、累计bytes保留前已用7B。当前master0的观测不证明公司归属。 |
| 正确目标、已通过prepare建立完整原文scope proof，reader/resolver | 两项：目标实读1次、parse0、master0、历史raw0；累计bytes=原文size+先前7B，预算未重置。 |
| 剩余bytes不足、expired deadline、cancelled；reader/resolver | 6 PASS；有限 unavailable/budget_exceeded、local_prepare_deadline或cancelled，未返回 absence/ready。 |
| URL公司正确但原文没有DEI scope | blocked/fiscal_period_unresolved，既有有限原因；不是not_found。 |
| 同一未知scope原文的preview和source_export | 两项：仍返回完全相同的真实原文字节。 |

正确缓存确实不会重扫已登记旧年度原件；完整proof确实不会重载master或重解析。这些已有改进是有效的，但不能接受尚未绑定公司归属的来源。

本次未再次复制或实读生产 MSFT 原件；作者的新实原件replay及上次独立只读MSFT观察仍各自保留。这里不将作者实原件replay等同于本次独立证据，也不将合成控制当成全公司RF/M3。

## 清理、源码范围和后续

首组28控验运行前后全部22个源码/测试 SHA一致、HEAD不变，owned TEMP先恢复到keep.bin基线，再删除；baseline_restored与owned_temp_absent均true。标准URL五控验结束，14个runtime源码仍与4c交付SHA一致；source owner已经同时开始补RED，修改了 `tests/contract/test_source_scope_qualification.py` 与 `tests/helpers/source_fact_fixture.py`。receipt如实记录这两个 owner变更，未假称所有测试仍未变，审查者没有修改它们。

生产raw/catalog/config、安装副本、Dayu、IQS、FF、RF没有写入；外网/付费为0。报告、自己的receipt与自己的可运行控验脚本是本次唯一持久写入。清理没有使用生产目录或整库恢复备份。

复现输入和五入口接口已直接交给source owner；作者用标准URL自己的RED也已确认5入口失败。MAIN待其共用责任修复和精确新源码交付后，再做一次集中重新验收并普通整合push/CI；本次不能把错误公司接受变成绿断言。
