# 三仓 hooks 与 CI 覆盖审计（2026-10-09）

审计者：`ci_hook_coverage_audit`。这是本地只读配置与历史代码审计，并已读取 MAIN 保存的 GitHub REST run/job/check annotations。完整 job log 的 REST 请求返回403，因此没有把annotation还原成完整traceback。下面区分已证实事实、MAIN历史修复定位与仍未得到完整日志的事项。

审计基线：CWP `7073bde5`、RF `79139534`、FF `de09787c`。只写本报告与同目录 `hook_audit.json`；未改代码、配置、原件、Git 状态、原三市场审查包或其它 reviewer 报告，未启动网络、LLM、全套测试。实际读取 CWP 根 `AGENTS.md`；RF/FF 根及所查脚本/工具/测试目录没有被 Git 跟踪的 `AGENTS.md`，上级目录也未发现该文件。生产 source/ET/FMP 配置和凭据未读取。

## 1. 当前实际执行路径

三仓 `git config --show-origin --get core.hooksPath` 都返回 `file:.git/config .githooks`；不能把 `.git/hooks` 是否存在当成 hooks 是否安装的证据。三个 `pre-commit` 包装器实际调用 Miniconda Python 的 `pre_commit hook-impl --config=.pre-commit-config.yaml --hook-type=pre-commit`，找不到 pre-commit 会非零退出。RF 另有已注释说明的 PATHEXT/PATH Windows 工具定位修复。

本机只读版本检查：Python **3.13.9**、ruff **0.15.18**、mypy **1.19.0**。三个 CI 都是 Ubuntu + Python **3.12**；本地 `language: system` 不创建干净依赖环境，也不自行执行 YAML 注释中的版本 pin 安装。

| 仓库 | pre-commit：实际内容与筛选 | 已安装 pre-push | 当前 CI | 已证实空隙 |
|---|---|---|---|---|
| CWP | 暂存且命中路径的 Python 跑 ruff；仅列出的 contract/runtime 模块触发固定 mypy 集；配置路径触发 `config_doctor --structure-only`；tests/src 的 Python 变更触发整根 host guard。没有 pytest。 | `tools/pre_push_gate.py --fast-contracts-only`：固定 **13 个 node ID**，含最新 dependency consistency test。 | 完整 ruff 范围、固定 mypy、compileall、完整 config doctor、**所有 unit**、同一13项冒烟、CLI退役行为、secret scan。只在 master/PR master；纯根 Markdown 与 docs Markdown 被忽略。 | pyproject/requirements/.github/tool-only 变更不会触发相应 commit 语义检查；13项push冒烟不覆盖新budget/adapter/OCR/完整unit。full gate 的 ruff范围还小于CI（少e2e/两个指定fixture），不能把无参数full gate描述成精确全CI。 |
| RF | scripts/tests/tools/e2e 暂存 Python 跑 ruff、host guard；仅 contracts/schema_compatibility/filing_fetch_client/trust_anchor 触发固定 mypy集。没有 pytest。 | 无参数 `tools/pre_push_gate.py`：ruff、固定mypy、**12 个测试文件**。 | 调用**同一个 gate**；先sparse checkout，再安装inline依赖并checkout manifest pins。 | 检查入口/测试集已统一，但本地兄弟仓当前代码与CI固定兄弟仓不同，依赖环境和Python/OS不同。变更到其余forecast/source-clock/provider路径不会自动扩展12文件集。 |
| FF | scripts/tests/tools/e2e 暂存 Python 跑 ruff、host guard；仅 `filing_contracts.py`/`fetch_filing.py` 触发固定mypy。没有 pytest。 | `tools/pre_push_gate.py --skip-install-sync`：ruff、compileall、两个模块import smoke、mypy、重复测试名、host guard、three-repo doctor、plan verifier、BOM；**不跑pytest**（只有手工 `--run-tests` 才跑）。 | 另写inline静态检查，然后独立列 **26 个回归文件**、doctor、plan verifier。当前复杂度只做诊断。 | CI回归清单与push没有共享行为定义；静态/import smoke不能证明provider/transcript/envelope行为。doctor找不到RF sibling会打印SKIP并返回0。FF CI没有调用同一fast gate，host guard/BOM也未作为同一CI步骤执行。 |

