# ET-LIVE：电话会议原文导入与 SourceRef 虚拟化验收

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

## 任务性质

状态：**一次性验收已执行并交报告；真实导入NOT RUN**。真实段只验证 `earnings-transcripts 工具 → company-wiki 临时导入 → SourceRef/SourceExport`；FF companion路由另跑现有确定性测试。此次FMP GET返回HTTP 402 entitlement，未取到正文，所以不能声称SourceRef live闭环。报告：[report.md](C:/Users/郑曾波/Projects/company-wiki-et-live-20261004/report.md)。

## 独占写入范围

- 独占目录：`C:\Users\郑曾波\Projects\company-wiki-et-live-20261004`。持久交付仅 `report.md`、必要的小型验收脚本及本线 `.planning/et-live-20261004/{task_plan,findings,progress}.md`；不复制整份原件/正文进报告。
- 运行期测试根：本线创建的全新随机临时目录；开始前记录该目录不存在，结束后删除并确认不存在。pytest如自动重定位短根，记录实际位置并仅清理本次自建子树，不动其他harness根。
- 只读项目：company-wiki、filing-fetch、earnings-transcripts。不得修改它们的代码、配置、全局技能安装、Git索引、缓存或任何生产目录。不得写 CWP PWF/结果目录；root接收报告后统一采纳摘要。
- 若临时根已存在、无法证明路径归属或 cleanup 失败，立即停止，不覆盖、不递归删除不明目录；报告原因。

## 单次运行步骤

1. 记录只读基线：CWP当前HEAD、FF/ET已发布commit/工具版本、工具是否由 `EARNINGS_TRANSCRIPTS_TOOL` 提供。记录变量是否存在，**绝不打印或保存其值**。使用稳定ET main `93fe52c`，不读正在实施的ET-DEADLINE工作目录。不得修改Git全局设置。
2. 检查现行schema，选精确证券、市场、财年和季度。**调用前**用现有CWP `SourceRequest`构造该来源请求，将其 `request_id`用于ET请求，避免事后自己猜request ID。现有provider/key/权益不具备就NOT RUN，不买订阅或增加provider。最多一次真实ET工具取数调用；工具调用数与实际HTTP次数分别记录。失败后不换provider、不循环尝试、不请求整年；沿用实际byte/time/cost上限。
3. 请求保持原始语言，关闭翻译。不得将年度财报推断成 Q4。若工具无法显式关闭翻译，确认其当前配置/输出仍为原语言；无法证明就记为未通过，不自行改工具配置。
4. 先按下方“导入准备”创建临时CWP根；将真实ET结果放入现有四字段import envelope的 `transcript_result`，整个envelope经stdin交 `company_wiki.source_catalog.transcript_import_cli --wiki-root <临时根>`。**ET结果不能直接作为import请求**。不翻译/LLM改写/复制到生产companies。读取machine JSON，保留request/source ID、期间、语言、payload/content SHA、字节数、provider/extractor版本与canonical状态，正文/key不入报告。
5. 用现有 SourceVersionReader/SourceExport v2 公共入口按 SourceRef 查询同一来源，验证真实字节 hash、身份/期间、原语言和可回放内容一致。消费者侧只能拿 ID/hash/locator 等公开 DTO；不得把临时根绝对路径当接口输入或输出。若当前公共入口不能完成该动作，记录精确缺口与文件/符号，不添加新接口。
6. 核查临时根只包含本次输入的单份 canonical 原件及必要的来源元数据；没有翻译件、第二份正文、遗留 `.part`、staging 或复用回执异常。保存目录文件清单和原始/导入 hash，不保存完整正文。
7. `finally` 删除本次创建的临时根；再次确认目录不存在、CWP生产配置与原件/数据库无变化。报告列出清理验证结果。

### 导入准备：复用已实现合同，不现场发明字段

临时根须先有 `companies/`、`config/source_catalog.yaml`，最小配置与 `tests/contract/test_transcript_import_cli_e2e.py::_fixture` 相同：

```yaml
schema_version: '1.0'
catalog_dir: .source_catalog
roots:
  - root_id: company_raw
    path: companies
    kind: company_raw
    priority: 10
    adapter_id: company_raw_v1
    read_only: false
```

