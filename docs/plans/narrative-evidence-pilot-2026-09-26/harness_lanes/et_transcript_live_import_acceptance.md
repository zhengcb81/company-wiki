# ET-LIVE：电话会议原文导入与 SourceRef 虚拟化验收

## 任务性质

这是一个可独立交给外部 harness 的**只读验收包**，不是生产代码施工。它验证 `filing-fetch → earnings-transcripts → company-wiki` 已有接口能否把一份真实电话会议原文导入临时库，并通过稳定 SourceRef/SourceExport 读取。它可与 CWP G1 门禁清理并行执行；若发现代码缺口，只交报告，代码修复排在 G1 后由主线统筹。

## 独占写入范围

- 唯一持久写入：本卡对应的报告文件 `docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/et_transcript_live_import_acceptance_2026-10-04.md`。
- 运行期测试根：操作系统临时目录中的全新随机目录；开始前必须记录该目录不存在，结束后必须删除并确认不存在。
- 只读项目：company-wiki、filing-fetch、earnings-transcripts。不得修改它们的代码、配置、全局技能安装、Git索引或任何生产目录。不得写 CWP 的其他 PWF 文件。
- 若临时根已存在、无法证明路径归属或 cleanup 失败，立即停止，不覆盖、不递归删除不明目录；报告原因。

## 单次运行步骤

1. 记录只读基线：CWP 当前 `HEAD`、FF/ET当前可用的 commit/工具版本、工具是否由 `EARNINGS_TRANSCRIPTS_TOOL` 提供。记录环境变量是否存在，**绝不打印或保存其值**。不得修改 Git `safe.directory` 全局设置。
2. 先检查现有 FF transcript companion 的 `--help`/schema，确认一条精确证券、市场、财年和季度的请求能调用 earnings-transcripts 工具。仅请求一家公司、一个季度；最多发起一次真实取数调用；失败后停止，不换 provider、不循环尝试、不请求整年。
3. 请求保持原始语言，关闭翻译。不得将年度财报推断成 Q4。若工具无法显式关闭翻译，确认其当前配置/输出仍为原语言；无法证明就记为未通过，不自行改工具配置。
4. 将工具返回的原始 transcript payload 直接通过 stdin 交给现有 `company_wiki.source_catalog.transcript_import_cli --wiki-root <临时根>`，不得经过正文翻译、LLM改写或复制到生产 `companies/`。读取 CLI 的 machine JSON 响应并保留最小审计值：request/source ID、期间、语言、payload/content SHA-256、字节数、provider/extractor版本、canonical状态。不得把正文或凭证写入报告。
5. 用现有 SourceVersionReader/SourceExport v2 公共入口按 SourceRef 查询同一来源，验证真实字节 hash、身份/期间、原语言和可回放内容一致。消费者侧只能拿 ID/hash/locator 等公开 DTO；不得把临时根绝对路径当接口输入或输出。若当前公共入口不能完成该动作，记录精确缺口与文件/符号，不添加新接口。
6. 核查临时根只包含本次输入的单份 canonical 原件及必要的来源元数据；没有翻译件、第二份正文、遗留 `.part`、staging 或复用回执异常。保存目录文件清单和原始/导入 hash，不保存完整正文。
7. `finally` 删除本次创建的临时根；再次确认目录不存在、CWP生产配置与原件/数据库无变化。报告列出清理验证结果。

## 测试包

在真实调用前先运行现有确定性测试，不修改测试：

```powershell
$env:PYTEST_ADDOPTS='-p no:langsmith_plugin'
python -m pytest tests/contract/test_transcript_original_import.py tests/contract/test_transcript_import_cli_e2e.py -q
```

测试应使用 pytest 自己的短期临时根；不指定生产数据目录。若pytest插件/参数环境失败，先记录插件和错误，再用仓库约定的本机测试环境处理；不能因工具环境问题删测试或改配置。

真实验收必须使用上述一次 ET 工具调用及一次 CWP 临时根导入。仅用 golden/mock 成功不得标为 live E2E。工具不可用或 provider 无该季度时，停止真实调用，仍报告现有确定性测试结果和 live 阻塞原因，不伪造成功。

## 交付接口

只交唯一报告，至少包含：

- repo/commit/工具版本基线；工作树是否dirty（只报计数与影响本试验的文件名，不读取密钥）；
- 精确证券、市场、FY/Q、请求次数、翻译状态；
- 确定性测试命令/结果；真实 E2E 每阶段状态；SourceRef字段与 SHA/字节核验结果；
- pathless DTO核验结论；临时根运行前/结束后的存在状态；生产配置/原件变化检查；
- 每个发现标为 `PASS`、`FAIL` 或 `NOT RUN`，失败附文件/符号/最短重现，不直接修代码。

## 完成标准

- 一次真实工具取数与临时 CWP 导入成功，或清楚说明 live 未运行的可验证阻塞原因；
- 原始字节、语言、证券/期次及 SourceRef SHA/size闭环；公共读取不依赖物理路径；
- 确定性测试结果真实记录；测试临时目录恢复到运行前状态；
- 没有生产文件、配置、数据库、其他仓库或代码改动。