证据入口（行号为当前基线）：

- CWP `.pre-commit-config.yaml:12,20,90,110`；`.githooks/pre-push:23`；`tools/pre_push_gate.py:44,52,102,143`；`.github/workflows/ci.yml:3,38,42,45,48,53,68,83,104`。
- RF `.pre-commit-config.yaml:10,18,39`；`.githooks/pre-push:22`；`tools/pre_push_gate.py:73,89,93`；`.github/workflows/quality.yml:14,33,34,41`。
- FF `.pre-commit-config.yaml:10,18,31`；`.githooks/pre-push:19`；`tools/pre_push_gate.py:133,179,219,246,250,262,273,283`；`.github/workflows/quality.yml:15,17,29,35,37,39,64,94,96`。

## 2. 为什么会显示 skipped；merge 检查的边界

本机已安装 pre-commit runner 源码的 `_all_filenames` 已只读核对。普通commit取 `git diff --staged --name-only --diff-filter=ACMRTUXB`，再按hook的 `files`/`types`筛选。三仓没有 `always_run: true`。`pass_filenames: false` 的意思是触发后不传文件名，**不是无条件运行**。

- 仅Markdown/JSON证据提交：通常ruff/mypy/host guard全SKIP；CWP `config/*.json`会触发structure-only doctor，docs JSON不会。
- CWP新 `bounded_http.py`、`adapter_process.py`、`download_budget.py` 命中ruff/host guard，**不在mypy触发白名单**。`pyproject.toml`和`requirements.txt`不命中现有dependency专用hook。
- FF `3945efb4` 改的transcript/transport/envelope模块不命中mypy触发白名单；`afbef653`改`fetch_filing.py`才会触发该mypy集。两者都不会在commit/push执行CI的行为测试。
- 合并状态存在MERGE_MSG/MERGE_HEAD时，framework取MERGE_MSG conflict paths，加 `git diff -m <staged tree> HEAD MERGE_HEAD`的文件集合；仍按上述hook路径筛选。这不是对完整merge-base至最终HEAD的行为影响测试。
- 三仓pre-push不读取Git传入的remote SHA范围，gate没有changed-files/merge-base选择器；固定全静态范围/固定smoke集。CWP/FF CI也固定清单，RF固定共享清单；CWP仅有workflow路径忽略规则，RF的sparse checkout是排除历史档案，不是影响分析。

证据：`C:/Miniconda/Lib/site-packages/pre_commit/commands/run.py` 的 `_all_filenames` 与 `pre_commit/git.py` 的 `get_staged_files/get_conflicted_files/is_in_merge_conflict`；三仓hook源码没有range参数或变更影响分支。未执行framework中的write-tree命令，仅通过inspect读取函数源码。

## 3. 与已知失败SHA对应的确定事实

