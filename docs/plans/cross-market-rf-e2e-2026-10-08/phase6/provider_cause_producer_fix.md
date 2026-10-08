# CWP provider cause producer：隔离实施交接

2026-10-09；工作树 `C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki`，base `ade1d991`。本次不commit/merge/push，不改主仓、生产配置、安装副本、邻仓或Dayu；由MAIN统一并线。本记录只解释CWP来源工程，不能当公司研究验收。

## 已完成责任改造

旧 `structured_error` 精确四字段保持；采集operation有证明时附 `acquisition_failure`。adapter invocation proof先进入既有共享 `AcquisitionBudget`，ensure责任层投影整次operation：discovery、每一次fetch、已有最多3次fetch重试。没有另一计数账或许可门，原成功SourceRef与下载策略不变。

`JsonCommandAdapter`统一有界调用/accounting；final/完整checkpoint先验证schema和目标adapter身份/版本、usage数值，checkpoint只取最后一条有效累计值一次计费，不累加同invocation多行。有效final error的retryable事实保留，unknown费用仍沿既有策略禁止自动retry。超额保留两维actual overage，不clamp。

真实Windows barrier在release前失败可证明未执行；bootstrap/Popen活与普通OSError不能证明目标执行。实际final/checkpoint可证明目标程序执行（不等于HTTP）。timeout/output hardkill保留已知下界。scratch、process cleanup、retry cleanup、journal二次错误不能遮蔽原异常和回执。successful verified final后的scratch故障保留已知usage。预算恢复有正counter是已知发生部分；zero+incomplete是unknown，不是假最终零。

返回型黑洞也接同DTO：latest_as_of provider失败的GAP、legacy close-gap failed结果、SourceRef v2 facade。普通GAP/missing/reuse不凭空加failure；保留原status/returncode。ensure后envelope/CLI SourceRef projector异常保留此前共享budget；真正writer异常用canonical_import_failed，writer内预算截止仍是acquisition_budget_exceeded。

## 固定接口：消费者只读最外层

CWP CLI stderr异常，以及返回body（有identity wrapper、SourceRef v2也一样），都可从最外层 `JSON["acquisition_failure"]` 读取。内部legacy acquisition/close_gap也保留同对象；FF无需扫描嵌套。后者legacy failed returncode 0照旧，不新增重试或改成新许可。

精确7键，闭集常量 `src/company_wiki/source_catalog/acquisition_failure.py::ACQUISITION_FAILURE_CODES`，实际33码（此前协调消息手数34有误；FF AST比对双方33差集为空）：

```json
{
  "schema_version": "acquisition-failure/1",
  "code": "adapter_timeout",
  "retryable": false,
  "provider_started": true,
  "usage_complete": false,
  "acquisition_usage": {"schema_version":"1.0","response_bytes":36,"cost_usd":"0.03"},
  "usage_scope": "operation"
}
```

provider_started是整个operation曾有目标执行证据；后一次prestart/unknown不能抹掉之前true。usage_complete true=全部已验证最终回执/实际本地pre-target最终零，false=已明确不完整，null=完整性不可知。数值只表示预算已有确认counter，false/null不能宣称最终费用；无数值证据时acquisition_usage=null。恶意code安全降级adapter_process_failed，不复制正文、stderr、路径、URLquery或密钥。retryable是已证明producer事实，诊断不覆盖旧外层generic retry政策。

单独AdapterProcessError的invocation attrs不会由structured_error直接当operation发布；只发布ensure/CLI拥有预算后附的共用投影。FF仍保留filing-upstream-cause/1固定六键，RF传播同一对象；真实费用不另建下游账。

## TDD与集中验收

