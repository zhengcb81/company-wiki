# 解耦前置：端口、协议、部署和测试边界复核

2026-11-02，独立只读审查 `/root/decoupling_ports`。本次无产品、配置、原件、Git修改，无测试/网络/收费调用。只新增本报告。按最新用户顺序：**先由ROOT完成解耦验收，再派发RF/AUDIT模块任务**；内部只读审计可并行，不代表外部施工已经启动。

## 结论

当前需要先处理的是可验证的实现/测试耦合，不是重造SourceRef或共享SDK。StockWiki端口已有可注入命令；RF narrative端口也已有。FF多入口自己拼CWP模块/目录，RF原文入口仍固定运行方式，RF跨仓测试及CI还依赖CWP源码/内部表。只增加一份接口说明，不足以让它们独立开发与验收。

## 当前具体文件与问题

| 面 | 实际入口 | 判断 |
|---|---|---|
| RF原文read | `revenue-forecast/scripts/company_wiki_source_reader_v2.py::_run_reader`，约148–176；`open_source_version_v2`约240起 | 固定`sys.executable -m company_wiki.source_catalog.source_reader_cli`，没有命令注入；公开JSON边界已在，部署形式仍绑CWP模块安装 |
| RF编排 | `scripts/source_preparation.py:94–104,249–275,374–441` | catalog配置路径验证、原文reader调用和narrative接线仍由业务流程逐处负责。新端口必须真正穿透这些公开入口，不能仅在底层新增未使用参数 |
| RF narrative | `scripts/company_wiki_narrative_reader.py:18–31,52–80`；`scripts/narrative_source_preparation.py:30–39` | 已支持`reader_command`，可复用此小适配模式；无需另一套transport框架 |
| FF配置 | `filing-fetch/scripts/ff_configuration.py:79–125` | `company_wiki_root`必须存在且含`config/source_catalog.yaml`；配置schema只能表达root和少量ET/key字段，不能表达一个独立可执行服务端口 |
| FF通用query/ensure | `scripts/fetch_filing.py:540–557,1194–1221` | 自己拼CWP模块、config路径、cwd；移库/换安装布局会改调用代码 |
| FF local_prepare | `scripts/ff_local_source_prepare.py:51–80` | 同样拼`company_wiki.source_catalog.local_prepare_cli`及root/config路径；请求还在此处创建局部默认limits，须与操作额度owner一并核对 |
| FF电话会 | `scripts/transcript_tool_transport.py:348–355,395–417,1007–1018` | query/read/import各自拼CWP入口与配置；最终预算问题要一并覆盖import，而非只接ET worker |
| FF财务三表 | `scripts/ff_financial_statements.py:137–173` | `build_cwp_command(root)`固定`-m company_wiki.source_catalog.financial_statements.cli --wiki-root`，必须纳入端口迁移，不能只修财报下载入口 |
| StockWiki raw | `StockWiki/stockwiki/_source_reader_v2_transport.py:57–147` | 已有`VerifiedOpenTransport(argv_prefix, timeout_s, max_stdout_bytes, max_receipt_bytes)`及config loader，不碰CWP DB/物理root。可作为既有模式，保持不重写 |
| StockWiki narrative | `stockwiki/narrative_source.py:25–78` | 已有argv_prefix与runner注入；只需参与公开协议兼容验证 |

RF的`company_wiki_source.py:115`旧artifact_dag直接import存在，但当前production v2走`source_preparation.prepare_source`，legacy分支是兼容路径；不能拿这项旧代码冒当前主链必然跨层。解耦审查要记录仍受支持的legacy范围，明确退役/隔离，不让其偷偷成为主链回退。

## 协议核心与诊断扩展

RF `company_wiki_source_reader_v2.py:30–53,239–242`、`company_wiki_narrative_contracts.py:30–58,101–103`，StockWiki `_source_reader_v2_transport.py:179–219`、`_narrative_wire.py:19–34`、`_narrative_bundle.py:30–31,314–327`分别手写精确字段集。

这属于维护耦合，但**精确schema本身不是全部应删除的门禁**。SourceRef身份/hash、source/claim关系、核心状态、实际不兼容版本不能盲目忽略。需要producer-owned的稳定核心和明确非权威diagnostics扩展点，并用同一公开新旧fixture约束消费者；可选诊断新增不能迫使所有消费者理解CWP内部reading实现。

不能做的“解耦”：把所有unknown字段/状态一律当合法；在RF/Stock复制CWP语义推断；用强制全仓同时升级替代兼容；引入一个所有仓都必须导入的可变共享大包。

当前RF/Stock对合法uncertain/needs_review已能保留并传播，不能新造“必须先取消unknown全拒”的任务。当前RF artifact ID128限制没有合法producer超长例子，仍是候选，不作为已确认接口坏例。

## 真实测试耦合与已有夹具

### RF

