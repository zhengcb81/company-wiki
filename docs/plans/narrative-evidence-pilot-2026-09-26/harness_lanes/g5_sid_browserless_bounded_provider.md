# G5-SID-RUNTIME：纯API provider 解耦与完整预算

**当前状态：complete，MAIN已验收、并线并推送（2026-10-07）。** 不重新开工；原卡冻结输入、写集和工作树命令仅为施工历史。实际交付/当前测试、兼容接线、真实安装和未做范围见[MAIN验收](../g5_main_acceptance_2026-10-07.md)。下文原ready/未创建/paused说明不覆盖本结论，三个交接工作树保留。

## 1. 项目、冻结输入、目录

- 原仓 `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`，执行分支 `v2-clean-rewrite`。
- 基线 `0cb3c1f0b4a5784757971265b2b20a7a0b4c5104`（G4代码eb8495c、PWF收尾0cb3c1f）。原remote仍名StockInfoDownloader，不能因此维护旧main。
- 新目录 `C:/Users/郑曾波/Projects/_g5/sid`，分支 `codex/g5-sid-runtime`；发卡时未创建。
- 冻结只读 CWP consumer代码 `df7d7ba58955e224c1799355f479ad5378ef38a7`，位于 `C:/Users/郑曾波/Projects/company-wiki`，用 git archive 导出，仅取已提交代码/配置，不用原仓未提交 G2-12。

```powershell
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' status --short
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' worktree add -b codex/g5-sid-runtime 'C:/Users/郑曾波/Projects/_g5/sid' 0cb3c1f0b4a5784757971265b2b20a7a0b4c5104
Set-Location 'C:/Users/郑曾波/Projects/_g5/sid'
```

已占用时核本卡归属；不能reset未知树。PWF唯一位置 `<工作树>/.planning/g5-sid-runtime/`，设置 `PLAN_ID=g5-sid-runtime/PWF_PLAN_ROOT=<工作树>`，resolver读本处三文件，不做第二份docs镜像。读取父级适用规范；原SID无仓内AGENTS，不创建替代规则。

先建缺少的三PWF，再在本工作树设置两项独立env并解析：

```powershell
$env:PLAN_ID='g5-sid-runtime'
$env:PWF_PLAN_ROOT=(Get-Location).Path
& "$env:USERPROFILE/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1"
```

先读：本卡、`src/company_wiki_adapter{,_cli}.py`、`src/cninfo_api.py/acquisition_budget.py/config.py`；只读 `downloader.py/mapping.py/orgid.py/string_utils.py`；G4 `MAIN_ACCEPTANCE.md`、全部对应 unit/CLI/budget/G4 E2E。

## 2. 已证问题与设计目标

CLI `_build_adapter`构造StockDownloader；adapter仍runtime import downloader和两个过滤helper。StockDownloader本身有失败日志创建，访问 `.mapping`会先访问 `.browser`并initialize；orgID旧requests.post/浏览器fallback也不接ProviderAcquisitionBudget。即使公告/PDF读取已是API，缺orgID/本地cache时仍多余启动浏览器、进行预算外网络。

让 CWP provider 真正只依赖：请求验证→只读本地映射/有界官方身份查询→既有有界公告/文件HTTP。orgID解析、分页和fetch使用同一传入budget，不重置deadline/累计response bytes，不造第二账本。CLI无需Playwright/Chromium可完成 discover/fetch；legacy人工浏览器下载器不在这次改造中。

禁止通过给CWP强制新org_id字段或永久预seed全公司映射来躲问题。CWP SourceRequest不携带org_id，必须覆盖真实无orgID请求。缓存只作为stock_code→org_id线索，不表示原件已验真；官方候选仍核SEC/期间/公开日/完整性。

## 3. 写集和接口冻结

可写：

- `src/company_wiki_adapter.py/company_wiki_adapter_cli.py/cninfo_api.py/acquisition_budget.py`。
- 新 `src/cninfo_identity.py`（只读cache+budgeted orgID解析）、`src/disclosure_matching.py`（必要纯过滤helper）。可以少建一个文件，不建provider registry/服务或重复下载器。
- 精确 tests：`tests/unit/test_company_wiki_adapter{,_cli,_cli_budget}.py`、`test_cninfo_api{,_budget,_fixture_contract}.py`、`test_g4_latest_discovery.py`；`tests/e2e/test_g4_latest_cli_offline.py`仅为当前adapter/身份依赖调整，不删除G4实际反例。
- 新 `tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g5_browserless_provider.py`，`tests/fixtures/g5_provider/`、自己的PWF。

**禁写：**原仓及其中11个tracked owner（README/config_template/main、browser/downloader/logger/mapping/models、official e2e、两downloader测试）、未跟踪名单/scripts；`src/orgid.py`仅参考，不修改旧浏览器调用链；所有真实 config/stock_orgid_mapping、CWP/FF/ET/RF/Dayu/IQS、依赖安装/CI/总PWF。

公开保持：CLI discover/fetch和config/staging参数；success/failure JSON schema1.0、adapter name/version `stockinfo-cninfo/1.3.0`（本卡为内部解耦/预算bugfix，无新wire形状，不另制造版本门）；candidate/receipt/SourceRef字段和exact/latest语义、G4五页完整性。旧 `StockInfoCompanyWikiAdapter(downloader, *, cninfo_client=...)`调用仍可用，允许追加可选identity resolver；不能让bounded调用回到预算外legacy mapping。