- 初次RED：21项中20失败、旧四字段兼容1通过。真实新增Windows barrier/preflight/cleanup三项再次RED。
- 返回型RED：5项中GAP、close-gap、CLI后处理3失败，普通GAP和实际3fetch账2通过。
- scratch/barrier二次清理3项RED；既有预算恢复正数/未知零和writer预算被误标import均有RED，然后共用责任层修复。
- fakeCLI首跑配置夹具误把HK/US设json_command_v1，按已有dayu_sdk_bounded_v1接口修正夹具，生产配置不改。后一次唯一失败为测试预估原文字节73，实际75，改成len(同RAW_BODY)精确算式，未放宽标准。
- 新责任：31 unit + 7 contract + 10真实CWP CLI/fakeprovider integration = 48项。覆盖discovery+3fetch整次累计、handled error、checkpoint多行/坏identity/非法usage、无checkpoint未知、超额、writer/入库后失败、GAP/close-gap/v2、scratch/journal/cleanup遮蔽、真正pre-target barrier、unknown不retry、成功import→reuse的相同SourceRef/原件SHA且provider仅discovery+fetch两次。
- 先前集中132项（新增45+旧87）全PASS，33.77秒。最终补unknown zero恢复分支后133项全PASS，30.75秒；MAIN审查又指出builder可能让未记录budget覆盖exception已证明True，2参数RED复现后已修proof单调并集及unknown初始完整性；这项最终接线后的当前48新责任项集中结果见下文实际追加；不能以此当供应商或经济模型全绿。
- ruff --no-cache对本次所有Python路径PASS；mypy --no-incremental对acquisition_failure.py、既有strict close_gap.py/source_operation.py PASS（3文件）。

最终集中命令（不是每次commit门）：

```powershell
python -X utf8 -B -m pytest tests/unit/test_acquisition_failure_diagnostic.py tests/unit/test_adapter_process_budget.py tests/unit/test_acquisition_usage_recovery.py tests/unit/test_acquisition_budget.py tests/unit/test_error_taxonomy.py tests/unit/test_bounded_process.py tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_acquisition.py tests/contract/test_single_intent_latest_acquisition.py tests/contract/test_acquisition_failure_return_paths.py tests/integration/test_acquisition_failure_cli_e2e.py -q -p no:cacheprovider
```

## 临时清理、原件和隔离

新CLI每案TemporaryDirectory在finally恢复起初不存在；无收费模型/供应商HTTP，费用与外部调用0。fakeprovider的字节/费用回执用于证明协议和累计账，不证明真实供应商计费。成功样本先import再reuse，原文及sidecar所有文件SHA前后相同；失败样本没有原件入库，staging无原文残留。真实timeout已验证拥有的子孙进程停止、不晚写；测试sandbox恢复空。主仓生产原件删除0、原件写0；Dayu代码写0。此树既有finite/cache不作无归属删除；不用完整备份恢复。

## 仅以下14个路径属于本次候选

- src/company_wiki/_bounded_process.py
- src/company_wiki/source_catalog/acquisition_failure.py（新）
- src/company_wiki/source_catalog/acquisition.py
- src/company_wiki/source_catalog/acquisition_service.py
- src/company_wiki/source_catalog/adapter_process.py
- src/company_wiki/source_catalog/cli.py
- src/company_wiki/source_catalog/close_gap.py
- src/company_wiki/source_catalog/download_budget.py
- src/company_wiki/source_catalog/error_taxonomy.py
- src/company_wiki/source_catalog/source_operation.py
- tests/unit/test_acquisition_failure_diagnostic.py（新）
- tests/contract/test_acquisition_failure_return_paths.py（新）
- tests/integration/test_acquisition_failure_cli_e2e.py（新）
- 本provider_cause_producer_fix.md（新）

必须保留、由MAIN另收finite已验收四路径：scripts/writer_policy.py、tests/unit/test_finite_configured_entrypoint_launch.py、tests/integration/test_narrative_batch_cli_e2e.py、phase6/finite_entry_launch_fix.md。本agent未编辑、暂存、覆盖该四路径。没有改根三个PWF。

## MAIN交接

FF consumer已获稳定接口/目录并运行FFCLI→CWP CLI→fakeprovider。它初次23/24通过唯一是provider_start预期2而真实4；源码固定1discovery+3fetch retry，FF自身fatal没有retry，已告知应精确断言4（不可用>=），operation2048+0+0+0。该三仓联调报告由FF owner写自己的交接，不由本记录冒签。

MAIN统一审查两个互不重叠CWP包、FF/RF候选，集中跨仓校验通过后再commit/merge/push并按现有工具定点同步；本agent不直接切换正在冻结的NVDA研究入口。unknown/外部账户限制仍明确记录，不购买套餐或添加人工合同。


## 最终handoff补充（只读主审查收尾）

