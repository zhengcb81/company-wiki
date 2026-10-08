# ET-DEADLINE：电话会议采集硬截止时间收口

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> 状态：**ready，可现在交给另一独立harness**。这是ET-S3合入后的实际资源限制缺口，不重复provider/翻译flag/电话会协议开发。可与CWP G1并行，交付由MAIN在第二优先S3联调时合入。

## 1. 独占目录与固定基线

- 仓库：`C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts`；已合主线 `93fe52c`。
- 唯一worktree：`C:\Users\郑曾波\Projects\earnings-transcripts-s3-deadline`；新分支 `codex/et-s3-deadline`，从`93fe52c`建立。
- 局部PWF：`.planning/s3-et-deadline-20261004/{task_plan,findings,progress}.md`。已有ET-S3卡/handoff是已交付历史，不能按其中Not Started重复施工。
- 原ET owner目录的 `.workbuddy-ai/`、`eval_results.json` 不复制、不清理。CWP/FF/RF/StockWiki/IQS/Dayu/Dropbox及全局技能全部只读。
- 若目标目录/分支已有不明工作，先核身份/status，不reset。正常用户上下文操作本线Git，不改全局设置，不自行并main。

## 2. 已验证的缺口

`transcript_api.py` 的同步`Session.get`/`iter_content`只在阻塞返回后检查deadline；`scraper.py::_request_timeout`还将剩余秒数抬到至少1秒。已有慢流测试只断言最终拒绝/close，不证明及时终止。

零网络复现：预算0.02秒，fake get阻塞0.25秒，实际0.250秒后才报`batch_deadline`。因此不能将当前实现宣称为硬总截止时间。

另外显式翻译未接批次预算，而README称`--max-seconds`是全批总时长。本项目默认不翻译；本包修正范围声明，不扩建翻译预算系统。

## 3. 交付责任与不变接口

- 硬截止保证**正式 `transcript_tool.py` 与 `scraper.py` 的provider采集**，包括fetch/discover/fetch-candidate/list。批次共享同一采集deadline，不按文档复位。
- 外部请求仍 `earnings-transcript-request/1`，原result `/1`、`/2`、精确FY/Q、原语言、payload/hash/size和全部serializer goldens保持不变。FF命令仍 `--request-stdin --include-source-payload`。
- 纯Python API/custom session注入可保留合作式检查；不要把它的阻塞回调测试当成正式CLI硬保证，也不要跨进程pickle lambda/session对象。
- 默认翻译构造/请求为0；显式`--translate`是独立旧功能，`--max-seconds`只约束采集，help/README不声称翻译也受该硬限额。ET工具协议路径始终不翻译。
- 不增加provider、授权文件、公开协议字段、跨仓数据库或生产host测试开关。

## 4. 精确写集

```text
scraper.py
transcript_tool.py
retrieval_runtime.py                 # 新内部supervisor
retrieval_worker.py                  # 新内部HTTP执行worker
retrieval_budget.py                  # 仅在抽出已有预算类确有必要时新增
tests/test_retrieval_runtime.py      # 新增
tests/test_retrieval_cli_e2e.py       # 新增
tests/test_batch_runtime.py          # 只改受影响行为/旧seam
README.md
.planning/s3-et-deadline-20261004/**
docs/implementation/s3-et-deadline-handoff.md
```

`transcript_api.py`仅允许抽出已有内部共用入口所需的无语义重排；优先保持不动。现有CLI相关测试如需调整fake transport seam，仅限受影响测试并逐文件列于交接。不改已发布golden字节、不写key/config、原件目录、CWP/FF或其他owner代码。

## 5. 最小实现方案

