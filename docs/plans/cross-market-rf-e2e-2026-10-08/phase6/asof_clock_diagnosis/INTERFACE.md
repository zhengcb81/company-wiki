# Source clock：拟议共用接口，尚未实现

## 1. 资格与真实事件分开

RF 新纯 helper 建议置于 `scripts/contracts/source_clock.py`，由同一 owner 固定命名。逻辑接口：

```python
qualify_source_information(
    *, source_sha256: str, published_date: str | None,
    as_of: date, availability_evidence: dict | None = None,
) -> InformationEligibility

validate_source_events(
    *, eligibility: InformationEligibility,
    original_retrieved_at: str | None,
    current_read_at: str | None,
    capture_date: str | None,
    claim_verified_date: str | None,
) -> None
```

`InformationEligibility` 是验证过程内的 enriched source fact，不是另一份研究 state、任务库或授权凭证。包含 status、basis、available_by、source_sha256。已知 published_date 的来源直接从 exact-version manifest 计算，无须加一份重复签收。source、capture、claim 共用资格结果；claim 验证不再次自行给发表日猜默认值。

资格顺序：

1. SHA、日期格式、proof 绑定不合法，具名拒绝。
2. 已知 publication > as_of：`source_publication_after_asof`，即使有人给了更早 capture/proof 也不能覆盖它。
3. 已知 publication <= as_of：合法历史信息；later original retrieval/current read/current verification 本身不拒绝。
4. publication 未知：只接受 producer 验证过、同 exact SHA 的 prior availability proof，available_by <= as_of；保持 published_date=null。
5. proof 缺失：`source_availability_unknown`；proof 在 as-of 之后：`source_availability_after_asof`；SHA 不同：`source_availability_version_mismatch`。均不作为新下载缺失来隐藏既有原件。

未知资料不能从一次 Oct9 新读取得出 Oct8 已可用。可靠历史证明只提供 availability 的上界，不能把该日期写成精确 publication。

## 2. 可选 prior availability DTO

**当前 public v2 不支持该字段，不能声称现在已可用。** MAIN 需固定 producer/consumer 同一版本扩展；SourceRef v2 identity 不改。拟议 `availability_evidence` 最小字段：

```json
{
  "schema_version": "source-availability-evidence/1",
  "source_sha256": "<exact raw SHA>",
  "available_by": "<verified ISO date>",
  "basis": "prior_verified_capture | primary_archive",
  "evidence_ref": "<existing immutable capture/assertion/archive reference>",
  "locator": "<time and exact-version binding in that existing evidence>"
}
```

这是拟议 DTO，不是可以由 RF 研究者填写一串值就获得历史资格的接口。CWP producer 必须实际打开已有可信 proof，核其 exact raw version、真实时间与来源含义，再通过 public reader/export 返回它。复用已有 immutable capture、source assertion、归档索引/收据；不新建 DB、不新增人工签收或身份许可、不另造一条签名链。旧 archive 需按已有 official local import/storage 层合法登记时，同步保留可靠 proof 事实，不能替造 pub。

不能作为 proof：mtime/文件名年份、collector 名非空但无来源证据的裸 sidecar、call_date、会话当前时间、自报的 as_of_cutoff_verified、旧 URL 配上新 SHA、仅 self-hash 的未验证 JSON。原件 raw capture 是否确实证明公开可用，由上游来源边界判断；RF 不私自拼存储路径。

未扩展 public producer 之前，unknown+proof transport 集成测试应标出接口依赖/NOT_RUN 或拒绝，不将单元 fixture 称作真实来源通过。known publication 的 clock 修复不依赖这项生产扩展。

### 公共传输放置与 strict 字段修改

建议选定协议如下，交 MAIN 一次固定，不让不同 owner 各自发明字段：

- 当前 source read receipt 是 **2.1**，不是 SourceRef 的 2.0。保留 2.1 的原精确字段、manifest 字段和默认 CLI 行为。
- producer 若提供 proof，以显式 `--include-availability-evidence` 输出 **source read receipt 2.2（拟议）**。2.2 仅新增一个顶层 `availability_evidence`，值为上述 DTO 或 null；`manifest.published_date` 仍可为 null，manifest 的字段集合不变，SourceRef v2 不变。此选项是返回事实的格式协商，不是 admission/人工授权。
- RF `company_wiki_source_reader_v2.py:_validate_receipt_shape` 按 schema 精确分支：2.1 必须等于现行 `_RECEIPT_FIELDS`；2.2 必须等于现行集合加 `availability_evidence`。未知版本/额外字段仍拒。不得简单改成接受任意额外 key。
- RF `company_wiki_source_v2.py` 的 receipt shape 同步按同一版本分支。reader 的现行三元返回 `(body, bare_receipt, manifest)` 保持；2.2 proof 放在 bare_receipt 内，传给 builder，再在 SourceRecord 的可选 `availability_evidence` 中只保留同一已验证事实。source_trace 保留 receipt，不另生签收。两处 `_MANIFEST_FIELDS` **无需添加** proof 字段。
- RF current 2.1 known-publication 路径正常工作；unknown + 2.1 缺 proof 返回具名 gap。RF 仅在 MAIN 已声明 producer 支持 2.2 后请求 flag，不靠模型名、目录、try/error 猜能力。旧消费者继续请求 2.1。unsupported producer 不转成新下载/付费 fallback。
- 2.2 proof SHA 必须同时等于 receipt、manifest、SourceRef、当前 buffer SHA；`available_by` 格式与 basis/ref/locator 精确校验；pub>asof 永远优先拒绝。对未知 publication，只验裸 DTO 结构不构成可靠证明；上游实际 proof 解析是 producer 责任，RF 消费这个受版本约束的 public transport。

