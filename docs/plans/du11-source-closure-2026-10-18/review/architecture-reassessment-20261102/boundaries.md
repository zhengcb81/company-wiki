# 跨仓边界复核：已解耦部分、确定遗漏与并行条件

日期：2026-11-02。独立只读检查 CWP、filing-fetch、revenue-forecast、StockWiki 和 earnings-transcripts 当前代码；先查询 CodeGraph，再读明确文件及字面调用。CodeGraph 部分内容为旧位置，结论以下列当前文件为准。没有产品修改、下载、收费调用、生产配置或原件写入。仅运行一次纯内存反例，未执行完整跨仓 E2E。

**结论：存储位置虚拟化和进程边界已经建立，契约及测试耦合尚未全部消除；可以按稳定接口有界并行，不必等完全零依赖。上一轮 ET/FF 预算改造未覆盖最后 CWP 入库，仍存在确定的正常结果拒绝路径。**

## 1. 已有边界及不能误判的历史代码

- RF 生产入口 `scripts/source_preparation.py:246–299` 通过 pathless SourceRef 打开原文，得到 `VerifiedOriginalRead` 后直接组合研究 source record；历史 tuple 输入才重新按原始输入验真。`scripts/company_wiki_source_v2.py:145–160` 消费该不可变值，不再次读取物理文件。
- RF `scripts/company_wiki_source.py:115` 的 CWP `artifact_dag` 直接 import 确实存在，但生产 `prepare_source` 不调用它所属的历史 artifact 路径。`source_preparation.py:302–308` 明确隔离为旧离线夹具路径。不能据此声称当前主链跨层读取 CWP DAG。
- StockWiki `stockwiki/_source_reader_v2_transport.py:57–85,126–156` 只依赖可配置命令、SourceRef/manifest 和实际进程预算；不读 CWP SQLite 或物理原件目录。公开接收端对实收字节复核属于该进程边界，不是重复内部许可。
- ET 的 `transcript_tool.py`、`transcript_api.py`、`retrieval_runtime.py`、`transcript_artifact.py` 当前检查范围没有 CWP/StockWiki 内部导入。ET负责采集与输出；CWP负责 canonical 入库。
- 正常 `needs_review/uncertain` 未被 RF/StockWiki 一律禁读。RF `scripts/company_wiki_narrative_contracts.py:409–412,452,977–981` 接受并传播不确定性，必要时降标但保内容；StockWiki `stockwiki/_narrative_bundle.py:131,148,352–374` 同样接受。`replay_status=verified` 是来源/locator复验，不是投资结论已确认。

## 2. 确认遗漏：预算到 ET 为止，CWP import 仍二次收窄

生产调用链证据：

1. FF `scripts/transcript_tool_transport.py:691–722` 将请求真实额度送 ET；`:737–749` 按原文字节预算推导编码 pipe 空间。
2. 同文件 `:1000–1018` 将返回结果送 `company_wiki.source_catalog.transcript_import_cli`。import envelope 仅有 `schema_version/source_request/candidate/transcript_result`，不含此次实际预算。
3. CWP `src/company_wiki/source_catalog/transcript_import_cli.py:27,50–53,95–96` 固定入站 `25MiB + 128KiB`、结果 `25MiB`。
4. `src/company_wiki/source_catalog/transcript_import.py:115–120` 向 parser 强制传常量 `MAX_PROVIDER_PAYLOAD_BYTES`。
5. `src/company_wiki/source_catalog/transcript_tool_contract.py:25–26` 定义结果 `25MiB`、原件 `16MiB`；`:127,134` 拦 JSON 大小；`:166–173` 限 base64 24MiB/原文16MiB；`:286–290` 连显式 `max_bytes > 16MiB` 本身也拒；`:306–309` 又把 content_bytes 限在表示常量内。

因此，上轮“FF→ET public CLI→supervised worker”成功不能证明最终入库成功。这个问题是完整测试端点缺失，不能用另一轮仅到 ET 的相同单测代替。

纯内存复现（CWP 根目录，`C:/Miniconda/python.exe -B -X utf8`；无原件写入）：

```python
import sys, base64
sys.path.insert(0, "src")
from company_wiki.source_catalog import transcript_tool_contract as c

original = b"x" * (17 * 1024 * 1024)
payload = {
    "provider_payload_encoding": "base64",
    "provider_payload_base64": base64.b64encode(original).decode("ascii"),
}
for name, call in [
    ("decode_17MiB", lambda: c._decode_original(payload)),
    ("explicit_22MiB_budget_small_original",
     lambda: c._validate_byte_cap(b"ok", 22 * 1024 * 1024)),
]:
    try:
        call()
        print(name, "accepted")
    except Exception as exc:
        print(name, type(exc).__name__, str(exc))
```