推荐内部小接口 `resolve_org_id(stock_code, *, budget=None)`，并由同一Cninfo客户端有界HTTP实现，复用现有stream预算代码。具体class名字可自行选择，交接口/清理表即可。旧downloader只在真正legacy兼容路径按需使用；provider正常runtime不得import它来拿两个string helper，helper等价行为由反例证明。

## 4. 实施细则与 TDD

1. 记基线/owner SHA；列provider所有runtime依赖与外网出口。先新增真实RED：拦截/禁止playwright与src.browser/src.downloader导入时，literal CLI无orgID仍应成功；有cache请求也不应启动浏览器或写失败日志。
2. 拆adapter的轻身份依赖，CLI用纯API runtime；保留旧公共constructor兼容。不改已有config含义、不删用户include/exclude、不把`--headless`当无需browser的证明。
3. orgID顺序：显式有效请求org_id→已有本地cache只读→同budget官方API。cache读取路径规则从实际旧实现核对，支持必要的原 src、cwd、configs兼容，不改变/补写原cache。错证券/多个不同orgID/坏schema不得取首条；身份未确认是身份失败，不能报“最新财报覆盖但空”。
4. 身份HTTP每次流式计量、timeout<=remaining；bytes耗尽/截止不继续公告查询，真实网络失败保留明确代码/重试性/已耗usage。不能使用无budget requests.post/read-all、API失败fallback browser、无限retry或另一个30秒budget。没有budget的兼容调用仍API-only，不恢复浏览器fallback。
5. fetch不需要初始化身份cache/browser/downloader；按真实candidate transport执行既有暂存SHA/PDF流程。CLI cleanup兼容fake/legacyadapter与纯API对象，不因`.downloader`缺失掩盖原始成功/失败。
6. 完工集中测新反例+有关旧责任/G4 E2E；交每步request计数/真实response字节，零外网/模型。除非反例暴露另一已选中责任，别顺手重构legacy下载器、全部types或安装Playwright。

## 5. 独立测试包与真实离线链

新unit：三种orgID路径；cache原bytes/mtime不变；错误SEC/歧义/schema拒绝；身份查询+公告同budget精确总量；首次lookup耗尽budget后公告0调用；异常usage完整传播；过滤helper/constructor/finally兼容。

新E2E用真实 `python -m src.company_wiki_adapter_cli`、loopback ThreadingHTTPServer，HTTP唯一替换为官方host映射到127.0.0.1。需要额外sitecustomize fixture明确拒绝所有非loopback外网，并使browser/downloader导入一发生就失败（不要只mock initialize后声称不需依赖）。请求无org_id、cache为空，server先回复准确SEC/orgID，再实际公告；client累计identity+announcement bytes。cache命中/显式orgID应少一次HTTP。oversize/deadline/错身份无候选、无后续HTTP；fetch实际合成PDF SHA/size/.part清理。

G4旧exact/annual/H1/Q1/Q3/未来/更正/分页矛盾继续绿。跨仓走冻CWP真实JsonCommandAdapter消费JSON并检查错误usage，不mock该CLI返回。明确环境：

```powershell
$env:G4_CWP_REPO='C:/Users/郑曾波/Projects/company-wiki'
$env:G4_CWP_COMMIT='df7d7ba58955e224c1799355f479ad5378ef38a7'
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
```

开发只跑所属反例；完工单轮新unit/E2E+已列adapter/API/budget/G4 E2E，交完整命令。原12个base mypy错误不扩成新门；只修自己新增类型问题。仓无workflow，不称CI绿，不创建日常browser/live矩阵。

短测试root `<工作树>/.planning/test-tmp/g5-runtime`：先建父目录并记absent；真实cache/config/PDF/log/export副本均在owned根，HTTP/child退出后finally只删自己产物、恢复absent。禁止测试写src/stock_orgid_mapping或真实用户下载目录，不删除原owner资料。费用/真实外网0，不做备份恢复演练。

## 6. 输出与 MAIN 接线

唯一 `.planning/g5-sid-runtime/` 提交三PWF、`HANDOFF.md/handoff.json/main_wiring.md/dependency_map.json`。dependency_map是前后依赖与所有HTTP出口/预算/写盘路径说明，不是人工许可。

handoff必需字段：`schema_version=g5-handoff/1`、`package_id=G5-SID-RUNTIME`、`repo/worktree/branch/base_commit/implementation_commit/owned_files/public_contracts/tests/protection/cleanup/main_wiring/remaining/delivery_status`。tests含RED/GREEN、literal命令/exit/耗时/pass/fail/skip、replace_seams、HTTP计数/bytes、external_network_requests=0；partial/unrun如实写。交实际Git tip，不写自指SHA或固定pass门。

字段类型与列表结构见只读 [统一交接格式](g5_handoff.schema.json)。schema不是人工许可或provider请求合同；实际wire不变。不允许以格式检查代替真实无cache HTTP/预算验收。

正常commit，可推自己的codex分支，不合正式执行分支。MAIN后续收完整历史、按当前CWP消费/真实无cache请求再验证，合/推v2-clean-rewrite；继续完成G2-12下载/入库/并发复用。provider解耦绿不能冒充完整ensure链已完成；本包不改变其他两线接口，无须等它们。