### CWP producer 的文件/符号依赖（仅 MAIN 或单一 CWP owner）

建议新 `source_catalog/source_availability.py:verified_availability_evidence(catalog, ref)` 负责从已有 immutable capture/source assertion/archive proof 取得可证明事实，实际校验既有 evidence 与 exact raw SHA，再返回上述 DTO/null。它不建 DB、不重扫全库、不自动修退休身份。MAIN 决定 legacy facts/eligibility owner 是否复用此模块，避免两个 proof resolver。

唯一接线文件 `source_catalog/source_reader_cli.py:main`：在既有 raw verification 后、stdout 写入前解析选定 availability facts，再按显式请求形成 2.2 receipt；CLI 已有 query_ref/open_version/describe_version，继续使用公共 SourceVersionReader。路径定位留 producer 存储层。协议常量 `SOURCE_READ_RECEIPT_SCHEMA_VERSION` 当前在 `source_reader.py:47`；**不要为了本包自行改其默认值或抢写 source_reader.py**。可在新模块定义 2.2 扩展常量，default2.1保持；若必须动 SourceVersionReader/qualification，MAIN 与即将启动 legacy intake/facts/eligibility owner 串行整合。

需要一次取得原件与当前 exact-version manifest 时可直接调用已有 `SourceVersionReader.open_described_version(ref, purpose=...)`（source_reader.py:468），不为每个 proof/claim 再打开同一原件，也不需要给该 class 加另一套读取接口。

known publication 复用当前 `qualification.qualify_source` 的精确 cutoff 语义；增加 unknown proof 能力时在该公共资格边界统一计算，再导出给 selection/consumer，不以 capture_ready 替代历史资格。RF standalone engine 不直接 import CWP 私有 DB 层；它只在 source contract 验证收到的 source fact/qualification 和现有引用一致，并用同一日期规则保证未来拒绝。新增 producer tests 对 current qualify_source 和 RF helper 做相同 cutoff 矩阵，避免漂移。

## 3. 事件约束与具名冲突

新 RF SourceRecord 的 capture/accessed_date 使用此次真实 verified read 日期，host_receipt.timestamp 使用真实 read_at。原始 manifest.retrieved_at 保留原值/null；`company_wiki_trace` 保留旧原件采集和本次 read 的区分。新 claim 的 verified_date 使用实际验证日期；fresh narrative 自动 claim 从本次 context 的实际 read/check 事件得到，不再传 as_of。

仍验证日期格式、UTC/full timestamp 的现行要求、capture receipt/host receipt/excerpt/raw SHA、source identity/period、current read/capture 同次事件关系。当前 read 早于已知 public availability、current capture 与 read 日期不一致、claim verification 早于它绑定的 capture，返回 `source_clock_conflict`，附 conflicting field 名和真实值，不写回修补时间。旧 claim 若绑定旧真实 capture，不因后来再读发生较晚而重写 claim 或旧 receipt。

original public capture 与 publication 的矛盾应具名，不能默默把 capture 当 publication。原始采集本身若只是 private/local possession，不自动充当 publicly available proof。known publication 路径不把 later original capture 当冲突。

日期级 as-of 按既有 ISO date 语义；actual read_at 保持 UTC，不用机器时区截取带 offset 时间造成一天误差。不向 frozen deterministic validator 注入当前墙钟作为 as_of 替代。

## 4. Engine 和旧产物

当前 forecast schema 3.7/opt-in 3.8，capture/host receipt 1.0，RF skill 4.1.0。known-publication 修复不加 source identity、人工许可或重复 proof。新语义需记录 engine/validator 的正式版本及 CHANGELOG；按 `schema_compatibility.py` 的 documented emit matrix 处理旧 output/snapshot，不能只改当前常量导致旧合法 emit pair 被遗漏。

旧 frozen input、capture、claim、snapshot_id/result_sha256 保持原字节。需要旧 pinned runtime 的 snapshots 继续用它；不以今天的 read_at 迁移历史 receipt，不把旧记录的 verified_date 追改成今天。新 fresh 输出以新 engine 执行。若 unknown publication 的可选 extension 进入 formal source contract，明确该 extension 的版本和 legacy reader 行为，不能用 nullable pub 偷偷改变旧 runtime 的含义。

原有准确率/backtest actual availability 和 future source leak 检查保留。晚研究时间只允许复查旧信息，不允许把后来实际收入提前写入历史预测。
