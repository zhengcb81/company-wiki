# RF 本地读取观察消费端：独立复核通过

**PASS_RF_LOCAL_OBSERVATION_CONSUMER_ONLY**。绑定产品 **`dedebe0be27bad0723e6a642be5083bf53b357fc`**；唯一 runtime 为 `scripts/filing_upstream_cause.py`，物理 SHA **`1cefb1e79ffc4b024619ca957013aeca4c117060630ae015a1ee6679654f5c08`**。此处是与 FF136 同一个独立大节点的消费端复核，不是新的许可或签收门。

## 结果

**16 个新独立场景，16P/0F/0S，3.12s；Ruff 与现有公共13模块 mypy 通过。没有新产品缺陷或未解决项。** 六个产品代码/测试/fixture/runner/baseline 文件测试前后物理 SHA 不变，各自与冻结 Git LF blob 绑定；作者文档 HEAD `32f013a9`，工区 clean。没有因文档 HEAD 改变重复跑产品测试，也没把作者201P/1skip计入独立数量。

| 检查 | 结果 |
|---|---|
| 实际 RF client/source_preparation ×小/大输入 | 4 个真实子进程回放本轮独审 FF136 **真实 CLI 已输出的合成 envelope**；不 import FF runtime、不运行真实供应商。大 FF原 stdout123,177B，RF client stderr82,588B、prep stderr82,570B，均超过旧64KiB窗口且完整保留 |
| sidecar/原错误事实 | 整体 sidecar canonical SHA 与输入一致；实际 local producer exit0/7 和 FF replay exit2、RF client exit2/prep exit3分开；safe cause、calls3/downloads0、company_ir未执行状态保留 |
| UNKNOWN和解耦 | provider_started/usage_complete 的 null 保持，local_io_usage保持null；unknown owner status/code/字段、URN schema、file:missing保真，512候选这一机器值不在RF再次做 owner预算范围判断；副本不与输入共享嵌套可变数据 |
| 旧界限与兼容 | 无optional的旧failure、正常GAP不需要新proof；即使有大optional，原base16KiB仍有效；optional精确131,072B接受，+1B拒绝完整sidecar、独立safe cause仍可提取 |
| malformed/扩展窗口 | 小坏版本/显式file:/地址不能冒充完整sidecar，但原safe cause/exit/计数仍保留。原64KiB小错误语义保持；超过旧窗口只有完整合法扩展可使用1MiB UTF-8 raw allowance，坏large、重复键、截断、raw超限和任意巨大wrapper均拒绝 |

这些检查只校验版本/type/有界/pathless wire，不复制 FF/CWP 的 owner 预算、业务状态枚举、来源身份、原文hash或期间资格判断；没有新增重试、计费或下载语义。安全 cause 与完整 sidecar 分开验证；不把坏 optional 提升成合法完整结果，也不将 UNKNOWN改成0。

## 命令与隔离

- 从冻结 RF树导入，用本审查独占 pytest.ini/conftest；实际 child 内用自有 sitecustomize 禁socket，禁dotenv并移除真实provider key。CLI 的 FFroot 指向隔离 replay stub，不是生产安装。
- `python -B -X utf8 -m pytest -c <本目录>/pytest.ini <本目录>/test_consumer_independent.py --basetemp=<母仓>/.planning/rforv --junitxml=<本目录>/final.xml -v --tb=short`。
- Ruff 检查唯一 runtime、作者测试/现有smoke runner、两份独审文件通过；mypy沿用现13模块公开范围（原12+新cause helper），没有撤掉检查或添加CI job/人工门。
- 0外部API、0供应商/LLM、0费用、0下载，未读真实key或生产原件。自有 `.planning/rforv` 初始不存在，四个CLI fixture先恢复 keep marker，再核绝对路径清理含mypy cache的191文件/10,566,636B，最终恢复不存在；不清理作者目录。
- CodeGraph未在作者只读工区初始化，本审查没有建索引；使用冻结diff和精确文件。逐文件 SHA、实际CLI stderr字节/exit/完整sidecar SHA、命令、XML与清理收据见同名JSON/目录。

## ROOT 后续

FF136路径卫生修复与 RFdedebe 消费端现在均为工程范围通过。ROOT可合入 CWP预算观察owner，再做一次实际 CWP→FF→RF 离线联调，并按既定consumer先发布/安装顺序处理；RF本次只需定点同步该唯一 runtime。

本报告不代签实际CWP计量/部分操作持久化、真实供应商/W07摘要内容或费用、RF业务数据/实际参数公式消费、主线push/CI/安装。这些由ROOT后续节点负责，没有把本次错误观察留证当成研究流程已完成。