| SHA | 历史代码/配置已证实 | 为什么pre-commit不会阻止此类问题 | 本次不能单凭代码断言的部分 |
|---|---|---|---|
| CWP `335df5d3`，10-08 19:15 London | run **37822907874**，push/master，同一head SHA；Unit tests exit2，annotation `::tests.unit.test_bounded_http [unknown_error]`。新增 `bounded_http.py` 的 `import httpx`；pyproject新增 `httpx>=0.27,<1`，同SHA requirements未加。`7071e035`（19:23）补requirements、新测试和push smoke。 | static ruff不验证干净安装；新模块不在mypy白名单；包/requirements变更没有专用hook。旧push 12项没有dependency一致性，也没有test_bounded_http。 | 声明漂移及unit collection错误位置已证实；具体import异常无完整日志，不能仅凭漏直接声明就断言HTTPX必然缺失（可能被其它包传递安装）。 |
| CWP `bf8f0e82`，10-08 22:29 London | run **37847182377** 是真实push/master失败，head精确匹配，Unit tests exit1。annotations包含versioned_resume identity/period、select metadata/read_policy、verify metadata drift、current_read language旧断言。HEAD自身只改两份docs，前序 `1a58ad11`改metadata责任，`2e54b5df`更新4个unit文件；历史stat已独立核实。 | 此docs commit静态hook不触发；此前业务变化的行为测试也不在push smoke中。workflow的docs忽略不会证明整个push范围只有docs，更不能否定真实REST run。 | MAIN报告该unit失败共21项；本agent只读API可见annotation（有上限）不复算完整失败数量。不将docs文本当成失败原因。 |
| CWP `a901b67f`，10-09 05:21 London | run **37883563191**，Unit tests exit1。annotations含versioned_resume `[scoped-job_hash]`冻结成员、多个current metadata BatchResumeError、format_pipeline PPTX assertion。前序 `002824df`在空generation仍用 `narrative-run-binding/3`，`d11db2a2`修/2与/3分支及PPTX parser1.1.0断言；历史diff已独立核实。HEAD新增local_ocr config，配置hook仅structure-only。 | push烟测没有versioned_resume或format_pipeline；语法/type/config结构均不能判断frozen execution复用版本和parser版本断言。 | 真实失败不是凭local_ocr新增猜测而来。是否另有OCR配置污染由后续实际测试单独核实，不能替代已知version/hash/parser错误。 |
| FF `3945efb4`，10-08 20:32 London | run **37832787908**，Run focused regression suite once exit1；API没有test node/traceback。改transcript/transport/envelope，旧CI仍含complexity ratchet，push不跑pytest。 | transcript模块无mypy触发，commit/push不执行CI行为或复杂度测试。 | 无完整job log，不能指定该run具体失败node。 |
| FF `afbef653`，10-09 00:53 London | run **37861936346**，Run focused regression suite once exit1；API无具体node。MAIN核实本地历史证据 **419PASS/1FAIL：ff_provider_cause complexity14>10**。CI旧清单未含provider/consumer新测试，仍含complexity ratchet。 | mypy可检查fetch contract体，不能验证失败因果/envelope行为或旧complexity阈值；push无pytest。 | 本地complexity失败已证实，不能在无远端node的情况下声称它就是该run唯一失败。 |

FF `e9b0d08`（10-09 01:21）历史diff已核实：添加provider/consumer两个CI文件，将复杂度阈值改为诊断，并增加diagnostic真实行为测试。旧ratchet要求新文件top-level函数AST计数≤10、fetch_filing≤34，属于维护指标与行为质量混在一个回归清单的历史事实。本报告未改该设计，也不建议通过删核心行为测试取得绿色。

**当前CWP FAST_CASES具体遗漏**：`tests/unit/test_bounded_http.py`、`test_narrative_versioned_resume.py`、`test_narrative_select_handler.py`、`test_narrative_verify_handler.py`、`test_narrative_current_read.py`、`test_narrative_format_pipeline.py`均不在13项清单。新增dependency一致性检查只补声明类，不能替代以上collection与状态/metadata/parser行为测试。历史修复已变更正确行为，遗漏责任测试入口仍然存在。

CWP另一条**已记录的本地push失败**：旧gate把pytest scratch固定在PROJECT_ROOT/tmp并要求路径≤60且diagnostic `relocated=false`。`d7923191`改成owned系统TemporaryDirectory并保留真实child返回值；见同phase6 `pre_push_temp_scope_fix.md`及新3项回归。此问题在pytest前发生，commit静态检查不会预见；它与远端unit失败需要分别按日志归因。

## 4. 依赖、兄弟仓版本与平台

**CWP** CI从 `requirements.txt + requirements-test.txt`安装；包声明是另一份 `pyproject.toml`。当前dependency一致性test仅比较直接项目依赖字符串是否被requirements包含；它不验证extras、import成功、依赖版本兼容或RF/FF的安装入口。