- `tests/e2e_support/isolated_lake.py:244–255`直接import CWP CatalogConfig/SourceCatalog。
- `:352–369`导入CWP flags/policy/runtime_snapshot；`:382–385`导入旧prompt review写入器和RULESET_HASH。
- `:387–470`直接SQLite写`artifacts`、`producer_events`，自行构造生成器版本/derived路径；约505处继续访问catalog DB。
- `tests/test_fc1002_three_process_e2e.py:37–40`发现兄弟源码并写sys.path，约110/189处存在依赖旧环境的skip。这是跨仓集成，不应当消费者本仓独立性证明。
- 当前`.github/workflows/quality.yml:34–40`无条件`tools/ci_checkout_siblings.py`并给`PYTHONPATH`加CWP src，再运行`tools/pre_push_gate.py --ci`。后者列明41个CI测试文件；不能直接假定41个全都需要上游，更不能删除这步后让缺依赖跳过变绿。

已有可复用独立fixture：`tests/fixtures/cwp_source_ref_v2.json`、`cwp_verified_open_receipt_normalized.json`及`cwp_narrative_transport_v1/`、`du11_narrative_citation/`。`tests/test_company_wiki_source_reader_v2.py`已靠本仓golden和fake subprocess测试真实字节/identity，不需要CWP import；其第65行固定断言CWP模块名应迁成“默认兼容路径”和“注入外部命令”两类行为测试。

### CWP

`tests/fixtures/source_lake_v2/factory.py`是生产者仓内的纯合成文件树factory，`tests/contract/test_source_lake_v2_fixture.py`验证临时范围、sha和根通用性。它**不是已发布的跨仓fixture服务，也不生成所有RF所需normalized artifacts**。

已有公开`company_wiki.source_catalog.cli register`和official等入口；`CanonicalSourceWriter`是生产者内部owner，不应直接变成RF依赖。最小路径是生产者通过自己的真实入口生成公开导出样本，RF保存便携wire golden；真实整链由ROOT在CWP侧构造源环境，再通过公开CLI调用消费者。若必须保留内部测试seed，只留在CWP测试支持内部，由ROOT测试端口调用，不向RF泄漏表结构。

### FF与StockWiki

FF已有`tests/fixtures/w06_contract_matrix/authority/artifacts/`可复用请求/结果fixture；`tests/e2e_support/isolated_wiki.py`仍是ROOT整链环境，不能伪称一个FF单仓mock。
StockWiki已有`tests/fixtures/narrative_v1/`、`tests/test_narrative_source.py`、`tests/test_narrative_source_cli.py`及`tests/e2e/test_cwp_narrative_source.py`；区分portable consumer与真实CWP E2E即可，无需重写transport。

## 最小迁移顺序

1. **固定端口行为和兼容规则**：SourceRef/open/query、source preparation/import、narrative read、financial statements。数据协议沿用现有版本；定义哪些是核心、哪些是诊断。ROOT拥有一张操作/配置/预算/错误映射表，不是新许可文件。
2. **部署适配集中**：FF新增小的本仓connection/command adapter；操作只消费配置命令和opaque config handle/可选cwd，domain不再拼root/config/module。旧`company_wiki_root`配置由一个legacy constructor转换为同adapter，保旧用户配置。RF原文reader加入与现有narrative相同的命令注入，并贯穿source_preparation公开入口；StockWiki复用现状。
3. **资源与最终端点一起闭合**：同一请求budget到CWP import及verified-open；不能只改FF/ET。协议需要新增预算字段时由ROOT同步producer/consumer与新旧fixture，无provider自授权、无额外许可flag。真实费用/字节计量、原件校验继续各自负责。
4. **消费者本仓与跨仓测试分层**：RF/FF/Stock本仓验证只依赖本仓公开fixture/fake endpoint；ROOT真实组合测试保留现有断言并移除消费者侧CWP内部SQL/import。不是删测试或依赖missing时skip。RF默认本仓CI应能在只有RF代码/依赖的干净环境执行，ROOT组合CI/大节点显式部署所需仓库版本。
5. **一组隔离验证＋集中独审**：临时无CWP/FF checkout、无CWP PYTHONPATH环境跑RF/Stock consumer真实CLI；FF通过configured fake ports跑所有操作；然后一遍真实跨仓集成验证，最终终点到入库/verified-open及真实consumer读取。只有这两层都通过才撤销外部任务NOT_DISPATCHABLE状态。

## 建议受影响测试包（先核实际入口，失败定点追）

- RF：`test_company_wiki_source_reader_v2.py`、`test_company_wiki_narrative_reader.py`、`test_p5_source_default_v2.py`、`test_p5_source_default_cli_e2e.py`、`test_source_preparation.py`、`test_narrative_source_preparation_transport.py`、`test_ci_smoke_plan.py`。
- FF：`test_local_source_prepare.py`、`test_source_ref_v2_db_query.py`、`test_transcript_owner_budget.py`、financial_statements下`test_fetch_statements_subprocess.py`和`test_layer_boundary.py`；新增connection迁移行为测试覆盖query/ensure/local_prepare/raw read/transcript import/三表入口。
- StockWiki：`test_narrative_source.py`、`test_narrative_source_cli.py`及现有source-export/verified-open域；新旧诊断扩展兼容与真实错身份/错hash反控。
- ROOT：保留真实FF→ET→CWP import→verified-open，已有/缺失材料、旧新协议、数据湖根移动和隔离恢复；不能仅以fake endpoint完成便声明生产整链解耦。

本报告没有运行上述测试，均为后续最小验证范围建议。解耦完成条件不需要预先修完所有公司研究/自由文本语义缺陷，但必须保证业务问题归正确owner，消费者不会通过私有API/文件/表去补上游缺陷。
