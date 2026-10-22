# FF 本地读取观察：独立复核通过

**PASS_FF_LOCAL_OBSERVATION_ONLY**。最终产品绑定 **`136ab5a627083f173c60fc88b7b3f74879a4bf99`**，由 `6dbb9e84` 经作者修复 `a30024e5`、`136ab5a6` 得到。非作者没有修改作者源码、测试、索引、分支或配置，也没有提交、合并、推送或安装。

## 结果

**18 个新独立场景，18P/0F/0S，2.21s；Ruff 10 文件与现有公共 mypy 两入口通过。** 九个产品源码/测试/CI runner/精确测试 baseline 的物理字节与 Git LF blob 分别绑定，测试前后字节相同。后续交接文档 HEAD 不当作未测源码；最终文档观察另有收据。

| 检查 | 实际证据 |
|---|---|
| 正式 FF CLI、小响应/producer exit0 | 真子进程调用生产 `fetch_filing.main` 和 JSON 序列化；仅把上游三种命令路由到真实有界合成 JSON 子进程。FF exit2，cause、原操作、实际 limits 保真 |
| 正式 FF CLI、大响应/producer exit7 | **123,177 bytes** 完整 stdout，950 条 diagnostic 不丢；真实非零业务 JSON 没被改成 transport failure；producer_exit7 保留 |
| 无新下载、计费或重试 | 两个实际 CLI 都只有 `identity → query → local` 三次调用、downloads0；provider 路由一旦出现即失败。已请求 company_ir 电话会仍 `not_run`，没有启动/计量伪造 |
| owner 计量与抽象 | 旧 metadata 操作、`local-read-budget/1`、已计入134,217,720与观察到134,217,729字节、null trigger 原样保留；`local_io_usage:null`，没有从 provider0 推成 local0 |
| 精确大小与结构 | 131,072B compact UTF-8 接受，+1B 整体丢弃 optional，既有六字段 safe cause 保留；depth>8、list>1024、dict>32、非有限数、bool 冒充 limit、raw/header 与物理字段拒绝 |
| 解耦兼容 | unknown owner schema/field、`urn:owner:budget/2`、`file:missing` 保真；深复制隔离；不新增 owner 业务枚举、身份、许可、来源 SHA、重试或费用语义 |

共享的旧 identity/query/wiki 构造器仅用于准备合成夹具，18 个场景和断言由本审查独立编写，不把作者139P或其32P算作独立数量。此处真实的是 **FF CLI/有界子进程边界**，不是声称扫描真实资料湖或执行了实际 CWP 预算计量。

## 发现与根因修复

**FF-OBS-INDEP-01，已解决。** 初版 nested `schema_version` 的 token grammar 允许 colon/slash，而 shared physical guard 只检查字段名。因此 `C:/Users/example/raw.pdf`、`file:///C:/Users/example/raw.pdf` 被放进承诺 pathless 的 optional observation。初轮 **15P/2F/2.92s**，不是 fixture setup 错误。

作者保留原 opaque token grammar，另拒显式地址前缀；第一补丁 `a30024e5` 使原17例和 opaque 正控通过，但标准单斜杠绝对 `file:/C:/...` URI 仍漏。同一地址根因的补充为 **17P/1F/3.06s**。最终 `136ab5a6` 同一规则明确覆盖 drive:/、file:/、scheme://，大小写不敏感，18例一次全绿。没有把修复扩成业务 schema 白名单或新的权限链。

原始 RED、URI 补充 RED、最终 GREEN 与初始/最终测试快照均保留。曾有一次前置 inline 探针漏了测试支持 import path，在执行验证前报 ModuleNotFoundError；它未计为行为 RED，正式隔离 pytest 已合法复现。

## 静态、baseline 与清理

- 使用自有 pytest.ini/conftest，显式源码 import 路径，禁 dotenv、删进程内真实 provider key、禁 socket；受控子进程没有 provider/真实来源扫描路由。0 外部 API、0 LLM、0 供应商费用、0 下载，未读真实 key、未接触生产原件。
- mypy 仍是原有 `scripts/filing_contracts.py scripts/fetch_filing.py` 两入口，递归检查新 runtime 依赖；无撤检查。新快测仅加入既有 CI_TESTS 一次，不加 CI job/门。配置与 hook 文件没改。
- 作者 host guard 误报两个刻意恶意路径测试字符串，现有 baseline 仅加两条精确“文件+字符串”项并说明不用于真实 Path/I/O、跨平台都应拒绝；本审查查过该精确 diff，无通配豁免、无 guard 逻辑变更。
- 独占 `.planning/fforv` 初始不存在；两个 CLI fixture 清理时恢复原有 keep marker；最终短 TEMP 与其中 mypy cache共223文件/11,204,185B已核绝对路径删除并恢复不存在。没有清理作者目录或任何真实原文。
- 作者只读工区 CodeGraph 未初始化，本审查没有建索引，用冻结 diff、精确文件和真实测试；最终逐文件 SHA、命令、exit、XML、CLI 观察与证据 SHA 在同名 JSON/目录。

## ROOT 下一步及未代签边界

可将该冻结 FF 修复与 ROOT 的 CWP owner 预算观察、RF 可选观察兼容整合，再做一次真实离线 CWP→FF→RF 联调。尤其 RF 原完整 sidecar16KiB/错误 decode64KiB不能继续吞掉合法大观察。

安装需一起同步交接中的 **五个 runtime 文件**，包括新 `scripts/ff_local_preparation_observation.py`，不能只更新入口。原 FF2.0、CWP local-source-prepare/1、safe cause/exit/retry 语义保持。此报告不代签 CWP 实际计量/部分操作持久化、RF 消费、真实 H1/供应商运行、主线发布或安装。ROOT 持有这些后续步骤；本审查没有新建许可、任务库或收费账。