**RF** CI inline安装 `pytest pyyaml requests pymupdf cryptography ruff==0.15.18 mypy==1.19.0`。helper读取本次RF checkout的 `compatibility/current.json`，跳过repo under test，其余checkout到 `current_triplet`。审计时固定兄弟仓为FF `5001dcbef1845a08e90cda6f2a86365610a662af`（10-07 22:41）和CWP `6cd9b6d7ca4faee3348fdd8afcf70bf7e3d6a5fb`（10-08 07:11），与本机最新FF/CWP不同。local gate不会改本机兄弟仓，也不会检查三仓SHA是否等于manifest；local E2E使用sibling工作目录，可由显式code-root覆盖。因此同一个gate源码不等于同一组三仓代码。

**FF** CI先浮动clone RF远端默认分支，再用该clone的manifest/helper checkout CWP；`--skip filing`保留FF under test并建立configured layout软链接。CWP pin本身固定，**提供manifest的RF bootstrap仍浮动**，同一FF SHA稍后重跑可能读到不同manifest。CI仅安装 `pytest pyyaml requests mypy`及随后ruff，没有安装CWP package/requirements，也没有声明所选CWP reader/parser所需依赖的共享subset。本地已安装包可能遮住这个缺口；是否已造成本次run错误必须对日志判定。

RF/FF mypy都只查指定public contract模块；RF与CWP `follow_imports=skip`，FF mypy声明platform linux。FF ruff target-version是py313，CI执行是3.12；compileall是实际3.12语法检查。三个CI均没有Windows矩阵；host guard只检查有限绝对路径字面量、能力API及skip语法，源码docstring明确承认看不到computed paths、错误断言层、pytest.skip背后的语义。Python/OS、权限、进程清理、软链接与OCR可执行文件问题仍要实际平台测试。

证据：CWP `.github/workflows/ci.yml:38`、`tests/unit/test_runtime_dependencies.py:8`；RF `.github/workflows/quality.yml:33`、`tools/ci_checkout_siblings.py:29`、`tests/test_p5_source_default_cli_e2e.py:48`、`mypy.ini:10`；FF `.github/workflows/quality.yml:15`、`pyproject.toml:3,19`；CWP `scripts/host_assumption_guard.py:16`。

## 5. 旁路hooks：证据限定

本次没有找到这些失败SHA对应的 `--no-verify`、SKIP变量或hook改路径执行证据。CWP当次plan Markdown的限定literal搜索只有纠正 `.git/hooks`误读的记录。提交对象/目前hooks配置不能证明历史命令实际执行了哪些hooks；本次也没有读取会话私有环境、shell完整历史或凭据。所以结论是 **旁路未证实**，不能把漏检归罪于人为绕过。三个pre-push包装器都在gate文件缺失时exit0；这是代码中的可见放行条件，本次基线文件均存在，未发现它在这些历史事件中实际触发。

## 6. 轻量且可执行的根本预防方案

以下是拟议方案，本审计未实现：