用实际 `SourceRequest.to_dict()` 与 `dataclasses.asdict(DownloadCandidate)`，不要手写少字段对象。FF `scripts/transcript_tool_transport.py::_candidate` 与 `acquire_exact` 已有真实result映射/封装，可按同一helper和该CWP测试构造：

```python
envelope = {
    "schema_version": "company-wiki-transcript-import-request/2",
    "source_request": request.to_dict(),
    "candidate": asdict(candidate),
    "transcript_result": et_result,
}
```

request ID必须与调用前的ET request一致；公司/市场/证券/FY/Q、provider/source URL等来自已选请求与真实结果。FMP未知publication保留None，不用运行日/季度结束日/假golden值补成“已公开”。真实结果不足以构成合法import时记精确缺口并停，不发第二次取数修正，不伪造元数据。这是导入执行细节，不新增人工授权合同。

## 测试包

在真实调用前先运行现有确定性测试，不修改测试：

```powershell
$env:PYTEST_ADDOPTS='-p no:langsmith_plugin'
$env:PYTHONDONTWRITEBYTECODE='1'
# 从只读CWP根运行，cache关闭；pytest fixture/temp只用本线短根
python -m pytest -p no:cacheprovider tests/contract/test_transcript_original_import.py tests/contract/test_transcript_import_cli_e2e.py -q
# 从只读filing-fetch根运行，同样只用隔离fixture
python -m pytest -p no:cacheprovider tests/test_transcript_companion.py tests/test_transcript_companion_transport.py -q
```

两条pytest命令须各自记录cwd和实际临时根；不指定生产数据目录。`PYTHONDONTWRITEBYTECODE`也传入测试子进程。若环境问题导致cache/bytecode仍写入只读仓，立即停止并记录，不继续污染。插件/参数失败按仓库本机约定处理，不删测试或改配置。

真实验收必须使用上述一次 ET 工具调用及一次 CWP 临时根导入。仅用 golden/mock 成功不得标为 live E2E。工具不可用或 provider 无该季度时，停止真实调用，仍报告现有确定性测试结果和 live 阻塞原因，不伪造成功。

## 交付接口

只交独占目录中的 `report.md`，至少包含：

- repo/commit/工具版本基线；工作树是否dirty（只报计数与影响本试验的文件名，不读取密钥）；
- 精确证券、市场、FY/Q、tool/HTTP次数、翻译状态、实际资源限制；
- 确定性FF companion测试命令/结果；ET真实段每阶段状态；SourceRef字段与SHA/字节核验结果；分别标记`ff_companion_live=NOT RUN`（除非确实经正式FF入口）与`et_import_live`，不混称整链成功；
- pathless DTO核验结论；临时根运行前/结束后的存在状态；生产配置/原件变化检查；
- 每个发现标为 `PASS`、`FAIL` 或 `NOT RUN`，失败附文件/符号/最短重现，不直接修代码。

## 完成标准

- 一次真实ET工具取数与临时CWP导入成功，或说明live未运行的可验证阻塞；后者表示本验收报告完成，不表示S3真实链成功；
- 原始字节、语言、证券/期次及 SourceRef SHA/size闭环；公共读取不依赖物理路径；
- 确定性测试结果真实记录；测试临时目录恢复到运行前状态；
- 没有生产文件、配置、数据库、其他仓库或代码改动。

## 本次执行结果（2026-10-04）

- 确定性前置：CWP transcript importer **7 passed**；FF companion/transport **17 passed**；两次pytest basetemp均删除。
- 真实工具调用1次；ET代码仅发起1个FMP GET、关闭redirect且无重试。结果为 `unavailable/provider_entitlement_required`，该错误码由ET对HTTP 402的映射产生；公共结果未单独输出HTTP状态字段。没有获取正文，故CWP导入与SourceRef回读为NOT RUN。
- CWP临时根以系统TEMP下随机 `et-*` 名称创建，finally清理并确认不存在；精确随机名称未留存。生产配置SHA前后相同。密钥和原始返回正文均未进入报告。
- 本次报告完成ET-LIVE记录要求；真实来源链仍待合法provider权益可用后才能验证，不重复调用或购买套餐。