MAIN发现：builder先取exception True后却用未观察budget False/null覆盖。实际Json路径均先observe target proof，但共用builder不应依赖调用顺序。两个责任参数RED均复现；实现将True作单调并集，若此次proof尚未记入预算，则初始complete=True不能当该调用final，明确降unknown（已知False保留）；没有实际record时usage=null。仍不把exception的77bytes/0.5单invocation数冒充总量，不改变retry策略或创建账。最终新责任48项当前代码集中GREEN/静态结果由实际工具输出验证，原133项在此前一步全PASS。

以下仅供MAIN精确选择候选，source/test当前SHA-256：

```json
{
  "src/company_wiki/_bounded_process.py": "0b49f8fcbd298c1a3b18b1a2e62ffbcf2ad9e7376fbd322ce3336c2d19b3a0db",
  "src/company_wiki/source_catalog/acquisition_failure.py": "2739854e53b17fcd3ce17ed7eaeca9088805047904e1aa50132bc15a81813e13",
  "src/company_wiki/source_catalog/acquisition.py": "889a5942f5c31d775fe4f90089fbd7c8b3ad05d704d530a644f405dedfb64a47",
  "src/company_wiki/source_catalog/acquisition_service.py": "dc0928a08e86c65fd1ec19a68933f63de11583531fcbc1d9912f6fb1f78cfd9c",
  "src/company_wiki/source_catalog/adapter_process.py": "36408d17822b91f2f9ffc21a02a7ad59c3088034d7eb91157ed9794ff91ce838",
  "src/company_wiki/source_catalog/cli.py": "fdbf6f0aa801aa8c2ff7e240da9d53075cc66927cb66455ad0b5ca8c2b051961",
  "src/company_wiki/source_catalog/close_gap.py": "149e4f0c0fa11899c2fcfda6d3209fd45080d0be3ee0d492074d101aa7aafa68",
  "src/company_wiki/source_catalog/download_budget.py": "a9bf447f5ca7b5cd8e0956390ed67eeb8623252130cbd6a3688248190f24104f",
  "src/company_wiki/source_catalog/error_taxonomy.py": "cd36616fd5f515325e8bef0a4e75b0a2cbbcc10bdabdc0ec41d2e734caed7f67",
  "src/company_wiki/source_catalog/source_operation.py": "96447611da595a3542922c8b805c2d54d16bd46975b01fcdaffbdc500a7697ea",
  "tests/unit/test_acquisition_failure_diagnostic.py": "5ea9da389fddbc09f5af213c23be3340e731229a11c51bc01e8b30cb4c2e45d4",
  "tests/contract/test_acquisition_failure_return_paths.py": "c7e8938ffea8d094fcb085a22bb75ccea37ee3d0e33049e434d79a3776d925fc",
  "tests/integration/test_acquisition_failure_cli_e2e.py": "62475325645b483c88fbc4261d9930de66691fa4a7ae1c2be77b77253e46f564"
}
```

最终当前代码新责任集中：**48 PASS，0 FAIL/ERROR/SKIP，16.19秒**；同一次命令随后ruff全部本次Python PASS、mypy三文件PASS。git diff --check本次候选路径PASS。未commit/merge/push。

## MAIN concentrated integration before candidate commit

After the final monotonic proof correction, MAIN ran the full listed producer responsibility suite plus finite real startup/three configured worker-resume cases together: **146 PASS, 47.48s**. This resolves the prior133-before-final-patch qualifier for the final candidate. Real RF→FF→CWP CLI milestone against the same frozen source: **23/23 PASS**, failure/GAP specific cause retained, new download/verified raw open/reuse preserved, short owned TEMP restored. Reports live in RF docs/implementation/company-pool-provider-cause-20261009/three_repo_e2e_report.json. Supplier calls/fees0.

The146-case invocation initially used pytest default TEMP rather than an explicit owned wrapper. MAIN inspected current-session directory pytest-220, its exact new-test/finite fixture markers, time and 16,216,787 bytes/385 files, checked no reparse points and removed only that exact new directory. Earlier teammate roots218/219 were not removed by this cleanup; owners must identify them separately. Future milestone commands use an explicit short TemporaryDirectory and finally restore it. No production original bytes modified. Candidate remains isolated until independent NVDA reports/expert integration.