1. **共享CI责任入口，commit保持static，按实际本机成本决定push范围。** MAIN正常OS完整CWP unit基线 **2299PASS / 128.21秒**，远端unit约37–50秒；这说明不能按远端时长估计本机成本。CWP push拟取真实推送范围，经保守AST传递import选择受影响unit，加既有fast contracts单次pytest；依赖/配置/runner/conftest或关系不明时fallback完整unit，CI继续完整unit。FF先把26文件移进唯一 `tools/ci_tests.py` 定义，`--ci-tests`与CI同runner，push调用这个小suite；远端约42秒，本机实现后测量再决定有无必要影响选择。RF现有共享gate保持。各仓手工full/milestone suite继续独立。
2. **依赖修改当次commit做亚秒级声明一致性检查。** staged `pyproject.toml`、requirements、CI安装声明或依赖profile变更触发无网络tomllib/AST checker；统一以package/runtime extras为声明责任，CI requirements由该声明生成或校验。能在 `335df5d3` 类直接声明漂移进入历史前阻止。CWP现有test可转换成小CLI并供hook/CI共用，不能只放在push smoke。RF/FF声明所需CWP离线reader/test extra，按所checkout pin安装，不手工维护另一份pip命令。
3. **影响选择必须覆盖整个真实推送范围。** staged commit只作syntax/static和指定type集；push读取Git stdin四列ref，对所有非删除ref的remote-old→local-new求并集，包含merge结果、删除/rename两端及配置/依赖。不能取HEAD^，否则末尾docs commit会遮住前序代码变更。zero old SHA、缺object或基线不可求时保守fallback，不能返回空集合。AST静态import关系含relative/from-import与tests/support/conftest传递依赖，改测试本身直接纳入；依赖/配置/runner/conftest变更fallback。结果应覆盖此次失败的bounded_http、versioned_resume、select/verify/current_read、format_pipeline责任单元。

   **诚实局限**：AST无法保证追踪 `importlib`/`runpy`、模块名字符串、subprocess CLI、运行时registry、外仓协议与computed imports。发现改变这些入口、解析歧义或未归类runtime关系时fallback完整unit；即便如此，语义上没有显式import的外部契约仍可能漏选，因此CI保持完整unit，大节点保留跨仓/平台测试。多个ref必须合并，不能只读stdin第一行；本机pytest通常执行当前工作树，未提交WIP不等于被推送SHA的严格证明，结果要记录此环境边界而不增加HEAD许可证。
4. **兄弟仓版本纳入可复查输出与兼容测试。** gate输出repo SHA/Python版本/所选集合即可；不是签收、许可证或commit门。保留当前工作树的快速local smoke；显式大节点在owned temp checkout按manifest组跑跨仓smoke。FF bootstrap改用本repo版本化manifest或稳定的显式manifest来源，防同一SHA重跑浮动。更新manifest时跑合同/版本兼容与required import smoke；不写穿主checkout，不要求HEAD永远等于manifest。
5. **全unit和跨平台仍由CI/大节点负责。** CWP所有unit、完整contract/full integration、Windows/Linux真实文件/进程/OCR执行、网络供应商、真实原件和预算回收留在相应大节点。出现生产配置新增时，相应unit测试必须显式tmp配置，避免默认production配置漂进fixture。依赖/CI/profile修改做一次干净环境安装与import smoke可防本机隐式包；无需每次commit重建环境。不要删核心测试、加人工签收、HEAD许可证或CI完成才能commit的门。

最小实现的可测验收：mock child runner验证push与CI最终选择同一suite、只运行一次；真实或stub pytest exit7原样使gate失败；新增tests/module在共有scope被collection；dependency声明漏项立即非零；deep worktree仍使用owned scratch且清理；共享mode不写生产配置或安装根。影响选择仅在实现后另测跨两个区域的merge推送。静态host guard只承诺语法范围，避免把它包装成跨平台行为证明。

## 7. 证据状态与未闭合的点

- 五个run的head SHA、event与失败step由同目录 `*-runs.json`/`*-jobs.json`证实。CWP两个行为失败已有具体annotation node及MAIN历史修复diff定位，不能降格为docs/config猜测。
- 335df5d3的具体collection traceback、FF两个远端node/traceback仍无完整日志；REST403是信息限制，保留该限定。
- CWP production OCR配置进入测试默认值的其它风险，由MAIN正在运行的本机测试单独定位；本机sandbox子进程错误不自动等于远端CI根因。
- FF本地复杂度14>10与e9b0d08诊断改造已证实，远端唯一失败原因仍未闭合。provider consumer在旧CI清单之外是事实，但不代表这些未列测试本身失败。
- 真实执行命令有无旁路hooks。没有执行证据时保留“未证实”。latest green不能否定这些历史缺口。

原始历史可复查命令均为只读 `git show SHA:path`/`git log -- path`；当前文件SHA-256与结构化结论见 `hook_audit.json`。