实际输出：

```text
decode_17MiB TranscriptToolContractError provider payload is empty or oversized
explicit_22MiB_budget_small_original TranscriptToolContractError invalid provider payload byte cap
```

原文 17,825,792 B、base64 23,767,724 B（小于 24MiB）；第一例直接命中额外原件帽。第二例原文仅 2 B，仍不接受显式更大预算。这是当前可触达拒绝的函数级实证加调用链证明，尚非完整入库端到端实测。

同一请求预算应由采集编排传至最终入库，公开省略值可保默认；不得换成更大的固定帽。整条链验收应覆盖：请求22MiB、合法17MiB原件，经真实 FF→ET CLI/supervisor（假HTTP）→CWP import/writer→verified-open；保存字节/SHA完全相同，再调复用0下载。真实超22MiB、坏SHA/公司/期间反控仍拒。测试仅用自有隔离目录，完成恢复初始状态。

## 3. 仍存在的耦合，不一律等于错误门禁

| 面 | 当前证据 | 意义与最小改善 |
|---|---|---|
| 深层 wire 结构复制 | RF `scripts/company_wiki_narrative_contracts.py:30–58,101–103,509,584–950`；StockWiki `stockwiki/_narrative_bundle.py`、`_narrative_wire.py:19–34` | 多仓手写exact字段/enum，内部reading或诊断结构改变容易要求全仓同步。明确核心字段和可选扩展的兼容策略，提供便携正反例；不笼统接受所有未知核心语义。 |
| 部署命令/配置耦合 | FF `scripts/ff_configuration.py:79–95` 固定 `config/source_catalog.yaml`；`fetch_filing.py:194–222,545–547`；RF `scripts/company_wiki_source_reader_v2.py::_run_reader` 直接 `python -m company_wiki...` | 属连接适配的部署约束，未见主链原件路径泄漏。可在现有配置适配层收敛command/connection，不必创建微服务或共享SDK仓。 |
| 测试越过边界 | RF `tests/e2e_support/isolated_lake.py:245,352–355,382–385` 导入CWP内部配置/策略，后续直接构造artifact表 | 属集成夹具耦合。RF本仓纯测试用冻结public fixture；ROOT跨仓集成使用CWP公开入口或所属仓fixture builder。不能让每次内部表变更迫使下游单测同步修改。 |
| 表示兼容风险 | RF `company_wiki_narrative_contracts.py:70,188–189` artifact ID限128字；当前CWP `narrative_artifact_store.py:289`生成`narrative-UUID`；StockWiki `_source_reader_v2_wire.py:92–111,357–359`质量flag闭集 | 当前没有合法生产者超长ID/新flag被拒的实例。列前向兼容候选，**不是已确认生产故障**。单行receipt也是现行协议约定；不能仅凭严格判断认定违规。 |

底线是消费下层验真的不可变值，跨进程公开原始输入仍按责任层验真；原文完整、质量未知和研究接受分开。不因取消门禁而信任未知核心版本或错误引用。

## 4. 与 ROOT 当前并行方案对齐

不另开竞争施工包。原建议的逻辑责任分工已按 ROOT 当前 `COORDINATION.md` 收敛：

- **ROOT-CWP + ROOT-FF**：同一owner修最终入库预算链及本地codec表示门；CWP继续原T4父链/SEM-QUAL-01。FF/CWP契约变更一起协调，避免分包后互等。
- **RF仓内线**：原R4期间补集/ghost/采用等研究责任，冻结public fixtures开展独立离线测试，不修CWP父链/不扫描物理原件目录。最终实际采用依赖ROOT产出新artifact。
- **AUDIT仓内线**：原R4记录完整性与审查责任；native成功、观察完整、质量通过分开。用fake native输入独立完成，最终绑定ROOT新真实run。
- **StockWiki/ET/invest**：当前不强开新任务。作为相关接口消费者/生产者参与必要组合回归。

各仓一个实现writer，只维护本仓PWF；总控保接口、依赖和组合版本事实记录。交付一份handoff，含commit、问题处置、测试与非作者独审、剩余风险和ROOT一次重放所需引用即可，不新增许可JSON/逐文件签名。接口冻结是稳定输入输出语义，不是人审放行。

已读本目录 `README.md`、`COORDINATION.md`：与本次代码证据一致，ROOT保FF/CWP、RF与AUDIT独立的安排无文件写入重叠。其“两个遗漏族先闭、再来源正确性、再同artifact真实RF采用”保留真实因果依赖。没有发现需要因本边界检查而增加额外门禁或再拆任务的理由。