1. 每次provider retrieval由一个ET内部子进程执行。worker只做现有HTTP/解析/serializer和有限临时结果，不保存正式原件、不翻译、不生成后代进程。复用当前API，不再复制一套HTTP实现。
2. parent supervisor接收内部operation、现有request/options、provider非敏感设置及**剩余float秒数/请求数/字节数**；返回现有wire result + 内部usage。内部usage不出现在公共stdout，不改变请求/响应版本。
3. 唯一自建临时目录包含有限请求文件和原子结果文件，stdout/stderr指向DEVNULL，避免大pipe/后台reader线程/部分消息写入阻塞。真实key只沿已有受控进程环境/凭证加载方式使用，不写请求/结果/日志/交接文件；不要序列化含key的ProviderSettings对象。
4. deadline从正式操作开始，用monotonic计时；parent等待使用**同一个剩余deadline**，不得四舍五入到1秒，不得每份文件重新给整批额度。硬保证是worker采集在deadline+统一清理宽限内停止；parent本地读取/JSON验证有大小上限且验证后检查总时间，已过deadline不接受fetched。本地返回开销单独说明/实测，不冒称`Popen.wait`能抢占parent解析，也不为此新建解析进程。
5. 超时terminate，必要时kill；只回收自己创建并仍归属本次的进程。清理宽限采用一个固定有限总值（例如1秒），多次wait不能各获得一份新宽限。只有确认退出后才删除该进程临时结果；清理异常具名报告，不能假装已回收。
6. 成功退出后parent复核结果文件大小/JSON/请求标识/现有wire形状及usage。输入、子结果写入和parent读取都有限；JSON膨胀上限根据当前serializer最坏转义/编码推导，不能猜一个会误拒合法最大payload的值。超额/缺结果/坏JSON/坏退出均不是fetched。
7. worker被kill而无法确定usage时标未知并停止该批，不能宣称0消耗或再次恢复完整预算。原件仍由parent原有`_store_original`保存；第一份成功原件和预置keep不回滚，失败文档无正式原件/part。
8. 工具与批次入口都必须接同一supervisor；不能只给batch套timeout而让正式FF工具继续同步阻塞。list metadata同样受限，dry-run、disabled provider、缺key仍零外发。

Python线程取消、仅改requests timeout、阻塞返回后再查表都不足以证明硬deadline。无需泛化成任务服务或多agent调度；一个内部父子执行边界足够。

## 6. TDD与一个集中节点

先RED，再按上面方案实现：

- fake worker的get永久阻塞；真实parent在deadline+统一清理宽限内返回且worker退出。
- 首块完成、下一块永久阻塞；连接随worker退出，临时文件清完。
- 两份正式batch：第一份成功、第二份阻塞；第二份只有剩余额度，第一份与keep不变，第二份没有原件。
- 零额度/disabled provider/缺key零外发；402/429/错误响应保留现有具名状态。
- 假FMP200走真实CLI dispatch→supervisor→worker→现有API→serializer，原语言/hash/size正确。不能mock整个fetch为成功。
- child坏退出/缺结果/坏JSON/超大结果不能成功，不泄露key/body；默认translator构造和翻译调用为0。

私有测试launcher seam在child安装fake session，不加生产CLI/环境变量host后门。elapsed断言使用明确阻塞marker、合理平台启动余量和统一清理宽限；不要用0.02秒这种演示预算当CI临界断言。生产预算仍包含启动耗时，测试不能悄悄等marker后才开始给预算。普通测试不访问真实API。

一次集中运行：

```powershell
python -m pytest tests/test_transcript_api.py tests/test_batch_runtime.py tests/test_translation_controls.py tests/test_retrieval_runtime.py tests/test_retrieval_cli_e2e.py -q
python tests/generate_transcript_goldens.py --check
git diff --check
```

沿用仓库现有lint/轻量CI，不恢复覆盖率数字门。红灯只重跑受影响责任包。独立测试根同账号创建/运行/finally恢复，本次生成资料/日志/part退出删除，原先keep保留；生产ET/CWP原件与配置无变化。

## 7. 交接给MAIN

`docs/implementation/s3-et-deadline-handoff.md`至少写base/head/branch、修改文件、两正式入口路由、保证范围和宽限、wall-clock/worker退出测试、usage未知语义、golden无变化、临时根恢复、未覆盖事项。更新本线PWF，commit/push自己分支；不自行并main/安装全局技能。

MAIN接收后一次FF→ET→CWP受影响离线接口联调并合入。真实电话会取数由[ET-LIVE](et_transcript_live_import_acceptance.md)承担，最多一次；本施工包零真实paid/LLM请求，不重复live验证。

完成标准是正式两个入口兑现采集deadline、超时资源回收、原件不丢和协议不变。不是增加一个仅由测试调用的supervisor，也不是错误最终出现就称总时限已生效。
