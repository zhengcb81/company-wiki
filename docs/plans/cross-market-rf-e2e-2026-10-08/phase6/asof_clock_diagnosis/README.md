# 历史信息日与实际研究时间：只读共因诊断

状态：**DIAGNOSED / IMPLEMENTATION NOT RUN**。信息日保持 `2026-10-08`。本目录只保存诊断、接口和可施工卡；没有改 RF/CWP 代码、原件、生产配置或主 PWF，也没有重跑 71 项、OCR、下载或模型。

## 已证实的失败

`phase6/full_replay_979792e0.json`：71 项，144.37 秒，整体 FAIL，external_model_calls=0，project_llm_cost_usd=0，临时根已恢复为不存在。

| case | 原件 byte replay | RF→FF reuse | 对应命令 | 秒 / exit |
| --- | --- | --- | --- | --- |
| CN-688012 | PASS | BLOCKED | 1 | 3.202 / 3 |
| HK-00700 | PASS | BLOCKED | 12 | 2.845 / 3 |
| US-MSFT | PASS | BLOCKED | 17 | 2.745 / 3 |

三次 stderr 同为 `source capture is outside as_of_date`，77 bytes，SHA256 `be4a2166751c6f030b5d6d5528d1cd73eb53f1cd67bbb682d86f717c8166a5a8`。详见 `fixed71_evidence.json`，保留原 report SHA、SourceRef 和命令证据；不是新执行成功。

该 report 的 spec SHA 与当前 `benchmarks/cross_market_rf/cases.json` 完全相同。harness 登记侧使用 source.metadata，再对 published_date 做 setdefault：三份实际输入发表日为 CN 2026-03-31、HK 2026-04-09、US 2025-07-30；三份 original retrieved_at 都未知。HK case 外层旧 published_date=Oct8 不覆盖 metadata 的 Apr9，不能把外层旧值写回真实 source。这里只核这三个固定输入，不重扫来源库。

## 共因 RC-ASOF-CLOCK-01

RF 把 information availability 的截止日同时用作当前读取、当前 capture、当前 claim 验证的上限。旧公开文件在 Oct9 真实再读，研究仍只使用 Oct8 前公开的信息，却因再读发生于 Oct9 被拒绝。

实际链：`source_preparation._prepare_source_ref_v2` → `company_wiki_source_reader_v2.open_source_version_v2` → `company_wiki_source_v2.build_revenue_source_record_from_verified_read` → `contracts.document.validate_sources` → `contracts.evidence.validate_source_capture` → `contracts.document.validate_evidence_claims`。

最先观察到的错误来自 `company_wiki_source_v2.py:302`：原始 `manifest.retrieved_at` 未知时正确保留 null，并用真实 `read_receipt.read_at` 作为本次 capture 时间；随后错误要求这个时间 `<= as_of`。精确报错由该函数产生。原始 raw read receipt 没有被这份失败 report 导出，不能声称报告直接记录了完整 read_at；当前 reader 的真实时间生成和错误分支、harness 的固定 request 共同解释这次跨日失效。

其余重复门：

| 责任文件 | 当前条件 | 影响 |
| --- | --- | --- |
| RF `company_wiki_source_reader_v2.py:209` | published <= original retrieved <= as_of | 原件首次于 Oct9 合法下载也会被拒 |
| RF `company_wiki_source_v2.py:176` | 同上 | 第二份 manifest 日期门 |
| RF `company_wiki_source_v2.py:302` | published <= capture <= as_of | 三市场本次 exact stderr |
| RF `contracts/evidence.py:385` | published <= captured <= as_of | 只改 adapter，formal engine 仍拒 |
| RF `contracts/document.py:622` | published <= verified_date <= as_of | 只改 capture，新研究仍拒 |
| RF legacy `company_wiki_source.py:426` | published <= captured <= as_of | 显式 legacy 路径同样有问题 |

另一个同因错误：`source_narrative_context._claim:48` 在实际 narrative read 后直接生成 `verified_date=as_of`；`:97` 传入 input 的 as_of。这会把新验证写成旧日期，必须同包修复。`research/input_evidence._bind_narrative_span:288` 用实际 read_at 生成 current capture，却被 formal 日期门阻断。普通 input template 的 placeholder 不是实际 capture 证据，不能直接拿它宣布 fresh 验证。

## 四个时间的责任

| 字段/事实 | 含义 | 与历史 as-of 的关系 |
| --- | --- | --- |
| published_date / 可靠 prior availability proof | 这份具体原件何时已公开或已可靠可用 | 必须能证明 <= as_of；未来发表仍拒绝 |
| manifest.retrieved_at | 原版本实际采集观察；未知保持 null | 保留真实值；不能因晚于 as_of 就否定已公开旧资料 |
| read_receipt.read_at / 新 capture / accessed_date | 本次真实打开并校验原件的时间 | 可晚于 as_of；不得 backdate |
| claim.verified_date / 实际研究时间 | 本次实际检查引用、生成新研究的时间 | 可晚于 as_of；不得自动写成 as_of |

raw SHA 改变意味着另一版本：旧 SHA 的 publication/availability proof 不能沿用。当前 read hash 验证、source/claim/capture receipt 链仍保留。未来 actual 的 source publication > as_of 仍拒；本次研究日期较晚不授予读取未来事实的资格。

## 当前表达能力与最小责任

CWP `SourceVersionReader` 已有 pathless SourceRef、具体版本 manifest、真实 UTC read_at。`qualification.qualify_source` 已按 published_date 判断历史资格，没有 retrieved<=as_of 的规则。先由**同一 RF owner**在一个纯 source clock helper 汇总资格与事件顺序，再接 source preparation、capture、claim、narrative builder，避免每市场补一个 if。

已知发表日的跨日修正可使用现有字段，SourceRef v2 和 capture 1.0 的字节格式不需要改变。未知发表日目前不能通过原 public v2 表达可靠 prior availability proof：RF manifest/receipt 有封闭字段集合，engine 的 source、claim、narrative binder 都要求非空 published_date。不能拿裸 retrieved_at、文件 mtime、call_date 或今天 read_at 冒充历史可用性。

若实现 unknown+proof 路径，需要 MAIN 固定一份最小可选 pathless proof DTO，由 CWP 公共 producer 复用已有 immutable capture/metadata assertion/archive 证据，绑定 exact SHA；RF 只消费已验证 DTO。没有 producer proof 的资料继续具名 availability gap，不为了源数齐全造日期。细节见 `INTERFACE.md` 与 `W01_source_clock.md`。

## 保留的独立问题

HK 旧 input 同段正反 role 的 formal FAIL 与此无关；US 无 OCR 的纯图片 PPTX fixture PARSER_INCOMPLETE 与此无关。修时钟不改变这两项结果。现有 backtesting 的 actual 信息日、历史准确率记录可用日也不能因“研究日期可较晚”一起放宽。

旧 source-clock PWF 曾通过让 fixture capture 和 as-of 在同一固定日期修测试；那不能覆盖真实 next-day 再分析。本次方案保留当年的原件真实性与未来发表拒绝，增加跨日反例，详见 `diagnosis.json` 的已有计划引用。

交接：`W01_source_clock.md` 是具体施工卡；`tdd_plan.json` 全部新增用例标记 NOT_RUN；新 owner 在隔离 worktree 先 RED 后实现。本目录诊断时 CWP HEAD=a40eb065，RF HEAD=e688b0a2，不能冻结未来施工或 fresh 执行的最终 HEAD。
